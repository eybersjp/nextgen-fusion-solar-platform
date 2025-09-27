"""Task Dependency Models for NextGen Fusion Platform

Provides comprehensive task dependency management:
- Task hierarchy and relationships
- Dependency types (finish-to-start, start-to-start, etc.)
- Critical path calculation
- Resource allocation and conflicts
- Timeline optimization
- Progress tracking and reporting
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON,
    ForeignKey, Numeric, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class TaskStatus(str, Enum):
    """Task execution status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DependencyType(str, Enum):
    """Types of task dependencies"""
    FINISH_TO_START = "finish_to_start"  # Task B starts after Task A finishes
    START_TO_START = "start_to_start"    # Task B starts when Task A starts
    FINISH_TO_FINISH = "finish_to_finish" # Task B finishes when Task A finishes
    START_TO_FINISH = "start_to_finish"   # Task B finishes when Task A starts


class ResourceType(str, Enum):
    """Types of project resources"""
    HUMAN = "human"
    EQUIPMENT = "equipment"
    MATERIAL = "material"
    BUDGET = "budget"
    FACILITY = "facility"


class AllocationStatus(str, Enum):
    """Resource allocation status"""
    PLANNED = "planned"
    ALLOCATED = "allocated"
    IN_USE = "in_use"
    COMPLETED = "completed"
    RELEASED = "released"


