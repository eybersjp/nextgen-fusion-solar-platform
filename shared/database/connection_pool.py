#!/usr/bin/env python3
"""
Enhanced Database Connection Pooling for NextGen Fusion Services

Provides optimized connection pooling with multi-tenant isolation,
performance monitoring, and automatic failover capabilities.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Dict, Optional, Any, AsyncGenerator, Generator
from dataclasses import dataclass
from enum import Enum

import asyncpg
from sqlalchemy import (
    create_engine, event, text, pool as sqlalchemy_pool
)
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DisconnectionError, OperationalError


logger = logging.getLogger(__name__)


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MYSQL = "mysql"


class PoolStrategy(str, Enum):
    """Connection pool strategies."""
    SHARED = "shared"  # Single pool for all tenants
    TENANT_ISOLATED = "tenant_isolated"  # Separate pools per tenant
    HYBRID = "hybrid"  # Shared pool with tenant-aware routing


@dataclass
class PoolConfig:
    """Database connection pool configuration."""
    # Basic connection settings
    database_url: str
    database_type: DatabaseType
    
    # Pool sizing
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600  # 1 hour
    pool_pre_ping: bool = True
    
    # Multi-tenant settings
    pool_strategy: PoolStrategy = PoolStrategy.SHARED
    tenant_pool_size: int = 5  # Per-tenant pool size
    max_tenant_pools: int = 50
    
    # Performance settings
    echo: bool = False
    echo_pool: bool = False
    connect_timeout: int = 10
    query_timeout: int = 30
    
    # Health check settings
    health_check_interval: int = 60  # seconds
    max_connection_age: int = 7200  # 2 hours
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Monitoring
    enable_metrics: bool = True
    slow_query_threshold: float = 1.0  # seconds


class ConnectionPoolManager:
    """Enhanced connection pool manager with multi-tenant support."""
    
    def __init__(self, config: PoolConfig):
        self.config = config
        self._engines: Dict[str, Engine] = {}
        self._async_engines: Dict[str, Any] = {}
        self._session_factories: Dict[str, sessionmaker] = {}
        self._async_session_factories: Dict[str, async_sessionmaker] = {}
        self._pool_metrics: Dict[str, Dict[str, Any]] = {}
        self._last_health_check = 0
        
    def _get_connect_args(self) -> Dict[str, Any]:
        """Get database-specific connection arguments."""
        if self.config.database_type == DatabaseType.POSTGRESQL:
            return {
                "connect_timeout": self.config.connect_timeout,
                "command_timeout": self.config.query_timeout,
                "application_name": "nextgen_fusion",
                "server_settings": {
                    "jit": "off",  # Disable JIT for faster connection
                    "timezone": "UTC"
                }
            }
        elif self.config.database_type == DatabaseType.SQLITE:
            return {
                "check_same_thread": False,
                "timeout": self.config.connect_timeout
            }
        elif self.config.database_type == DatabaseType.MYSQL:
            return {
                "connect_timeout": self.config.connect_timeout,
                "read_timeout": self.config.query_timeout,
                "write_timeout": self.config.query_timeout,
                "charset": "utf8mb4"
            }
        return {}
    
    def _setup_engine_events(self, engine: Engine, tenant_id: str = "default"):
        """Setup engine event listeners for monitoring and optimization."""
        
        @event.listens_for(engine, "connect")
        def set_database_pragmas(dbapi_connection, connection_record):
            """Set database-specific optimizations."""
            if self.config.database_type == DatabaseType.SQLITE:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
            elif self.config.database_type == DatabaseType.POSTGRESQL:
                # Set PostgreSQL-specific optimizations
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = %s", (self.config.query_timeout * 1000,))
                    cursor.execute("SET lock_timeout = %s", (self.config.query_timeout * 1000,))
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Track connection checkout."""
            if self.config.enable_metrics:
                self._update_pool_metrics(tenant_id, "checkout")
            logger.debug(f"Connection checked out for tenant: {tenant_id}")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Track connection checkin."""
            if self.config.enable_metrics:
                self._update_pool_metrics(tenant_id, "checkin")
            logger.debug(f"Connection checked in for tenant: {tenant_id}")
        
        @event.listens_for(engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation."""
            logger.warning(f"Connection invalidated for tenant {tenant_id}: {exception}")
            if self.config.enable_metrics:
                self._update_pool_metrics(tenant_id, "invalidate")
    
    def _update_pool_metrics(self, tenant_id: str, event_type: str):
        """Update pool metrics for monitoring."""
        if tenant_id not in self._pool_metrics:
            self._pool_metrics[tenant_id] = {
                "checkouts": 0,
                "checkins": 0,
                "invalidations": 0,
                "created_at": time.time()
            }
        
        if event_type in self._pool_metrics[tenant_id]:
            self._pool_metrics[tenant_id][event_type] += 1
        
        self._pool_metrics[tenant_id]["last_activity"] = time.time()
    
    def create_engine(self, tenant_id: str = "default") -> Engine:
        """Create or get existing engine for tenant."""
        if tenant_id in self._engines:
            return self._engines[tenant_id]
        
        # Determine pool class and size based on strategy
        if self.config.pool_strategy == PoolStrategy.TENANT_ISOLATED:
            pool_size = self.config.tenant_pool_size
            max_overflow = min(self.config.max_overflow, self.config.tenant_pool_size * 2)
        else:
            pool_size = self.config.pool_size
            max_overflow = self.config.max_overflow
        
        # Use NullPool for SQLite to avoid threading issues
        if self.config.database_type == DatabaseType.SQLITE:
            poolclass = NullPool
            pool_kwargs = {}
        else:
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pool_pre_ping": self.config.pool_pre_ping
            }
        
        engine = create_engine(
            self.config.database_url,
            poolclass=poolclass,
            echo=self.config.echo,
            echo_pool=self.config.echo_pool,
            connect_args=self._get_connect_args(),
            **pool_kwargs
        )
        
        self._setup_engine_events(engine, tenant_id)
        self._engines[tenant_id] = engine
        
        # Create session factory
        self._session_factories[tenant_id] = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        logger.info(f"Created database engine for tenant: {tenant_id}")
        return engine
    
    def create_async_engine(self, tenant_id: str = "default"):
        """Create or get existing async engine for tenant."""
        if tenant_id in self._async_engines:
            return self._async_engines[tenant_id]
        
        # Convert sync URL to async URL
        async_url = self.config.database_url
        if "sqlite://" in async_url:
            async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
        elif "postgresql://" in async_url:
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
        elif "mysql://" in async_url:
            async_url = async_url.replace("mysql://", "mysql+aiomysql://")
        
        # Determine pool settings
        if self.config.database_type == DatabaseType.SQLITE:
            engine = create_async_engine(
                async_url,
                echo=self.config.echo,
                poolclass=NullPool
            )
        else:
            pool_size = (
                self.config.tenant_pool_size 
                if self.config.pool_strategy == PoolStrategy.TENANT_ISOLATED 
                else self.config.pool_size
            )
            
            # For async engines, don't specify poolclass - it uses AsyncAdaptedQueuePool by default
            engine = create_async_engine(
                async_url,
                echo=self.config.echo,
                pool_size=pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=self.config.pool_pre_ping,
                connect_args=self._get_connect_args()
            )
        
        self._async_engines[tenant_id] = engine
        
        # Create async session factory
        self._async_session_factories[tenant_id] = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        logger.info(f"Created async database engine for tenant: {tenant_id}")
        return engine
    
    @contextmanager
    def get_session(self, tenant_id: str = "default") -> Generator[Session, None, None]:
        """Get database session with automatic cleanup."""
        if tenant_id not in self._session_factories:
            self.create_engine(tenant_id)
        
        session = self._session_factories[tenant_id]()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self, tenant_id: str = "default") -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic cleanup."""
        if tenant_id not in self._async_session_factories:
            self.create_async_engine(tenant_id)
        
        session = self._async_session_factories[tenant_id]()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_pool_status(self, tenant_id: str = "default") -> Dict[str, Any]:
        """Get connection pool status for monitoring."""
        if tenant_id not in self._engines:
            return {"status": "not_initialized"}
        
        engine = self._engines[tenant_id]
        pool = engine.pool
        
        status = {
            "tenant_id": tenant_id,
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
            "total_connections": pool.size() + pool.overflow(),
            "utilization": pool.checkedout() / (pool.size() + pool.overflow()) if (pool.size() + pool.overflow()) > 0 else 0
        }
        
        if tenant_id in self._pool_metrics:
            status.update(self._pool_metrics[tenant_id])
        
        return status
    
    def get_all_pool_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all tenant pools."""
        return {
            tenant_id: self.get_pool_status(tenant_id)
            for tenant_id in self._engines.keys()
        }
    
    async def health_check(self, tenant_id: str = "default") -> bool:
        """Perform health check on database connection."""
        try:
            if tenant_id in self._async_engines:
                engine = self._async_engines[tenant_id]
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
            elif tenant_id in self._engines:
                engine = self._engines[tenant_id]
                with engine.begin() as conn:
                    conn.execute(text("SELECT 1"))
            else:
                return False
            
            logger.debug(f"Health check passed for tenant: {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Health check failed for tenant {tenant_id}: {e}")
            return False
    
    async def cleanup_idle_connections(self):
        """Clean up idle connections across all pools."""
        current_time = time.time()
        
        for tenant_id, engine in self._engines.items():
            try:
                # Force cleanup of idle connections
                if hasattr(engine.pool, 'recreate'):
                    engine.pool.recreate()
                logger.debug(f"Cleaned up idle connections for tenant: {tenant_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup connections for tenant {tenant_id}: {e}")
    
    def close_all(self):
        """Close all database connections and engines."""
        for tenant_id, engine in self._engines.items():
            try:
                engine.dispose()
                logger.info(f"Disposed engine for tenant: {tenant_id}")
            except Exception as e:
                logger.error(f"Error disposing engine for tenant {tenant_id}: {e}")
        
        for tenant_id, engine in self._async_engines.items():
            try:
                asyncio.create_task(engine.dispose())
                logger.info(f"Disposed async engine for tenant: {tenant_id}")
            except Exception as e:
                logger.error(f"Error disposing async engine for tenant {tenant_id}: {e}")
        
        self._engines.clear()
        self._async_engines.clear()
        self._session_factories.clear()
        self._async_session_factories.clear()
        self._pool_metrics.clear()


# Global pool manager instance
_pool_manager: Optional[ConnectionPoolManager] = None


def initialize_pool_manager(config: PoolConfig) -> ConnectionPoolManager:
    """Initialize global pool manager."""
    global _pool_manager
    _pool_manager = ConnectionPoolManager(config)
    return _pool_manager


def get_pool_manager() -> ConnectionPoolManager:
    """Get global pool manager instance."""
    if _pool_manager is None:
        raise RuntimeError("Pool manager not initialized. Call initialize_pool_manager() first.")
    return _pool_manager


# Convenience functions
def get_session(tenant_id: str = "default"):
    """Get database session for tenant."""
    return get_pool_manager().get_session(tenant_id)


def get_async_session(tenant_id: str = "default"):
    """Get async database session for tenant."""
    return get_pool_manager().get_async_session(tenant_id)


def get_engine(tenant_id: str = "default") -> Engine:
    """Get database engine for tenant."""
    return get_pool_manager().create_engine(tenant_id)


def get_async_engine(tenant_id: str = "default"):
    """Get async database engine for tenant."""
    return get_pool_manager().create_async_engine(tenant_id)