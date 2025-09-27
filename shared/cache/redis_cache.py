"""Redis Caching Service for NextGen Fusion Platform

Provides comprehensive Redis-based caching for expensive operations:
- Design calculations and layout optimizations
- Compliance rule evaluations
- Currency rate conversions
- Database query results
- API response caching
- Session and authentication data

Features:
- Automatic serialization/deserialization
- TTL management and cache invalidation
- Cache warming and preloading
- Performance monitoring and metrics
- Distributed cache coordination
- Cache tags and bulk invalidation
"""

import json
import pickle
import hashlib
import asyncio
from typing import Any, Optional, Dict, List, Union, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import redis.asyncio as redis
from redis.asyncio import Redis
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategy options"""
    WRITE_THROUGH = "write_through"  # Write to cache and storage simultaneously
    WRITE_BEHIND = "write_behind"    # Write to cache first, storage later
    WRITE_AROUND = "write_around"    # Write to storage, invalidate cache
    READ_THROUGH = "read_through"    # Read from cache, fallback to storage
    CACHE_ASIDE = "cache_aside"      # Manual cache management


class SerializationMethod(Enum):
    """Serialization method options"""
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"
    MSGPACK = "msgpack"


class CacheNamespace(Enum):
    """Predefined cache namespaces"""
    DESIGN_CALCULATIONS = "design_calc"
    LAYOUT_OPTIMIZATION = "layout_opt"
    COMPLIANCE_RULES = "compliance"
    CURRENCY_RATES = "fx_rates"
    USER_SESSIONS = "sessions"
    API_RESPONSES = "api_resp"
    DATABASE_QUERIES = "db_queries"
    AUTHENTICATION = "auth"
    PROJECT_DATA = "projects"
    COMPONENT_SPECS = "components"


@dataclass
class CacheConfig:
    """Cache configuration settings"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 20
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    default_ttl: int = 3600  # 1 hour
    max_key_length: int = 250
    compression_threshold: int = 1024  # Compress values larger than 1KB
    enable_metrics: bool = True
    key_prefix: str = "ngf"  # NextGen Fusion prefix


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_requests: int = 0
    average_response_time_ms: float = 0.0
    cache_size_bytes: int = 0
    evictions: int = 0
    expired_keys: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 100.0 - self.hit_rate


class CacheKeyBuilder:
    """Utility class for building cache keys"""
    
    @staticmethod
    def build_key(
        namespace: Union[str, CacheNamespace],
        identifier: str,
        *args,
        **kwargs
    ) -> str:
        """Build a cache key from components"""
        if isinstance(namespace, CacheNamespace):
            namespace = namespace.value
        
        # Create base key
        key_parts = [namespace, identifier]
        
        # Add positional arguments
        if args:
            key_parts.extend(str(arg) for arg in args)
        
        # Add keyword arguments (sorted for consistency)
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            for k, v in sorted_kwargs:
                key_parts.append(f"{k}:{v}")
        
        # Join with colons and add prefix
        key = ":".join(key_parts)
        return f"ngf:{key}"
    
    @staticmethod
    def hash_key(data: Any) -> str:
        """Create a hash-based key from complex data"""
        if isinstance(data, dict):
            # Sort dict for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, (list, tuple)):
            data_str = json.dumps(sorted(data) if all(isinstance(x, (str, int, float)) for x in data) else list(data))
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    @staticmethod
    def pattern_key(namespace: Union[str, CacheNamespace], pattern: str = "*") -> str:
        """Build a pattern key for bulk operations"""
        if isinstance(namespace, CacheNamespace):
            namespace = namespace.value
        return f"ngf:{namespace}:{pattern}"


