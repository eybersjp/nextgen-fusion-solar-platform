"""Database Integration Service for Project Service

Integrates the shared database connection pooling with project service operations:
- Project data persistence and retrieval
- Task dependency management
- Resource allocation tracking
- Timeline and milestone management
- Critical path calculation caching
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


class ProjectDatabaseService:
    """Database service for project operations with optimized connection pooling"""
    
    def __init__(self, service_name: str = "svc-project"):
        self.service_name = service_name
        self.pool_manager = get_pool_manager()
        self._initialized = False
    
    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """Initialize database pools for project service"""
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
                pool_size=12,
                max_overflow=18,
                pool_timeout=30,
                command_timeout=90,  # Longer timeout for complex project queries
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
    
    async def store_project(
        self,
        project_id: str,
        name: str,
        description: str,
        start_date: datetime,
        end_date: datetime,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store project data in database"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO projects 
                (project_id, name, description, start_date, end_date, status, metadata, created_at, updated_at)
                VALUES (:project_id, :name, :description, :start_date, :end_date, :status, :metadata, :created_at, :updated_at)
                ON CONFLICT (project_id)
                DO UPDATE SET 
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """)
            
            now = datetime.utcnow()
            result = await session.execute(query, {
                "project_id": project_id,
                "name": name,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now
            })
            
            db_id = result.scalar()
            logger.info(f"Stored project {project_id}")
            return db_id
    
    async def get_project(
        self,
        project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve project by ID"""
        async with self.get_async_session_context() as session:
            query = text("""
                SELECT id, project_id, name, description, start_date, end_date, 
                       status, metadata, created_at, updated_at
                FROM projects
                WHERE project_id = :project_id
            """)
            
            result = await session.execute(query, {"project_id": project_id})
            row = result.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "project_id": row[1],
                    "name": row[2],
                    "description": row[3],
                    "start_date": row[4],
                    "end_date": row[5],
                    "status": row[6],
                    "metadata": row[7],
                    "created_at": row[8],
                    "updated_at": row[9]
                }
            
            return None
    
    async def store_task(
        self,
        task_id: str,
        project_id: str,
        name: str,
        description: str,
        start_date: datetime,
        end_date: datetime,
        duration_hours: float,
        status: str,
        assigned_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store task data in database"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO tasks 
                (task_id, project_id, name, description, start_date, end_date, 
                 duration_hours, status, assigned_to, metadata, created_at, updated_at)
                VALUES (:task_id, :project_id, :name, :description, :start_date, :end_date, 
                        :duration_hours, :status, :assigned_to, :metadata, :created_at, :updated_at)
                ON CONFLICT (task_id)
                DO UPDATE SET 
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    duration_hours = EXCLUDED.duration_hours,
                    status = EXCLUDED.status,
                    assigned_to = EXCLUDED.assigned_to,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """)
            
            now = datetime.utcnow()
            result = await session.execute(query, {
                "task_id": task_id,
                "project_id": project_id,
                "name": name,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
                "duration_hours": duration_hours,
                "status": status,
                "assigned_to": assigned_to,
                "metadata": metadata or {},
                "created_at": now,
                "updated_at": now
            })
            
            db_id = result.scalar()
            logger.info(f"Stored task {task_id} for project {project_id}")
            return db_id
    
    async def store_task_dependency(
        self,
        predecessor_task_id: str,
        successor_task_id: str,
        dependency_type: str = "finish_to_start",
        lag_hours: float = 0.0
    ) -> str:
        """Store task dependency relationship"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO task_dependencies 
                (predecessor_task_id, successor_task_id, dependency_type, lag_hours, created_at)
                VALUES (:predecessor_task_id, :successor_task_id, :dependency_type, :lag_hours, :created_at)
                ON CONFLICT (predecessor_task_id, successor_task_id)
                DO UPDATE SET 
                    dependency_type = EXCLUDED.dependency_type,
                    lag_hours = EXCLUDED.lag_hours
                RETURNING id
            """)
            
            result = await session.execute(query, {
                "predecessor_task_id": predecessor_task_id,
                "successor_task_id": successor_task_id,
                "dependency_type": dependency_type,
                "lag_hours": lag_hours,
                "created_at": datetime.utcnow()
            })
            
            dep_id = result.scalar()
            logger.info(f"Stored dependency {predecessor_task_id} -> {successor_task_id}")
            return dep_id
    
    async def get_task_dependencies(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """Get all task dependencies for a project"""
        async with self.get_async_session_context() as session:
            query = text("""
                SELECT td.id, td.predecessor_task_id, td.successor_task_id, 
                       td.dependency_type, td.lag_hours, td.created_at,
                       t1.name as predecessor_name, t2.name as successor_name
                FROM task_dependencies td
                JOIN tasks t1 ON td.predecessor_task_id = t1.task_id
                JOIN tasks t2 ON td.successor_task_id = t2.task_id
                WHERE t1.project_id = :project_id AND t2.project_id = :project_id
                ORDER BY td.created_at
            """)
            
            result = await session.execute(query, {"project_id": project_id})
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "predecessor_task_id": row[1],
                    "successor_task_id": row[2],
                    "dependency_type": row[3],
                    "lag_hours": row[4],
                    "created_at": row[5],
                    "predecessor_name": row[6],
                    "successor_name": row[7]
                }
                for row in rows
            ]
    
    async def store_resource_allocation(
        self,
        allocation_id: str,
        project_id: str,
        task_id: str,
        resource_type: str,
        resource_id: str,
        allocation_percentage: float,
        start_date: datetime,
        end_date: datetime,
        cost_per_hour: Optional[float] = None
    ) -> str:
        """Store resource allocation"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO resource_allocations 
                (allocation_id, project_id, task_id, resource_type, resource_id, 
                 allocation_percentage, start_date, end_date, cost_per_hour, created_at, updated_at)
                VALUES (:allocation_id, :project_id, :task_id, :resource_type, :resource_id, 
                        :allocation_percentage, :start_date, :end_date, :cost_per_hour, :created_at, :updated_at)
                ON CONFLICT (allocation_id)
                DO UPDATE SET 
                    allocation_percentage = EXCLUDED.allocation_percentage,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    cost_per_hour = EXCLUDED.cost_per_hour,
                    updated_at = EXCLUDED.updated_at
                RETURNING id
            """)
            
            now = datetime.utcnow()
            result = await session.execute(query, {
                "allocation_id": allocation_id,
                "project_id": project_id,
                "task_id": task_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "allocation_percentage": allocation_percentage,
                "start_date": start_date,
                "end_date": end_date,
                "cost_per_hour": cost_per_hour,
                "created_at": now,
                "updated_at": now
            })
            
            db_id = result.scalar()
            logger.info(f"Stored resource allocation {allocation_id}")
            return db_id
    
    async def get_resource_allocations(
        self,
        project_id: str,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get resource allocations for a project"""
        async with self.get_async_session_context() as session:
            conditions = ["project_id = :project_id"]
            params = {"project_id": project_id}
            
            if resource_type:
                conditions.append("resource_type = :resource_type")
                params["resource_type"] = resource_type
            
            if start_date:
                conditions.append("end_date >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("start_date <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions)
            
            query = text(f"""
                SELECT ra.id, ra.allocation_id, ra.task_id, ra.resource_type, ra.resource_id,
                       ra.allocation_percentage, ra.start_date, ra.end_date, ra.cost_per_hour,
                       ra.created_at, ra.updated_at, t.name as task_name
                FROM resource_allocations ra
                JOIN tasks t ON ra.task_id = t.task_id
                WHERE {where_clause}
                ORDER BY ra.start_date, ra.resource_type
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "allocation_id": row[1],
                    "task_id": row[2],
                    "resource_type": row[3],
                    "resource_id": row[4],
                    "allocation_percentage": row[5],
                    "start_date": row[6],
                    "end_date": row[7],
                    "cost_per_hour": row[8],
                    "created_at": row[9],
                    "updated_at": row[10],
                    "task_name": row[11]
                }
                for row in rows
            ]
    
    async def store_critical_path_calculation(
        self,
        project_id: str,
        calculation_id: str,
        critical_path_tasks: List[str],
        total_duration_hours: float,
        calculation_metadata: Dict[str, Any]
    ) -> str:
        """Store critical path calculation result"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO critical_path_calculations 
                (calculation_id, project_id, critical_path_tasks, total_duration_hours, 
                 calculation_metadata, created_at)
                VALUES (:calculation_id, :project_id, :critical_path_tasks, :total_duration_hours, 
                        :calculation_metadata, :created_at)
                RETURNING id
            """)
            
            result = await session.execute(query, {
                "calculation_id": calculation_id,
                "project_id": project_id,
                "critical_path_tasks": critical_path_tasks,
                "total_duration_hours": total_duration_hours,
                "calculation_metadata": calculation_metadata,
                "created_at": datetime.utcnow()
            })
            
            db_id = result.scalar()
            logger.info(f"Stored critical path calculation {calculation_id}")
            return db_id
    
    async def get_latest_critical_path(
        self,
        project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get latest critical path calculation for project"""
        async with self.get_async_session_context() as session:
            query = text("""
                SELECT id, calculation_id, critical_path_tasks, total_duration_hours, 
                       calculation_metadata, created_at
                FROM critical_path_calculations
                WHERE project_id = :project_id
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = await session.execute(query, {"project_id": project_id})
            row = result.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "calculation_id": row[1],
                    "project_id": project_id,
                    "critical_path_tasks": row[2],
                    "total_duration_hours": row[3],
                    "calculation_metadata": row[4],
                    "created_at": row[5]
                }
            
            return None
    
    async def store_project_metrics(
        self,
        project_id: str,
        metrics_date: datetime,
        completion_percentage: float,
        budget_used: float,
        budget_total: float,
        tasks_completed: int,
        tasks_total: int,
        schedule_variance_hours: float,
        cost_variance: float,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store project performance metrics"""
        async with self.get_async_session_context() as session:
            query = text("""
                INSERT INTO project_metrics 
                (project_id, metrics_date, completion_percentage, budget_used, budget_total,
                 tasks_completed, tasks_total, schedule_variance_hours, cost_variance, 
                 additional_metrics, created_at)
                VALUES (:project_id, :metrics_date, :completion_percentage, :budget_used, :budget_total,
                        :tasks_completed, :tasks_total, :schedule_variance_hours, :cost_variance, 
                        :additional_metrics, :created_at)
                RETURNING id
            """)
            
            result = await session.execute(query, {
                "project_id": project_id,
                "metrics_date": metrics_date,
                "completion_percentage": completion_percentage,
                "budget_used": budget_used,
                "budget_total": budget_total,
                "tasks_completed": tasks_completed,
                "tasks_total": tasks_total,
                "schedule_variance_hours": schedule_variance_hours,
                "cost_variance": cost_variance,
                "additional_metrics": additional_metrics or {},
                "created_at": datetime.utcnow()
            })
            
            metrics_id = result.scalar()
            logger.info(f"Stored project metrics for {project_id}")
            return metrics_id
    
    async def get_project_metrics_history(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get project metrics history"""
        async with self.get_async_session_context() as session:
            conditions = ["project_id = :project_id"]
            params = {"project_id": project_id, "limit": limit}
            
            if start_date:
                conditions.append("metrics_date >= :start_date")
                params["start_date"] = start_date
            
            if end_date:
                conditions.append("metrics_date <= :end_date")
                params["end_date"] = end_date
            
            where_clause = " AND ".join(conditions)
            
            query = text(f"""
                SELECT id, metrics_date, completion_percentage, budget_used, budget_total,
                       tasks_completed, tasks_total, schedule_variance_hours, cost_variance, 
                       additional_metrics, created_at
                FROM project_metrics
                WHERE {where_clause}
                ORDER BY metrics_date DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [
                {
                    "id": row[0],
                    "project_id": project_id,
                    "metrics_date": row[1],
                    "completion_percentage": row[2],
                    "budget_used": row[3],
                    "budget_total": row[4],
                    "tasks_completed": row[5],
                    "tasks_total": row[6],
                    "schedule_variance_hours": row[7],
                    "cost_variance": row[8],
                    "additional_metrics": row[9],
                    "created_at": row[10]
                }
                for row in rows
            ]
    
    async def get_project_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get project service statistics"""
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
            
            # Get project statistics
            proj_query = text(f"""
                SELECT 
                    COUNT(*) as total_projects,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_projects,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_projects,
                    COUNT(CASE WHEN status = 'on_hold' THEN 1 END) as on_hold_projects
                FROM projects
                WHERE {where_clause}
            """)
            
            proj_result = await session.execute(proj_query, params)
            proj_row = proj_result.fetchone()
            
            # Get task statistics
            task_query = text(f"""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_tasks,
                    AVG(duration_hours) as avg_task_duration
                FROM tasks
                WHERE {where_clause}
            """)
            
            task_result = await session.execute(task_query, params)
            task_row = task_result.fetchone()
            
            return {
                "projects": {
                    "total_projects": proj_row[0] if proj_row else 0,
                    "active_projects": proj_row[1] if proj_row else 0,
                    "completed_projects": proj_row[2] if proj_row else 0,
                    "on_hold_projects": proj_row[3] if proj_row else 0
                },
                "tasks": {
                    "total_tasks": task_row[0] if task_row else 0,
                    "completed_tasks": task_row[1] if task_row else 0,
                    "in_progress_tasks": task_row[2] if task_row else 0,
                    "avg_task_duration_hours": float(task_row[3]) if task_row and task_row[3] else 0
                },
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def cleanup_old_data(
        self,
        retention_days: int = 730  # 2 years for project data
    ) -> Dict[str, int]:
        """Clean up old data based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        async with self.get_async_session_context() as session:
            # Clean up old critical path calculations
            query1 = text("""
                DELETE FROM critical_path_calculations 
                WHERE created_at < :cutoff_date
            """)
            result1 = await session.execute(query1, {"cutoff_date": cutoff_date})
            
            # Clean up old project metrics (keep more recent ones)
            metrics_cutoff = datetime.utcnow() - timedelta(days=365)
            query2 = text("""
                DELETE FROM project_metrics 
                WHERE created_at < :cutoff_date
            """)
            result2 = await session.execute(query2, {"cutoff_date": metrics_cutoff})
            
            cleanup_stats = {
                "critical_path_calculations_deleted": result1.rowcount,
                "project_metrics_deleted": result2.rowcount
            }
            
            logger.info(f"Cleaned up old project data: {cleanup_stats}")
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
_project_db_service: Optional[ProjectDatabaseService] = None


def get_project_database_service() -> ProjectDatabaseService:
    """Get global project database service instance"""
    global _project_db_service
    if _project_db_service is None:
        _project_db_service = ProjectDatabaseService()
    return _project_db_service


# Convenience functions
async def store_project_data(
    project_id: str,
    name: str,
    description: str,
    start_date: datetime,
    end_date: datetime,
    status: str
) -> str:
    """Store project data"""
    service = get_project_database_service()
    return await service.store_project(
        project_id, name, description, start_date, end_date, status
    )


async def get_project_data(project_id: str) -> Optional[Dict[str, Any]]:
    """Get project data"""
    service = get_project_database_service()
    return await service.get_project(project_id)


async def store_task_data(
    task_id: str,
    project_id: str,
    name: str,
    description: str,
    start_date: datetime,
    end_date: datetime,
    duration_hours: float,
    status: str
) -> str:
    """Store task data"""
    service = get_project_database_service()
    return await service.store_task(
        task_id, project_id, name, description, start_date, end_date, duration_hours, status
    )


# Create global instance for easy import
project_db_service = get_project_database_service()