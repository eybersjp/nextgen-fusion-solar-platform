"""Cache Integration for Compliance Service

Integrates Redis caching for expensive compliance operations:
- Rule evaluation results
- Jurisdiction-specific rule sets
- Entity validation results
- Compliance report data
- Rule performance metrics
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

# Import compliance service models
from .rules_engine_service import (
    EvaluationContext, ConditionResult, RuleResult, RuleSetResult,
    RulesEngineService
)

logger = logging.getLogger(__name__)


class ComplianceCacheService:
    """Cache service for compliance operations"""
    
    def __init__(self, cache: Optional[RedisCache] = None):
        self.cache = cache or get_cache()
        self.key_builder = CacheKeyBuilder()
    
    # Rule Evaluation Caching
    
    async def get_cached_rule_evaluation(
        self,
        rule_id: str,
        entity_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[RuleResult]:
        """Get cached rule evaluation result"""
        cache_key = self._build_rule_evaluation_key(rule_id, entity_data, context)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_rule_evaluation(
        self,
        rule_id: str,
        entity_data: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        result: RuleResult,
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache rule evaluation result"""
        cache_key = self._build_rule_evaluation_key(rule_id, entity_data, context)
        return await self.cache.set(
            cache_key,
            result,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_rule_evaluation_key(
        self,
        rule_id: str,
        entity_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build cache key for rule evaluation"""
        # Create hash from entity data and context for consistent key
        data_hash = self.key_builder.hash_key({
            "entity_data": entity_data,
            "context": context or {}
        })
        return self.key_builder.build_key(
            CacheNamespace.COMPLIANCE_RULES,
            "rule_eval",
            rule_id,
            data_hash
        )
    
    # Rule Set Evaluation Caching
    
    async def get_cached_ruleset_evaluation(
        self,
        ruleset_id: str,
        entity_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[RuleSetResult]:
        """Get cached rule set evaluation result"""
        cache_key = self._build_ruleset_evaluation_key(ruleset_id, entity_data, context)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_ruleset_evaluation(
        self,
        ruleset_id: str,
        entity_data: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        result: RuleSetResult,
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache rule set evaluation result"""
        cache_key = self._build_ruleset_evaluation_key(ruleset_id, entity_data, context)
        return await self.cache.set(
            cache_key,
            result,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_ruleset_evaluation_key(
        self,
        ruleset_id: str,
        entity_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build cache key for rule set evaluation"""
        data_hash = self.key_builder.hash_key({
            "entity_data": entity_data,
            "context": context or {}
        })
        return self.key_builder.build_key(
            CacheNamespace.COMPLIANCE_RULES,
            "ruleset_eval",
            ruleset_id,
            data_hash
        )
    
    # Entity Validation Caching
    
    async def get_cached_entity_validation(
        self,
        entity_type: str,
        entity_id: str,
        jurisdiction: str,
        validation_rules: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get cached entity validation result"""
        cache_key = self._build_entity_validation_key(
            entity_type, entity_id, jurisdiction, validation_rules
        )
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_entity_validation(
        self,
        entity_type: str,
        entity_id: str,
        jurisdiction: str,
        validation_rules: List[str],
        validation_result: Dict[str, Any],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache entity validation result"""
        cache_key = self._build_entity_validation_key(
            entity_type, entity_id, jurisdiction, validation_rules
        )
        return await self.cache.set(
            cache_key,
            validation_result,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_entity_validation_key(
        self,
        entity_type: str,
        entity_id: str,
        jurisdiction: str,
        validation_rules: List[str]
    ) -> str:
        """Build cache key for entity validation"""
        rules_hash = self.key_builder.hash_key(sorted(validation_rules))
        return self.key_builder.build_key(
            CacheNamespace.COMPLIANCE_RULES,
            "entity_validation",
            entity_type,
            entity_id,
            jurisdiction,
            rules_hash
        )
    
    # Jurisdiction Rules Caching
    
    async def get_cached_jurisdiction_rules(
        self,
        jurisdiction: str,
        entity_type: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached jurisdiction rules"""
        cache_key = self._build_jurisdiction_rules_key(jurisdiction, entity_type)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_jurisdiction_rules(
        self,
        jurisdiction: str,
        rules: List[Dict[str, Any]],
        entity_type: Optional[str] = None,
        ttl: int = 7200  # 2 hours
    ) -> bool:
        """Cache jurisdiction rules"""
        cache_key = self._build_jurisdiction_rules_key(jurisdiction, entity_type)
        return await self.cache.set(
            cache_key,
            rules,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_jurisdiction_rules_key(
        self,
        jurisdiction: str,
        entity_type: Optional[str] = None
    ) -> str:
        """Build cache key for jurisdiction rules"""
        if entity_type:
            return self.key_builder.build_key(
                CacheNamespace.COMPLIANCE_RULES,
                "jurisdiction_rules",
                jurisdiction,
                entity_type
            )
        else:
            return self.key_builder.build_key(
                CacheNamespace.COMPLIANCE_RULES,
                "jurisdiction_rules",
                jurisdiction
            )
    
    # Compliance Report Caching
    
    async def get_cached_compliance_report(
        self,
        report_type: str,
        entity_id: str,
        jurisdiction: str,
        report_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached compliance report"""
        cache_key = self._build_compliance_report_key(
            report_type, entity_id, jurisdiction, report_params
        )
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_compliance_report(
        self,
        report_type: str,
        entity_id: str,
        jurisdiction: str,
        report_params: Dict[str, Any],
        report_data: Dict[str, Any],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache compliance report"""
        cache_key = self._build_compliance_report_key(
            report_type, entity_id, jurisdiction, report_params
        )
        return await self.cache.set(
            cache_key,
            report_data,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_compliance_report_key(
        self,
        report_type: str,
        entity_id: str,
        jurisdiction: str,
        report_params: Dict[str, Any]
    ) -> str:
        """Build cache key for compliance reports"""
        params_hash = self.key_builder.hash_key(report_params)
        return self.key_builder.build_key(
            CacheNamespace.COMPLIANCE_RULES,
            "compliance_report",
            report_type,
            entity_id,
            jurisdiction,
            params_hash
        )
    
    # Rule Performance Metrics Caching
    
    async def get_cached_rule_performance(
        self,
        rule_id: str,
        time_period: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached rule performance metrics"""
        cache_key = self._build_rule_performance_key(rule_id, time_period)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_rule_performance(
        self,
        rule_id: str,
        time_period: str,
        performance_data: Dict[str, Any],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache rule performance metrics"""
        cache_key = self._build_rule_performance_key(rule_id, time_period)
        return await self.cache.set(
            cache_key,
            performance_data,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_rule_performance_key(
        self,
        rule_id: str,
        time_period: str
    ) -> str:
        """Build cache key for rule performance metrics"""
        return self.key_builder.build_key(
            CacheNamespace.COMPLIANCE_RULES,
            "rule_performance",
            rule_id,
            time_period
        )
    
    # Bulk Operations
    
    async def get_cached_bulk_validations(
        self,
        validation_requests: List[Dict[str, Any]]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get multiple cached validation results"""
        cache_keys = []
        request_map = {}
        
        for i, request in enumerate(validation_requests):
            cache_key = self._build_entity_validation_key(
                request["entity_type"],
                request["entity_id"],
                request["jurisdiction"],
                request["validation_rules"]
            )
            cache_keys.append(cache_key)
            request_map[cache_key] = i
        
        cached_values = await self.cache.mget(
            cache_keys,
            serialization=SerializationMethod.JSON
        )
        
        # Map results back to requests
        result = {}
        for cache_key, value in cached_values.items():
            if cache_key in request_map:
                request_index = request_map[cache_key]
                result[str(request_index)] = value
        
        return result
    
    async def cache_bulk_validations(
        self,
        validation_results: Dict[str, Dict[str, Any]],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache multiple validation results"""
        cache_mapping = {}
        
        for request_key, result in validation_results.items():
            # Extract request details from the key or result
            # This would need to be adapted based on your specific data structure
            cache_mapping[request_key] = result
        
        return await self.cache.mset(
            cache_mapping,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    # Cache Management
    
    async def invalidate_rule_cache(
        self,
        rule_id: Optional[str] = None,
        jurisdiction: Optional[str] = None
    ) -> int:
        """Invalidate rule-related cache entries"""
        patterns = []
        
        if rule_id:
            # Invalidate specific rule
            patterns.append(
                self.key_builder.pattern_key(
                    CacheNamespace.COMPLIANCE_RULES,
                    f"*{rule_id}*"
                )
            )
        
        if jurisdiction:
            # Invalidate jurisdiction-specific entries
            patterns.append(
                self.key_builder.pattern_key(
                    CacheNamespace.COMPLIANCE_RULES,
                    f"*{jurisdiction}*"
                )
            )
        
        if not patterns:
            # Invalidate all compliance cache
            patterns.append(
                self.key_builder.pattern_key(CacheNamespace.COMPLIANCE_RULES)
            )
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await self.cache.delete_pattern(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} compliance cache entries")
        return total_deleted
    
    async def warm_jurisdiction_cache(
        self,
        jurisdictions: List[str],
        rules_service: RulesEngineService
    ) -> None:
        """Warm cache with jurisdiction rules"""
        try:
            cache_mapping = {}
            
            for jurisdiction in jurisdictions:
                # Get rules for jurisdiction from service
                rules = await rules_service.get_rules_for_jurisdiction(jurisdiction)
                if rules:
                    cache_key = self._build_jurisdiction_rules_key(jurisdiction)
                    # Convert rules to serializable format
                    serializable_rules = [asdict(rule) if hasattr(rule, '__dict__') else rule for rule in rules]
                    cache_mapping[cache_key] = serializable_rules
            
            if cache_mapping:
                await self.cache.mset(
                    cache_mapping,
                    ttl=7200,  # 2 hours
                    serialization=SerializationMethod.JSON
                )
                logger.info(f"Warmed compliance cache with {len(cache_mapping)} jurisdiction rule sets")
        
        except Exception as e:
            logger.error(f"Failed to warm compliance cache: {e}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for compliance service"""
        try:
            # Get overall cache metrics
            metrics = self.cache.get_metrics()
            
            # Get compliance-specific key counts
            compliance_pattern = self.key_builder.pattern_key(CacheNamespace.COMPLIANCE_RULES)
            compliance_keys = await self.cache.keys(compliance_pattern)
            
            # Count different types of cached data
            rule_eval_count = len([k for k in compliance_keys if "rule_eval" in k])
            ruleset_eval_count = len([k for k in compliance_keys if "ruleset_eval" in k])
            entity_validation_count = len([k for k in compliance_keys if "entity_validation" in k])
            jurisdiction_rules_count = len([k for k in compliance_keys if "jurisdiction_rules" in k])
            
            return {
                "overall_metrics": asdict(metrics),
                "compliance_cache_keys": len(compliance_keys),
                "rule_evaluations": rule_eval_count,
                "ruleset_evaluations": ruleset_eval_count,
                "entity_validations": entity_validation_count,
                "jurisdiction_rules": jurisdiction_rules_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get compliance cache statistics: {e}")
            return {}


# Decorators for caching compliance operations

def cache_rule_evaluation(
    ttl: int = 1800,
    cache_service: Optional[ComplianceCacheService] = None
):
    """Decorator for caching rule evaluations"""
    return cached(
        namespace=CacheNamespace.COMPLIANCE_RULES,
        ttl=ttl,
        serialization=SerializationMethod.PICKLE,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_entity_validation(
    ttl: int = 3600,
    cache_service: Optional[ComplianceCacheService] = None
):
    """Decorator for caching entity validations"""
    return cached(
        namespace=CacheNamespace.COMPLIANCE_RULES,
        ttl=ttl,
        serialization=SerializationMethod.JSON,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_jurisdiction_rules(
    ttl: int = 7200,
    cache_service: Optional[ComplianceCacheService] = None
):
    """Decorator for caching jurisdiction rules"""
    return cached(
        namespace=CacheNamespace.COMPLIANCE_RULES,
        ttl=ttl,
        serialization=SerializationMethod.JSON,
        cache_instance=cache_service.cache if cache_service else None
    )


# Global compliance cache service instance
_compliance_cache_service: Optional[ComplianceCacheService] = None


def get_compliance_cache_service() -> ComplianceCacheService:
    """Get global compliance cache service instance"""
    global _compliance_cache_service
    if _compliance_cache_service is None:
        _compliance_cache_service = ComplianceCacheService()
    return _compliance_cache_service