class RedisCache:
    """Advanced Redis cache implementation"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis: Optional[Redis] = None
        self.metrics = CacheMetrics()
        self._key_builder = CacheKeyBuilder()
        self._serializers = {
            SerializationMethod.JSON: (json.dumps, json.loads),
            SerializationMethod.PICKLE: (pickle.dumps, pickle.loads),
            SerializationMethod.STRING: (str, str),
        }
        self._connected = False
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> None:
        """Connect to Redis server"""
        try:
            self.redis = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                ssl=self.config.ssl,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=False  # We handle encoding ourselves
            )
            
            # Test connection
            await self.redis.ping()
            self._connected = True
            
            # Start health check task
            if self.config.health_check_interval > 0:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
        
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis server"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Disconnected from Redis")
    
    async def _health_check_loop(self) -> None:
        """Periodic health check loop"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                if self.redis:
                    await self.redis.ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
                self._connected = False
    
    def _serialize(self, value: Any, method: SerializationMethod = SerializationMethod.PICKLE) -> bytes:
        """Serialize value for storage"""
        try:
            if method == SerializationMethod.JSON:
                return json.dumps(value).encode('utf-8')
            elif method == SerializationMethod.PICKLE:
                return pickle.dumps(value)
            elif method == SerializationMethod.STRING:
                return str(value).encode('utf-8')
            else:
                raise ValueError(f"Unsupported serialization method: {method}")
        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise
    
    def _deserialize(self, data: bytes, method: SerializationMethod = SerializationMethod.PICKLE) -> Any:
        """Deserialize value from storage"""
        try:
            if method == SerializationMethod.JSON:
                return json.loads(data.decode('utf-8'))
            elif method == SerializationMethod.PICKLE:
                return pickle.loads(data)
            elif method == SerializationMethod.STRING:
                return data.decode('utf-8')
            else:
                raise ValueError(f"Unsupported serialization method: {method}")
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise
    
    async def get(
        self,
        key: str,
        default: Any = None,
        serialization: SerializationMethod = SerializationMethod.PICKLE
    ) -> Any:
        """Get value from cache"""
        if not self._connected or not self.redis:
            return default
        
        start_time = datetime.utcnow()
        
        try:
            data = await self.redis.get(key)
            
            if data is None:
                self.metrics.misses += 1
                return default
            
            value = self._deserialize(data, serialization)
            self.metrics.hits += 1
            return value
        
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            self.metrics.errors += 1
            return default
        
        finally:
            self.metrics.total_requests += 1
            if self.config.enable_metrics:
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._update_average_response_time(response_time)
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialization: SerializationMethod = SerializationMethod.PICKLE
    ) -> bool:
        """Set value in cache"""
        if not self._connected or not self.redis:
            return False
        
        try:
            serialized_value = self._serialize(value, serialization)
            
            # Use default TTL if not specified
            cache_ttl = ttl or self.config.default_ttl
            
            await self.redis.setex(key, cache_ttl, serialized_value)
            self.metrics.sets += 1
            return True
        
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            self.metrics.errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._connected or not self.redis:
            return False
        
        try:
            result = await self.redis.delete(key)
            self.metrics.deletes += 1
            return result > 0
        
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            self.metrics.errors += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._connected or not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key"""
        if not self._connected or not self.redis:
            return False
        
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire failed for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self._connected or not self.redis:
            return -1
        
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL check failed for key {key}: {e}")
            return -1
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        if not self._connected or not self.redis:
            return []
        
        try:
            keys = await self.redis.keys(pattern)
            return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Cache keys search failed for pattern {pattern}: {e}")
            return []
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._connected or not self.redis:
            return 0
        
        try:
            keys = await self.keys(pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                self.metrics.deletes += deleted
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache pattern delete failed for pattern {pattern}: {e}")
            return 0
    
    async def flush_namespace(self, namespace: Union[str, CacheNamespace]) -> int:
        """Flush all keys in a namespace"""
        pattern = self._key_builder.pattern_key(namespace)
        return await self.delete_pattern(pattern)
    
    async def mget(self, keys: List[str], serialization: SerializationMethod = SerializationMethod.PICKLE) -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not self._connected or not self.redis or not keys:
            return {}
        
        try:
            values = await self.redis.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = self._deserialize(value, serialization)
                        self.metrics.hits += 1
                    except Exception as e:
                        logger.warning(f"Failed to deserialize value for key {key}: {e}")
                        self.metrics.errors += 1
                else:
                    self.metrics.misses += 1
            
            return result
        
        except Exception as e:
            logger.error(f"Cache mget failed: {e}")
            self.metrics.errors += 1
            return {}
    
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None, serialization: SerializationMethod = SerializationMethod.PICKLE) -> bool:
        """Set multiple values in cache"""
        if not self._connected or not self.redis or not mapping:
            return False
        
        try:
            # Serialize all values
            serialized_mapping = {}
            for key, value in mapping.items():
                serialized_mapping[key] = self._serialize(value, serialization)
            
            # Set all values
            await self.redis.mset(serialized_mapping)
            
            # Set TTL if specified
            if ttl:
                pipeline = self.redis.pipeline()
                for key in mapping.keys():
                    pipeline.expire(key, ttl)
                await pipeline.execute()
            
            self.metrics.sets += len(mapping)
            return True
        
        except Exception as e:
            logger.error(f"Cache mset failed: {e}")
            self.metrics.errors += 1
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a numeric value"""
        if not self._connected or not self.redis:
            return None
        
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            return None
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis server information"""
        if not self._connected or not self.redis:
            return {}
        
        try:
            info = await self.redis.info()
            return {
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "evicted_keys": info.get("evicted_keys"),
                "expired_keys": info.get("expired_keys")
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}
    
    def _update_average_response_time(self, response_time_ms: float) -> None:
        """Update average response time metric"""
        if self.metrics.total_requests == 1:
            self.metrics.average_response_time_ms = response_time_ms
        else:
            # Calculate running average
            total_time = self.metrics.average_response_time_ms * (self.metrics.total_requests - 1)
            self.metrics.average_response_time_ms = (total_time + response_time_ms) / self.metrics.total_requests
    
    def get_metrics(self) -> CacheMetrics:
        """Get current cache metrics"""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset cache metrics"""
        self.metrics = CacheMetrics()


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        config = CacheConfig()
        _cache_instance = RedisCache(config)
    return _cache_instance


