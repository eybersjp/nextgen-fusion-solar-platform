"""Shared Database Components

Provides database connection pooling, configuration, and utilities
for all NextGen Fusion services.
"""

from .pool_config import (
    DatabaseConfig,
    DatabasePoolManager,
    PoolMetrics,
    get_pool_manager,
    initialize_service_database,
    get_default_configs,
    initialize_all_service_pools,
    cleanup_all_pools,
)

__all__ = [
    "DatabaseConfig",
    "DatabasePoolManager", 
    "PoolMetrics",
    "get_pool_manager",
    "initialize_service_database",
    "get_default_configs",
    "initialize_all_service_pools",
    "cleanup_all_pools",
]