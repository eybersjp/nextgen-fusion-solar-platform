"""Database management for the Design Service.

Provides SQLAlchemy session management, connection pooling,
health checks, and database utilities.
"""

import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, Optional

import asyncpg
from sqlalchemy import (
    create_engine, text, event, pool, MetaData,
    inspect, Table, Column, Integer, String, DateTime
)
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.engine import Engine
from alembic import command
from alembic.config import Config

from .config import get_settings
from .logging import get_logger


logger = get_logger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Global engine and session factory
_engine: Optional[Engine] = None
_async_engine = None
_session_factory: Optional[sessionmaker] = None
_async_session_factory = None


def get_database_url(async_mode: bool = False) -> str:
    """Get database URL for sync or async connections."""
    settings = get_settings()
    
    if async_mode:
        return settings.DATABASE_ASYNC_URL
    else:
        return settings.DATABASE_URL


def create_database_engine(
    database_url: str = None,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600
) -> Engine:
    """Create SQLAlchemy engine with connection pooling."""
    settings = get_settings()
    
    if not database_url:
        database_url = get_database_url()
    
    # Set connect_args based on database type
    connect_args = {}
    if "postgresql" in database_url:
        connect_args = {
            "connect_timeout": 10,
            "application_name": "design_service"
        }
    elif "sqlite" in database_url:
        connect_args = {
            "check_same_thread": False
        }
    
    engine = create_engine(
        database_url,
        echo=echo or settings.DATABASE_ECHO,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,  # Validate connections before use
        connect_args=connect_args
    )
    
    # Add event listeners
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance."""
        if "sqlite" in database_url:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_connection, connection_record, connection_proxy):
        """Log connection checkout."""
        logger.debug("Database connection checked out")
    
    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_connection, connection_record):
        """Log connection checkin."""
        logger.debug("Database connection checked in")
    
    return engine


def create_async_database_engine(
    database_url: str = None,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600
):
    """Create async SQLAlchemy engine."""
    settings = get_settings()
    
    if not database_url:
        database_url = get_database_url(async_mode=True)
    
    # For SQLite async, we don't use connection pooling
    if "sqlite" in database_url:
        engine = create_async_engine(
            database_url,
            echo=echo or settings.DATABASE_ECHO,
            poolclass=pool.NullPool
        )
    else:
        engine = create_async_engine(
            database_url,
            echo=echo or settings.DATABASE_ECHO,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            connect_args={
                "server_settings": {
                    "application_name": "design_service_async"
                }
            }
        )
    
    return engine


def init_database():
    """Initialize database connections and session factories."""
    global _engine, _async_engine, _session_factory, _async_session_factory
    
    try:
        # Create sync engine
        _engine = create_database_engine()
        _session_factory = sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        # Create async engine
        _async_engine = create_async_database_engine()
        _async_session_factory = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        logger.info("Database connections initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_engine() -> Engine:
    """Get the database engine."""
    if _engine is None:
        init_database()
    return _engine


def get_async_engine():
    """Get the async database engine."""
    if _async_engine is None:
        init_database()
    return _async_engine


def get_session_factory() -> sessionmaker:
    """Get the session factory."""
    if _session_factory is None:
        init_database()
    return _session_factory


def get_async_session_factory():
    """Get the async session factory."""
    if _async_session_factory is None:
        init_database()
    return _async_session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    session_factory = get_session_factory()
    session = session_factory()
    
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session():
    """Get async database session with automatic cleanup."""
    session_factory = get_async_session_factory()
    session = session_factory()
    
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Async database session error: {e}")
        raise
    finally:
        await session.close()


def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def check_async_database_connection() -> bool:
    """Check if async database connection is working."""
    try:
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Async database connection check failed: {e}")
        return False


def database_health_check() -> Dict[str, Any]:
    """Comprehensive database health check."""
    try:
        start_time = datetime.utcnow()
        engine = get_engine()
        
        with engine.connect() as conn:
            # Basic connectivity
            conn.execute(text("SELECT 1"))
            
            # Check current time
            result = conn.execute(text("SELECT NOW() as current_time"))
            db_time = result.fetchone()[0]
            
            # Get database info
            if "postgresql" in str(engine.url):
                version_result = conn.execute(text("SELECT version()"))
                db_version = version_result.fetchone()[0]
                
                # Get connection count
                conn_result = conn.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                ))
                active_connections = conn_result.fetchone()[0]
            else:
                db_version = "Unknown"
                active_connections = 0
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2),
            'database_time': str(db_time),
            'database_version': db_version,
            'active_connections': active_connections,
            'pool_size': engine.pool.size(),
            'checked_out_connections': engine.pool.checkedout(),
            'overflow_connections': engine.pool.overflow(),
            'checked_in_connections': engine.pool.checkedin()
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


async def async_database_health_check() -> Dict[str, Any]:
    """Async database health check."""
    try:
        start_time = datetime.utcnow()
        engine = get_async_engine()
        
        async with engine.begin() as conn:
            # Basic connectivity
            await conn.execute(text("SELECT 1"))
            
            # Check current time
            result = await conn.execute(text("SELECT NOW() as current_time"))
            db_time = (await result.fetchone())[0]
            
            # Get database info
            if "postgresql" in str(engine.url):
                version_result = await conn.execute(text("SELECT version()"))
                db_version = (await version_result.fetchone())[0]
                
                # Get connection count
                conn_result = await conn.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                ))
                active_connections = (await conn_result.fetchone())[0]
            else:
                db_version = "Unknown"
                active_connections = 0
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'status': 'healthy',
            'response_time_ms': round(response_time, 2),
            'database_time': str(db_time),
            'database_version': db_version,
            'active_connections': active_connections
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def get_database_info() -> Dict[str, Any]:
    """Get detailed database information."""
    try:
        engine = get_engine()
        inspector = inspect(engine)
        
        # Get table names
        table_names = inspector.get_table_names()
        
        # Get schema info
        schema_info = {}
        for table_name in table_names[:10]:  # Limit to first 10 tables
            columns = inspector.get_columns(table_name)
            schema_info[table_name] = {
                'columns': len(columns),
                'column_names': [col['name'] for col in columns[:5]]  # First 5 columns
            }
        
        return {
            'database_url': str(engine.url).replace(engine.url.password or '', '***'),
            'driver': engine.dialect.name,
            'total_tables': len(table_names),
            'table_names': table_names[:10],  # First 10 tables
            'schema_info': schema_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            'error': str(e)
        }


def run_migrations(alembic_cfg_path: str = "alembic.ini"):
    """Run database migrations using Alembic."""
    try:
        alembic_cfg = Config(alembic_cfg_path)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def create_tables():
    """Create all tables defined in models."""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


def drop_tables():
    """Drop all tables (use with caution!)."""
    try:
        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise


def reset_database():
    """Reset database by dropping and recreating all tables."""
    logger.warning("Resetting database - all data will be lost!")
    drop_tables()
    create_tables()
    logger.info("Database reset completed")


class DatabaseManager:
    """Database manager for advanced operations."""
    
    def __init__(self):
        self.engine = get_engine()
        self.async_engine = get_async_engine()
    
    def execute_raw_sql(self, sql: str, params: Dict[str, Any] = None) -> Any:
        """Execute raw SQL query."""
        try:
            with self.engine.connect() as conn:
                if params:
                    result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                
                if result.returns_rows:
                    return result.fetchall()
                else:
                    return result.rowcount
                    
        except Exception as e:
            logger.error(f"Raw SQL execution failed: {e}")
            raise
    
    async def execute_raw_sql_async(
        self, 
        sql: str, 
        params: Dict[str, Any] = None
    ) -> Any:
        """Execute raw SQL query asynchronously."""
        try:
            async with self.async_engine.begin() as conn:
                if params:
                    result = await conn.execute(text(sql), params)
                else:
                    result = await conn.execute(text(sql))
                
                if result.returns_rows:
                    return await result.fetchall()
                else:
                    return result.rowcount
                    
        except Exception as e:
            logger.error(f"Async raw SQL execution failed: {e}")
            raise
    
    def backup_table(self, table_name: str, backup_name: str = None) -> bool:
        """Create a backup of a table."""
        try:
            if not backup_name:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{table_name}_backup_{timestamp}"
            
            sql = f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name}"
            self.execute_raw_sql(sql)
            
            logger.info(f"Table {table_name} backed up as {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Table backup failed: {e}")
            return False
    
    def get_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a table."""
        try:
            # Row count
            count_sql = f"SELECT COUNT(*) FROM {table_name}"
            row_count = self.execute_raw_sql(count_sql)[0][0]
            
            # Table size (PostgreSQL specific)
            if "postgresql" in str(self.engine.url):
                size_sql = f"SELECT pg_size_pretty(pg_total_relation_size('{table_name}'))"
                table_size = self.execute_raw_sql(size_sql)[0][0]
            else:
                table_size = "Unknown"
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'table_size': table_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get table stats for {table_name}: {e}")
            return {
                'table_name': table_name,
                'error': str(e)
            }


# Global database manager instance
db_manager = DatabaseManager()


def close_database_connections():
    """Close all database connections."""
    global _engine, _async_engine
    
    try:
        if _engine:
            _engine.dispose()
            logger.info("Sync database connections closed")
        
        if _async_engine:
            # Note: async engine disposal should be done in async context
            logger.info("Async database engine marked for disposal")
            
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


async def close_async_database_connections():
    """Close async database connections."""
    global _async_engine
    
    try:
        if _async_engine:
            await _async_engine.dispose()
            logger.info("Async database connections closed")
            
    except Exception as e:
        logger.error(f"Error closing async database connections: {e}")