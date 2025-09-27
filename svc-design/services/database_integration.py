"""Database Integration Service for Design Service

Integrates the shared database connection pooling with design service operations:
- Layout optimization data persistence
- Component specifications caching
- Design validation results
- Performance metrics storage
- 3D model data management
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


class DesignDatabaseService:
    """Database service for design operations with optimized connection pooling"""
    
    def __init__(self, service_name: str = "svc-design"):
        self.service_name = service_name
        self.pool_manager = get_pool_manager()
        self._initialized = False
    
    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize database pools for design service"""
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
                pool_size=15,  # Higher for complex design calculations
                max_overflow=25,
                pool_timeout=45,
                command_timeout=120,  # Longer for complex queries
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
    
    async def store_layout_optimization_result(
        self,
        design_id: str,
        optimization_data: Dict[str, Any],
        result_data: Dict[str, Any]
    ) -> str:
        """Store layout optimization result in database"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO design_optimization_results 
                (design_id, optimization_data, result_data, created_at)
                VALUES (:design_id, :optimization_data, :result_data, :created_at)
                RETURNING id
            """)
            
            result = await session.execute(query, {
                "design_id": design_id,
                "optimization_data": optimization_data,
                "result_data": result_data,
                "created_at": datetime.utcnow()
            })
            
            result_id = result.scalar()
            logger.info(f"Stored optimization result {result_id} for design {design_id}")
            return result_id
    
    async def get_layout_optimization_result(
        self,
        design_id: str,
        optimization_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve layout optimization result from database"""
        async with self.get_async_session_context() as session:
            if optimization_hash:
                query = text("""
                    SELECT id, optimization_data, result_data, created_at
                    FROM design_optimization_results
                    WHERE design_id = :design_id 
                    AND MD5(optimization_data::text) = :optimization_hash
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                params = {"design_id": design_id, "optimization_hash": optimization_hash}
            else:
                query = text("""
                    SELECT id, optimization_data, result_data, created_at
                    FROM design_optimization_results
                    WHERE design_id = :design_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                params = {"design_id": design_id}
            
            result = await session.execute(query, params)
            row = result.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "optimization_data": row[1],
                    "result_data": row[2],
                    "created_at": row[3]
                }
            
            return None
    
    async def store_component_specification(
        self,
        component_type: str,
        manufacturer: str,
        model: str,
        specifications: Dict[str, Any]
    ) -> str:
        """Store component specification in database"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO component_specifications 
                (component_type, manufacturer, model, specifications, created_at, updated_at)
                VALUES (:component_type, :manufacturer, :model, :specifications, :created_at, :updated_at)
                ON CONFLICT (component_type, manufacturer, model)
                DO UPDATE SET 
                    specifications = EXCLUDED.specifications,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """)
            
            now = datetime.utcnow()
            result = await session.execute(query, {
                "component_type": component_type,
                "manufacturer": manufacturer,
                "model": model,
                "specifications": specifications,
                "created_at": now,
                "updated_at": now
            })
            
            component_id = result.scalar()
            logger.info(f"Stored component specification {component_id}")
            return component_id
    
    async def get_component_specification(
        self,
        component_type: str,
        manufacturer: str,
        model: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve component specification from database"""
        async with self.get_async_session_context() as session:
            query = text("""
                SELECT id, specifications, created_at, updated_at
                FROM component_specifications
                WHERE component_type = :component_type 
                AND manufacturer = :manufacturer 
                AND model = :model
            """)
            
            result = await session.execute(query, {
                "component_type": component_type,
                "manufacturer": manufacturer,
                "model": model
            })
            
            row = result.fetchone()
            if row:
                return {
                    "id": row[0],
                    "specifications": row[1],
                    "created_at": row[2],
                    "updated_at": row[3]
                }
            
            return None
    
    async def store_design_validation_result(
        self,
        design_id: str,
        validation_type: str,
        validation_data: Dict[str, Any],
        result: Dict[str, Any]
    ) -> str:
        """Store design validation result"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO design_validation_results 
                (design_id, validation_type, validation_data, result, created_at)
                VALUES (:design_id, :validation_type, :validation_data, :result, :created_at)
                RETURNING id
            """)
            
            result_db = await session.execute(query, {
                "design_id": design_id,
                "validation_type": validation_type,
                "validation_data": validation_data,
                "result": result,
                "created_at": datetime.utcnow()
            })
            
            validation_id = result_db.scalar()
            logger.info(f"Stored validation result {validation_id} for design {design_id}")
            return validation_id
    
    async def get_design_validation_results(
        self,
        design_id: str,
        validation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve design validation results"""
        async with self.get_async_session_context() as session:
            if validation_type:
                query = text("""
                    SELECT id, validation_type, validation_data, result, created_at
                    FROM design_validation_results
                    WHERE design_id = :design_id AND validation_type = :validation_type
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                params = {"design_id": design_id, "validation_type": validation_type, "limit": limit}
            else:
                query = text("""
                    SELECT id, validation_type, validation_data, result, created_at
                    FROM design_validation_results
                    WHERE design_id = :design_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
                params = {"design_id": design_id, "limit": limit}
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "validation_type": row[1],
                    "validation_data": row[2],
                    "result": row[3],
                    "created_at": row[4]
                }
                for row in rows
            ]
    
    async def store_performance_metrics(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> None:
        """Store performance metrics for design operations"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO design_performance_metrics 
                (operation_type, operation_data, metrics, created_at)
                VALUES (:operation_type, :operation_data, :metrics, :created_at)
            """)
            
            await session.execute(query, {
                "operation_type": operation_type,
                "operation_data": operation_data,
                "metrics": metrics,
                "created_at": datetime.utcnow()
            })
            
            logger.debug(f"Stored performance metrics for {operation_type}")
    
    async def get_performance_metrics(
        self,
        operation_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve performance metrics"""
        async with self.get_async_session_context() as session:
            conditions = ["operation_type = :operation_type"]
            params = {"operation_type": operation_type, "limit": limit}
            
            if start_date:
                conditions.append("created_at >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("created_at <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions)
            
            query = text(f"""
                SELECT operation_data, metrics, created_at
                FROM design_performance_metrics
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "operation_data": row[0],
                    "metrics": row[1],
                    "created_at": row[2]
                }
                for row in rows
            ]
    
    async def cleanup_old_data(
        self,
        retention_days: int = 90
    ) -> Dict[str, int]:
        """Clean up old data based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        async with self.get_async_session_context() as session:
            # Clean up old optimization results
            query1 = text("""
                DELETE FROM design_optimization_results 
                WHERE created_at < :cutoff_date
            """)
            result1 = await session.execute(query1, {"cutoff_date": cutoff_date})
            
            # Clean up old validation results
            query2 = text("""
                DELETE FROM design_validation_results 
                WHERE created_at < :cutoff_date
            """)
            result2 = await session.execute(query2, {"cutoff_date": cutoff_date})
            
            # Clean up old performance metrics
            query3 = text("""
                DELETE FROM design_performance_metrics 
                WHERE created_at < :cutoff_date
            """)
            result3 = await session.execute(query3, {"cutoff_date": cutoff_date})
            
            cleanup_stats = {
                "optimization_results_deleted": result1.rowcount,
                "validation_results_deleted": result2.rowcount,
                "performance_metrics_deleted": result3.rowcount
            }
            
            logger.info(f"Cleaned up old data: {cleanup_stats}")
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
_design_db_service: Optional[DesignDatabaseService] = None


def get_design_database_service() -> DesignDatabaseService:
    """Get global design database service instance"""
    global _design_db_service
    if _design_db_service is None:
        _design_db_service = DesignDatabaseService()
    return _design_db_service


# Convenience functions
async def store_layout_optimization(
    design_id: str,
    optimization_data: Dict[str, Any],
    result_data: Dict[str, Any]
) -> str:
    """Store layout optimization result"""
    service = get_design_database_service()
    return await service.store_layout_optimization_result(
        design_id, optimization_data, result_data
    )


async def get_layout_optimization(
    design_id: str,
    optimization_hash: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get layout optimization result"""
    service = get_design_database_service()
    return await service.get_layout_optimization_result(design_id, optimization_hash)


async def store_component_spec(
    component_type: str,
    manufacturer: str,
    model: str,
    specifications: Dict[str, Any]
) -> str:
    """Store component specification"""
    service = get_design_database_service()
    return await service.store_component_specification(
        component_type, manufacturer, model, specifications
    )


async def get_component_spec(
    component_type: str,
    manufacturer: str,
    model: str
) -> Optional[Dict[str, Any]]:
    """Get component specification"""
    service = get_design_database_service()
    return await service.get_component_specification(
        component_type, manufacturer, model
    )