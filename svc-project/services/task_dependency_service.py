"""Task Dependency Management Service for NextGen Fusion Platform

Provides comprehensive project management capabilities:
- Critical path method (CPM) calculations
- Resource leveling and optimization
- Schedule optimization and conflict resolution
- Progress tracking and reporting
- Gantt chart data generation
- What-if scenario analysis
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum
import networkx as nx
from sqlalchemy import select, and_, or_, desc, asc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from ..models.task_dependencies import (
    ProjectTask, TaskDependency, ProjectResource, TaskResourceAllocation, TaskProgressLog,
    TaskStatus, TaskPriority, DependencyType, ResourceType, AllocationStatus
)
from shared.database.session import get_async_session
from shared.cache.redis_cache import cached, CacheManager

logger = logging.getLogger(__name__)


@dataclass
class CriticalPathResult:
    """Result of critical path analysis"""
    critical_path_tasks: List[str]  # Task IDs
    project_duration_hours: Decimal
    total_float_by_task: Dict[str, Decimal]
    free_float_by_task: Dict[str, Decimal]
    earliest_dates: Dict[str, Tuple[datetime, datetime]]  # start, finish
    latest_dates: Dict[str, Tuple[datetime, datetime]]    # start, finish


@dataclass
class ResourceConflict:
    """Resource allocation conflict"""
    resource_id: str
    resource_name: str
    conflicting_tasks: List[str]
    overallocation_amount: Decimal
    conflict_period: Tuple[datetime, datetime]
    suggested_resolution: str


@dataclass
class ScheduleOptimization:
    """Schedule optimization result"""
    original_duration: Decimal
    optimized_duration: Decimal
    time_saved: Decimal
    resource_conflicts_resolved: int
    task_adjustments: List[Dict[str, Any]]
    cost_impact: Optional[Decimal]


@dataclass
class ProjectMetrics:
    """Project performance metrics"""
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    overdue_tasks: int
    completion_percentage: Decimal
    schedule_performance_index: Decimal  # SPI
    cost_performance_index: Decimal      # CPI
    estimated_completion_date: datetime
    budget_variance: Decimal
    resource_utilization: Dict[str, Decimal]


class TaskDependencyService:
    """Service for managing task dependencies and project scheduling"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
    
    async def calculate_critical_path(self, project_id: str) -> CriticalPathResult:
        """Calculate critical path using CPM algorithm"""
        async with get_async_session() as session:
            # Load all tasks and dependencies for the project
            tasks_query = select(ProjectTask).where(
                ProjectTask.project_id == project_id
            ).options(
                selectinload(ProjectTask.predecessor_dependencies),
                selectinload(ProjectTask.successor_dependencies)
            )
            
            tasks_result = await session.execute(tasks_query)
            tasks = tasks_result.scalars().all()
            
            if not tasks:
                return CriticalPathResult(
                    critical_path_tasks=[],
                    project_duration_hours=Decimal('0'),
                    total_float_by_task={},
                    free_float_by_task={},
                    earliest_dates={},
                    latest_dates={}
                )
            
            # Create directed graph for CPM calculation
            graph = nx.DiGraph()
            
            # Add nodes (tasks)
            for task in tasks:
                duration = task.estimated_duration_hours or Decimal('0')
                graph.add_node(str(task.id), 
                              duration=float(duration),
                              task=task)
            
            # Add edges (dependencies)
            for task in tasks:
                for dep in task.predecessor_dependencies:
                    if dep.is_active and dep.dependency_type == DependencyType.FINISH_TO_START:
                        lag = float(dep.lag_hours or 0)
                        graph.add_edge(str(dep.predecessor_task_id), 
                                     str(dep.successor_task_id),
                                     lag=lag)
            
            # Forward pass - calculate earliest start/finish times
            earliest_start = {}
            earliest_finish = {}
            
            # Topological sort to process tasks in dependency order
            try:
                topo_order = list(nx.topological_sort(graph))
            except nx.NetworkXError:
                # Circular dependency detected
                logger.error(f"Circular dependency detected in project {project_id}")
                raise ValueError("Circular dependency detected in project schedule")
            
            for task_id in topo_order:
                task_data = graph.nodes[task_id]
                duration = task_data['duration']
                
                # Calculate earliest start
                max_predecessor_finish = 0
                for pred_id in graph.predecessors(task_id):
                    edge_data = graph.edges[pred_id, task_id]
                    lag = edge_data.get('lag', 0)
                    pred_finish = earliest_finish.get(pred_id, 0)
                    max_predecessor_finish = max(max_predecessor_finish, pred_finish + lag)
                
                earliest_start[task_id] = max_predecessor_finish
                earliest_finish[task_id] = max_predecessor_finish + duration
            
            # Project duration is the maximum earliest finish time
            project_duration = max(earliest_finish.values()) if earliest_finish else 0
            
            # Backward pass - calculate latest start/finish times
            latest_start = {}
            latest_finish = {}
            
            # Initialize latest finish times
            for task_id in topo_order:
                if not list(graph.successors(task_id)):  # End task
                    latest_finish[task_id] = project_duration
            
            # Process tasks in reverse topological order
            for task_id in reversed(topo_order):
                task_data = graph.nodes[task_id]
                duration = task_data['duration']
                
                if task_id not in latest_finish:
                    # Calculate latest finish based on successors
                    min_successor_start = float('inf')
                    for succ_id in graph.successors(task_id):
                        edge_data = graph.edges[task_id, succ_id]
                        lag = edge_data.get('lag', 0)
                        succ_start = latest_start.get(succ_id, project_duration)
                        min_successor_start = min(min_successor_start, succ_start - lag)
                    
                    latest_finish[task_id] = min_successor_start if min_successor_start != float('inf') else project_duration
                
                latest_start[task_id] = latest_finish[task_id] - duration
            
            # Calculate float times
            total_float = {}
            free_float = {}
            critical_path_tasks = []
            
            for task_id in topo_order:
                # Total float = Latest Start - Earliest Start
                total_float[task_id] = latest_start[task_id] - earliest_start[task_id]
                
                # Free float calculation
                min_successor_es = float('inf')
                for succ_id in graph.successors(task_id):
                    edge_data = graph.edges[task_id, succ_id]
                    lag = edge_data.get('lag', 0)
                    succ_es = earliest_start.get(succ_id, project_duration)
                    min_successor_es = min(min_successor_es, succ_es - lag)
                
                if min_successor_es == float('inf'):
                    free_float[task_id] = total_float[task_id]
                else:
                    free_float[task_id] = min_successor_es - earliest_finish[task_id]
                
                # Critical path tasks have zero total float
                if abs(total_float[task_id]) < 0.01:  # Account for floating point precision
                    critical_path_tasks.append(task_id)
            
            # Convert times to datetime objects
            project_start = min(task.planned_start_date for task in tasks if task.planned_start_date) or datetime.utcnow()
            
            earliest_dates = {}
            latest_dates = {}
            
            for task_id in topo_order:
                es_datetime = project_start + timedelta(hours=earliest_start[task_id])
                ef_datetime = project_start + timedelta(hours=earliest_finish[task_id])
                ls_datetime = project_start + timedelta(hours=latest_start[task_id])
                lf_datetime = project_start + timedelta(hours=latest_finish[task_id])
                
                earliest_dates[task_id] = (es_datetime, ef_datetime)
                latest_dates[task_id] = (ls_datetime, lf_datetime)
            
            # Update task records with calculated values
            for task in tasks:
                task_id = str(task.id)
                if task_id in earliest_dates:
                    task.earliest_start, task.earliest_finish = earliest_dates[task_id]
                    task.latest_start, task.latest_finish = latest_dates[task_id]
                    task.total_float = Decimal(str(total_float.get(task_id, 0)))
                    task.free_float = Decimal(str(free_float.get(task_id, 0)))
                    task.is_critical_path = task_id in critical_path_tasks
            
            await session.commit()
            
            return CriticalPathResult(
                critical_path_tasks=critical_path_tasks,
                project_duration_hours=Decimal(str(project_duration)),
                total_float_by_task={k: Decimal(str(v)) for k, v in total_float.items()},
                free_float_by_task={k: Decimal(str(v)) for k, v in free_float.items()},
                earliest_dates=earliest_dates,
                latest_dates=latest_dates
            )
    
    async def detect_resource_conflicts(self, project_id: str) -> List[ResourceConflict]:
        """Detect resource allocation conflicts"""
        async with get_async_session() as session:
            # Get all resource allocations for the project
            allocations_query = select(TaskResourceAllocation).join(
                ProjectTask
            ).join(
                ProjectResource
            ).where(
                and_(
                    ProjectTask.project_id == project_id,
                    TaskResourceAllocation.status.in_([
                        AllocationStatus.ALLOCATED, 
                        AllocationStatus.IN_USE
                    ])
                )
            ).options(
                joinedload(TaskResourceAllocation.task),
                joinedload(TaskResourceAllocation.resource)
            )
            
            allocations_result = await session.execute(allocations_query)
            allocations = allocations_result.scalars().all()
            
            # Group allocations by resource
            resource_allocations = {}
            for allocation in allocations:
                resource_id = str(allocation.resource_id)
                if resource_id not in resource_allocations:
                    resource_allocations[resource_id] = []
                resource_allocations[resource_id].append(allocation)
            
            conflicts = []
            
            # Check each resource for conflicts
            for resource_id, resource_allocs in resource_allocations.items():
                if len(resource_allocs) < 2:
                    continue
                
                resource = resource_allocs[0].resource
                
                # Sort allocations by start date
                sorted_allocs = sorted(resource_allocs, 
                                     key=lambda a: a.start_date or datetime.min)
                
                # Check for overlapping allocations
                for i in range(len(sorted_allocs)):
                    for j in range(i + 1, len(sorted_allocs)):
                        alloc1 = sorted_allocs[i]
                        alloc2 = sorted_allocs[j]
                        
                        # Check if allocations overlap
                        if (alloc1.start_date and alloc1.end_date and 
                            alloc2.start_date and alloc2.end_date):
                            
                            overlap_start = max(alloc1.start_date, alloc2.start_date)
                            overlap_end = min(alloc1.end_date, alloc2.end_date)
                            
                            if overlap_start < overlap_end:
                                # Calculate overallocation
                                total_allocated = alloc1.allocated_units + alloc2.allocated_units
                                available_capacity = resource.available_capacity or Decimal('0')
                                overallocation = max(Decimal('0'), total_allocated - available_capacity)
                                
                                if overallocation > 0:
                                    conflict = ResourceConflict(
                                        resource_id=resource_id,
                                        resource_name=resource.name,
                                        conflicting_tasks=[str(alloc1.task_id), str(alloc2.task_id)],
                                        overallocation_amount=overallocation,
                                        conflict_period=(overlap_start, overlap_end),
                                        suggested_resolution=self._suggest_conflict_resolution(
                                            alloc1, alloc2, overallocation
                                        )
                                    )
                                    conflicts.append(conflict)
            
            return conflicts
    
    def _suggest_conflict_resolution(
        self, 
        alloc1: TaskResourceAllocation, 
        alloc2: TaskResourceAllocation, 
        overallocation: Decimal
    ) -> str:
        """Suggest resolution for resource conflict"""
        task1 = alloc1.task
        task2 = alloc2.task
        
        # Priority-based resolution
        if task1.priority != task2.priority:
            higher_priority_task = task1 if task1.priority == TaskPriority.CRITICAL else task2
            return f"Prioritize {higher_priority_task.name} due to higher priority"
        
        # Critical path-based resolution
        if task1.is_critical_path and not task2.is_critical_path:
            return f"Prioritize {task1.name} as it's on the critical path"
        elif task2.is_critical_path and not task1.is_critical_path:
            return f"Prioritize {task2.name} as it's on the critical path"
        
        # Float-based resolution
        if task1.total_float and task2.total_float:
            if task1.total_float > task2.total_float:
                return f"Delay {task1.name} as it has more schedule flexibility"
            else:
                return f"Delay {task2.name} as it has more schedule flexibility"
        
        # Default suggestion
        return f"Consider splitting resource allocation or extending timeline"
    
    async def optimize_schedule(
        self, 
        project_id: str, 
        optimization_goals: List[str] = None
    ) -> ScheduleOptimization:
        """Optimize project schedule for time, cost, or resource efficiency"""
        if optimization_goals is None:
            optimization_goals = ['minimize_duration', 'resolve_conflicts']
        
        # Get current project state
        critical_path = await self.calculate_critical_path(project_id)
        conflicts = await self.detect_resource_conflicts(project_id)
        
        original_duration = critical_path.project_duration_hours
        task_adjustments = []
        
        # Resolve resource conflicts
        conflicts_resolved = 0
        for conflict in conflicts:
            # Implement conflict resolution logic
            adjustment = await self._resolve_resource_conflict(conflict)
            if adjustment:
                task_adjustments.append(adjustment)
                conflicts_resolved += 1
        
        # Optimize for duration if requested
        if 'minimize_duration' in optimization_goals:
            duration_optimizations = await self._optimize_for_duration(project_id, critical_path)
            task_adjustments.extend(duration_optimizations)
        
        # Recalculate critical path after optimizations
        optimized_critical_path = await self.calculate_critical_path(project_id)
        optimized_duration = optimized_critical_path.project_duration_hours
        
        time_saved = original_duration - optimized_duration
        
        return ScheduleOptimization(
            original_duration=original_duration,
            optimized_duration=optimized_duration,
            time_saved=time_saved,
            resource_conflicts_resolved=conflicts_resolved,
            task_adjustments=task_adjustments,
            cost_impact=None  # Would calculate based on adjustments
        )
    
    async def _resolve_resource_conflict(self, conflict: ResourceConflict) -> Optional[Dict[str, Any]]:
        """Resolve a specific resource conflict"""
        # This is a simplified implementation
        # In practice, this would involve complex optimization algorithms
        
        async with get_async_session() as session:
            # Get the conflicting tasks
            tasks_query = select(ProjectTask).where(
                ProjectTask.id.in_(conflict.conflicting_tasks)
            )
            tasks_result = await session.execute(tasks_query)
            tasks = tasks_result.scalars().all()
            
            if len(tasks) != 2:
                return None
            
            task1, task2 = tasks
            
            # Determine which task to delay based on priority and float
            if task1.priority == TaskPriority.CRITICAL and task2.priority != TaskPriority.CRITICAL:
                delay_task = task2
            elif task2.priority == TaskPriority.CRITICAL and task1.priority != TaskPriority.CRITICAL:
                delay_task = task1
            elif task1.total_float and task2.total_float:
                delay_task = task1 if task1.total_float > task2.total_float else task2
            else:
                delay_task = task2  # Default to delaying second task
            
            # Calculate delay amount (simplified)
            delay_hours = float(conflict.overallocation_amount)
            
            # Update task timeline
            if delay_task.planned_start_date:
                delay_task.planned_start_date += timedelta(hours=delay_hours)
            if delay_task.planned_end_date:
                delay_task.planned_end_date += timedelta(hours=delay_hours)
            
            await session.commit()
            
            return {
                'type': 'resource_conflict_resolution',
                'task_id': str(delay_task.id),
                'task_name': delay_task.name,
                'action': 'delayed',
                'delay_hours': delay_hours,
                'reason': f"Resolved resource conflict for {conflict.resource_name}"
            }
    
    async def _optimize_for_duration(self, project_id: str, critical_path: CriticalPathResult) -> List[Dict[str, Any]]:
        """Optimize schedule to minimize project duration"""
        optimizations = []
        
        async with get_async_session() as session:
            # Look for opportunities to parallelize tasks
            critical_tasks_query = select(ProjectTask).where(
                and_(
                    ProjectTask.project_id == project_id,
                    ProjectTask.id.in_(critical_path.critical_path_tasks)
                )
            ).options(
                selectinload(ProjectTask.predecessor_dependencies),
                selectinload(ProjectTask.successor_dependencies)
            )
            
            critical_tasks_result = await session.execute(critical_tasks_query)
            critical_tasks = critical_tasks_result.scalars().all()
            
            # Look for tasks that can be started earlier
            for task in critical_tasks:
                # Check if any dependencies can be relaxed
                for dep in task.predecessor_dependencies:
                    if (dep.dependency_type == DependencyType.FINISH_TO_START and 
                        not dep.is_hard_constraint):
                        
                        # Suggest changing to start-to-start with overlap
                        optimizations.append({
                            'type': 'dependency_optimization',
                            'task_id': str(task.id),
                            'task_name': task.name,
                            'action': 'change_dependency_type',
                            'from_type': dep.dependency_type,
                            'to_type': DependencyType.START_TO_START,
                            'estimated_time_saved': 24,  # hours
                            'reason': 'Allow parallel execution with predecessor'
                        })
        
        return optimizations
    
    @cached(namespace="project_metrics", ttl=300)
    async def calculate_project_metrics(self, project_id: str) -> ProjectMetrics:
        """Calculate comprehensive project performance metrics"""
        async with get_async_session() as session:
            # Get all tasks for the project
            tasks_query = select(ProjectTask).where(
                ProjectTask.project_id == project_id
            ).options(
                selectinload(ProjectTask.resource_allocations)
            )
            
            tasks_result = await session.execute(tasks_query)
            tasks = tasks_result.scalars().all()
            
            if not tasks:
                return ProjectMetrics(
                    total_tasks=0,
                    completed_tasks=0,
                    in_progress_tasks=0,
                    blocked_tasks=0,
                    overdue_tasks=0,
                    completion_percentage=Decimal('0'),
                    schedule_performance_index=Decimal('1'),
                    cost_performance_index=Decimal('1'),
                    estimated_completion_date=datetime.utcnow(),
                    budget_variance=Decimal('0'),
                    resource_utilization={}
                )
            
            # Count tasks by status
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
            in_progress_tasks = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS)
            blocked_tasks = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
            overdue_tasks = sum(1 for t in tasks if t.is_overdue())
            
            # Calculate completion percentage
            total_completion = sum(t.completion_percentage or 0 for t in tasks)
            completion_percentage = total_completion / total_tasks if total_tasks > 0 else Decimal('0')
            
            # Calculate schedule performance index (SPI)
            planned_value = Decimal('0')
            earned_value = Decimal('0')
            actual_cost = Decimal('0')
            
            for task in tasks:
                if task.estimated_cost:
                    planned_value += task.estimated_cost
                    earned_value += task.estimated_cost * (task.completion_percentage / 100)
                
                if task.actual_cost:
                    actual_cost += task.actual_cost
            
            spi = earned_value / planned_value if planned_value > 0 else Decimal('1')
            cpi = earned_value / actual_cost if actual_cost > 0 else Decimal('1')
            
            # Estimate completion date based on current progress
            critical_path = await self.calculate_critical_path(project_id)
            remaining_work_ratio = (100 - completion_percentage) / 100
            estimated_remaining_hours = critical_path.project_duration_hours * remaining_work_ratio
            estimated_completion_date = datetime.utcnow() + timedelta(hours=float(estimated_remaining_hours))
            
            # Calculate budget variance
            budget_variance = actual_cost - planned_value
            
            # Calculate resource utilization
            resource_utilization = await self._calculate_resource_utilization(project_id)
            
            return ProjectMetrics(
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                in_progress_tasks=in_progress_tasks,
                blocked_tasks=blocked_tasks,
                overdue_tasks=overdue_tasks,
                completion_percentage=completion_percentage,
                schedule_performance_index=spi,
                cost_performance_index=cpi,
                estimated_completion_date=estimated_completion_date,
                budget_variance=budget_variance,
                resource_utilization=resource_utilization
            )
    
    async def _calculate_resource_utilization(self, project_id: str) -> Dict[str, Decimal]:
        """Calculate resource utilization rates"""
        async with get_async_session() as session:
            # Get all resources and their allocations
            resources_query = select(ProjectResource).where(
                ProjectResource.project_id == project_id
            ).options(
                selectinload(ProjectResource.allocations)
            )
            
            resources_result = await session.execute(resources_query)
            resources = resources_result.scalars().all()
            
            utilization = {}
            
            for resource in resources:
                total_capacity = resource.total_capacity or Decimal('0')
                if total_capacity == 0:
                    continue
                
                allocated_capacity = Decimal('0')
                for allocation in resource.allocations:
                    if allocation.status in [AllocationStatus.ALLOCATED, AllocationStatus.IN_USE]:
                        allocated_capacity += allocation.allocated_units or Decimal('0')
                
                utilization_rate = (allocated_capacity / total_capacity) * 100
                utilization[resource.name] = utilization_rate
            
            return utilization
    
    async def generate_gantt_data(self, project_id: str) -> Dict[str, Any]:
        """Generate data for Gantt chart visualization"""
        async with get_async_session() as session:
            # Get all tasks with dependencies
            tasks_query = select(ProjectTask).where(
                ProjectTask.project_id == project_id
            ).options(
                selectinload(ProjectTask.predecessor_dependencies),
                selectinload(ProjectTask.successor_dependencies),
                selectinload(ProjectTask.assigned_user)
            ).order_by(ProjectTask.planned_start_date)
            
            tasks_result = await session.execute(tasks_query)
            tasks = tasks_result.scalars().all()
            
            gantt_tasks = []
            dependencies = []
            
            for task in tasks:
                gantt_task = {
                    'id': str(task.id),
                    'name': task.name,
                    'start': task.planned_start_date.isoformat() if task.planned_start_date else None,
                    'end': task.planned_end_date.isoformat() if task.planned_end_date else None,
                    'duration': float(task.estimated_duration_hours or 0),
                    'progress': float(task.completion_percentage or 0),
                    'status': task.status,
                    'priority': task.priority,
                    'is_critical': task.is_critical_path,
                    'assigned_to': task.assigned_user.name if task.assigned_user else None,
                    'parent': str(task.parent_task_id) if task.parent_task_id else None
                }
                gantt_tasks.append(gantt_task)
                
                # Add dependencies
                for dep in task.predecessor_dependencies:
                    if dep.is_active:
                        dependencies.append({
                            'from': str(dep.predecessor_task_id),
                            'to': str(dep.successor_task_id),
                            'type': dep.dependency_type,
                            'lag': float(dep.lag_hours or 0)
                        })
            
            return {
                'tasks': gantt_tasks,
                'dependencies': dependencies,
                'project_id': project_id
            }
    
    async def create_task_dependency(
        self, 
        predecessor_task_id: str, 
        successor_task_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_hours: Decimal = Decimal('0'),
        created_by_user_id: str = None
    ) -> TaskDependency:
        """Create a new task dependency"""
        async with get_async_session() as session:
            # Validate that tasks exist and are in the same project
            tasks_query = select(ProjectTask).where(
                ProjectTask.id.in_([predecessor_task_id, successor_task_id])
            )
            tasks_result = await session.execute(tasks_query)
            tasks = tasks_result.scalars().all()
            
            if len(tasks) != 2:
                raise ValueError("Both tasks must exist")
            
            if tasks[0].project_id != tasks[1].project_id:
                raise ValueError("Tasks must be in the same project")
            
            # Check for circular dependencies
            if await self._would_create_cycle(predecessor_task_id, successor_task_id, session):
                raise ValueError("Dependency would create a circular reference")
            
            # Create dependency
            dependency = TaskDependency(
                predecessor_task_id=predecessor_task_id,
                successor_task_id=successor_task_id,
                dependency_type=dependency_type,
                lag_hours=lag_hours,
                created_by_user_id=created_by_user_id
            )
            
            session.add(dependency)
            await session.commit()
            await session.refresh(dependency)
            
            # Recalculate critical path
            project_id = tasks[0].project_id
            await self.calculate_critical_path(str(project_id))
            
            return dependency
    
    async def _would_create_cycle(
        self, 
        predecessor_id: str, 
        successor_id: str, 
        session: AsyncSession
    ) -> bool:
        """Check if adding a dependency would create a cycle"""
        # Get all existing dependencies
        deps_query = select(TaskDependency).where(
            TaskDependency.is_active == True
        )
        deps_result = await session.execute(deps_query)
        dependencies = deps_result.scalars().all()
        
        # Build graph
        graph = nx.DiGraph()
        
        for dep in dependencies:
            graph.add_edge(str(dep.predecessor_task_id), str(dep.successor_task_id))
        
        # Add the proposed edge
        graph.add_edge(predecessor_id, successor_id)
        
        # Check for cycles
        try:
            nx.find_cycle(graph)
            return True
        except nx.NetworkXNoCycle:
            return False


# Global service instance
task_dependency_service = TaskDependencyService()