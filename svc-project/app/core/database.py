#!/usr/bin/env python3
"""
Database configuration and models for the Project Management Service

This module defines SQLAlchemy models for project management entities
including projects, tasks, milestones, resources, and team management.
Enhanced with multi-tenant connection pooling and performance optimization.
"""

import enum
import sys
import os
from datetime import datetime, date
from typing import Optional, List, AsyncGenerator
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Date, Boolean, Float,
    ForeignKey, Enum, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from .config import get_settings

# Add shared module to path for enhanced pooling
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

# Try to import enhanced pooling system
try:
    from database import (
        ServiceType, ServiceDatabaseManager, 
        get_service_db_manager, initialize_service_database
    )
    ENHANCED_POOLING_AVAILABLE = True
except ImportError:
    ENHANCED_POOLING_AVAILABLE = False

settings = get_settings()

# Global variables for database components
_engine = None
_session_factory = None
_service_manager = None


def init_database(tenant_id: Optional[str] = None) -> None:
    """Initialize database with enhanced pooling support.
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant isolation
    """
    global _engine, _session_factory, _service_manager
    
    if ENHANCED_POOLING_AVAILABLE:
        # Use enhanced pooling system
        _service_manager = initialize_service_database(
            service_type=ServiceType.PROJECT,
            database_url=settings.DATABASE_URL,
            tenant_id=tenant_id
        )
        _engine = _service_manager.get_async_engine(tenant_id)
        _session_factory = _service_manager.get_async_session_factory(tenant_id)
    else:
        # Fallback to legacy pooling
        if "sqlite" in settings.DATABASE_URL:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO
            )
        else:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW
            )
        _session_factory = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )


def get_engine() -> create_async_engine:
    """Get the database engine."""
    if _engine is None:
        init_database()
    return _engine


def get_session_factory() -> sessionmaker:
    """Get the session factory."""
    if _session_factory is None:
        init_database()
    return _session_factory


# Legacy compatibility
engine = get_engine()
AsyncSessionLocal = get_session_factory()

# Base class for all models
Base = declarative_base()


# Enums
class ProjectStatus(enum.Enum):
    """Project status enumeration."""
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(enum.Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    TESTING = "testing"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(enum.Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MilestoneStatus(enum.Enum):
    """Milestone status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class ResourceType(enum.Enum):
    """Resource type enumeration."""
    HUMAN = "human"
    EQUIPMENT = "equipment"
    MATERIAL = "material"
    BUDGET = "budget"


class TeamRole(enum.Enum):
    """Team member role enumeration."""
    PROJECT_MANAGER = "project_manager"
    TEAM_LEAD = "team_lead"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    TESTER = "tester"
    ANALYST = "analyst"
    STAKEHOLDER = "stakeholder"


# Models
class Project(Base):
    """Project model."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNING, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    
    # Dates
    start_date = Column(Date)
    end_date = Column(Date)
    actual_start_date = Column(Date)
    actual_end_date = Column(Date)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    budget = Column(Float)
    actual_cost = Column(Float, default=0.0)
    
    # Client information
    client_name = Column(String(255))
    project_manager_id = Column(String(255))
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields
    tags = Column(JSON)
    custom_fields = Column(JSON)
    
    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    team_members = relationship("ProjectTeamMember", back_populates="project", cascade="all, delete-orphan")
    resources = relationship("ProjectResource", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_project_status_dates', 'status', 'start_date', 'end_date'),
    )


class Task(Base):
    """Task model."""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, index=True)
    
    # Assignment
    assigned_to = Column(String(255), index=True)
    assigned_by = Column(String(255))
    
    # Dates and time tracking
    start_date = Column(Date)
    due_date = Column(Date, index=True)
    completed_date = Column(Date)
    estimated_hours = Column(Float)
    actual_hours = Column(Float, default=0.0)
    
    # Progress
    progress_percentage = Column(Float, default=0.0)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields
    tags = Column(JSON)
    attachments = Column(JSON)
    custom_fields = Column(JSON)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id])
    subtasks = relationship("Task", cascade="all, delete-orphan")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    time_logs = relationship("TaskTimeLog", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_task_project_status', 'project_id', 'status'),
        Index('idx_task_assigned_status', 'assigned_to', 'status'),
        Index('idx_task_due_date_status', 'due_date', 'status'),
    )


