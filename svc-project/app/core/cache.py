#!/usr/bin/env python3
"""
Caching service for the Project Management Service

Provides Redis-based caching for expensive operations like critical path calculations.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from shared.cache import (
    RedisCache, CacheConfig, CacheNamespace, SerializationMethod,
    get_cache, init_cache, cache_context
)
from app.core.config import get_settings
from app.core.logging import get_logger, log_cache_operation

settings = get_settings()
logger = get_logger(__name__)

# Cache instance
_cache_instance: Optional[RedisCache] = None


class CriticalPathCache:
    """Cache service for critical path calculations."""
    
    def __init__(self, cache: RedisCache):
        self.cache = cache
        self.namespace = "critical_path"
        self.default_ttl = 600  # 10 minutes
    
    def _generate_cache_key(self, project_id: int, task_graph_hash: str) -> str:
        """Generate cache key for critical path."""
        return f"{self.namespace}:{project_id}:{task_graph_hash}"
    
    def _calculate_task_graph_hash(self, tasks: List[Dict[str, Any]]) -> str:
        """Calculate hash of task graph for cache invalidation."""
        # Sort tasks by ID to ensure consistent hashing
        sorted_tasks = sorted(tasks, key=lambda x: x.get('id', 0))
        
        # Create a simplified representation for hashing
        task_data = []
        for task in sorted_tasks:
            task_data.append({
                'id': task.get('id'),
                'duration': task.get('duration_hours', 0),
                'dependencies': sorted(task.get('depends_on', [])),
                'status': task.get('status')
            })
        
        # Generate hash
        task_json = json.dumps(task_data, sort_keys=True)
        return hashlib.md5(task_json.encode()).hexdigest()
    
    async def get_critical_path(self, project_id: int, tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get cached critical path or return None if not found."""
        start_time = time.time()
        
        try:
            task_graph_hash = self._calculate_task_graph_hash(tasks)
            cache_key = self._generate_cache_key(project_id, task_graph_hash)
            
            result = await self.cache.get(cache_key)
            duration_ms = (time.time() - start_time) * 1000
            
            if result is not None:
                log_cache_operation("get", cache_key, hit=True, duration_ms=duration_ms)
                logger.info(f"Critical path cache hit for project {project_id}")
                return result
            else:
                log_cache_operation("get", cache_key, hit=False, duration_ms=duration_ms)
                logger.info(f"Critical path cache miss for project {project_id}")
                return None
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Error getting critical path from cache: {e}")
            log_cache_operation("get", f"project:{project_id}", hit=False, duration_ms=duration_ms)
            return None
    
    async def set_critical_path(self, project_id: int, tasks: List[Dict[str, Any]], 
                               critical_path_data: Dict[str, Any]) -> bool:
        """Cache critical path calculation result."""
        start_time = time.time()
        
        try:
            task_graph_hash = self._calculate_task_graph_hash(tasks)
            cache_key = self._generate_cache_key(project_id, task_graph_hash)
            
            # Add metadata to cached data
            cache_data = {
                'critical_path': critical_path_data,
                'calculated_at': datetime.utcnow().isoformat(),
                'project_id': project_id,
                'task_graph_hash': task_graph_hash
            }
            
            await self.cache.set(cache_key, cache_data, ttl=self.default_ttl)
            
            duration_ms = (time.time() - start_time) * 1000
            log_cache_operation("set", cache_key, hit=False, duration_ms=duration_ms)
            logger.info(f"Critical path cached for project {project_id}")
            return True
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Error caching critical path: {e}")
            log_cache_operation("set", f"project:{project_id}", hit=False, duration_ms=duration_ms)
            return False
    
    async def invalidate_project_cache(self, project_id: int) -> bool:
        """Invalidate all cached critical paths for a project."""
        try:
            # Get all keys matching the project pattern
            pattern = f"{self.namespace}:{project_id}:*"
            keys = await self.cache.redis.keys(pattern)
            
            if keys:
                await self.cache.redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} critical path cache entries for project {project_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating project cache: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = await self.cache.get_info()
            pattern = f"{self.namespace}:*"
            keys = await self.cache.redis.keys(pattern)
            
            return {
                'total_keys': len(keys),
                'namespace': self.namespace,
                'redis_info': {
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}


async def get_critical_path_cache() -> CriticalPathCache:
    """Get critical path cache instance."""
    global _cache_instance
    
    if _cache_instance is None:
        # Initialize Redis cache
        config = CacheConfig(
            host=settings.REDIS_URL.split('://')[1].split(':')[0] if settings.REDIS_URL else 'localhost',
            port=int(settings.REDIS_URL.split(':')[-1]) if settings.REDIS_URL and ':' in settings.REDIS_URL else 6379,
            db=0,
            max_connections=20,
            socket_timeout=5.0,
            default_ttl=settings.CACHE_TTL_SECONDS,
            key_prefix='svc_project'
        )
        
        _cache_instance = await init_cache(config)
    
    return CriticalPathCache(_cache_instance)


async def close_cache():
    """Close cache connection."""
    global _cache_instance
    if _cache_instance:
        await _cache_instance.disconnect()
        _cache_instance = None


# Decorator for caching critical path calculations
def cache_critical_path(ttl: int = 600):
    """Decorator to cache critical path calculations."""
    def decorator(func):
        async def wrapper(project_id: int, tasks: List[Dict[str, Any]], *args, **kwargs):
            if not settings.ENABLE_CACHING:
                return await func(project_id, tasks, *args, **kwargs)
            
            cache = await get_critical_path_cache()
            
            # Try to get from cache first
            cached_result = await cache.get_critical_path(project_id, tasks)
            if cached_result is not None:
                return cached_result['critical_path']
            
            # Calculate and cache result
            start_time = time.time()
            result = await func(project_id, tasks, *args, **kwargs)
            calculation_time = (time.time() - start_time) * 1000
            
            # Cache the result
            await cache.set_critical_path(project_id, tasks, result)
            
            logger.info(f"Critical path calculated in {calculation_time:.2f}ms for project {project_id}")
            return result
        
        return wrapper
    return decorator