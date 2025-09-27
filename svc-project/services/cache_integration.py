"""Cache Integration for Project Service

Integrates Redis caching for expensive project operations:
- Task dependency calculations
- Critical path analysis
- Resource optimization results
- Project metrics and KPIs
- Gantt chart data
- Schedule optimization
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import asdict
import logging

# Import from shared cache module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from cache import (
    RedisCache, CacheConfig, CacheNamespace, CacheKeyBuilder,
    SerializationMethod, cached, get_cache
)

# Import project service models
from .task_dependency_service import (
    CriticalPathResult, ResourceConflict, ScheduleOptimization,
    ProjectMetrics, TaskDependencyService
)

logger = logging.getLogger(__name__)


class ProjectCacheService:
    """Cache service for project operations"""
    
    def __init__(self, cache: Optional[RedisCache] = None):
        self.cache = cache or get_cache()
        self.key_builder = CacheKeyBuilder()
    
    # Critical Path Caching
    
    async def get_cached_critical_path(
        self,
        project_id: str,
        task_version_hash: str
    ) -> Optional[CriticalPathResult]:
        """Get cached critical path calculation"""
        cache_key = self._build_critical_path_key(project_id, task_version_hash)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_critical_path(
        self,
        project_id: str,
        task_version_hash: str,
        result: CriticalPathResult,
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache critical path calculation result"""
        cache_key = self._build_critical_path_key(project_id, task_version_hash)
        return await self.cache.set(
            cache_key,
            result,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_critical_path_key(self, project_id: str, task_version_hash: str) -> str:
        """Build cache key for critical path"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "critical_path",
            project_id,
            task_version_hash
        )
    
    # Resource Optimization Caching
    
    async def get_cached_resource_optimization(
        self,
        project_id: str,
        resource_config_hash: str
    ) -> Optional[List[ResourceConflict]]:
        """Get cached resource optimization result"""
        cache_key = self._build_resource_optimization_key(project_id, resource_config_hash)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_resource_optimization(
        self,
        project_id: str,
        resource_config_hash: str,
        conflicts: List[ResourceConflict],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache resource optimization result"""
        cache_key = self._build_resource_optimization_key(project_id, resource_config_hash)
        return await self.cache.set(
            cache_key,
            conflicts,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_resource_optimization_key(self, project_id: str, resource_config_hash: str) -> str:
        """Build cache key for resource optimization"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "resource_optimization",
            project_id,
            resource_config_hash
        )
    
    # Schedule Optimization Caching
    
    async def get_cached_schedule_optimization(
        self,
        project_id: str,
        optimization_params_hash: str
    ) -> Optional[ScheduleOptimization]:
        """Get cached schedule optimization result"""
        cache_key = self._build_schedule_optimization_key(project_id, optimization_params_hash)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_schedule_optimization(
        self,
        project_id: str,
        optimization_params_hash: str,
        result: ScheduleOptimization,
        ttl: int = 2400  # 40 minutes
    ) -> bool:
        """Cache schedule optimization result"""
        cache_key = self._build_schedule_optimization_key(project_id, optimization_params_hash)
        return await self.cache.set(
            cache_key,
            result,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_schedule_optimization_key(self, project_id: str, optimization_params_hash: str) -> str:
        """Build cache key for schedule optimization"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "schedule_optimization",
            project_id,
            optimization_params_hash
        )
    
    # Project Metrics Caching
    
    async def get_cached_project_metrics(
        self,
        project_id: str,
        metrics_period: str
    ) -> Optional[ProjectMetrics]:
        """Get cached project metrics"""
        cache_key = self._build_project_metrics_key(project_id, metrics_period)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_project_metrics(
        self,
        project_id: str,
        metrics_period: str,
        metrics: ProjectMetrics,
        ttl: int = 900  # 15 minutes
    ) -> bool:
        """Cache project metrics"""
        cache_key = self._build_project_metrics_key(project_id, metrics_period)
        return await self.cache.set(
            cache_key,
            metrics,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_project_metrics_key(self, project_id: str, metrics_period: str) -> str:
        """Build cache key for project metrics"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "project_metrics",
            project_id,
            metrics_period
        )
    
    # Gantt Chart Data Caching
    
    async def get_cached_gantt_data(
        self,
        project_id: str,
        view_config_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached Gantt chart data"""
        cache_key = self._build_gantt_data_key(project_id, view_config_hash)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_gantt_data(
        self,
        project_id: str,
        view_config_hash: str,
        gantt_data: Dict[str, Any],
        ttl: int = 1200  # 20 minutes
    ) -> bool:
        """Cache Gantt chart data"""
        cache_key = self._build_gantt_data_key(project_id, view_config_hash)
        return await self.cache.set(
            cache_key,
            gantt_data,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_gantt_data_key(self, project_id: str, view_config_hash: str) -> str:
        """Build cache key for Gantt chart data"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "gantt_data",
            project_id,
            view_config_hash
        )
    
    # Task Dependencies Caching
    
    async def get_cached_task_dependencies(
        self,
        project_id: str,
        dependency_version_hash: str
    ) -> Optional[Dict[str, List[str]]]:
        """Get cached task dependencies graph"""
        cache_key = self._build_task_dependencies_key(project_id, dependency_version_hash)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_task_dependencies(
        self,
        project_id: str,
        dependency_version_hash: str,
        dependencies: Dict[str, List[str]],
        ttl: int = 7200  # 2 hours
    ) -> bool:
        """Cache task dependencies graph"""
        cache_key = self._build_task_dependencies_key(project_id, dependency_version_hash)
        return await self.cache.set(
            cache_key,
            dependencies,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_task_dependencies_key(self, project_id: str, dependency_version_hash: str) -> str:
        """Build cache key for task dependencies"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "task_dependencies",
            project_id,
            dependency_version_hash
        )
    
    # Project Timeline Caching
    
    async def get_cached_project_timeline(
        self,
        project_id: str,
        timeline_config_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached project timeline"""
        cache_key = self._build_project_timeline_key(project_id, timeline_config_hash)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_project_timeline(
        self,
        project_id: str,
        timeline_config_hash: str,
        timeline_data: Dict[str, Any],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache project timeline"""
        cache_key = self._build_project_timeline_key(project_id, timeline_config_hash)
        return await self.cache.set(
            cache_key,
            timeline_data,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_project_timeline_key(self, project_id: str, timeline_config_hash: str) -> str:
        """Build cache key for project timeline"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "project_timeline",
            project_id,
            timeline_config_hash
        )
    
    # Resource Allocation Caching
    
    async def get_cached_resource_allocation(
        self,
        project_id: str,
        allocation_period: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached resource allocation data"""
        cache_key = self._build_resource_allocation_key(project_id, allocation_period)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_resource_allocation(
        self,
        project_id: str,
        allocation_period: str,
        allocation_data: Dict[str, Any],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache resource allocation data"""
        cache_key = self._build_resource_allocation_key(project_id, allocation_period)
        return await self.cache.set(
            cache_key,
            allocation_data,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_resource_allocation_key(self, project_id: str, allocation_period: str) -> str:
        """Build cache key for resource allocation"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "resource_allocation",
            project_id,
            allocation_period
        )
    
    # Bulk Operations
    
    async def get_cached_bulk_project_data(
        self,
        project_ids: List[str],
        data_type: str
    ) -> Dict[str, Optional[Any]]:
        """Get multiple cached project data entries"""
        cache_keys = []
        project_map = {}
        
        for project_id in project_ids:
            cache_key = self.key_builder.build_key(
                CacheNamespace.PROJECT_DATA,
                data_type,
                project_id
            )
            cache_keys.append(cache_key)
            project_map[cache_key] = project_id
        
        cached_values = await self.cache.mget(
            cache_keys,
            serialization=SerializationMethod.PICKLE
        )
        
        # Map results back to project IDs
        result = {}
        for cache_key, value in cached_values.items():
            if cache_key in project_map:
                project_id = project_map[cache_key]
                result[project_id] = value
        
        return result
    
    async def cache_bulk_project_data(
        self,
        project_data: Dict[str, Any],
        data_type: str,
        ttl: int = 1800
    ) -> bool:
        """Cache multiple project data entries"""
        cache_mapping = {}
        
        for project_id, data in project_data.items():
            cache_key = self.key_builder.build_key(
                CacheNamespace.PROJECT_DATA,
                data_type,
                project_id
            )
            cache_mapping[cache_key] = data
        
        return await self.cache.mset(
            cache_mapping,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    # What-If Scenario Caching
    
    async def get_cached_scenario_analysis(
        self,
        project_id: str,
        scenario_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached what-if scenario analysis"""
        cache_key = self._build_scenario_analysis_key(project_id, scenario_hash)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_scenario_analysis(
        self,
        project_id: str,
        scenario_hash: str,
        analysis_result: Dict[str, Any],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache what-if scenario analysis"""
        cache_key = self._build_scenario_analysis_key(project_id, scenario_hash)
        return await self.cache.set(
            cache_key,
            analysis_result,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_scenario_analysis_key(self, project_id: str, scenario_hash: str) -> str:
        """Build cache key for scenario analysis"""
        return self.key_builder.build_key(
            CacheNamespace.PROJECT_DATA,
            "scenario_analysis",
            project_id,
            scenario_hash
        )
    
    # Cache Management
    
    async def invalidate_project_cache(
        self,
        project_id: Optional[str] = None,
        data_types: Optional[List[str]] = None
    ) -> int:
        """Invalidate project-related cache entries"""
        patterns = []
        
        if project_id and data_types:
            # Invalidate specific data types for a project
            for data_type in data_types:
                patterns.append(
                    self.key_builder.pattern_key(
                        CacheNamespace.PROJECT_DATA,
                        data_type,
                        project_id,
                        "*"
                    )
                )
        elif project_id:
            # Invalidate all data for a specific project
            patterns.append(
                self.key_builder.pattern_key(
                    CacheNamespace.PROJECT_DATA,
                    "*",
                    project_id,
                    "*"
                )
            )
        elif data_types:
            # Invalidate specific data types for all projects
            for data_type in data_types:
                patterns.append(
                    self.key_builder.pattern_key(
                        CacheNamespace.PROJECT_DATA,
                        data_type,
                        "*"
                    )
                )
        else:
            # Invalidate all project cache
            patterns.append(
                self.key_builder.pattern_key(CacheNamespace.PROJECT_DATA)
            )
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} project cache entries")
        return total_deleted
    
    async def warm_project_cache(
        self,
        project_ids: List[str],
        dependency_service: TaskDependencyService
    ) -> None:
        """Warm cache with frequently accessed project data"""
        try:
            for project_id in project_ids:
                # Warm critical path cache
                # This would need to be integrated with actual project data
                logger.info(f"Warming cache for project {project_id}")
                
                # Example: Pre-calculate and cache critical path
                # critical_path = await dependency_service.calculate_critical_path(project_id)
                # if critical_path:
                #     await self.cache_critical_path(project_id, "current", critical_path)
        
        except Exception as e:
            logger.error(f"Failed to warm project cache: {e}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for project service"""
        try:
            # Get overall cache metrics
            metrics = self.cache.get_metrics()
            
            # Get project-specific key counts
            project_pattern = self.key_builder.pattern_key(CacheNamespace.PROJECT_DATA)
            project_keys = await self.cache.keys(project_pattern)
            
            # Count different types of cached data
            critical_path_count = len([k for k in project_keys if "critical_path" in k])
            resource_opt_count = len([k for k in project_keys if "resource_optimization" in k])
            schedule_opt_count = len([k for k in project_keys if "schedule_optimization" in k])
            metrics_count = len([k for k in project_keys if "project_metrics" in k])
            gantt_count = len([k for k in project_keys if "gantt_data" in k])
            
            return {
                "overall_metrics": asdict(metrics),
                "project_cache_keys": len(project_keys),
                "critical_path_calculations": critical_path_count,
                "resource_optimizations": resource_opt_count,
                "schedule_optimizations": schedule_opt_count,
                "project_metrics": metrics_count,
                "gantt_charts": gantt_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get project cache statistics: {e}")
            return {}


# Decorators for caching project operations

def cache_critical_path_calculation(
    ttl: int = 3600,
    cache_service: Optional[ProjectCacheService] = None
):
    """Decorator for caching critical path calculations"""
    return cached(
        namespace=CacheNamespace.PROJECT_DATA,
        ttl=ttl,
        serialization=SerializationMethod.PICKLE,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_resource_optimization(
    ttl: int = 1800,
    cache_service: Optional[ProjectCacheService] = None
):
    """Decorator for caching resource optimization"""
    return cached(
        namespace=CacheNamespace.PROJECT_DATA,
        ttl=ttl,
        serialization=SerializationMethod.PICKLE,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_project_metrics(
    ttl: int = 900,
    cache_service: Optional[ProjectCacheService] = None
):
    """Decorator for caching project metrics"""
    return cached(
        namespace=CacheNamespace.PROJECT_DATA,
        ttl=ttl,
        serialization=SerializationMethod.PICKLE,
        cache_instance=cache_service.cache if cache_service else None
    )


# Global project cache service instance
_project_cache_service: Optional[ProjectCacheService] = None


def get_project_cache_service() -> ProjectCacheService:
    """Get global project cache service instance"""
    global _project_cache_service
    if _project_cache_service is None:
        _project_cache_service = ProjectCacheService()
    return _project_cache_service