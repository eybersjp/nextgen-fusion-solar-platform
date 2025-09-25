"""Database configuration and session management for the Design Service.

This module provides database connection management, session handling,
and database initialization utilities.
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from .core.config import get_settings
from .core.logging import get_logger
from .models import Base

# Get logger
logger = get_logger(__name__)

# Global variables for engines and session makers
_sync_engine = None
_async_engine = None
_sync_session_maker = None
_async_session_maker = None


def get_sync_engine():
    """Get or create synchronous database engine.
    
    Returns:
        Engine: SQLAlchemy synchronous engine
    """
    global _sync_engine
    
    if _sync_engine is None:
        settings = get_settings()
        
        # Create engine with connection pooling
        _sync_engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,
            echo=settings.db_echo,
            echo_pool=settings.is_development,
        )
        
        # Add event listeners for connection management
        @event.listens_for(_sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance."""
            if "sqlite" in settings.database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
        
        @event.listens_for(_sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log database connection checkout."""
            logger.debug("Database connection checked out")
        
        @event.listens_for(_sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log database connection checkin."""
            logger.debug("Database connection checked in")
        
        logger.info(f"Created synchronous database engine: {settings.database_url}")
    
    return _sync_engine


def get_async_engine():
    """Get or create asynchronous database engine.
    
    Returns:
        AsyncEngine: SQLAlchemy asynchronous engine
    """
    global _async_engine
    
    if _async_engine is None:
        settings = get_settings()
        
        # Create async engine with connection pooling
        _async_engine = create_async_engine(
            settings.async_database_url,
            poolclass=pool.QueuePool,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=True,
            echo=settings.db_echo,
            echo_pool=settings.is_development,
        )
        
        logger.info(f"Created asynchronous database engine: {settings.async_database_url}")
    
    return _async_engine


def get_sync_session_maker():
    """Get or create synchronous session maker.
    
    Returns:
        sessionmaker: SQLAlchemy synchronous session maker
    """
    global _sync_session_maker
    
    if _sync_session_maker is None:
        engine = get_sync_engine()
        _sync_session_maker = sessionmaker(
            bind=engine,
            class_=Session,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        logger.info("Created synchronous session maker")
    
    return _sync_session_maker


def get_async_session_maker():
    """Get or create asynchronous session maker.
    
    Returns:
        async_sessionmaker: SQLAlchemy asynchronous session maker
    """
    global _async_session_maker
    
    if _async_session_maker is None:
        engine = get_async_engine()
        _async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        logger.info("Created asynchronous session maker")
    
    return _async_session_maker


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Get synchronous database session with automatic cleanup.
    
    Yields:
        Session: SQLAlchemy synchronous session
        
    Example:
        with get_sync_session() as session:
            user = session.query(User).first()
    """
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    try:
        logger.debug("Created synchronous database session")
        yield session
        session.commit()
        logger.debug("Committed synchronous database session")
    except Exception as e:
        logger.error(f"Error in synchronous database session: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        logger.debug("Closed synchronous database session")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session with automatic cleanup.
    
    Yields:
        AsyncSession: SQLAlchemy asynchronous session
        
    Example:
        async with get_async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    session_maker = get_async_session_maker()
    session = session_maker()
    
    try:
        logger.debug("Created asynchronous database session")
        yield session
        await session.commit()
        logger.debug("Committed asynchronous database session")
    except Exception as e:
        logger.error(f"Error in asynchronous database session: {e}")
        await session.rollback()
        raise
    finally:
        await session.close()
        logger.debug("Closed asynchronous database session")


def create_sync_session() -> Session:
    """Create a new synchronous database session.
    
    Returns:
        Session: SQLAlchemy synchronous session
        
    Note:
        Remember to close the session when done.
    """
    session_maker = get_sync_session_maker()
    return session_maker()


def create_async_session() -> AsyncSession:
    """Create a new asynchronous database session.
    
    Returns:
        AsyncSession: SQLAlchemy asynchronous session
        
    Note:
        Remember to close the session when done.
    """
    session_maker = get_async_session_maker()
    return session_maker()


def init_database(drop_existing: bool = False) -> None:
    """Initialize database tables.
    
    Args:
        drop_existing: Whether to drop existing tables first
    """
    engine = get_sync_engine()
    
    try:
        if drop_existing:
            logger.warning("Dropping all existing database tables")
            Base.metadata.drop_all(bind=engine)
        
        logger.info("Creating database tables")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def init_async_database(drop_existing: bool = False) -> None:
    """Initialize database tables asynchronously.
    
    Args:
        drop_existing: Whether to drop existing tables first
    """
    engine = get_async_engine()
    
    try:
        async with engine.begin() as conn:
            if drop_existing:
                logger.warning("Dropping all existing database tables")
                await conn.run_sync(Base.metadata.drop_all)
            
            logger.info("Creating database tables")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            
    except Exception as e:
        logger.error(f"Error initializing async database: {e}")
        raise


def check_database_connection() -> bool:
    """Check if database connection is working.
    
    Returns:
        bool: True if connection is working
    """
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection check successful")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def check_async_database_connection() -> bool:
    """Check if asynchronous database connection is working.
    
    Returns:
        bool: True if connection is working
    """
    try:
        engine = get_async_engine()
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("Async database connection check successful")
        return True
    except Exception as e:
        logger.error(f"Async database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """Get database information and statistics.
    
    Returns:
        dict: Database information
    """
    settings = get_settings()
    engine = get_sync_engine()
    
    info = {
        "database_url": settings.database_url,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
        "pool_recycle": settings.db_pool_recycle,
        "echo": settings.db_echo,
    }
    
    # Add pool statistics if available
    if hasattr(engine.pool, 'size'):
        info.update({
            "pool_current_size": engine.pool.size(),
            "pool_checked_in": engine.pool.checkedin(),
            "pool_checked_out": engine.pool.checkedout(),
        })
    
    return info


def close_database_connections() -> None:
    """Close all database connections and dispose engines."""
    global _sync_engine, _async_engine, _sync_session_maker, _async_session_maker
    
    try:
        if _sync_engine:
            _sync_engine.dispose()
            logger.info("Disposed synchronous database engine")
        
        if _async_engine:
            # Note: async engine disposal should be done in async context
            logger.info("Async database engine marked for disposal")
        
        # Reset global variables
        _sync_engine = None
        _async_engine = None
        _sync_session_maker = None
        _async_session_maker = None
        
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


async def close_async_database_connections() -> None:
    """Close all asynchronous database connections and dispose engines."""
    global _async_engine
    
    try:
        if _async_engine:
            await _async_engine.dispose()
            logger.info("Disposed asynchronous database engine")
            _async_engine = None
        
        logger.info("Async database connections closed")
        
    except Exception as e:
        logger.error(f"Error closing async database connections: {e}")


# Health check function
def database_health_check() -> dict:
    """Perform comprehensive database health check.
    
    Returns:
        dict: Health check results
    """
    health = {
        "status": "healthy",
        "checks": {},
        "timestamp": None,
    }
    
    try:
        # Check basic connection
        health["checks"]["connection"] = check_database_connection()
        
        # Check pool status
        engine = get_sync_engine()
        if hasattr(engine.pool, 'size'):
            pool_size = engine.pool.size()
            checked_out = engine.pool.checkedout()
            health["checks"]["pool_utilization"] = {
                "size": pool_size,
                "checked_out": checked_out,
                "utilization_percent": (checked_out / pool_size * 100) if pool_size > 0 else 0,
            }
        
        # Overall status
        if not all(health["checks"].values()):
            health["status"] = "unhealthy"
        
    except Exception as e:
        health["status"] = "unhealthy"
        health["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    health["timestamp"] = logger.get_current_time()
    return health


# Dependency injection functions for FastAPI
def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency for getting database session.
    
    Yields:
        Session: Database session
    """
    with get_sync_session() as session:
        yield session


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting async database session.
    
    Yields:
        AsyncSession: Async database session
    """
    async with get_async_session() as session:
        yield session