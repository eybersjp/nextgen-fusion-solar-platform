"""Cache Integration for Design Service

Integrates Redis caching for expensive design operations:
- Layout optimization results
- 3D calculations and spatial analysis
- Shading analysis results
- Component specifications
- Design validation results
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import asdict
import logging

# Import from shared cache module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from cache import (
    RedisCache, CacheConfig, CacheNamespace, CacheKeyBuilder,
    SerializationMethod, cached, get_cache
)

# Import design service models
from .layout_optimizer import (
    OptimizationResult, LayoutSuggestion, ShadingResult,
    Point3D, BoundingBox, PanelPlacement, OptimizationConstraints
)

logger = logging.getLogger(__name__)


class DesignCacheService:
    """Cache service for design operations"""
    
    def __init__(self, cache: Optional[RedisCache] = None):
        self.cache = cache or get_cache()
        self.key_builder = CacheKeyBuilder()
    
    # Layout Optimization Caching
    
    async def get_cached_optimization(
        self,
        design_id: str,
        constraints: OptimizationConstraints,
        strategy: str
    ) -> Optional[OptimizationResult]:
        """Get cached layout optimization result"""
        cache_key = self._build_optimization_key(design_id, constraints, strategy)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_optimization_result(
        self,
        design_id: str,
        constraints: OptimizationConstraints,
        strategy: str,
        result: OptimizationResult,
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache layout optimization result"""
        cache_key = self._build_optimization_key(design_id, constraints, strategy)
        return await self.cache.set(
            cache_key,
            result,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_optimization_key(
        self,
        design_id: str,
        constraints: OptimizationConstraints,
        strategy: str
    ) -> str:
        """Build cache key for optimization results"""
        # Create hash from constraints for consistent key
        constraints_hash = self.key_builder.hash_key(asdict(constraints))
        return self.key_builder.build_key(
            CacheNamespace.LAYOUT_OPTIMIZATION,
            design_id,
            strategy,
            constraints_hash
        )
    
    # Shading Analysis Caching
    
    async def get_cached_shading_analysis(
        self,
        design_id: str,
        analysis_params: Dict[str, Any]
    ) -> Optional[ShadingResult]:
        """Get cached shading analysis result"""
        cache_key = self._build_shading_key(design_id, analysis_params)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_shading_analysis(
        self,
        design_id: str,
        analysis_params: Dict[str, Any],
        result: ShadingResult,
        ttl: int = 7200  # 2 hours
    ) -> bool:
        """Cache shading analysis result"""
        cache_key = self._build_shading_key(design_id, analysis_params)
        return await self.cache.set(
            cache_key,
            result,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_shading_key(
        self,
        design_id: str,
        analysis_params: Dict[str, Any]
    ) -> str:
        """Build cache key for shading analysis"""
        params_hash = self.key_builder.hash_key(analysis_params)
        return self.key_builder.build_key(
            CacheNamespace.DESIGN_CALCULATIONS,
            "shading",
            design_id,
            params_hash
        )
    
    # Component Specifications Caching
    
    async def get_cached_component_specs(
        self,
        component_type: str,
        specifications: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached component specifications"""
        cache_key = self._build_component_key(component_type, specifications)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_component_specs(
        self,
        component_type: str,
        specifications: Dict[str, Any],
        specs_data: Dict[str, Any],
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """Cache component specifications"""
        cache_key = self._build_component_key(component_type, specifications)
        return await self.cache.set(
            cache_key,
            specs_data,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_component_key(
        self,
        component_type: str,
        specifications: Dict[str, Any]
    ) -> str:
        """Build cache key for component specifications"""
        specs_hash = self.key_builder.hash_key(specifications)
        return self.key_builder.build_key(
            CacheNamespace.COMPONENT_SPECS,
            component_type,
            specs_hash
        )
    
    # Design Validation Caching
    
    async def get_cached_validation(
        self,
        design_id: str,
        validation_rules: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get cached design validation result"""
        cache_key = self._build_validation_key(design_id, validation_rules)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_validation_result(
        self,
        design_id: str,
        validation_rules: List[str],
        validation_result: Dict[str, Any],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache design validation result"""
        cache_key = self._build_validation_key(design_id, validation_rules)
        return await self.cache.set(
            cache_key,
            validation_result,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_validation_key(
        self,
        design_id: str,
        validation_rules: List[str]
    ) -> str:
        """Build cache key for validation results"""
        rules_hash = self.key_builder.hash_key(sorted(validation_rules))
        return self.key_builder.build_key(
            CacheNamespace.DESIGN_CALCULATIONS,
            "validation",
            design_id,
            rules_hash
        )
    
    # ML Suggestions Caching
    
    async def get_cached_ml_suggestions(
        self,
        design_id: str,
        context_params: Dict[str, Any]
    ) -> Optional[List[LayoutSuggestion]]:
        """Get cached ML layout suggestions"""
        cache_key = self._build_ml_suggestions_key(design_id, context_params)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_ml_suggestions(
        self,
        design_id: str,
        context_params: Dict[str, Any],
        suggestions: List[LayoutSuggestion],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache ML layout suggestions"""
        cache_key = self._build_ml_suggestions_key(design_id, context_params)
        return await self.cache.set(
            cache_key,
            suggestions,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_ml_suggestions_key(
        self,
        design_id: str,
        context_params: Dict[str, Any]
    ) -> str:
        """Build cache key for ML suggestions"""
        context_hash = self.key_builder.hash_key(context_params)
        return self.key_builder.build_key(
            CacheNamespace.LAYOUT_OPTIMIZATION,
            "ml_suggestions",
            design_id,
            context_hash
        )
    
    # Cache Management
    
    async def invalidate_design_cache(self, design_id: str) -> int:
        """Invalidate all cache entries for a design"""
        patterns = [
            self.key_builder.pattern_key(CacheNamespace.LAYOUT_OPTIMIZATION, f"*{design_id}*"),
            self.key_builder.pattern_key(CacheNamespace.DESIGN_CALCULATIONS, f"*{design_id}*")
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} cache entries for design {design_id}")
        return total_deleted
    
    async def warm_component_cache(
        self,
        component_types: List[str],
        common_specs: List[Dict[str, Any]]
    ) -> None:
        """Warm cache with common component specifications"""
        try:
            # This would typically load from a component database
            # For now, we'll create a placeholder implementation
            cache_mapping = {}
            
            for component_type in component_types:
                for specs in common_specs:
                    cache_key = self._build_component_key(component_type, specs)
                    # In a real implementation, this would fetch actual component data
                    mock_data = {
                        "component_type": component_type,
                        "specifications": specs,
                        "cached_at": datetime.utcnow().isoformat()
                    }
                    cache_mapping[cache_key] = mock_data
            
            if cache_mapping:
                await self.cache.mset(
                    cache_mapping,
                    ttl=86400,  # 24 hours
                    serialization=SerializationMethod.JSON
                )
                logger.info(f"Warmed component cache with {len(cache_mapping)} entries")
        
        except Exception as e:
            logger.error(f"Failed to warm component cache: {e}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for design service"""
        try:
            # Get overall cache metrics
            metrics = self.cache.get_metrics()
            
            # Get namespace-specific key counts
            namespace_stats = {}
            for namespace in [CacheNamespace.LAYOUT_OPTIMIZATION, 
                            CacheNamespace.DESIGN_CALCULATIONS,
                            CacheNamespace.COMPONENT_SPECS]:
                pattern = self.key_builder.pattern_key(namespace)
                keys = await self.cache.keys(pattern)
                namespace_stats[namespace.value] = len(keys)
            
            return {
                "overall_metrics": asdict(metrics),
                "namespace_stats": namespace_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {}


# Decorators for caching design operations

def cache_layout_optimization(
    ttl: int = 3600,
    cache_service: Optional[DesignCacheService] = None
):
    """Decorator for caching layout optimization results"""
    return cached(
        namespace=CacheNamespace.LAYOUT_OPTIMIZATION,
        ttl=ttl,
        serialization=SerializationMethod.PICKLE,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_shading_analysis(
    ttl: int = 7200,
    cache_service: Optional[DesignCacheService] = None
):
    """Decorator for caching shading analysis results"""
    return cached(
        namespace=CacheNamespace.DESIGN_CALCULATIONS,
        ttl=ttl,
        serialization=SerializationMethod.PICKLE,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_component_lookup(
    ttl: int = 86400,
    cache_service: Optional[DesignCacheService] = None
):
    """Decorator for caching component lookups"""
    return cached(
        namespace=CacheNamespace.COMPONENT_SPECS,
        ttl=ttl,
        serialization=SerializationMethod.JSON,
        cache_instance=cache_service.cache if cache_service else None
    )


# Global design cache service instance
_design_cache_service: Optional[DesignCacheService] = None


def get_design_cache_service() -> DesignCacheService:
    """Get global design cache service instance"""
    global _design_cache_service
    if _design_cache_service is None:
        _design_cache_service = DesignCacheService()
    return _design_cache_service