class ProjectTask(Base):
    """Enhanced project task with dependency support"""
    __tablename__ = "project_tasks"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id"), nullable=True, index=True)
    
    # Task details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    task_code = Column(String(50), nullable=True)  # WBS code like "1.2.3"
    
    # Status and priority
    status = Column(String(20), nullable=False, default=TaskStatus.NOT_STARTED, index=True)
    priority = Column(String(20), nullable=False, default=TaskPriority.MEDIUM, index=True)
    
    # Timeline
    planned_start_date = Column(DateTime, nullable=True, index=True)
    planned_end_date = Column(DateTime, nullable=True, index=True)
    actual_start_date = Column(DateTime, nullable=True)
    actual_end_date = Column(DateTime, nullable=True)
    
    # Duration and effort
    estimated_duration_hours = Column(Numeric(10, 2), nullable=True)
    actual_duration_hours = Column(Numeric(10, 2), nullable=True)
    estimated_effort_hours = Column(Numeric(10, 2), nullable=True)
    actual_effort_hours = Column(Numeric(10, 2), nullable=True)
    
    # Progress tracking
    completion_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    
    # Assignment
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    assigned_team = Column(String(100), nullable=True)
    
    # Critical path analysis
    is_critical_path = Column(Boolean, default=False, index=True)
    earliest_start = Column(DateTime, nullable=True)
    earliest_finish = Column(DateTime, nullable=True)
    latest_start = Column(DateTime, nullable=True)
    latest_finish = Column(DateTime, nullable=True)
    total_float = Column(Numeric(10, 2), nullable=True)  # In hours
    free_float = Column(Numeric(10, 2), nullable=True)   # In hours
    
    # Cost tracking
    estimated_cost = Column(Numeric(12, 2), nullable=True)
    actual_cost = Column(Numeric(12, 2), nullable=True)
    budget_code = Column(String(50), nullable=True)
    
    # Quality and deliverables
    deliverables = Column(JSON, nullable=True)  # List of expected deliverables
    quality_criteria = Column(JSON, nullable=True)  # Quality checkpoints
    
    # Risk and issues
    risk_level = Column(String(20), default="low")
    issues = Column(JSON, nullable=True)  # Current issues/blockers
    
    # Metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    parent_task = relationship("ProjectTask", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("ProjectTask", back_populates="parent_task", cascade="all, delete-orphan")
    assigned_user = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    
    # Dependencies
    predecessor_dependencies = relationship(
        "TaskDependency", 
        foreign_keys="TaskDependency.successor_task_id",
        back_populates="successor_task",
        cascade="all, delete-orphan"
    )
    successor_dependencies = relationship(
        "TaskDependency", 
        foreign_keys="TaskDependency.predecessor_task_id",
        back_populates="predecessor_task",
        cascade="all, delete-orphan"
    )
    
    # Resource allocations
    resource_allocations = relationship(
        "TaskResourceAllocation", 
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    # Progress logs
    progress_logs = relationship(
        "TaskProgressLog", 
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskProgressLog.logged_at.desc()"
    )
    
    __table_args__ = (
        Index("idx_project_tasks_project_status", "project_id", "status"),
        Index("idx_project_tasks_assigned_status", "assigned_to_user_id", "status"),
        Index("idx_project_tasks_timeline", "planned_start_date", "planned_end_date"),
        Index("idx_project_tasks_critical_path", "is_critical_path", "project_id"),
        Index("idx_project_tasks_parent_child", "parent_task_id", "project_id"),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_task_completion_percentage"
        ),
        CheckConstraint(
            "estimated_duration_hours >= 0",
            name="ck_task_estimated_duration"
        ),
        CheckConstraint(
            "actual_duration_hours >= 0",
            name="ck_task_actual_duration"
        ),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'on_hold', 'completed', 'cancelled', 'blocked')",
            name="ck_task_status"
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_task_priority"
        )
    )
    
    @validates('completion_percentage')
    def validate_completion_percentage(self, key, value):
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Completion percentage must be between 0 and 100")
        return value
    
    @validates('status')
    def validate_status_transition(self, key, value):
        # Add business logic for valid status transitions
        if value == TaskStatus.COMPLETED and self.completion_percentage < 100:
            self.completion_percentage = 100
        return value
    
    def calculate_schedule_variance(self) -> Optional[timedelta]:
        """Calculate schedule variance (actual vs planned)"""
        if self.actual_end_date and self.planned_end_date:
            return self.actual_end_date - self.planned_end_date
        return None
    
    def calculate_cost_variance(self) -> Optional[Decimal]:
        """Calculate cost variance (actual vs estimated)"""
        if self.actual_cost is not None and self.estimated_cost is not None:
            return self.actual_cost - self.estimated_cost
        return None
    
    def get_total_estimated_cost(self) -> Decimal:
        """Get total estimated cost including subtasks"""
        total = self.estimated_cost or Decimal('0')
        for subtask in self.subtasks:
            total += subtask.get_total_estimated_cost()
        return total
    
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        
        if self.planned_end_date:
            return datetime.utcnow() > self.planned_end_date
        
        return False
    
    def can_start(self) -> bool:
        """Check if task can start based on dependencies"""
        if self.status != TaskStatus.NOT_STARTED:
            return False
        
        # Check if all predecessor dependencies are satisfied
        for dep in self.predecessor_dependencies:
            if not dep.is_satisfied():
                return False
        
        return True


