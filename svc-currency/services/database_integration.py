"""Database Integration Service for Currency Service

Integrates the shared database connection pooling with currency service operations:
- FX rate storage and retrieval
- Historical rate data management
- Currency conversion audit trails
- Rate provider performance tracking
- Cross-rate calculation caching
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from database import (
    DatabaseConfig,
    get_pool_manager,
    initialize_service_database,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CurrencyDatabaseService:
    """Database service for currency operations with optimized connection pooling"""
    
    def __init__(self, service_name: str = "svc-currency"):
        self.service_name = service_name
        self.pool_manager = get_pool_manager()
        self._initialized = False
    
    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize database pools for currency service"""
        if self._initialized:
            return
        
        if config is None:
            # Use default configuration
            config = DatabaseConfig(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "nextgen_fusion"),
                username=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "password"),
                service_name=self.service_name,
                pool_size=8,
                max_overflow=12,
                pool_timeout=30,
                command_timeout=45,
            )
        
        initialize_service_database(self.service_name, config)
        self._initialized = True
        logger.info(f"Initialized database service for {self.service_name}")
    
    def get_sync_session(self) -> Session:
        """Get synchronous database session"""
        if not self._initialized:
            self.initialize()
        return self.pool_manager.get_sync_session(self.service_name)
    
    def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session"""
        if not self._initialized:
            self.initialize()
        return self.pool_manager.get_async_session(self.service_name)
    
    @asynccontextmanager
    async def get_async_session_context(self):
        """Get async session with automatic cleanup"""
        if not self._initialized:
            self.initialize()
        async with self.pool_manager.get_async_session_context(self.service_name) as session:
            yield session
    
    def get_sync_session_context(self):
        """Get sync session with automatic cleanup"""
        if not self._initialized:
            self.initialize()
        with self.pool_manager.get_sync_session_context(self.service_name) as session:
            yield session
    
    async def store_fx_rate(
        self,
        base_currency: str,
        target_currency: str,
        rate: Decimal,
        provider: str,
        rate_date: datetime,
        bid_rate: Optional[Decimal] = None,
        ask_rate: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store FX rate in database"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO fx_rates 
                (base_currency, target_currency, rate, bid_rate, ask_rate, provider, rate_date, metadata, created_at)
                VALUES (:base_currency, :target_currency, :rate, :bid_rate, :ask_rate, :provider, :rate_date, :metadata, :created_at)
                ON CONFLICT (base_currency, target_currency, provider, rate_date)
                DO UPDATE SET 
                    rate = EXCLUDED.rate,
                    bid_rate = EXCLUDED.bid_rate,
                    ask_rate = EXCLUDED.ask_rate,
                    metadata = EXCLUDED.metadata,
                    updated_at = :created_at
                RETURNING id
            """)
            
            now = datetime.utcnow()
            result = await session.execute(query, {
                "base_currency": base_currency,
                "target_currency": target_currency,
                "rate": float(rate),
                "bid_rate": float(bid_rate) if bid_rate else None,
                "ask_rate": float(ask_rate) if ask_rate else None,
                "provider": provider,
                "rate_date": rate_date,
                "metadata": metadata or {},
                "created_at": now
            })
            
            rate_id = result.scalar()
            logger.debug(f"Stored FX rate {base_currency}/{target_currency} = {rate}")
            return rate_id
    
    async def get_latest_fx_rate(
        self,
        base_currency: str,
        target_currency: str,
        provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get latest FX rate for currency pair"""
        async with self.get_async_session_context() as session:
            conditions = [
                "base_currency = :base_currency",
                "target_currency = :target_currency"
            ]
            params = {
                "base_currency": base_currency,
                "target_currency": target_currency
            }
            
            if provider:
                conditions.append("provider = :provider")
                params["provider"] = provider
            
            where_clause = " AND ".join(conditions)
            
            query = text(f"""
                SELECT id, rate, bid_rate, ask_rate, provider, rate_date, metadata, created_at
                FROM fx_rates
                WHERE {where_clause}
                ORDER BY rate_date DESC, created_at DESC
                LIMIT 1
            """)
            
            result = await session.execute(query, params)
            row = result.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "base_currency": base_currency,
                    "target_currency": target_currency,
                    "rate": Decimal(str(row[1])),
                    "bid_rate": Decimal(str(row[2])) if row[2] else None,
                    "ask_rate": Decimal(str(row[3])) if row[3] else None,
                    "provider": row[4],
                    "rate_date": row[5],
                    "metadata": row[6],
                    "created_at": row[7]
                }
            
            return None
    
    async def get_historical_fx_rates(
        self,
        base_currency: str,
        target_currency: str,
        start_date: datetime,
        end_date: datetime,
        provider: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get historical FX rates for currency pair"""
        async with self.get_async_session_context() as session:
            conditions = [
                "base_currency = :base_currency",
                "target_currency = :target_currency",
                "rate_date >= :start_date",
                "rate_date <= :end_date"
            ]
            params = {
                "base_currency": base_currency,
                "target_currency": target_currency,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
            
            if provider:
                conditions.append("provider = :provider")
                params["provider"] = provider
            
            where_clause = " AND ".join(conditions)
            
            query = text(f"""
                SELECT id, rate, bid_rate, ask_rate, provider, rate_date, metadata, created_at
                FROM fx_rates
                WHERE {where_clause}
                ORDER BY rate_date DESC, created_at DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "base_currency": base_currency,
                    "target_currency": target_currency,
                    "rate": Decimal(str(row[1])),
                    "bid_rate": Decimal(str(row[2])) if row[2] else None,
                    "ask_rate": Decimal(str(row[3])) if row[3] else None,
                    "provider": row[4],
                    "rate_date": row[5],
                    "metadata": row[6],
                    "created_at": row[7]
                }
                for row in rows
            ]
    
    async def store_conversion_audit(
        self,
        base_currency: str,
        target_currency: str,
        base_amount: Decimal,
        target_amount: Decimal,
        rate_used: Decimal,
        provider: str,
        conversion_context: Dict[str, Any]
    ) -> str:
        """Store currency conversion audit entry"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO currency_conversion_audit 
                (base_currency, target_currency, base_amount, target_amount, rate_used, 
                 provider, conversion_context, created_at)
                VALUES (:base_currency, :target_currency, :base_amount, :target_amount, 
                        :rate_used, :provider, :conversion_context, :created_at)
                RETURNING id
            """)
            
            result = await session.execute(query, {
                "base_currency": base_currency,
                "target_currency": target_currency,
                "base_amount": float(base_amount),
                "target_amount": float(target_amount),
                "rate_used": float(rate_used),
                "provider": provider,
                "conversion_context": conversion_context,
                "created_at": datetime.utcnow()
            })
            
            audit_id = result.scalar()
            logger.debug(f"Stored conversion audit {audit_id}")
            return audit_id
    
    async def get_conversion_audit_trail(
        self,
        base_currency: Optional[str] = None,
        target_currency: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get currency conversion audit trail"""
        async with self.get_async_session_context() as session:
            conditions = []
            params = {"limit": limit}
            
            if base_currency:
                conditions.append("base_currency = :base_currency")
                params["base_currency"] = base_currency
            
            if target_currency:
                conditions.append("target_currency = :target_currency")
                params["target_currency"] = target_currency
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = text(f"""
                SELECT id, base_currency, target_currency, base_amount, target_amount, 
                       rate_used, provider, conversion_context, created_at
                FROM currency_conversion_audit
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "base_currency": row[1],
                    "target_currency": row[2],
                    "base_amount": Decimal(str(row[3])),
                    "target_amount": Decimal(str(row[4])),
                    "rate_used": Decimal(str(row[5])),
                    "provider": row[6],
                    "conversion_context": row[7],
                    "created_at": row[8]
                }
                for row in rows
            ]
    
    async def store_rate_provider_performance(
        self,
        provider: str,
        response_time_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        rate_count: int = 1
    ) -> None:
        """Store rate provider performance metrics"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO rate_provider_performance 
                (provider, response_time_ms, success, error_message, rate_count, created_at)
                VALUES (:provider, :response_time_ms, :success, :error_message, :rate_count, :created_at)
            """)
            
            await session.execute(query, {
                "provider": provider,
                "response_time_ms": response_time_ms,
                "success": success,
                "error_message": error_message,
                "rate_count": rate_count,
                "created_at": datetime.utcnow()
            })
            
            logger.debug(f"Stored provider performance for {provider}")
    
    async def get_provider_performance_summary(
        self,
        provider: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated provider performance summary"""
        async with self.get_async_session_context() as session:
            conditions = []
            params = {}
            
            if provider:
                conditions.append("provider = :provider")
                params["provider"] = provider
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = text(f"""
                SELECT 
                    provider,
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_requests,
                    AVG(response_time_ms) as avg_response_time,
                    MIN(response_time_ms) as min_response_time,
                    MAX(response_time_ms) as max_response_time,
                    SUM(rate_count) as total_rates_fetched
                FROM rate_provider_performance
                WHERE {where_clause}
                GROUP BY provider
                ORDER BY total_requests DESC
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            summary = []
            for row in rows:
                success_rate = (row[2] / row[1]) * 100 if row[1] > 0 else 0
                summary.append({
                    "provider": row[0],
                    "total_requests": row[1],
                    "successful_requests": row[2],
                    "success_rate_percent": success_rate,
                    "avg_response_time_ms": float(row[3]) if row[3] else 0,
                    "min_response_time_ms": float(row[4]) if row[4] else 0,
                    "max_response_time_ms": float(row[5]) if row[5] else 0,
                    "total_rates_fetched": row[6]
                })
            
            return {
                "summary": summary,
                "total_providers": len(summary),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def store_cross_rate_calculation(
        self,
        base_currency: str,
        target_currency: str,
        intermediate_currency: str,
        base_to_intermediate_rate: Decimal,
        intermediate_to_target_rate: Decimal,
        calculated_rate: Decimal,
        calculation_method: str
    ) -> str:
        """Store cross-rate calculation result"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO cross_rate_calculations 
                (base_currency, target_currency, intermediate_currency, 
                 base_to_intermediate_rate, intermediate_to_target_rate, 
                 calculated_rate, calculation_method, created_at)
                VALUES (:base_currency, :target_currency, :intermediate_currency, 
                        :base_to_intermediate_rate, :intermediate_to_target_rate, 
                        :calculated_rate, :calculation_method, :created_at)
                RETURNING id
            """)
            
            result = await session.execute(query, {
                "base_currency": base_currency,
                "target_currency": target_currency,
                "intermediate_currency": intermediate_currency,
                "base_to_intermediate_rate": float(base_to_intermediate_rate),
                "intermediate_to_target_rate": float(intermediate_to_target_rate),
                "calculated_rate": float(calculated_rate),
                "calculation_method": calculation_method,
                "created_at": datetime.utcnow()
            })
            
            calc_id = result.scalar()
            logger.debug(f"Stored cross-rate calculation {calc_id}")
            return calc_id
    
    async def get_currency_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get currency service statistics"""
        async with self.get_async_session_context() as session:
            conditions = []
            params = {}
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Get conversion statistics
            conv_query = text(f"""
                SELECT 
                    COUNT(*) as total_conversions,
                    COUNT(DISTINCT base_currency) as unique_base_currencies,
                    COUNT(DISTINCT target_currency) as unique_target_currencies,
                    SUM(base_amount) as total_base_amount,
                    SUM(target_amount) as total_target_amount
                FROM currency_conversion_audit
                WHERE {where_clause}
            """)
            
            conv_result = await session.execute(conv_query, params)
            conv_row = conv_result.fetchone()
            
            # Get rate statistics
            rate_query = text(f"""
                SELECT 
                    COUNT(*) as total_rates,
                    COUNT(DISTINCT base_currency || '/' || target_currency) as unique_pairs,
                    COUNT(DISTINCT provider) as unique_providers
                FROM fx_rates
                WHERE {where_clause}
            """)
            
            rate_result = await session.execute(rate_query, params)
            rate_row = rate_result.fetchone()
            
            return {
                "conversions": {
                    "total_conversions": conv_row[0] if conv_row else 0,
                    "unique_base_currencies": conv_row[1] if conv_row else 0,
                    "unique_target_currencies": conv_row[2] if conv_row else 0,
                    "total_base_amount": float(conv_row[3]) if conv_row and conv_row[3] else 0,
                    "total_target_amount": float(conv_row[4]) if conv_row and conv_row[4] else 0
                },
                "rates": {
                    "total_rates": rate_row[0] if rate_row else 0,
                    "unique_currency_pairs": rate_row[1] if rate_row else 0,
                    "unique_providers": rate_row[2] if rate_row else 0
                },
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def cleanup_old_data(
        self,
        retention_days: int = 365
    ) -> Dict[str, int]:
        """Clean up old data based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        async with self.get_async_session_context() as session:
            # Clean up old conversion audit entries
            query1 = text("""
                DELETE FROM currency_conversion_audit 
                WHERE created_at < :cutoff_date
            """)
            result1 = await session.execute(query1, {"cutoff_date": cutoff_date})
            
            # Clean up old provider performance metrics
            query2 = text("""
                DELETE FROM rate_provider_performance 
                WHERE created_at < :cutoff_date
            """)
            result2 = await session.execute(query2, {"cutoff_date": cutoff_date})
            
            # Clean up old cross-rate calculations
            query3 = text("""
                DELETE FROM cross_rate_calculations 
                WHERE created_at < :cutoff_date
            """)
            result3 = await session.execute(query3, {"cutoff_date": cutoff_date})
            
            # Keep FX rates for longer (2 years)
            fx_cutoff_date = datetime.utcnow() - timedelta(days=730)
            query4 = text("""
                DELETE FROM fx_rates 
                WHERE created_at < :cutoff_date
            """)
            result4 = await session.execute(query4, {"cutoff_date": fx_cutoff_date})
            
            cleanup_stats = {
                "conversion_audit_deleted": result1.rowcount,
                "provider_performance_deleted": result2.rowcount,
                "cross_rate_calculations_deleted": result3.rowcount,
                "fx_rates_deleted": result4.rowcount
            }
            
            logger.info(f"Cleaned up old currency data: {cleanup_stats}")
            return cleanup_stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on database connection"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        return await self.pool_manager.health_check(self.service_name)
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and metrics"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        return self.pool_manager.get_pool_status(self.service_name)


# Global instance
_currency_db_service: Optional[CurrencyDatabaseService] = None


def get_currency_database_service() -> CurrencyDatabaseService:
    """Get global currency database service instance"""
    global _currency_db_service
    if _currency_db_service is None:
        _currency_db_service = CurrencyDatabaseService()
    return _currency_db_service


# Convenience functions
async def store_fx_rate_data(
    base_currency: str,
    target_currency: str,
    rate: Decimal,
    provider: str,
    rate_date: datetime
) -> str:
    """Store FX rate data"""
    service = get_currency_database_service()
    return await service.store_fx_rate(
        base_currency, target_currency, rate, provider, rate_date
    )


async def get_latest_rate(
    base_currency: str,
    target_currency: str,
    provider: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get latest FX rate"""
    service = get_currency_database_service()
    return await service.get_latest_fx_rate(base_currency, target_currency, provider)


async def store_conversion_record(
    base_currency: str,
    target_currency: str,
    base_amount: Decimal,
    target_amount: Decimal,
    rate_used: Decimal,
    provider: str,
    context: Dict[str, Any]
) -> str:
    """Store currency conversion record"""
    service = get_currency_database_service()
    return await service.store_conversion_audit(
        base_currency, target_currency, base_amount, target_amount, rate_used, provider, context
    )