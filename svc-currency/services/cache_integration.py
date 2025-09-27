"""Cache Integration for Currency Service

Integrates Redis caching for expensive currency operations:
- FX rate lookups and conversions
- Historical rate data
- Rate statistics and analytics
- Cross-rate calculations
- External API responses
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta, date
from dataclasses import asdict
import logging

# Import from shared cache module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
from cache import (
    RedisCache, CacheConfig, CacheNamespace, CacheKeyBuilder,
    SerializationMethod, cached, get_cache
)

# Import currency service models
from .fx_history_service import (
    RateQuery, RatePoint, RateStatistics, FXHistoryService
)

logger = logging.getLogger(__name__)


class CurrencyCacheService:
    """Cache service for currency operations"""
    
    def __init__(self, cache: Optional[RedisCache] = None):
        self.cache = cache or get_cache()
        self.key_builder = CacheKeyBuilder()
    
    # FX Rate Caching
    
    async def get_cached_fx_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: Optional[date] = None
    ) -> Optional[float]:
        """Get cached FX rate"""
        cache_key = self._build_fx_rate_key(from_currency, to_currency, rate_date)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_fx_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: float,
        rate_date: Optional[date] = None,
        ttl: int = 300  # 5 minutes for live rates
    ) -> bool:
        """Cache FX rate"""
        cache_key = self._build_fx_rate_key(from_currency, to_currency, rate_date)
        return await self.cache.set(
            cache_key,
            rate,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_fx_rate_key(
        self,
        from_currency: str,
        to_currency: str,
        rate_date: Optional[date] = None
    ) -> str:
        """Build cache key for FX rates"""
        date_str = rate_date.isoformat() if rate_date else "latest"
        return self.key_builder.build_key(
            CacheNamespace.CURRENCY_RATES,
            "fx_rate",
            f"{from_currency}_{to_currency}",
            date_str
        )
    
    # Currency Conversion Caching
    
    async def get_cached_conversion(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        conversion_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached currency conversion result"""
        cache_key = self._build_conversion_key(
            amount, from_currency, to_currency, conversion_date
        )
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_conversion_result(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        result: Dict[str, Any],
        conversion_date: Optional[date] = None,
        ttl: int = 300  # 5 minutes
    ) -> bool:
        """Cache currency conversion result"""
        cache_key = self._build_conversion_key(
            amount, from_currency, to_currency, conversion_date
        )
        return await self.cache.set(
            cache_key,
            result,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_conversion_key(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        conversion_date: Optional[date] = None
    ) -> str:
        """Build cache key for currency conversions"""
        date_str = conversion_date.isoformat() if conversion_date else "latest"
        # Round amount to avoid cache misses due to floating point precision
        rounded_amount = round(amount, 2)
        return self.key_builder.build_key(
            CacheNamespace.CURRENCY_RATES,
            "conversion",
            f"{from_currency}_{to_currency}",
            str(rounded_amount),
            date_str
        )
    
    # Historical Rate Data Caching
    
    async def get_cached_historical_rates(
        self,
        currency_pair: str,
        start_date: date,
        end_date: date
    ) -> Optional[List[RatePoint]]:
        """Get cached historical rate data"""
        cache_key = self._build_historical_key(currency_pair, start_date, end_date)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_historical_rates(
        self,
        currency_pair: str,
        start_date: date,
        end_date: date,
        rates: List[RatePoint],
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Cache historical rate data"""
        cache_key = self._build_historical_key(currency_pair, start_date, end_date)
        return await self.cache.set(
            cache_key,
            rates,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_historical_key(
        self,
        currency_pair: str,
        start_date: date,
        end_date: date
    ) -> str:
        """Build cache key for historical rates"""
        return self.key_builder.build_key(
            CacheNamespace.CURRENCY_RATES,
            "historical",
            currency_pair,
            start_date.isoformat(),
            end_date.isoformat()
        )
    
    # Rate Statistics Caching
    
    async def get_cached_rate_statistics(
        self,
        currency_pair: str,
        period_days: int
    ) -> Optional[RateStatistics]:
        """Get cached rate statistics"""
        cache_key = self._build_statistics_key(currency_pair, period_days)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.PICKLE
        )
    
    async def cache_rate_statistics(
        self,
        currency_pair: str,
        period_days: int,
        statistics: RateStatistics,
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache rate statistics"""
        cache_key = self._build_statistics_key(currency_pair, period_days)
        return await self.cache.set(
            cache_key,
            statistics,
            ttl=ttl,
            serialization=SerializationMethod.PICKLE
        )
    
    def _build_statistics_key(
        self,
        currency_pair: str,
        period_days: int
    ) -> str:
        """Build cache key for rate statistics"""
        return self.key_builder.build_key(
            CacheNamespace.CURRENCY_RATES,
            "statistics",
            currency_pair,
            str(period_days)
        )
    
    # External API Response Caching
    
    async def get_cached_api_response(
        self,
        api_provider: str,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get cached external API response"""
        cache_key = self._build_api_response_key(api_provider, endpoint, params)
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_api_response(
        self,
        api_provider: str,
        endpoint: str,
        params: Dict[str, Any],
        response: Dict[str, Any],
        ttl: int = 300  # 5 minutes
    ) -> bool:
        """Cache external API response"""
        cache_key = self._build_api_response_key(api_provider, endpoint, params)
        return await self.cache.set(
            cache_key,
            response,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_api_response_key(
        self,
        api_provider: str,
        endpoint: str,
        params: Dict[str, Any]
    ) -> str:
        """Build cache key for API responses"""
        params_hash = self.key_builder.hash_key(params)
        return self.key_builder.build_key(
            CacheNamespace.API_RESPONSES,
            "currency_api",
            api_provider,
            endpoint,
            params_hash
        )
    
    # Cross-Rate Calculations Caching
    
    async def get_cached_cross_rate(
        self,
        base_currency: str,
        target_currency: str,
        via_currency: str,
        calculation_date: Optional[date] = None
    ) -> Optional[float]:
        """Get cached cross-rate calculation"""
        cache_key = self._build_cross_rate_key(
            base_currency, target_currency, via_currency, calculation_date
        )
        return await self.cache.get(
            cache_key,
            serialization=SerializationMethod.JSON
        )
    
    async def cache_cross_rate(
        self,
        base_currency: str,
        target_currency: str,
        via_currency: str,
        rate: float,
        calculation_date: Optional[date] = None,
        ttl: int = 300  # 5 minutes
    ) -> bool:
        """Cache cross-rate calculation"""
        cache_key = self._build_cross_rate_key(
            base_currency, target_currency, via_currency, calculation_date
        )
        return await self.cache.set(
            cache_key,
            rate,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    def _build_cross_rate_key(
        self,
        base_currency: str,
        target_currency: str,
        via_currency: str,
        calculation_date: Optional[date] = None
    ) -> str:
        """Build cache key for cross-rate calculations"""
        date_str = calculation_date.isoformat() if calculation_date else "latest"
        return self.key_builder.build_key(
            CacheNamespace.CURRENCY_RATES,
            "cross_rate",
            f"{base_currency}_{target_currency}_via_{via_currency}",
            date_str
        )
    
    # Bulk Rate Operations
    
    async def get_cached_bulk_rates(
        self,
        currency_pairs: List[str],
        rate_date: Optional[date] = None
    ) -> Dict[str, Optional[float]]:
        """Get multiple cached FX rates"""
        cache_keys = []
        for pair in currency_pairs:
            from_curr, to_curr = pair.split('_')
            cache_keys.append(self._build_fx_rate_key(from_curr, to_curr, rate_date))
        
        cached_values = await self.cache.mget(
            cache_keys,
            serialization=SerializationMethod.JSON
        )
        
        # Map results back to currency pairs
        result = {}
        for pair, cache_key in zip(currency_pairs, cache_keys):
            result[pair] = cached_values.get(cache_key)
        
        return result
    
    async def cache_bulk_rates(
        self,
        rates_data: Dict[str, float],
        rate_date: Optional[date] = None,
        ttl: int = 300  # 5 minutes
    ) -> bool:
        """Cache multiple FX rates"""
        cache_mapping = {}
        
        for pair, rate in rates_data.items():
            from_curr, to_curr = pair.split('_')
            cache_key = self._build_fx_rate_key(from_curr, to_curr, rate_date)
            cache_mapping[cache_key] = rate
        
        return await self.cache.mset(
            cache_mapping,
            ttl=ttl,
            serialization=SerializationMethod.JSON
        )
    
    # Cache Management
    
    async def invalidate_currency_cache(
        self,
        currency: Optional[str] = None
    ) -> int:
        """Invalidate currency-related cache entries"""
        if currency:
            # Invalidate specific currency
            pattern = self.key_builder.pattern_key(
                CacheNamespace.CURRENCY_RATES,
                f"*{currency}*"
            )
        else:
            # Invalidate all currency cache
            pattern = self.key_builder.pattern_key(CacheNamespace.CURRENCY_RATES)
        
        deleted = await self.cache.delete_pattern(pattern)
        logger.info(f"Invalidated {deleted} currency cache entries")
        return deleted
    
    async def warm_popular_rates(
        self,
        popular_pairs: List[str],
        fx_service: FXHistoryService
    ) -> None:
        """Warm cache with popular currency pairs"""
        try:
            cache_mapping = {}
            
            for pair in popular_pairs:
                from_curr, to_curr = pair.split('_')
                
                # Get latest rate from service
                rate = await fx_service.get_latest_rate(from_curr, to_curr)
                if rate:
                    cache_key = self._build_fx_rate_key(from_curr, to_curr)
                    cache_mapping[cache_key] = rate
            
            if cache_mapping:
                await self.cache.mset(
                    cache_mapping,
                    ttl=300,  # 5 minutes
                    serialization=SerializationMethod.JSON
                )
                logger.info(f"Warmed currency cache with {len(cache_mapping)} popular rates")
        
        except Exception as e:
            logger.error(f"Failed to warm currency cache: {e}")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for currency service"""
        try:
            # Get overall cache metrics
            metrics = self.cache.get_metrics()
            
            # Get currency-specific key counts
            currency_pattern = self.key_builder.pattern_key(CacheNamespace.CURRENCY_RATES)
            api_pattern = self.key_builder.pattern_key(CacheNamespace.API_RESPONSES, "currency_api*")
            
            currency_keys = await self.cache.keys(currency_pattern)
            api_keys = await self.cache.keys(api_pattern)
            
            return {
                "overall_metrics": asdict(metrics),
                "currency_cache_keys": len(currency_keys),
                "api_cache_keys": len(api_keys),
                "total_currency_related": len(currency_keys) + len(api_keys),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get currency cache statistics: {e}")
            return {}


# Decorators for caching currency operations

def cache_fx_rate_lookup(
    ttl: int = 300,
    cache_service: Optional[CurrencyCacheService] = None
):
    """Decorator for caching FX rate lookups"""
    return cached(
        namespace=CacheNamespace.CURRENCY_RATES,
        ttl=ttl,
        serialization=SerializationMethod.JSON,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_currency_conversion(
    ttl: int = 300,
    cache_service: Optional[CurrencyCacheService] = None
):
    """Decorator for caching currency conversions"""
    return cached(
        namespace=CacheNamespace.CURRENCY_RATES,
        ttl=ttl,
        serialization=SerializationMethod.JSON,
        cache_instance=cache_service.cache if cache_service else None
    )


def cache_rate_statistics(
    ttl: int = 1800,
    cache_service: Optional[CurrencyCacheService] = None
):
    """Decorator for caching rate statistics"""
    return cached(
        namespace=CacheNamespace.CURRENCY_RATES,
        ttl=ttl,
        serialization=SerializationMethod.PICKLE,
        cache_instance=cache_service.cache if cache_service else None
    )


# Global currency cache service instance
_currency_cache_service: Optional[CurrencyCacheService] = None


def get_currency_cache_service() -> CurrencyCacheService:
    """Get global currency cache service instance"""
    global _currency_cache_service
    if _currency_cache_service is None:
        _currency_cache_service = CurrencyCacheService()
    return _currency_cache_service