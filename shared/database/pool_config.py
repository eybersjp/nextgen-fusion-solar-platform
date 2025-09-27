"""Database Connection Pooling Configuration

Optimized database connection pooling for all services:
- PostgreSQL connection pooling with SQLAlchemy
- Connection lifecycle management
- Performance monitoring and metrics
- Health checks and failover
- Service-specific pool configurations
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import asyncpg
import psycopg2
from sqlalchemy import create_engine, event, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool, StaticPool

logger = logging.getLogger(__name__)


@dataclass
class PoolMetrics:
    """Database pool performance metrics"""
    pool_size: int = 0
    checked_out: int = 0
    overflow: int = 0
    checked_in: int = 0
    total_connections: int = 0
    connection_errors: int = 0
    avg_connection_time: float = 0.0
    max_connection_time: float = 0.0
    active_queries: int = 0
    slow_queries: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DatabaseConfig:
    """Database configuration for connection pooling"""
    # Connection details
    host: str
    database: str
    username: str
    password: str
    port: int = 5432
    
    # Pool configuration
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600  # 1 hour
    pool_pre_ping: bool = True
    
    # Connection configuration
    connect_timeout: int = 10
    command_timeout: int = 60
    server_side_cursors: bool = False
    
    # Performance tuning
    statement_cache_size: int = 100
    prepared_statement_cache_size: int = 100
    
    # SSL configuration
    ssl_mode: str = "prefer"
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    
    # Service-specific settings
    service_name: str = "default"
    read_only: bool = False
    
    def get_sync_url(self) -> str:
        """Get synchronous database URL"""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
    
    def get_async_url(self) -> str:
        """Get asynchronous database URL"""
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for asyncpg"""
        params = {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.username,
            "password": self.password,
            "timeout": self.connect_timeout,
            "command_timeout": self.command_timeout,
            "server_settings": {
                "application_name": f"nextgen_fusion_{self.service_name}",
                "statement_timeout": str(self.command_timeout * 1000),  # milliseconds
            }
        }
        
        if self.ssl_mode != "disable":
            params["ssl"] = self.ssl_mode
            if self.ssl_cert:
                params["ssl_cert"] = self.ssl_cert
            if self.ssl_key:
                params["ssl_key"] = self.ssl_key
            if self.ssl_ca:
                params["ssl_ca"] = self.ssl_ca
        
        return params


