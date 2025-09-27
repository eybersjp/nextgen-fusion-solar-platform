"""Database Integration Service for Compliance Service

Integrates the shared database connection pooling with compliance service operations:
- Rule evaluation results persistence
- Jurisdiction-specific rule storage
- Compliance audit trails
- Performance metrics tracking
- Entity validation history
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
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


class ComplianceDatabaseService:
    """Database service for compliance operations with optimized connection pooling"""
    
    def __init__(self, service_name: str = "svc-compliance"):
        self.service_name = service_name
        self.pool_manager = get_pool_manager()
        self._initialized = False
    
    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize database pools for compliance service"""
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
                pool_size=10,
                max_overflow=15,
                pool_timeout=30,
                command_timeout=60,
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
    
    async def store_rule_evaluation_result(
        self,
        rule_id: str,
        entity_id: str,
        entity_type: str,
        evaluation_context: Dict[str, Any],
        result: Dict[str, Any]
    ) -> str:
        """Store rule evaluation result in database"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO rule_evaluation_results 
                (rule_id, entity_id, entity_type, evaluation_context, result, created_at)
                VALUES (:rule_id, :entity_id, :entity_type, :evaluation_context, :result, :created_at)
                RETURNING id
            """)
            
            result_db = await session.execute(query, {
                "rule_id": rule_id,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "evaluation_context": evaluation_context,
                "result": result,
                "created_at": datetime.utcnow()
            })
            
            evaluation_id = result_db.scalar()
            logger.info(f"Stored rule evaluation result {evaluation_id}")
            return evaluation_id
    
    async def get_rule_evaluation_results(
        self,
        rule_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve rule evaluation results with filtering"""
        async with self.get_async_session_context() as session:
            conditions = []
            params = {"limit": limit}
            
            if rule_id:
                conditions.append("rule_id = :rule_id")
                params["rule_id"] = rule_id
            
            if entity_id:
                conditions.append("entity_id = :entity_id")
                params["entity_id"] = entity_id
            
            if entity_type:
                conditions.append("entity_type = :entity_type")
                params["entity_type"] = entity_type
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = text(f"""
                SELECT id, rule_id, entity_id, entity_type, evaluation_context, result, created_at
                FROM rule_evaluation_results
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "rule_id": row[1],
                    "entity_id": row[2],
                    "entity_type": row[3],
                    "evaluation_context": row[4],
                    "result": row[5],
                    "created_at": row[6]
                }
                for row in rows
            ]
    
    async def store_jurisdiction_rule(
        self,
        jurisdiction: str,
        rule_type: str,
        rule_data: Dict[str, Any],
        version: str = "1.0"
    ) -> str:
        """Store jurisdiction-specific rule"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO jurisdiction_rules 
                (jurisdiction, rule_type, rule_data, version, created_at, updated_at)
                VALUES (:jurisdiction, :rule_type, :rule_data, :version, :created_at, :updated_at)
                ON CONFLICT (jurisdiction, rule_type, version)
                DO UPDATE SET 
                    rule_data = EXCLUDED.rule_data,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """)
            
            now = datetime.utcnow()
            result = await session.execute(query, {
                "jurisdiction": jurisdiction,
                "rule_type": rule_type,
                "rule_data": rule_data,
                "version": version,
                "created_at": now,
                "updated_at": now
            })
            
            rule_id = result.scalar()
            logger.info(f"Stored jurisdiction rule {rule_id} for {jurisdiction}")
            return rule_id
    
    async def get_jurisdiction_rules(
        self,
        jurisdiction: str,
        rule_type: Optional[str] = None,
        version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve jurisdiction-specific rules"""
        async with self.get_async_session_context() as session:
            conditions = ["jurisdiction = :jurisdiction"]
            params = {"jurisdiction": jurisdiction}
            
            if rule_type:
                conditions.append("rule_type = :rule_type")
                params["rule_type"] = rule_type
            
            if version:
                conditions.append("version = :version")
                params["version"] = version
            
            where_clause = " AND ".join(conditions)
            
            query = text(f"""
                SELECT id, rule_type, rule_data, version, created_at, updated_at
                FROM jurisdiction_rules
                WHERE {where_clause}
                ORDER BY rule_type, version DESC
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "rule_type": row[1],
                    "rule_data": row[2],
                    "version": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                }
                for row in rows
            ]
    
    async def store_compliance_audit_entry(
        self,
        entity_id: str,
        entity_type: str,
        audit_type: str,
        audit_data: Dict[str, Any],
        compliance_status: str,
        violations: List[Dict[str, Any]] = None
    ) -> str:
        """Store compliance audit entry"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO compliance_audit_trail 
                (entity_id, entity_type, audit_type, audit_data, compliance_status, violations, created_at)
                VALUES (:entity_id, :entity_type, :audit_type, :audit_data, :compliance_status, :violations, :created_at)
                RETURNING id
            """)
            
            result = await session.execute(query, {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "audit_type": audit_type,
                "audit_data": audit_data,
                "compliance_status": compliance_status,
                "violations": violations or [],
                "created_at": datetime.utcnow()
            })
            
            audit_id = result.scalar()
            logger.info(f"Stored compliance audit entry {audit_id}")
            return audit_id
    
    async def get_compliance_audit_trail(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        audit_type: Optional[str] = None,
        compliance_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve compliance audit trail"""
        async with self.get_async_session_context() as session:
            conditions = []
            params = {"limit": limit}
            
            if entity_id:
                conditions.append("entity_id = :entity_id")
                params["entity_id"] = entity_id
            
            if entity_type:
                conditions.append("entity_type = :entity_type")
                params["entity_type"] = entity_type
            
            if audit_type:
                conditions.append("audit_type = :audit_type")
                params["audit_type"] = audit_type
            
            if compliance_status:
                conditions.append("compliance_status = :compliance_status")
                params["compliance_status"] = compliance_status
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = text(f"""
                SELECT id, entity_id, entity_type, audit_type, audit_data, 
                       compliance_status, violations, created_at
                FROM compliance_audit_trail
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "entity_id": row[1],
                    "entity_type": row[2],
                    "audit_type": row[3],
                    "audit_data": row[4],
                    "compliance_status": row[5],
                    "violations": row[6],
                    "created_at": row[7]
                }
                for row in rows
            ]
    
    async def store_rule_performance_metrics(
        self,
        rule_id: str,
        execution_time_ms: float,
        memory_usage_mb: float,
        cache_hit: bool,
        evaluation_count: int = 1
    ) -> None:
        """Store rule performance metrics"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO rule_performance_metrics 
                (rule_id, execution_time_ms, memory_usage_mb, cache_hit, evaluation_count, created_at)
                VALUES (:rule_id, :execution_time_ms, :memory_usage_mb, :cache_hit, :evaluation_count, :created_at)
            """)
            
            await session.execute(query, {
                "rule_id": rule_id,
                "execution_time_ms": execution_time_ms,
                "memory_usage_mb": memory_usage_mb,
                "cache_hit": cache_hit,
                "evaluation_count": evaluation_count,
                "created_at": datetime.utcnow()
            })
            
            logger.debug(f"Stored performance metrics for rule {rule_id}")
    
    async def get_rule_performance_metrics(
        self,
        rule_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Retrieve rule performance metrics"""
        async with self.get_async_session_context() as session:
            conditions = []
            params = {"limit": limit}
            
            if rule_id:
                conditions.append("rule_id = :rule_id")
                params["rule_id"] = rule_id
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = text(f"""
                SELECT rule_id, execution_time_ms, memory_usage_mb, cache_hit, 
                       evaluation_count, created_at
                FROM rule_performance_metrics
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "rule_id": row[0],
                    "execution_time_ms": row[1],
                    "memory_usage_mb": row[2],
                    "cache_hit": row[3],
                    "evaluation_count": row[4],
                    "created_at": row[5]
                }
                for row in rows
            ]
    
    async def get_rule_performance_summary(
        self,
        rule_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated rule performance summary"""
        async with self.get_async_session_context() as session:
            conditions = []
            params = {}
            
            if rule_id:
                conditions.append("rule_id = :rule_id")
                params["rule_id"] = rule_id
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = text(f"""
                SELECT 
                    rule_id,
                    COUNT(*) as total_evaluations,
                    AVG(execution_time_ms) as avg_execution_time,
                    MIN(execution_time_ms) as min_execution_time,
                    MAX(execution_time_ms) as max_execution_time,
                    AVG(memory_usage_mb) as avg_memory_usage,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                    SUM(evaluation_count) as total_evaluation_count
                FROM rule_performance_metrics
                WHERE {where_clause}
                GROUP BY rule_id
                ORDER BY total_evaluations DESC
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            summary = []
            for row in rows:
                cache_hit_rate = (row[6] / row[0]) * 100 if row[0] > 0 else 0
                summary.append({
                    "rule_id": row[0],
                    "total_evaluations": row[1],
                    "avg_execution_time_ms": float(row[2]) if row[2] else 0,
                    "min_execution_time_ms": float(row[3]) if row[3] else 0,
                    "max_execution_time_ms": float(row[4]) if row[4] else 0,
                    "avg_memory_usage_mb": float(row[5]) if row[5] else 0,
                    "cache_hits": row[6],
                    "cache_hit_rate_percent": cache_hit_rate,
                    "total_evaluation_count": row[7]
                })
            
            return {
                "summary": summary,
                "total_rules": len(summary),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def cleanup_old_data(
        self,
        retention_days: int = 90
    ) -> Dict[str, int]:
        """Clean up old data based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        async with self.get_async_session_context() as session:
            # Clean up old evaluation results
            query1 = text("""
                DELETE FROM rule_evaluation_results 
                WHERE created_at < :cutoff_date
            """)
            result1 = await session.execute(query1, {"cutoff_date": cutoff_date})
            
            # Clean up old audit trail entries
            query2 = text("""
                DELETE FROM compliance_audit_trail 
                WHERE created_at < :cutoff_date
            """)
            result2 = await session.execute(query2, {"cutoff_date": cutoff_date})
            
            # Clean up old performance metrics
            query3 = text("""
                DELETE FROM rule_performance_metrics 
                WHERE created_at < :cutoff_date
            """)
            result3 = await session.execute(query3, {"cutoff_date": cutoff_date})
            
            cleanup_stats = {
                "evaluation_results_deleted": result1.rowcount,
                "audit_entries_deleted": result2.rowcount,
                "performance_metrics_deleted": result3.rowcount
            }
            
            logger.info(f"Cleaned up old compliance data: {cleanup_stats}")
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
_compliance_db_service: Optional[ComplianceDatabaseService] = None


def get_compliance_database_service() -> ComplianceDatabaseService:
    """Get global compliance database service instance"""
    global _compliance_db_service
    if _compliance_db_service is None:
        _compliance_db_service = ComplianceDatabaseService()
    return _compliance_db_service


# Convenience functions
async def store_rule_evaluation(
    rule_id: str,
    entity_id: str,
    entity_type: str,
    evaluation_context: Dict[str, Any],
    result: Dict[str, Any]
) -> str:
    """Store rule evaluation result"""
    service = get_compliance_database_service()
    return await service.store_rule_evaluation_result(
        rule_id, entity_id, entity_type, evaluation_context, result
    )


async def get_rule_evaluations(
    rule_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get rule evaluation results"""
    service = get_compliance_database_service()
    return await service.get_rule_evaluation_results(
        rule_id=rule_id, entity_id=entity_id, limit=limit
    )


async def store_audit_entry(
    entity_id: str,
    entity_type: str,
    audit_type: str,
    audit_data: Dict[str, Any],
    compliance_status: str,
    violations: List[Dict[str, Any]] = None
) -> str:
    """Store compliance audit entry"""
    service = get_compliance_database_service()
    return await service.store_compliance_audit_entry(
        entity_id, entity_type, audit_type, audit_data, compliance_status, violations
    )