class TaskDependency(Base):
    """Task dependency relationships"""
    __tablename__ = "task_dependencies"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    predecessor_task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id"), nullable=False, index=True)
    successor_task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id"), nullable=False, index=True)
    
    # Dependency configuration
    dependency_type = Column(String(20), nullable=False, default=DependencyType.FINISH_TO_START)
    lag_hours = Column(Numeric(10, 2), default=0)  # Delay between tasks
    lead_hours = Column(Numeric(10, 2), default=0)  # Overlap between tasks
    
    # Constraint details
    is_hard_constraint = Column(Boolean, default=True)  # Hard vs soft dependency
    constraint_reason = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    predecessor_task = relationship(
        "ProjectTask", 
        foreign_keys=[predecessor_task_id],
        back_populates="successor_dependencies"
    )
    successor_task = relationship(
        "ProjectTask", 
        foreign_keys=[successor_task_id],
        back_populates="predecessor_dependencies"
    )
    created_by = relationship("User")
    
    __table_args__ = (
        UniqueConstraint(
            "predecessor_task_id", "successor_task_id", "dependency_type",
            name="uq_task_dependency"
        ),
        Index("idx_task_dependencies_predecessor", "predecessor_task_id", "is_active"),
        Index("idx_task_dependencies_successor", "successor_task_id", "is_active"),
        CheckConstraint(
            "predecessor_task_id != successor_task_id",
            name="ck_dependency_no_self_reference"
        ),
        CheckConstraint(
            "dependency_type IN ('finish_to_start', 'start_to_start', 'finish_to_finish', 'start_to_finish')",
            name="ck_dependency_type"
        ),
        CheckConstraint(
            "lag_hours >= 0",
            name="ck_dependency_lag_hours"
        ),
        CheckConstraint(
            "lead_hours >= 0",
            name="ck_dependency_lead_hours"
        )
    )
    
    def is_satisfied(self) -> bool:
        """Check if dependency constraint is satisfied"""
        if not self.is_active:
            return True
        
        pred_task = self.predecessor_task
        succ_task = self.successor_task
        
        if self.dependency_type == DependencyType.FINISH_TO_START:
            return pred_task.status == TaskStatus.COMPLETED
        
        elif self.dependency_type == DependencyType.START_TO_START:
            return pred_task.status in [TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
        
        elif self.dependency_type == DependencyType.FINISH_TO_FINISH:
            if succ_task.status == TaskStatus.COMPLETED:
                return pred_task.status == TaskStatus.COMPLETED
            return True  # Can start, but must finish together
        
        elif self.dependency_type == DependencyType.START_TO_FINISH:
            if succ_task.status == TaskStatus.COMPLETED:
                return pred_task.status in [TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
            return True  # Can start, but finish timing depends on predecessor start
        
        return False
    
    def calculate_constraint_date(self, reference_date: datetime) -> datetime:
        """Calculate the constraint date based on dependency type and lag/lead"""
        lag_delta = timedelta(hours=float(self.lag_hours or 0))
        lead_delta = timedelta(hours=float(self.lead_hours or 0))
        
        if self.dependency_type == DependencyType.FINISH_TO_START:
            return reference_date + lag_delta - lead_delta
        
        elif self.dependency_type == DependencyType.START_TO_START:
            return reference_date + lag_delta - lead_delta
        
        elif self.dependency_type == DependencyType.FINISH_TO_FINISH:
            return reference_date + lag_delta - lead_delta
        
        elif self.dependency_type == DependencyType.START_TO_FINISH:
            return reference_date + lag_delta - lead_delta
        
        return reference_date


class ProjectResource(Base):
    """Project resources (people, equipment, materials, etc.)"""
    __tablename__ = "project_resources"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    
    # Resource details
    name = Column(String(200), nullable=False)
    resource_type = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Capacity and availability
    total_capacity = Column(Numeric(10, 2), nullable=True)  # Total available units
    available_capacity = Column(Numeric(10, 2), nullable=True)  # Currently available
    capacity_unit = Column(String(20), nullable=True)  # hours, days, units, etc.
    
    # Cost information
    cost_per_unit = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), default="USD")
    
    # Availability schedule
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)
    
    # Skills and attributes (for human resources)
    skills = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project")
    allocations = relationship(
        "TaskResourceAllocation", 
        back_populates="resource",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_project_resources_type_project", "resource_type", "project_id"),
        Index("idx_project_resources_availability", "available_from", "available_until"),
        CheckConstraint(
            "resource_type IN ('human', 'equipment', 'material', 'budget', 'facility')",
            name="ck_resource_type"
        ),
        CheckConstraint(
            "total_capacity >= 0",
            name="ck_resource_total_capacity"
        ),
        CheckConstraint(
            "available_capacity >= 0",
            name="ck_resource_available_capacity"
        ),
        CheckConstraint(
            "cost_per_unit >= 0",
            name="ck_resource_cost_per_unit"
        )
    )
    
    def get_allocated_capacity(self, start_date: datetime, end_date: datetime) -> Decimal:
        """Get total allocated capacity for a time period"""
        total_allocated = Decimal('0')
        
        for allocation in self.allocations:
            if (allocation.status in [AllocationStatus.ALLOCATED, AllocationStatus.IN_USE] and
                allocation.start_date and allocation.end_date and
                allocation.start_date < end_date and allocation.end_date > start_date):
                
                total_allocated += allocation.allocated_units or Decimal('0')
        
        return total_allocated
    
    def is_available(self, start_date: datetime, end_date: datetime, required_units: Decimal) -> bool:
        """Check if resource is available for allocation"""
        if not self.is_active:
            return False
        
        if self.available_from and start_date < self.available_from:
            return False
        
        if self.available_until and end_date > self.available_until:
            return False
        
        allocated = self.get_allocated_capacity(start_date, end_date)
        available = (self.available_capacity or Decimal('0')) - allocated
        
        return available >= required_units


