"""Caching integration for Design Service.

Provides Redis-based caching for expensive 3D calculations, database queries,
and design optimization results with multi-tenant support.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union
from functools import wraps

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

try:
    from cache import (
        CacheManager, get_cache_manager, cached, invalidate_cache,
        CacheConfig, CacheStats
    )
    from cache.config import get_config_for_environment, get_cache_preset
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    CacheManager = None

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

# Global cache manager instance
_design_cache_manager: Optional[CacheManager] = None


async def initialize_design_cache() -> bool:
    """Initialize cache manager for design service."""
    global _design_cache_manager
    
    if not CACHE_AVAILABLE:
        logger.warning("Cache not available, caching disabled for design service")
        return False
    
    try:
        # Get cache configuration
        config = get_config_for_environment()
        config.key_prefix = "nextgen_design"
        
        # Override with design-specific settings
        settings = get_settings()
        if hasattr(settings, 'REDIS_HOST'):
            config.host = settings.REDIS_HOST
        if hasattr(settings, 'REDIS_PORT'):
            config.port = settings.REDIS_PORT
        if hasattr(settings, 'REDIS_PASSWORD'):
            config.password = settings.REDIS_PASSWORD
        
        # Initialize cache manager
        _design_cache_manager = await get_cache_manager(config)
        
        if _design_cache_manager and _design_cache_manager.is_healthy:
            logger.info("Design service cache initialized successfully")
            return True
        else:
            logger.warning("Failed to initialize design service cache")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing design cache: {e}")
        return False


async def get_design_cache() -> Optional[CacheManager]:
    """Get design cache manager instance."""
    global _design_cache_manager
    
    if _design_cache_manager is None:
        await initialize_design_cache()
    
    return _design_cache_manager


async def close_design_cache():
    """Close design cache manager."""
    global _design_cache_manager
    
    if _design_cache_manager:
        await _design_cache_manager.close()
        _design_cache_manager = None
        logger.info("Design cache closed")


# Cache decorators for specific design operations

def cache_3d_calculation(ttl: int = 2700):  # 45 minutes
    """Cache decorator for expensive 3D calculations."""
    preset = get_cache_preset('design_calculations')
    return cached(ttl=ttl, namespace=preset['namespace'])


def cache_solar_analysis(ttl: int = 1800):  # 30 minutes
    """Cache decorator for solar analysis results."""
    return cached(ttl=ttl, namespace='solar_analysis')


def cache_shading_analysis(ttl: int = 2100):  # 35 minutes
    """Cache decorator for shading analysis results."""
    return cached(ttl=ttl, namespace='shading_analysis')


def cache_layout_optimization(ttl: int = 3600):  # 1 hour
    """Cache decorator for layout optimization results."""
    return cached(ttl=ttl, namespace='layout_optimization')


def cache_design_query(ttl: int = 600):  # 10 minutes
    """Cache decorator for database queries."""
    preset = get_cache_preset('fast_queries')
    return cached(ttl=ttl, namespace=preset['namespace'])


def cache_component_data(ttl: int = 86400):  # 24 hours
    """Cache decorator for static component data."""
    preset = get_cache_preset('static_data')
    return cached(ttl=ttl, namespace=preset['namespace'])


# Cache invalidation helpers

async def invalidate_design_cache(design_id: str, tenant_id: Optional[str] = None):
    """Invalidate all cache entries for a specific design."""
    cache_manager = await get_design_cache()
    if not cache_manager:
        return
    
    patterns = [
        f"*design_id:{design_id}*",
        f"*design:{design_id}*",
        f"*{design_id}*"
    ]
    
    total_invalidated = 0
    for pattern in patterns:
        invalidated = await cache_manager.invalidate_pattern(
            pattern, tenant_id=tenant_id, namespace='design_calculations'
        )
        total_invalidated += invalidated
    
    logger.info(f"Invalidated {total_invalidated} cache entries for design {design_id}")


async def invalidate_project_cache(project_id: str, tenant_id: Optional[str] = None):
    """Invalidate all cache entries for a specific project."""
    cache_manager = await get_design_cache()
    if not cache_manager:
        return
    
    patterns = [
        f"*project_id:{project_id}*",
        f"*project:{project_id}*",
        f"*{project_id}*"
    ]
    
    total_invalidated = 0
    namespaces = ['design_calculations', 'solar_analysis', 'shading_analysis', 'layout_optimization']
    
    for namespace in namespaces:
        for pattern in patterns:
            invalidated = await cache_manager.invalidate_pattern(
                pattern, tenant_id=tenant_id, namespace=namespace
            )
            total_invalidated += invalidated
    
    logger.info(f"Invalidated {total_invalidated} cache entries for project {project_id}")


async def invalidate_user_cache(user_id: str, tenant_id: Optional[str] = None):
    """Invalidate all cache entries for a specific user."""
    cache_manager = await get_design_cache()
    if not cache_manager:
        return
    
    patterns = [
        f"*user_id:{user_id}*",
        f"*user:{user_id}*"
    ]
    
    total_invalidated = 0
    for pattern in patterns:
        invalidated = await cache_manager.invalidate_pattern(
            pattern, tenant_id=tenant_id
        )
        total_invalidated += invalidated
    
    logger.info(f"Invalidated {total_invalidated} cache entries for user {user_id}")


# Cache warming functions

async def warm_component_cache(tenant_id: Optional[str] = None):
    """Pre-load frequently accessed component data into cache."""
    cache_manager = await get_design_cache()
    if not cache_manager:
        return
    
    logger.info("Starting component cache warming")
    
    try:
        # This would typically load common solar panels, inverters, etc.
        # For now, we'll just log the intent
        logger.info("Component cache warming completed")
        
    except Exception as e:
        logger.error(f"Error warming component cache: {e}")


async def warm_design_templates_cache(tenant_id: Optional[str] = None):
    """Pre-load design templates into cache."""
    cache_manager = await get_design_cache()
    if not cache_manager:
        return
    
    logger.info("Starting design templates cache warming")
    
    try:
        # This would typically load common design templates
        logger.info("Design templates cache warming completed")
        
    except Exception as e:
        logger.error(f"Error warming design templates cache: {e}")


# Cache statistics and monitoring

async def get_design_cache_stats() -> Optional[Dict[str, Any]]:
    """Get cache statistics for monitoring."""
    cache_manager = await get_design_cache()
    if not cache_manager:
        return None
    
    stats = await cache_manager.get_stats()
    return {
        'hits': stats.hits,
        'misses': stats.misses,
        'hit_ratio': stats.hit_ratio,
        'sets': stats.sets,
        'deletes': stats.deletes,
        'errors': stats.errors,
        'total_requests': stats.total_requests,
        'avg_response_time': stats.avg_response_time,
        'is_healthy': cache_manager.is_healthy,
        'last_reset': stats.last_reset.isoformat() if stats.last_reset else None
    }


async def reset_design_cache_stats():
    """Reset cache statistics."""
    cache_manager = await get_design_cache()
    if cache_manager:
        await cache_manager.reset_stats()
        logger.info("Design cache statistics reset")


# Cache health check

async def check_design_cache_health() -> Dict[str, Any]:
    """Check cache health status."""
    cache_manager = await get_design_cache()
    
    if not cache_manager:
        return {
            'status': 'unavailable',
            'message': 'Cache manager not initialized',
            'is_healthy': False
        }
    
    is_healthy = cache_manager.is_healthy
    
    return {
        'status': 'healthy' if is_healthy else 'unhealthy',
        'message': 'Cache is operational' if is_healthy else 'Cache connection issues',
        'is_healthy': is_healthy
    }


# Context manager for cache operations

class CacheContext:
    """Context manager for cache operations with automatic cleanup."""
    
    def __init__(self, tenant_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.cache_manager = None
    
    async def __aenter__(self):
        self.cache_manager = await get_design_cache()
        return self.cache_manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cache manager is global, don't close it here
        pass


# Utility functions

def generate_cache_key(*args, **kwargs) -> str:
    """Generate cache key for design operations."""
    key_parts = []
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))
    
    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        else:
            key_parts.append(f"{k}:{hash(str(v))}")
    
    return ":".join(key_parts)


def is_cache_available() -> bool:
    """Check if caching is available."""
    return CACHE_AVAILABLE