class DatabasePoolManager:
    """Manages database connection pools for multiple services"""
    
    def __init__(self):
        self.pools: Dict[str, Any] = {}
        self.async_pools: Dict[str, Any] = {}
        self.session_makers: Dict[str, sessionmaker] = {}
        self.async_session_makers: Dict[str, async_sessionmaker] = {}
        self.metrics: Dict[str, PoolMetrics] = {}
        self.configs: Dict[str, DatabaseConfig] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
    
    def register_database(
        self,
        service_name: str,
        config: DatabaseConfig
    ) -> None:
        """Register a database configuration for a service"""
        config.service_name = service_name
        self.configs[service_name] = config
        self.metrics[service_name] = PoolMetrics()
        
        logger.info(f"Registered database config for service: {service_name}")
    
    def create_sync_pool(self, service_name: str) -> None:
        """Create synchronous connection pool"""
        if service_name not in self.configs:
            raise ValueError(f"No database config found for service: {service_name}")
        
        config = self.configs[service_name]
        
        # Create engine with connection pooling
        engine = create_engine(
            config.get_sync_url(),
            poolclass=QueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=config.pool_pre_ping,
            connect_args={
                "connect_timeout": config.connect_timeout,
                "application_name": f"nextgen_fusion_{service_name}",
                "options": f"-c statement_timeout={config.command_timeout * 1000}"
            },
            echo=False,  # Set to True for SQL debugging
            future=True
        )
        
        # Add event listeners for monitoring
        self._add_sync_event_listeners(engine, service_name)
        
        # Create session maker
        session_maker = sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        self.pools[service_name] = engine
        self.session_makers[service_name] = session_maker
        
        logger.info(f"Created sync connection pool for service: {service_name}")
    
    def create_async_pool(self, service_name: str) -> None:
        """Create asynchronous connection pool"""
        if service_name not in self.configs:
            raise ValueError(f"No database config found for service: {service_name}")
        
        config = self.configs[service_name]
        
        # Create async engine with connection pooling
        # Note: For async engines, we don't specify poolclass as it uses AsyncAdaptedQueuePool by default
        engine = create_async_engine(
            config.get_async_url(),
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            pool_pre_ping=config.pool_pre_ping,
            connect_args={
                "server_settings": {
                    "application_name": f"nextgen_fusion_{service_name}",
                    "statement_timeout": str(config.command_timeout * 1000)
                }
            },
            echo=False,  # Set to True for SQL debugging
            future=True
        )
        
        # Add event listeners for monitoring
        self._add_async_event_listeners(engine, service_name)
        
        # Create async session maker
        async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        self.async_pools[service_name] = engine
        self.async_session_makers[service_name] = async_session_maker
        
        logger.info(f"Created async connection pool for service: {service_name}")
    
    def _add_sync_event_listeners(self, engine, service_name: str) -> None:
        """Add event listeners for synchronous engine monitoring"""
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            connection_record.info['connect_time'] = time.time()
            self.metrics[service_name].total_connections += 1
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            self.metrics[service_name].checked_out += 1
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            self.metrics[service_name].checked_in += 1
            if 'connect_time' in connection_record.info:
                connection_time = time.time() - connection_record.info['connect_time']
                metrics = self.metrics[service_name]
                metrics.avg_connection_time = (
                    (metrics.avg_connection_time * (metrics.checked_in - 1) + connection_time) /
                    metrics.checked_in
                )
                metrics.max_connection_time = max(metrics.max_connection_time, connection_time)
        
        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            self.metrics[service_name].connection_errors += 1
            logger.warning(f"Connection invalidated for {service_name}: {exception}")
    
    def _add_async_event_listeners(self, engine, service_name: str) -> None:
        """Add event listeners for asynchronous engine monitoring"""
        
        @event.listens_for(engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            connection_record.info['connect_time'] = time.time()
            self.metrics[service_name].total_connections += 1
        
        @event.listens_for(engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            self.metrics[service_name].checked_out += 1
        
        @event.listens_for(engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            self.metrics[service_name].checked_in += 1
        
        @event.listens_for(engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            self.metrics[service_name].connection_errors += 1
            logger.warning(f"Async connection invalidated for {service_name}: {exception}")
    
    def get_sync_session(self, service_name: str) -> Session:
        """Get synchronous database session"""
        if service_name not in self.session_makers:
            raise ValueError(f"No sync session maker found for service: {service_name}")
        
        return self.session_makers[service_name]()
    
    def get_async_session(self, service_name: str) -> AsyncSession:
        """Get asynchronous database session"""
        if service_name not in self.async_session_makers:
            raise ValueError(f"No async session maker found for service: {service_name}")
        
        return self.async_session_makers[service_name]()
    
    @asynccontextmanager
    async def get_async_session_context(self, service_name: str):
        """Get async session with automatic cleanup"""
        session = self.get_async_session(service_name)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_sync_session_context(self, service_name: str):
        """Get sync session with automatic cleanup"""
        session = self.get_sync_session(service_name)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def health_check(self, service_name: str) -> Dict[str, Any]:
        """Perform health check on database connection"""
        try:
            if service_name in self.async_pools:
                engine = self.async_pools[service_name]
                async with engine.begin() as conn:
                    result = await conn.execute("SELECT 1")
                    await result.fetchone()
            elif service_name in self.pools:
                engine = self.pools[service_name]
                with engine.begin() as conn:
                    conn.execute("SELECT 1")
            else:
                return {"status": "error", "message": f"No pool found for service: {service_name}"}
            
            # Get pool status
            pool_status = self.get_pool_status(service_name)
            
            return {
                "status": "healthy",
                "service": service_name,
                "pool_status": pool_status,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            return {
                "status": "unhealthy",
                "service": service_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_pool_status(self, service_name: str) -> Dict[str, Any]:
        """Get current pool status and metrics"""
        if service_name not in self.configs:
            return {"error": f"No config found for service: {service_name}"}
        
        status = {"service": service_name}
        
        # Get pool information
        if service_name in self.pools:
            pool = self.pools[service_name].pool
            status.update({
                "sync_pool": {
                    "size": pool.size(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "checked_in": pool.checkedin()
                }
            })
        
        if service_name in self.async_pools:
            pool = self.async_pools[service_name].pool
            status.update({
                "async_pool": {
                    "size": pool.size(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "checked_in": pool.checkedin()
                }
            })
        
        # Add metrics
        if service_name in self.metrics:
            metrics = self.metrics[service_name]
            status["metrics"] = {
                "total_connections": metrics.total_connections,
                "connection_errors": metrics.connection_errors,
                "avg_connection_time": metrics.avg_connection_time,
                "max_connection_time": metrics.max_connection_time,
                "last_updated": metrics.last_updated.isoformat()
            }
        
        return status
    
    def get_all_pool_status(self) -> Dict[str, Any]:
        """Get status for all registered pools"""
        return {
            service_name: self.get_pool_status(service_name)
            for service_name in self.configs.keys()
        }
    
    async def close_all_pools(self) -> None:
        """Close all database pools"""
        # Stop monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Close async pools
        for service_name, engine in self.async_pools.items():
            try:
                await engine.dispose()
                logger.info(f"Closed async pool for service: {service_name}")
            except Exception as e:
                logger.error(f"Error closing async pool for {service_name}: {e}")
        
        # Close sync pools
        for service_name, engine in self.pools.items():
            try:
                engine.dispose()
                logger.info(f"Closed sync pool for service: {service_name}")
            except Exception as e:
                logger.error(f"Error closing sync pool for {service_name}: {e}")
        
        # Clear all pools
        self.pools.clear()
        self.async_pools.clear()
        self.session_makers.clear()
        self.async_session_makers.clear()
    
    def start_monitoring(self, interval: int = 60) -> None:
        """Start background monitoring of pool metrics"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(
                self._monitor_pools(interval)
            )
            logger.info(f"Started pool monitoring with {interval}s interval")
    
    async def _monitor_pools(self, interval: int) -> None:
        """Background task to monitor pool metrics"""
        while True:
            try:
                for service_name in self.configs.keys():
                    # Update metrics timestamp
                    self.metrics[service_name].last_updated = datetime.utcnow()
                    
                    # Log pool status periodically
                    status = self.get_pool_status(service_name)
                    logger.debug(f"Pool status for {service_name}: {status}")
                
                await asyncio.sleep(interval)
            
            except asyncio.CancelledError:
                logger.info("Pool monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Error in pool monitoring: {e}")
                await asyncio.sleep(interval)


# Global pool manager instance
_pool_manager: Optional[DatabasePoolManager] = None


def get_pool_manager() -> DatabasePoolManager:
    """Get global database pool manager"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = DatabasePoolManager()
    return _pool_manager


def initialize_service_database(
    service_name: str,
    config: DatabaseConfig,
    create_async: bool = True,
    create_sync: bool = True
) -> None:
    """Initialize database pools for a service"""
    manager = get_pool_manager()
    manager.register_database(service_name, config)
    
    if create_sync:
        manager.create_sync_pool(service_name)
    
    if create_async:
        manager.create_async_pool(service_name)
    
    logger.info(f"Initialized database pools for service: {service_name}")


# Service-specific configurations
def get_default_configs() -> Dict[str, DatabaseConfig]:
    """Get default database configurations for all services"""
    import os
    
    # Base configuration from environment
    base_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "nextgen_fusion"),
        "username": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "password"),
    }
    
    return {
        "svc-design": DatabaseConfig(
            **base_config,
            service_name="svc-design",
            pool_size=15,  # Higher for complex calculations
            max_overflow=25,
            pool_timeout=45,
            command_timeout=120,  # Longer for complex queries
        ),
        "svc-project": DatabaseConfig(
            **base_config,
            service_name="svc-project",
            pool_size=12,
            max_overflow=20,
            pool_timeout=30,
            command_timeout=90,
        ),
        "svc-compliance": DatabaseConfig(
            **base_config,
            service_name="svc-compliance",
            pool_size=10,
            max_overflow=15,
            pool_timeout=30,
            command_timeout=60,
        ),
        "svc-currency": DatabaseConfig(
            **base_config,
            service_name="svc-currency",
            pool_size=8,
            max_overflow=12,
            pool_timeout=20,
            command_timeout=30,  # Fast operations
        ),
        "svc-auth": DatabaseConfig(
            **base_config,
            service_name="svc-auth",
            pool_size=10,
            max_overflow=15,
            pool_timeout=15,
            command_timeout=30,
        ),
    }


async def initialize_all_service_pools() -> None:
    """Initialize database pools for all services"""
    configs = get_default_configs()
    
    for service_name, config in configs.items():
        try:
            initialize_service_database(service_name, config)
            logger.info(f"Successfully initialized pools for {service_name}")
        except Exception as e:
            logger.error(f"Failed to initialize pools for {service_name}: {e}")
    
    # Start monitoring
    manager = get_pool_manager()
    manager.start_monitoring()
    
    logger.info("All service database pools initialized")


async def cleanup_all_pools() -> None:
    """Cleanup all database pools on shutdown"""
    manager = get_pool_manager()
    await manager.close_all_pools()
    logger.info("All database pools closed")