class TaskResourceAllocation(Base):
    """Resource allocation to tasks"""
    __tablename__ = "task_resource_allocations"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id"), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("project_resources.id"), nullable=False, index=True)
    
    # Allocation details
    allocated_units = Column(Numeric(10, 2), nullable=False)
    unit_type = Column(String(20), nullable=True)  # hours, days, percentage, etc.
    
    # Timeline
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default=AllocationStatus.PLANNED, index=True)
    
    # Cost tracking
    planned_cost = Column(Numeric(12, 2), nullable=True)
    actual_cost = Column(Numeric(12, 2), nullable=True)
    
    # Usage tracking
    actual_units_used = Column(Numeric(10, 2), nullable=True)
    
    # Notes and metadata
    allocation_notes = Column(Text, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    allocated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    task = relationship("ProjectTask", back_populates="resource_allocations")
    resource = relationship("ProjectResource", back_populates="allocations")
    allocated_by = relationship("User")
    
    __table_args__ = (
        Index("idx_task_resource_allocations_task_status", "task_id", "status"),
        Index("idx_task_resource_allocations_resource_status", "resource_id", "status"),
        Index("idx_task_resource_allocations_timeline", "start_date", "end_date"),
        CheckConstraint(
            "allocated_units > 0",
            name="ck_allocation_units"
        ),
        CheckConstraint(
            "status IN ('planned', 'allocated', 'in_use', 'completed', 'released')",
            name="ck_allocation_status"
        ),
        CheckConstraint(
            "planned_cost >= 0",
            name="ck_allocation_planned_cost"
        ),
        CheckConstraint(
            "actual_cost >= 0",
            name="ck_allocation_actual_cost"
        )
    )
    
    def calculate_utilization_rate(self) -> Optional[Decimal]:
        """Calculate resource utilization rate"""
        if self.actual_units_used is not None and self.allocated_units > 0:
            return (self.actual_units_used / self.allocated_units) * 100
        return None
    
    def is_overallocated(self) -> bool:
        """Check if resource is overallocated"""
        if self.actual_units_used is not None:
            return self.actual_units_used > self.allocated_units
        return False


class TaskProgressLog(Base):
    """Task progress tracking log"""
    __tablename__ = "task_progress_logs"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id"), nullable=False, index=True)
    
    # Progress details
    completion_percentage = Column(Numeric(5, 2), nullable=False)
    hours_worked = Column(Numeric(10, 2), nullable=True)
    work_description = Column(Text, nullable=True)
    
    # Issues and blockers
    issues_encountered = Column(JSON, nullable=True)
    blockers = Column(JSON, nullable=True)
    
    # Quality metrics
    quality_score = Column(Numeric(3, 1), nullable=True)  # 1-10 scale
    deliverables_completed = Column(JSON, nullable=True)
    
    # Timeline updates
    revised_end_date = Column(DateTime, nullable=True)
    
    # Audit fields
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    logged_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    task = relationship("ProjectTask", back_populates="progress_logs")
    logged_by = relationship("User")
    
    __table_args__ = (
        Index("idx_task_progress_logs_task_date", "task_id", "logged_at"),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_progress_completion_percentage"
        ),
        CheckConstraint(
            "hours_worked >= 0",
            name="ck_progress_hours_worked"
        ),
        CheckConstraint(
            "quality_score >= 1 AND quality_score <= 10",
            name="ck_progress_quality_score"
        )
    )