"""Database management for the Design Service.

Provides SQLAlchemy session management, enhanced connection pooling,
health checks, multi-tenant support, and database utilities.
"""

import asyncio
import sys
import os
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

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

try:
    from database import (
        ServiceType, ServiceDatabaseManager, 
        get_service_db_manager, initialize_service_database
    )
    ENHANCED_POOLING_AVAILABLE = True
except ImportError:
    ENHANCED_POOLING_AVAILABLE = False

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
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600
) -> Engine:
    """Create and configure the main database engine."""
    settings = get_settings()
    
    if not database_url:
        database_url = settings.DATABASE_URL
    
    # Determine if we're using SQLite
    is_sqlite = database_url.startswith('sqlite')
    
    if is_sqlite:
        # SQLite configuration
        engine = create_engine(
            database_url,
            echo=echo,
            poolclass=pool.StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20
            },
            pool_pre_ping=True
        )
    else:
        # PostgreSQL/other database configuration
        engine = create_engine(
            database_url,
            echo=echo,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True
        )
    
    # Add event listeners
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and reliability."""
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
    
    @event.listens_for(engine, "connect")
    def log_connection(dbapi_connection, connection_record):
        """Log database connections."""
        logger.debug(f"Database connection established: {id(dbapi_connection)}")
    
    @event.listens_for(engine, "close")
    def log_disconnection(dbapi_connection, connection_record):
        """Log database disconnections."""
        logger.debug(f"Database connection closed: {id(dbapi_connection)}")
    
    return engine


def create_async_database_engine(
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600
):
    """Create and configure the async database engine."""
    settings = get_settings()
    
    if not database_url:
        database_url = settings.DATABASE_URL
    
    # Convert sync URL to async URL
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    elif database_url.startswith('sqlite:///'):
        database_url = database_url.replace('sqlite:///', 'sqlite+aiosqlite:///', 1)
    
    # Determine if we're using SQLite
    is_sqlite = 'sqlite' in database_url
    
    if is_sqlite:
        # SQLite doesn't support connection pooling in the traditional sense
        engine = create_async_engine(
            database_url,
            echo=echo,
            poolclass=pool.NullPool,  # No pooling for SQLite
            connect_args={"check_same_thread": False}
        )
    else:
        # PostgreSQL configuration with connection pooling
        engine = create_async_engine(
            database_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True
        )
    
    return engine


def init_database(
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    tenant_id: Optional[str] = None
) -> None:
    """Initialize database engines and session factories.
    
    Args:
        database_url: Database connection URL
        echo: Enable SQL query logging
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum overflow connections
        pool_timeout: Timeout for getting connection from pool
        pool_recycle: Time to recycle connections (seconds)
        tenant_id: Optional tenant ID for multi-tenant setup
    """
    global _engine, _async_engine, _session_factory, _async_session_factory
    
    if not database_url:
        settings = get_settings()
        database_url = settings.DATABASE_URL
    
    logger.info(f"Initializing database with URL: {database_url[:50]}...")
    
    try:
        # Use enhanced pooling if available
        if ENHANCED_POOLING_AVAILABLE:
            logger.info("Using enhanced connection pooling system")
            
            # Initialize service database manager
            manager = initialize_service_database(
                service_type=ServiceType.DESIGN
            )
            
            # Get engines for tenant
            _engine = manager.get_engine(tenant_id)
            _async_engine = manager.get_async_engine(tenant_id)
            
            # Create session factories
            _session_factory = sessionmaker(
                bind=_engine,
                class_=Session,
                expire_on_commit=False
            )
            
            _async_session_factory = async_sessionmaker(
                bind=_async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
        else:
            # Fallback to legacy pooling
            logger.warning("Enhanced pooling not available, using legacy system")
            
            # Create sync engine
            _engine = create_database_engine(
                database_url=database_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle
            )
            
            # Create async engine
            _async_engine = create_async_database_engine(
                database_url=database_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle
            )
            
            # Create session factories
            _session_factory = sessionmaker(
                bind=_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            _async_session_factory = async_sessionmaker(
                bind=_async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
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
def get_db_session(tenant_id: Optional[str] = None) -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup.
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant setup
    
    Usage:
        with get_db_session() as session:
            # Use session here
            pass
    """
    if ENHANCED_POOLING_AVAILABLE and tenant_id:
        manager = get_service_db_manager()
        session = manager.get_session(tenant_id)
    else:
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


def get_db(tenant_id: Optional[str] = None) -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions.
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant setup
    
    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            # Use db session here
            pass
    """
    with get_db_session(tenant_id=tenant_id) as session:
        yield session


@asynccontextmanager
async def get_async_db_session(tenant_id: Optional[str] = None):
    """Get an async database session with automatic cleanup.
    
    Args:
        tenant_id: Optional tenant ID for multi-tenant setup
    
    Usage:
        async with get_async_db_session() as session:
            # Use session here
            pass
    """
    if ENHANCED_POOLING_AVAILABLE and tenant_id:
        manager = get_service_db_manager()
        session = await manager.get_async_session(tenant_id)
    else:
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