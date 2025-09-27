#!/usr/bin/env python3
"""
Service-specific database configuration for NextGen Fusion services.

Provides standardized database setup with service-specific optimizations
and multi-tenant support.
"""

import os
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .connection_pool import (
    PoolConfig, ConnectionPoolManager, DatabaseType, PoolStrategy,
    initialize_pool_manager, get_pool_manager
)


logger = logging.getLogger(__name__)


class ServiceType(str, Enum):
    """NextGen Fusion service types."""
    DESIGN = "svc-design"
    CURRENCY = "svc-currency"
    PROJECT = "svc-project"
    COMPLIANCE = "svc-compliance"
    API_GATEWAY = "api-gateway"


@dataclass
class ServiceDatabaseConfig:
    """Service-specific database configuration."""
    service_type: ServiceType
    database_url: str
    
    # Service-specific pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # Multi-tenant settings
    enable_multi_tenant: bool = True
    tenant_pool_size: int = 5
    max_tenant_pools: int = 50
    
    # Performance settings
    query_timeout: int = 30
    slow_query_threshold: float = 1.0
    enable_query_logging: bool = False
    
    # Health check settings
    health_check_interval: int = 60
    
    @classmethod
    def from_env(cls, service_type: ServiceType) -> 'ServiceDatabaseConfig':
        """Create configuration from environment variables."""
        # Get service-specific environment variable prefix
        env_prefix = service_type.value.upper().replace("-", "_")
        
        # Default database URL
        default_db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5432/nextgen_fusion"
        )
        
        # Service-specific database URL override
        database_url = os.getenv(
            f"{env_prefix}_DATABASE_URL",
            os.getenv("DATABASE_URL", default_db_url)
        )
        
        return cls(
            service_type=service_type,
            database_url=database_url,
            pool_size=int(os.getenv(f"{env_prefix}_POOL_SIZE", "10")),
            max_overflow=int(os.getenv(f"{env_prefix}_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv(f"{env_prefix}_POOL_TIMEOUT", "30")),
            pool_recycle=int(os.getenv(f"{env_prefix}_POOL_RECYCLE", "3600")),
            enable_multi_tenant=os.getenv(f"{env_prefix}_MULTI_TENANT", "true").lower() == "true",
            tenant_pool_size=int(os.getenv(f"{env_prefix}_TENANT_POOL_SIZE", "5")),
            max_tenant_pools=int(os.getenv(f"{env_prefix}_MAX_TENANT_POOLS", "50")),
            query_timeout=int(os.getenv(f"{env_prefix}_QUERY_TIMEOUT", "30")),
            slow_query_threshold=float(os.getenv(f"{env_prefix}_SLOW_QUERY_THRESHOLD", "1.0")),
            enable_query_logging=os.getenv(f"{env_prefix}_QUERY_LOGGING", "false").lower() == "true",
            health_check_interval=int(os.getenv(f"{env_prefix}_HEALTH_CHECK_INTERVAL", "60"))
        )


class ServiceDatabaseManager:
    """Service-specific database manager with optimized configurations."""
    
    # Service-specific optimizations
    SERVICE_OPTIMIZATIONS = {
        ServiceType.DESIGN: {
            "pool_size": 15,  # Higher for 3D processing
            "max_overflow": 30,
            "pool_recycle": 1800,  # 30 minutes for long-running 3D operations
            "query_timeout": 60,  # Longer timeout for complex 3D queries
            "slow_query_threshold": 2.0
        },
        ServiceType.CURRENCY: {
            "pool_size": 8,  # Moderate for FX operations
            "max_overflow": 15,
            "pool_recycle": 3600,
            "query_timeout": 15,  # Fast FX rate queries
            "slow_query_threshold": 0.5
        },
        ServiceType.PROJECT: {
            "pool_size": 12,  # Higher for project management
            "max_overflow": 25,
            "pool_recycle": 3600,
            "query_timeout": 30,
            "slow_query_threshold": 1.0
        },
        ServiceType.COMPLIANCE: {
            "pool_size": 10,  # Standard for compliance checks
            "max_overflow": 20,
            "pool_recycle": 3600,
            "query_timeout": 45,  # Longer for complex rule evaluation
            "slow_query_threshold": 1.5
        },
        ServiceType.API_GATEWAY: {
            "pool_size": 5,  # Lower for gateway (mostly routing)
            "max_overflow": 10,
            "pool_recycle": 3600,
            "query_timeout": 10,  # Fast gateway operations
            "slow_query_threshold": 0.3
        }
    }
    
    def __init__(self, service_config: ServiceDatabaseConfig):
        self.service_config = service_config
        self.pool_manager: Optional[ConnectionPoolManager] = None
        self._initialized = False
    
    def _apply_service_optimizations(self, config: ServiceDatabaseConfig) -> ServiceDatabaseConfig:
        """Apply service-specific optimizations to configuration."""
        optimizations = self.SERVICE_OPTIMIZATIONS.get(config.service_type, {})
        
        for key, value in optimizations.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    def _detect_database_type(self, database_url: str) -> DatabaseType:
        """Detect database type from URL."""
        if "sqlite" in database_url:
            return DatabaseType.SQLITE
        elif "postgresql" in database_url or "postgres" in database_url:
            return DatabaseType.POSTGRESQL
        elif "mysql" in database_url:
            return DatabaseType.MYSQL
        else:
            # Default to PostgreSQL
            return DatabaseType.POSTGRESQL
    
    def initialize(self) -> ConnectionPoolManager:
        """Initialize the database connection pool manager."""
        if self._initialized:
            return self.pool_manager
        
        # Apply service-specific optimizations
        optimized_config = self._apply_service_optimizations(self.service_config)
        
        # Detect database type
        db_type = self._detect_database_type(optimized_config.database_url)
        
        # Determine pool strategy based on service type and multi-tenant setting
        if optimized_config.enable_multi_tenant:
            if optimized_config.service_type in [ServiceType.DESIGN, ServiceType.PROJECT]:
                # Services with heavy workloads benefit from tenant isolation
                pool_strategy = PoolStrategy.TENANT_ISOLATED
            else:
                # Lighter services can use hybrid approach
                pool_strategy = PoolStrategy.HYBRID
        else:
            pool_strategy = PoolStrategy.SHARED
        
        # Create pool configuration
        pool_config = PoolConfig(
            database_url=optimized_config.database_url,
            database_type=db_type,
            pool_size=optimized_config.pool_size,
            max_overflow=optimized_config.max_overflow,
            pool_timeout=optimized_config.pool_timeout,
            pool_recycle=optimized_config.pool_recycle,
            pool_strategy=pool_strategy,
            tenant_pool_size=optimized_config.tenant_pool_size,
            max_tenant_pools=optimized_config.max_tenant_pools,
            query_timeout=optimized_config.query_timeout,
            slow_query_threshold=optimized_config.slow_query_threshold,
            health_check_interval=optimized_config.health_check_interval,
            echo=optimized_config.enable_query_logging,
            enable_metrics=True
        )
        
        # Initialize pool manager
        self.pool_manager = initialize_pool_manager(pool_config)
        self._initialized = True
        
        logger.info(
            f"Initialized database pool for {optimized_config.service_type.value} "
            f"with strategy: {pool_strategy.value}"
        )
        
        return self.pool_manager
    
    def get_session(self, tenant_id: str = "default"):
        """Get database session for tenant."""
        if not self._initialized:
            self.initialize()
        return self.pool_manager.get_session(tenant_id)
    
    def get_async_session(self, tenant_id: str = "default"):
        """Get async database session for tenant."""
        if not self._initialized:
            self.initialize()
        return self.pool_manager.get_async_session(tenant_id)
    
    def get_engine(self, tenant_id: str = "default"):
        """Get database engine for tenant."""
        if not self._initialized:
            self.initialize()
        return self.pool_manager.create_engine(tenant_id)
    
    def get_async_engine(self, tenant_id: str = "default"):
        """Get async database engine for tenant."""
        if not self._initialized:
            self.initialize()
        return self.pool_manager.create_async_engine(tenant_id)
    
    def get_pool_status(self, tenant_id: str = "default") -> Dict[str, Any]:
        """Get connection pool status."""
        if not self._initialized:
            return {"status": "not_initialized"}
        return self.pool_manager.get_pool_status(tenant_id)
    
    def get_all_pool_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all tenant pools."""
        if not self._initialized:
            return {}
        return self.pool_manager.get_all_pool_status()
    
    async def health_check(self, tenant_id: str = "default") -> bool:
        """Perform health check on database connection."""
        if not self._initialized:
            return False
        return await self.pool_manager.health_check(tenant_id)
    
    def close(self):
        """Close all database connections."""
        if self.pool_manager:
            self.pool_manager.close_all()
            self._initialized = False


# Service-specific factory functions
def create_design_db_manager() -> ServiceDatabaseManager:
    """Create database manager for svc-design."""
    config = ServiceDatabaseConfig.from_env(ServiceType.DESIGN)
    return ServiceDatabaseManager(config)


def create_currency_db_manager() -> ServiceDatabaseManager:
    """Create database manager for svc-currency."""
    config = ServiceDatabaseConfig.from_env(ServiceType.CURRENCY)
    return ServiceDatabaseManager(config)


def create_project_db_manager() -> ServiceDatabaseManager:
    """Create database manager for svc-project."""
    config = ServiceDatabaseConfig.from_env(ServiceType.PROJECT)
    return ServiceDatabaseManager(config)


def create_compliance_db_manager() -> ServiceDatabaseManager:
    """Create database manager for svc-compliance."""
    config = ServiceDatabaseConfig.from_env(ServiceType.COMPLIANCE)
    return ServiceDatabaseManager(config)


def create_api_gateway_db_manager() -> ServiceDatabaseManager:
    """Create database manager for api-gateway."""
    config = ServiceDatabaseConfig.from_env(ServiceType.API_GATEWAY)
    return ServiceDatabaseManager(config)


# Global service managers
_service_managers: Dict[ServiceType, ServiceDatabaseManager] = {}


def get_service_db_manager(service_type: ServiceType) -> ServiceDatabaseManager:
    """Get or create service-specific database manager."""
    if service_type not in _service_managers:
        config = ServiceDatabaseConfig.from_env(service_type)
        _service_managers[service_type] = ServiceDatabaseManager(config)
    
    return _service_managers[service_type]


def initialize_service_database(service_type: ServiceType) -> ServiceDatabaseManager:
    """Initialize database for specific service."""
    manager = get_service_db_manager(service_type)
    manager.initialize()
    return manager


def close_all_service_databases():
    """Close all service database connections."""
    for manager in _service_managers.values():
        manager.close()
    _service_managers.clear()