async def init_cache(config: Optional[CacheConfig] = None) -> RedisCache:
    """Initialize global cache instance"""
    global _cache_instance
    if config is None:
        config = CacheConfig()
    
    _cache_instance = RedisCache(config)
    await _cache_instance.connect()
    return _cache_instance


async def close_cache() -> None:
    """Close global cache instance"""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.disconnect()
        _cache_instance = None


# Decorator for caching function results
def cached(
    namespace: Union[str, CacheNamespace],
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
    serialization: SerializationMethod = SerializationMethod.PICKLE,
    cache_instance: Optional[RedisCache] = None
):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = cache_instance or get_cache()
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building
                func_name = func.__name__
                args_hash = CacheKeyBuilder.hash_key((args, kwargs))
                cache_key = CacheKeyBuilder.build_key(namespace, func_name, args_hash)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key, serialization=serialization)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl, serialization=serialization)
            
            return result
        
        return wrapper
    return decorator


# Context manager for cache operations
@asynccontextmanager
async def cache_context(config: Optional[CacheConfig] = None):
    """Context manager for cache operations"""
    cache = await init_cache(config)
    try:
        yield cache
    finally:
        await close_cache()


# Utility functions for common cache operations
class CacheUtils:
    """Utility functions for common cache operations"""
    
    @staticmethod
    async def warm_cache(
        cache: RedisCache,
        data_loader: Callable,
        namespace: Union[str, CacheNamespace],
        keys: List[str],
        ttl: Optional[int] = None
    ) -> None:
        """Warm cache with data"""
        try:
            # Load data
            data = await data_loader(keys)
            
            # Build cache mapping
            cache_mapping = {}
            for key in keys:
                if key in data:
                    cache_key = CacheKeyBuilder.build_key(namespace, key)
                    cache_mapping[cache_key] = data[key]
            
            # Set in cache
            if cache_mapping:
                await cache.mset(cache_mapping, ttl=ttl)
                logger.info(f"Warmed cache with {len(cache_mapping)} items in namespace {namespace}")
        
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
    
    @staticmethod
    async def invalidate_related(
        cache: RedisCache,
        namespace: Union[str, CacheNamespace],
        related_keys: List[str]
    ) -> int:
        """Invalidate related cache entries"""
        total_deleted = 0
        
        for key in related_keys:
            pattern = CacheKeyBuilder.build_key(namespace, key, "*")
            deleted = await cache.delete_pattern(pattern)
            total_deleted += deleted
        
        return total_deleted
    
    @staticmethod
    async def get_cache_stats(cache: RedisCache) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        metrics = cache.get_metrics()
        redis_info = await cache.get_info()
        
        return {
            "cache_metrics": asdict(metrics),
            "redis_info": redis_info,
            "health_status": "healthy" if cache._connected else "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }