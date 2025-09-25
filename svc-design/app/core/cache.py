"""Cache management for the Design Service.

Provides Redis-based caching with serialization,
expiration, and cache invalidation strategies.
"""

import json
import pickle
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Union, Callable
from uuid import UUID

import redis
from redis.exceptions import ConnectionError, TimeoutError

from .config import get_settings
from .logging import get_logger


logger = get_logger(__name__)


class CacheManager:
    """Redis cache manager with advanced features."""
    
    def __init__(self, redis_url: str = None):
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.REDIS_URL
        self._redis_client = None
        self._connection_pool = None
    
    @property
    def redis_client(self) -> redis.Redis:
        """Get Redis client with connection pooling."""
        if self._redis_client is None:
            try:
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.settings.REDIS_POOL_SIZE,
                    socket_timeout=self.settings.REDIS_TIMEOUT,
                    socket_connect_timeout=self.settings.REDIS_TIMEOUT,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                self._redis_client = redis.Redis(
                    connection_pool=self._connection_pool,
                    decode_responses=False  # We handle encoding ourselves
                )
                
                # Test connection
                self._redis_client.ping()
                logger.info("Redis connection established")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                # Use a mock client that does nothing
                self._redis_client = MockRedisClient()
        
        return self._redis_client
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            # Try JSON first for simple types
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                return json.dumps(value, default=str).encode('utf-8')
            else:
                # Use pickle for complex objects
                return pickle.dumps(value)
        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise ValueError(f"Cannot serialize value: {e}")
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Try JSON first
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            return None
    
    def _make_key(self, key: str, namespace: str = None) -> str:
        """Create namespaced cache key."""
        namespace = namespace or "design_service"
        return f"{namespace}:{key}"
    
    def get(self, key: str, namespace: str = None) -> Any:
        """Get value from cache."""
        try:
            cache_key = self._make_key(key, namespace)
            data = self.redis_client.get(cache_key)
            
            if data is None:
                return None
            
            return self._deserialize_value(data)
            
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = None,
        namespace: str = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            cache_key = self._make_key(key, namespace)
            serialized_value = self._serialize_value(value)
            
            if ttl:
                result = self.redis_client.setex(cache_key, ttl, serialized_value)
            else:
                result = self.redis_client.set(cache_key, serialized_value)
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    def delete(self, key: str, namespace: str = None) -> bool:
        """Delete value from cache."""
        try:
            cache_key = self._make_key(key, namespace)
            result = self.redis_client.delete(cache_key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False
    
    def exists(self, key: str, namespace: str = None) -> bool:
        """Check if key exists in cache."""
        try:
            cache_key = self._make_key(key, namespace)
            return bool(self.redis_client.exists(cache_key))
            
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False
    
    def expire(self, key: str, ttl: int, namespace: str = None) -> bool:
        """Set expiration for existing key."""
        try:
            cache_key = self._make_key(key, namespace)
            result = self.redis_client.expire(cache_key, ttl)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache expire failed for key {key}: {e}")
            return False
    
    def ttl(self, key: str, namespace: str = None) -> int:
        """Get TTL for key."""
        try:
            cache_key = self._make_key(key, namespace)
            return self.redis_client.ttl(cache_key)
            
        except Exception as e:
            logger.error(f"Cache TTL check failed for key {key}: {e}")
            return -1
    
    def increment(self, key: str, amount: int = 1, namespace: str = None) -> int:
        """Increment numeric value."""
        try:
            cache_key = self._make_key(key, namespace)
            return self.redis_client.incrby(cache_key, amount)
            
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            return 0
    
    def decrement(self, key: str, amount: int = 1, namespace: str = None) -> int:
        """Decrement numeric value."""
        try:
            cache_key = self._make_key(key, namespace)
            return self.redis_client.decrby(cache_key, amount)
            
        except Exception as e:
            logger.error(f"Cache decrement failed for key {key}: {e}")
            return 0
    
    def get_many(self, keys: List[str], namespace: str = None) -> Dict[str, Any]:
        """Get multiple values from cache."""
        try:
            cache_keys = [self._make_key(key, namespace) for key in keys]
            values = self.redis_client.mget(cache_keys)
            
            result = {}
            for i, key in enumerate(keys):
                if values[i] is not None:
                    result[key] = self._deserialize_value(values[i])
                else:
                    result[key] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Cache get_many failed: {e}")
            return {key: None for key in keys}
    
    def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: int = None,
        namespace: str = None
    ) -> bool:
        """Set multiple values in cache."""
        try:
            pipe = self.redis_client.pipeline()
            
            for key, value in mapping.items():
                cache_key = self._make_key(key, namespace)
                serialized_value = self._serialize_value(value)
                
                if ttl:
                    pipe.setex(cache_key, ttl, serialized_value)
                else:
                    pipe.set(cache_key, serialized_value)
            
            results = pipe.execute()
            return all(results)
            
        except Exception as e:
            logger.error(f"Cache set_many failed: {e}")
            return False
    
    def delete_many(self, keys: List[str], namespace: str = None) -> int:
        """Delete multiple values from cache."""
        try:
            cache_keys = [self._make_key(key, namespace) for key in keys]
            return self.redis_client.delete(*cache_keys)
            
        except Exception as e:
            logger.error(f"Cache delete_many failed: {e}")
            return 0
    
    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        try:
            pattern = f"{namespace}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                return self.redis_client.delete(*keys)
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear_namespace failed for {namespace}: {e}")
            return 0
    
    def get_keys(self, pattern: str = "*", namespace: str = None) -> List[str]:
        """Get keys matching pattern."""
        try:
            if namespace:
                pattern = f"{namespace}:{pattern}"
            
            keys = self.redis_client.keys(pattern)
            
            # Remove namespace prefix
            if namespace:
                prefix = f"{namespace}:"
                return [key.decode('utf-8').replace(prefix, '', 1) for key in keys]
            else:
                return [key.decode('utf-8') for key in keys]
            
        except Exception as e:
            logger.error(f"Cache get_keys failed: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Check cache health."""
        try:
            start_time = datetime.utcnow()
            self.redis_client.ping()
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            info = self.redis_client.info()
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', 'unknown'),
                'redis_version': info.get('redis_version', 'unknown'),
                'uptime_seconds': info.get('uptime_in_seconds', 0)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def close(self):
        """Close Redis connection."""
        if self._connection_pool:
            self._connection_pool.disconnect()
            logger.info("Redis connection closed")


class MockRedisClient:
    """Mock Redis client for testing or when Redis is unavailable."""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
    
    def get(self, key):
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return None
        return self._data.get(key)
    
    def set(self, key, value):
        self._data[key] = value
        return True
    
    def setex(self, key, ttl, value):
        self._data[key] = value
        self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
        return True
    
    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                if key in self._expiry:
                    del self._expiry[key]
                count += 1
        return count
    
    def exists(self, key):
        return key in self._data
    
    def expire(self, key, ttl):
        if key in self._data:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
            return True
        return False
    
    def ttl(self, key):
        if key in self._expiry:
            remaining = (self._expiry[key] - datetime.utcnow()).total_seconds()
            return int(remaining) if remaining > 0 else -2
        return -1
    
    def incrby(self, key, amount):
        current = int(self._data.get(key, 0))
        self._data[key] = str(current + amount)
        return current + amount
    
    def decrby(self, key, amount):
        return self.incrby(key, -amount)
    
    def mget(self, keys):
        return [self.get(key) for key in keys]
    
    def keys(self, pattern):
        # Simple pattern matching
        if pattern == "*":
            return list(self._data.keys())
        # Add more pattern matching as needed
        return []
    
    def ping(self):
        return True
    
    def info(self):
        return {
            'connected_clients': 1,
            'used_memory_human': '1M',
            'redis_version': 'mock',
            'uptime_in_seconds': 3600
        }
    
    def pipeline(self):
        return MockPipeline(self)


class MockPipeline:
    """Mock Redis pipeline."""
    
    def __init__(self, client):
        self.client = client
        self.commands = []
    
    def set(self, key, value):
        self.commands.append(('set', key, value))
        return self
    
    def setex(self, key, ttl, value):
        self.commands.append(('setex', key, ttl, value))
        return self
    
    def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == 'set':
                results.append(self.client.set(cmd[1], cmd[2]))
            elif cmd[0] == 'setex':
                results.append(self.client.setex(cmd[1], cmd[2], cmd[3]))
        return results


# Global cache manager instance
cache_manager = CacheManager()


def cached(
    ttl: int = 300,
    namespace: str = None,
    key_func: Callable = None
):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                
                # Add args
                for arg in args:
                    if isinstance(arg, (str, int, float, bool)):
                        key_parts.append(str(arg))
                    elif isinstance(arg, UUID):
                        key_parts.append(str(arg))
                    else:
                        key_parts.append(str(hash(str(arg))))
                
                # Add kwargs
                for k, v in sorted(kwargs.items()):
                    if isinstance(v, (str, int, float, bool)):
                        key_parts.append(f"{k}:{v}")
                    elif isinstance(v, UUID):
                        key_parts.append(f"{k}:{v}")
                    else:
                        key_parts.append(f"{k}:{hash(str(v))}")
                
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)
            
            if result is not None:
                cache_manager.set(cache_key, result, ttl, namespace)
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate(pattern: str, namespace: str = None):
    """Invalidate cache entries matching pattern."""
    try:
        keys = cache_manager.get_keys(pattern, namespace)
        if keys:
            return cache_manager.delete_many(keys, namespace)
        return 0
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        return 0


def cache_warm_up(data: Dict[str, Any], ttl: int = 300, namespace: str = None):
    """Warm up cache with initial data."""
    try:
        return cache_manager.set_many(data, ttl, namespace)
    except Exception as e:
        logger.error(f"Cache warm-up failed: {e}")
        return False


def get_cache_stats(namespace: str = None) -> Dict[str, Any]:
    """Get cache statistics."""
    try:
        keys = cache_manager.get_keys("*", namespace)
        
        stats = {
            'total_keys': len(keys),
            'namespace': namespace or 'all',
            'health': cache_manager.health_check()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {
            'total_keys': 0,
            'namespace': namespace or 'all',
            'health': {'status': 'unhealthy', 'error': str(e)}
        }


# Cache health check function
def check_cache_health() -> Dict[str, Any]:
    """Check cache health status."""
    return cache_manager.health_check()