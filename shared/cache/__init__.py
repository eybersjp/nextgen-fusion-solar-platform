"""Cache module for NextGen Fusion Platform

Provides Redis-based caching infrastructure for all services.
"""

from .redis_cache import (
    RedisCache,
    CacheConfig,
    CacheMetrics,
    CacheStrategy,
    SerializationMethod,
    CacheNamespace,
    CacheKeyBuilder,
    CacheUtils,
    get_cache,
    init_cache,
    close_cache,
    cached,
    cache_context
)

__all__ = [
    "RedisCache",
    "CacheConfig",
    "CacheMetrics",
    "CacheStrategy",
    "SerializationMethod",
    "CacheNamespace",
    "CacheKeyBuilder",
    "CacheUtils",
    "get_cache",
    "init_cache",
    "close_cache",
    "cached",
    "cache_context"
]