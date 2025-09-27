"""Cache configuration management for NextGen Fusion platform.

Provides environment-specific cache configurations and initialization utilities.
"""

import os
from typing import Optional
from .redis_cache import CacheConfig


def get_cache_config_from_env() -> CacheConfig:
    """Create cache configuration from environment variables."""
    return CacheConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD'),
        max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '20')),
        socket_timeout=float(os.getenv('REDIS_SOCKET_TIMEOUT', '5.0')),
        socket_connect_timeout=float(os.getenv('REDIS_CONNECT_TIMEOUT', '5.0')),
        retry_on_timeout=os.getenv('REDIS_RETRY_ON_TIMEOUT', 'true').lower() == 'true',
        health_check_interval=int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30')),
        default_ttl=int(os.getenv('CACHE_DEFAULT_TTL', '3600')),
        key_prefix=os.getenv('CACHE_KEY_PREFIX', 'nextgen'),
        enable_compression=os.getenv('CACHE_ENABLE_COMPRESSION', 'true').lower() == 'true',
        compression_threshold=int(os.getenv('CACHE_COMPRESSION_THRESHOLD', '1024'))
    )


def get_development_config() -> CacheConfig:
    """Get cache configuration for development environment."""
    return CacheConfig(
        host='localhost',
        port=6379,
        db=0,
        max_connections=10,
        default_ttl=1800,  # 30 minutes
        key_prefix='nextgen_dev',
        enable_compression=False  # Disable compression in dev for easier debugging
    )


def get_production_config() -> CacheConfig:
    """Get cache configuration for production environment."""
    return CacheConfig(
        host=os.getenv('REDIS_HOST', 'redis-cluster.production.local'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD'),
        max_connections=50,
        socket_timeout=3.0,
        socket_connect_timeout=3.0,
        health_check_interval=15,
        default_ttl=7200,  # 2 hours
        key_prefix='nextgen_prod',
        enable_compression=True,
        compression_threshold=512
    )


def get_test_config() -> CacheConfig:
    """Get cache configuration for testing environment."""
    return CacheConfig(
        host='localhost',
        port=6379,
        db=15,  # Use separate DB for tests
        max_connections=5,
        default_ttl=300,  # 5 minutes
        key_prefix='nextgen_test',
        enable_compression=False
    )


def get_config_for_environment(env: Optional[str] = None) -> CacheConfig:
    """Get cache configuration based on environment."""
    if env is None:
        env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return get_production_config()
    elif env == 'test' or env == 'testing':
        return get_test_config()
    elif env == 'development' or env == 'dev':
        return get_development_config()
    else:
        # Default to environment variables
        return get_cache_config_from_env()


# Cache configuration presets for different use cases
CACHE_PRESETS = {
    'fast_queries': {
        'ttl': 300,  # 5 minutes
        'namespace': 'queries'
    },
    'user_sessions': {
        'ttl': 1800,  # 30 minutes
        'namespace': 'sessions'
    },
    'api_responses': {
        'ttl': 600,  # 10 minutes
        'namespace': 'api'
    },
    'expensive_calculations': {
        'ttl': 3600,  # 1 hour
        'namespace': 'calc'
    },
    'static_data': {
        'ttl': 86400,  # 24 hours
        'namespace': 'static'
    },
    'compliance_rules': {
        'ttl': 7200,  # 2 hours
        'namespace': 'compliance'
    },
    'currency_rates': {
        'ttl': 900,  # 15 minutes
        'namespace': 'currency'
    },
    'project_data': {
        'ttl': 1800,  # 30 minutes
        'namespace': 'projects'
    },
    'design_calculations': {
        'ttl': 2700,  # 45 minutes
        'namespace': 'design'
    }
}


def get_cache_preset(preset_name: str) -> dict:
    """Get cache configuration preset."""
    return CACHE_PRESETS.get(preset_name, {
        'ttl': 3600,
        'namespace': 'default'
    })