class Milestone(Base):
    """Milestone model."""
    __tablename__ = "milestones"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(MilestoneStatus), default=MilestoneStatus.PENDING, index=True)
    
    # Dates
    due_date = Column(Date, nullable=False, index=True)
    completed_date = Column(Date)
    
    # Progress
    progress_percentage = Column(Float, default=0.0)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields
    deliverables = Column(JSON)
    success_criteria = Column(JSON)
    
    # Relationships
    project = relationship("Project", back_populates="milestones")
    
    __table_args__ = (
        Index('idx_milestone_project_due', 'project_id', 'due_date'),
    )


class ProjectTeamMember(Base):
    """Project team member model."""
    __tablename__ = "project_team_members"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    role = Column(Enum(TeamRole), nullable=False)
    
    # Permissions
    can_edit_tasks = Column(Boolean, default=True)
    can_delete_tasks = Column(Boolean, default=False)
    can_manage_team = Column(Boolean, default=False)
    can_view_reports = Column(Boolean, default=True)
    
    # Dates
    joined_date = Column(Date, default=date.today)
    left_date = Column(Date)
    
    # Financial
    hourly_rate = Column(Float)
    
    # Metadata
    added_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="team_members")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='uq_project_user'),
        Index('idx_team_member_project_role', 'project_id', 'role'),
    )


class ProjectResource(Base):
    """Project resource model."""
    __tablename__ = "project_resources"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    type = Column(Enum(ResourceType), nullable=False, index=True)
    description = Column(Text)
    
    # Allocation
    total_capacity = Column(Float)
    allocated_capacity = Column(Float, default=0.0)
    available_capacity = Column(Float)
    
    # Cost
    cost_per_unit = Column(Float)
    total_cost = Column(Float)
    
    # Dates
    available_from = Column(Date)
    available_until = Column(Date)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields
    properties = Column(JSON)
    
    # Relationships
    project = relationship("Project", back_populates="resources")
    
    __table_args__ = (
        Index('idx_resource_project_type', 'project_id', 'type'),
    )


class TaskComment(Base):
    """Task comment model."""
    __tablename__ = "task_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields
    attachments = Column(JSON)
    mentions = Column(JSON)
    
    # Relationships
    task = relationship("Task", back_populates="comments")


class TaskTimeLog(Base):
    """Task time log model."""
    __tablename__ = "task_time_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    
    user_id = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    hours = Column(Float, nullable=False)
    
    # Dates
    log_date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="time_logs")
    
    __table_args__ = (
        Index('idx_time_log_user_date', 'user_id', 'log_date'),
    )


class TaskDependency(Base):
    """Task dependency model."""
    __tablename__ = "task_dependencies"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    depends_on_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    
    dependency_type = Column(String(50), default="finish_to_start")  # finish_to_start, start_to_start, etc.
    lag_days = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_task_id])
    
    __table_args__ = (
        UniqueConstraint('task_id', 'depends_on_task_id', name='uq_task_dependency'),
    )


# Database utility functions
async def get_db(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """Get database session with optional tenant isolation.
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant sessions
        
    Yields:
        AsyncSession: Database session
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager and tenant_id:
        # Use enhanced pooling with tenant isolation
        async with _service_manager.get_async_session(tenant_id) as session:
            yield session
    else:
        # Use standard session factory
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()


async def get_db_session(tenant_id: Optional[str] = None) -> AsyncSession:
    """Get a single database session (not a generator).
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant sessions
        
    Returns:
        AsyncSession: Database session
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager and tenant_id:
        return _service_manager.get_async_session(tenant_id)
    else:
        session_factory = get_session_factory()
        return session_factory()


async def check_database_health(tenant_id: Optional[str] = None) -> dict:
    """Check database health with optional tenant context.
    
    Args:
        tenant_id: Optional tenant identifier
        
    Returns:
        dict: Health check results
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager:
        return await _service_manager.health_check(tenant_id)
    else:
        # Basic health check
        try:
            async with get_db_session(tenant_id) as session:
                await session.execute("SELECT 1")
            return {"status": "healthy", "tenant_id": tenant_id}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "tenant_id": tenant_id}


async def create_tables(tenant_id: Optional[str] = None):
    """Create all database tables.
    
    Args:
        tenant_id: Optional tenant identifier
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(tenant_id: Optional[str] = None):
    """Drop all database tables.
    
    Args:
        tenant_id: Optional tenant identifier
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def close_database_connections():
    """Close all database connections and dispose engines."""
    global _engine, _session_factory, _service_manager
    
    try:
        if ENHANCED_POOLING_AVAILABLE and _service_manager:
            await _service_manager.close_all_connections()
        elif _engine:
            await _engine.dispose()
        
        # Reset global variables
        _engine = None
        _session_factory = None
        _service_manager = None
        
    except Exception as e:
        print(f"Error closing database connections: {e}")