#!/usr/bin/env python3
"""
Project Management API endpoints

This module provides FastAPI endpoints for project management operations
including projects, tasks, milestones, team management, and Gantt chart data.
"""

import asyncio
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ...core import (
    get_db, get_logger, audit_logger,
    Project, Task, Milestone, ProjectTeamMember, ProjectResource,
    TaskComment, TaskTimeLog, TaskDependency,
    ProjectStatus, TaskStatus, TaskPriority, MilestoneStatus,
    ResourceType, TeamRole
)
from services.database_integration import project_db_service
from ...core.cache import get_critical_path_cache, cache_critical_path
from ...services.task_dependency_service import TaskDependencyService, CriticalPathResult

router = APIRouter()
logger = get_logger(__name__)

# Pydantic Models
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    budget: Optional[float] = Field(None, ge=0)
    client_name: Optional[str] = Field(None, max_length=255)
    project_manager_id: str = Field(..., max_length=255)
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = Field(None, ge=0)
    client_name: Optional[str] = Field(None, max_length=255)
    project_manager_id: Optional[str] = Field(None, max_length=255)
    status: Optional[ProjectStatus] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    start_date: date
    end_date: Optional[date]
    budget: Optional[float]
    client_name: Optional[str]
    project_manager_id: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: int
    assigned_to: Optional[str] = Field(None, max_length=255)
    priority: TaskPriority = TaskPriority.MEDIUM
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    parent_task_id: Optional[int] = None
    
    @validator('due_date')
    def validate_due_date(cls, v, values):
        if v and 'start_date' in values and values['start_date'] and v < values['start_date']:
            raise ValueError('Due date must be after start date')
        return v

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[str] = Field(None, max_length=255)
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    parent_task_id: Optional[int] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    project_id: int
    assigned_to: Optional[str]
    priority: TaskPriority
    status: TaskStatus
    start_date: Optional[date]
    due_date: Optional[date]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    progress_percentage: int
    parent_task_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MilestoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    project_id: int
    due_date: date
    deliverables: Optional[List[str]] = None

class MilestoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[MilestoneStatus] = None
    deliverables: Optional[List[str]] = None
    completion_date: Optional[date] = None

class MilestoneResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    project_id: int
    due_date: date
    status: MilestoneStatus
    deliverables: Optional[List[str]]
    completion_date: Optional[date]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TeamMemberCreate(BaseModel):
    project_id: int
    user_id: str = Field(..., max_length=255)
    role: TeamRole
    hourly_rate: Optional[float] = Field(None, ge=0)

class TeamMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: str
    role: TeamRole
    hourly_rate: Optional[float]
    joined_date: date
    
    class Config:
        from_attributes = True

class GanttTaskData(BaseModel):
    id: int
    title: str
    start_date: Optional[date]
    due_date: Optional[date]
    progress_percentage: int
    assigned_to: Optional[str]
    priority: TaskPriority
    status: TaskStatus
    parent_task_id: Optional[int]
    dependencies: List[int] = []

class GanttChartResponse(BaseModel):
    project_id: int
    project_name: str
    project_start_date: date
    project_end_date: Optional[date]
    tasks: List[GanttTaskData]
    milestones: List[MilestoneResponse]

class TimeLogCreate(BaseModel):
    task_id: int
    user_id: str = Field(..., max_length=255)
    hours: float = Field(..., gt=0)
    description: Optional[str] = None
    log_date: date = Field(default_factory=lambda: datetime.utcnow().date())

class TimeLogResponse(BaseModel):
    id: int
    task_id: int
    user_id: str
    hours: float
    description: Optional[str]
    log_date: date
    created_at: datetime
    
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    task_id: int
    user_id: str = Field(..., max_length=255)
    content: str = Field(..., min_length=1)

class CommentResponse(BaseModel):
    id: int
    task_id: int
    user_id: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Service Classes
class ProjectService:
    """Service for project management operations."""
    
    @staticmethod
    async def create_project(db: AsyncSession, project_data: ProjectCreate, created_by: str) -> Project:
        """Create a new project."""
        project_dict = {
            'name': project_data.name,
            'description': project_data.description,
            'start_date': project_data.start_date,
            'end_date': project_data.end_date,
            'budget': project_data.budget,
            'client_name': project_data.client_name,
            'project_manager_id': project_data.project_manager_id,
            'status': ProjectStatus.PLANNING.value
        }
        
        # Store project using ProjectDatabaseService
        project_id = await project_db_service.store_project_data(project_dict)
        
        # Retrieve the created project
        project_data_result = await project_db_service.get_project_data(project_id)
        
        # Convert to Project model
        project = Project(
            id=project_data_result['id'],
            name=project_data_result['name'],
            description=project_data_result['description'],
            start_date=project_data_result['start_date'],
            end_date=project_data_result['end_date'],
            budget=project_data_result['budget'],
            client_name=project_data_result['client_name'],
            project_manager_id=project_data_result['project_manager_id'],
            status=ProjectStatus(project_data_result['status']),
            created_at=project_data_result['created_at'],
            updated_at=project_data_result['updated_at']
        )
        
        audit_logger.log_project_created(
            project_id=project.id,
            project_name=project.name,
            created_by=created_by
        )
        
        return project
    
    @staticmethod
    async def get_projects(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Project]:
        """Get list of projects with pagination."""
        # Use ProjectDatabaseService to get projects
        projects_data = await project_db_service.get_project_data()
        
        # Convert to Project models and apply pagination
        projects = []
        for project_dict in projects_data[skip:skip+limit]:
            project = Project(
                id=project_dict['id'],
                name=project_dict['name'],
                description=project_dict['description'],
                start_date=project_dict['start_date'],
                end_date=project_dict['end_date'],
                budget=project_dict['budget'],
                client_name=project_dict['client_name'],
                project_manager_id=project_dict['project_manager_id'],
                status=ProjectStatus(project_dict['status']),
                created_at=project_dict['created_at'],
                updated_at=project_dict['updated_at']
            )
            projects.append(project)
        
        return projects
    
    @staticmethod
    async def get_project(db: AsyncSession, project_id: int) -> Optional[Project]:
        """Get a project by ID."""
        try:
            project_dict = await project_db_service.get_project_data(project_id)
            if not project_dict:
                return None
            
            return Project(
                id=project_dict['id'],
                name=project_dict['name'],
                description=project_dict['description'],
                start_date=project_dict['start_date'],
                end_date=project_dict['end_date'],
                budget=project_dict['budget'],
                client_name=project_dict['client_name'],
                project_manager_id=project_dict['project_manager_id'],
                status=ProjectStatus(project_dict['status']),
                created_at=project_dict['created_at'],
                updated_at=project_dict['updated_at']
            )
        except Exception:
            return None
    
    @staticmethod
    async def update_project(db: AsyncSession, project_id: int, project_data: ProjectUpdate, updated_by: str) -> Optional[Project]:
        """Update a project."""
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        changes = {}
        for field, value in project_data.dict(exclude_unset=True).items():
            if hasattr(project, field) and getattr(project, field) != value:
                changes[field] = {'old': getattr(project, field), 'new': value}
                setattr(project, field, value)
        
        if changes:
            project.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(project)
            
            audit_logger.log_project_updated(
                project_id=project.id,
                updated_by=updated_by,
                changes=changes
            )
        
        return project
    
    @staticmethod
    async def delete_project(db: AsyncSession, project_id: int, deleted_by: str) -> bool:
        """Delete a project."""
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return False
        
        await db.delete(project)
        await db.commit()
        
        audit_logger.log_project_deleted(
            project_id=project_id,
            deleted_by=deleted_by
        )
        
        return True

class TaskService:
    """Service for task management operations."""
    
    @staticmethod
    async def create_task(db: AsyncSession, task_data: TaskCreate, created_by: str) -> Task:
        """Create a new task."""
        task_dict = {
            'title': task_data.title,
            'description': task_data.description,
            'project_id': task_data.project_id,
            'assigned_to': task_data.assigned_to,
            'priority': task_data.priority.value,
            'start_date': task_data.start_date,
            'due_date': task_data.due_date,
            'estimated_hours': task_data.estimated_hours,
            'parent_task_id': task_data.parent_task_id,
            'status': TaskStatus.TODO.value
        }
        
        # Store task using ProjectDatabaseService
        task_id = await project_db_service.store_task_data(task_dict)
        
        # Retrieve the created task
        task_data_result = await project_db_service.get_task_data(task_id)
        
        # Convert to Task model
        task = Task(
            id=task_data_result['id'],
            title=task_data_result['title'],
            description=task_data_result['description'],
            project_id=task_data_result['project_id'],
            assigned_to=task_data_result['assigned_to'],
            priority=TaskPriority(task_data_result['priority']),
            start_date=task_data_result['start_date'],
            due_date=task_data_result['due_date'],
            estimated_hours=task_data_result['estimated_hours'],
            parent_task_id=task_data_result['parent_task_id'],
            status=TaskStatus(task_data_result['status']),
            created_at=task_data_result['created_at'],
            updated_at=task_data_result['updated_at']
        )
        
        audit_logger.log_task_created(
            task_id=task.id,
            project_id=task.project_id,
            task_title=task.title,
            created_by=created_by
        )
        
        return task
    
    @staticmethod
    async def get_tasks(db: AsyncSession, project_id: Optional[int] = None, assigned_to: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Task]:
        """Get list of tasks with optional filtering."""
        query = select(Task).order_by(desc(Task.created_at))
        
        if project_id:
            query = query.where(Task.project_id == project_id)
        if assigned_to:
            query = query.where(Task.assigned_to == assigned_to)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
        """Get a task by ID."""
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_task(db: AsyncSession, task_id: int, task_data: TaskUpdate, updated_by: str) -> Optional[Task]:
        """Update a task."""
        result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        changes = {}
        for field, value in task_data.dict(exclude_unset=True).items():
            if hasattr(task, field) and getattr(task, field) != value:
                changes[field] = {'old': getattr(task, field), 'new': value}
                setattr(task, field, value)
        
        if changes:
            task.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(task)
            
            audit_logger.log_task_updated(
                task_id=task.id,
                project_id=task.project_id,
                updated_by=updated_by,
                changes=changes
            )
        
        return task
    
    @staticmethod
    async def get_gantt_data(db: AsyncSession, project_id: int) -> Optional[GanttChartResponse]:
        """Get Gantt chart data for a project."""
        # Get project
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            return None
        
        # Get tasks with dependencies
        tasks_result = await db.execute(
            select(Task)
            .options(selectinload(Task.dependencies))
            .where(Task.project_id == project_id)
            .order_by(Task.start_date.asc().nullslast(), Task.created_at.asc())
        )
        tasks = tasks_result.scalars().all()
        
        # Get milestones
        milestones_result = await db.execute(
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.due_date.asc())
        )
        milestones = milestones_result.scalars().all()
        
        # Convert tasks to Gantt format
        gantt_tasks = []
        for task in tasks:
            dependencies = [dep.dependency_task_id for dep in task.dependencies]
            gantt_tasks.append(GanttTaskData(
                id=task.id,
                title=task.title,
                start_date=task.start_date,
                due_date=task.due_date,
                progress_percentage=task.progress_percentage,
                assigned_to=task.assigned_to,
                priority=task.priority,
                status=task.status,
                parent_task_id=task.parent_task_id,
                dependencies=dependencies
            ))
        
        return GanttChartResponse(
            project_id=project.id,
            project_name=project.name,
            project_start_date=project.start_date,
            project_end_date=project.end_date,
            tasks=gantt_tasks,
            milestones=[MilestoneResponse.from_orm(m) for m in milestones]
        )

# API Endpoints
@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Create a new project."""
    try:
        new_project = await ProjectService.create_project(db, project, current_user)
        return ProjectResponse.from_orm(new_project)
    except Exception as e:
        logger.error("Failed to create project", error=str(e), project_data=project.dict())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

@router.get("/projects", response_model=List[ProjectResponse])
async def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get list of projects with pagination."""
    projects = await ProjectService.get_projects(db, skip, limit)
    return [ProjectResponse.from_orm(p) for p in projects]

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a project by ID."""
    project = await ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return ProjectResponse.from_orm(project)

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Update a project."""
    project = await ProjectService.update_project(db, project_id, project_update, current_user)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return ProjectResponse.from_orm(project)

@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Delete a project."""
    success = await ProjectService.delete_project(db, project_id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Create a new task."""
    try:
        new_task = await TaskService.create_task(db, task, current_user)
        return TaskResponse.from_orm(new_task)
    except Exception as e:
        logger.error("Failed to create task", error=str(e), task_data=task.dict())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    project_id: Optional[int] = Query(None),
    assigned_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get list of tasks with optional filtering."""
    tasks = await TaskService.get_tasks(db, project_id, assigned_to, skip, limit)
    return [TaskResponse.from_orm(t) for t in tasks]

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a task by ID."""
    task = await TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return TaskResponse.from_orm(task)

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Update a task."""
    task = await TaskService.update_task(db, task_id, task_update, current_user)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return TaskResponse.from_orm(task)

@router.get("/projects/{project_id}/gantt", response_model=GanttChartResponse)
async def get_gantt_chart(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get Gantt chart data for a project."""
    gantt_data = await TaskService.get_gantt_data(db, project_id)
    if not gantt_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return gantt_data


# Milestone Management Endpoints
@router.post("/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    milestone: MilestoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Create a new milestone."""
    try:
        new_milestone = Milestone(
            name=milestone.name,
            description=milestone.description,
            project_id=milestone.project_id,
            due_date=milestone.due_date,
            deliverables=milestone.deliverables,
            status=MilestoneStatus.PENDING
        )
        
        db.add(new_milestone)
        await db.commit()
        await db.refresh(new_milestone)
        
        # audit_logger.log_milestone_created(
        #     milestone_id=new_milestone.id,
        #     project_id=new_milestone.project_id,
        #     milestone_name=new_milestone.name,
        #     created_by=current_user
        # )
        
        return MilestoneResponse.from_orm(new_milestone)
    except Exception as e:
        logger.error("Failed to create milestone", error=str(e), milestone_data=milestone.dict())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create milestone"
        )


@router.get("/projects/{project_id}/milestones", response_model=List[MilestoneResponse])
async def get_project_milestones(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all milestones for a project."""
    result = await db.execute(
        select(Milestone)
        .where(Milestone.project_id == project_id)
        .order_by(Milestone.due_date.asc())
    )
    milestones = result.scalars().all()
    return [MilestoneResponse.from_orm(m) for m in milestones]


@router.get("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def get_milestone(
    milestone_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a milestone by ID."""
    result = await db.execute(
        select(Milestone).where(Milestone.id == milestone_id)
    )
    milestone = result.scalar_one_or_none()
    
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    
    return MilestoneResponse.from_orm(milestone)


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: int,
    milestone_update: MilestoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Update a milestone."""
    result = await db.execute(
        select(Milestone).where(Milestone.id == milestone_id)
    )
    milestone = result.scalar_one_or_none()
    
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    
    changes = {}
    for field, value in milestone_update.dict(exclude_unset=True).items():
        if hasattr(milestone, field) and getattr(milestone, field) != value:
            changes[field] = {'old': getattr(milestone, field), 'new': value}
            setattr(milestone, field, value)
    
    if changes:
        milestone.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(milestone)
        
        # audit_logger.log_milestone_updated(
        #     milestone_id=milestone.id,
        #     project_id=milestone.project_id,
        #     updated_by=current_user,
        #     changes=changes
        # )
    
    return MilestoneResponse.from_orm(milestone)


# Team Member Management Endpoints
@router.post("/projects/{project_id}/team", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    project_id: int,
    team_member: TeamMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Add a team member to a project."""
    try:
        # Verify project exists
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        if not project_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if user is already a team member
        existing_result = await db.execute(
            select(ProjectTeamMember).where(
                and_(
                    ProjectTeamMember.project_id == project_id,
                    ProjectTeamMember.user_id == team_member.user_id
                )
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a team member"
            )
        
        new_member = ProjectTeamMember(
            project_id=project_id,
            user_id=team_member.user_id,
            role=team_member.role,
            hourly_rate=team_member.hourly_rate
        )
        
        db.add(new_member)
        await db.commit()
        await db.refresh(new_member)
        
        # audit_logger.log_team_member_added(
        #     project_id=project_id,
        #     user_id=team_member.user_id,
        #     role=team_member.role.value,
        #     added_by=current_user
        # )
        
        return TeamMemberResponse.from_orm(new_member)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add team member", error=str(e), project_id=project_id, user_id=team_member.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member"
        )


@router.get("/projects/{project_id}/team", response_model=List[TeamMemberResponse])
async def get_project_team(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all team members for a project."""
    result = await db.execute(
        select(ProjectTeamMember)
        .where(ProjectTeamMember.project_id == project_id)
        .order_by(ProjectTeamMember.joined_date.asc())
    )
    team_members = result.scalars().all()
    return [TeamMemberResponse.from_orm(tm) for tm in team_members]


@router.delete("/projects/{project_id}/team/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    project_id: int,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Remove a team member from a project."""
    result = await db.execute(
        select(ProjectTeamMember).where(
            and_(
                ProjectTeamMember.project_id == project_id,
                ProjectTeamMember.user_id == user_id
            )
        )
    )
    team_member = result.scalar_one_or_none()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    await db.delete(team_member)
    await db.commit()
    
    # audit_logger.log_team_member_removed(
    #     project_id=project_id,
    #     user_id=user_id,
    #     removed_by=current_user
    # )


# Time Logging Endpoints
@router.post("/time-logs", response_model=TimeLogResponse, status_code=status.HTTP_201_CREATED)
async def create_time_log(
    time_log: TimeLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Create a new time log entry."""
    try:
        # Verify task exists
        task_result = await db.execute(
            select(Task).where(Task.id == time_log.task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        new_time_log = TaskTimeLog(
            task_id=time_log.task_id,
            user_id=time_log.user_id,
            hours=time_log.hours,
            description=time_log.description,
            log_date=time_log.log_date
        )
        
        db.add(new_time_log)
        
        # Update task actual hours
        task.actual_hours = (task.actual_hours or 0) + time_log.hours
        
        await db.commit()
        await db.refresh(new_time_log)
        
        # audit_logger.log_time_logged(
        #     task_id=time_log.task_id,
        #     user_id=time_log.user_id,
        #     hours=time_log.hours,
        #     logged_by=current_user
        # )
        
        return TimeLogResponse.from_orm(new_time_log)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create time log", error=str(e), time_log_data=time_log.dict())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create time log"
        )


@router.get("/tasks/{task_id}/time-logs", response_model=List[TimeLogResponse])
async def get_task_time_logs(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all time logs for a task."""
    result = await db.execute(
        select(TaskTimeLog)
        .where(TaskTimeLog.task_id == task_id)
        .order_by(desc(TaskTimeLog.log_date), desc(TaskTimeLog.created_at))
    )
    time_logs = result.scalars().all()
    return [TimeLogResponse.from_orm(tl) for tl in time_logs]


# Task Comments Endpoints
@router.post("/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = "system"  # TODO: Replace with actual auth
):
    """Create a new task comment."""
    try:
        # Verify task exists
        task_result = await db.execute(
            select(Task).where(Task.id == comment.task_id)
        )
        if not task_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        new_comment = TaskComment(
            task_id=comment.task_id,
            author=comment.user_id,
            content=comment.content
        )
        
        db.add(new_comment)
        await db.commit()
        await db.refresh(new_comment)
        
        # audit_logger.log_comment_added(
        #     task_id=comment.task_id,
        #     user_id=comment.user_id,
        #     added_by=current_user
        # )
        
        return CommentResponse.from_orm(new_comment)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create comment", error=str(e), comment_data=comment.dict())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )


@router.get("/tasks/{task_id}/comments", response_model=List[CommentResponse])
async def get_task_comments(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all comments for a task."""
    result = await db.execute(
        select(TaskComment)
        .where(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.asc())
    )
    comments = result.scalars().all()
    return [CommentResponse.from_orm(c) for c in comments]


# Critical Path Response Model
class CriticalPathResponse(BaseModel):
    """Response model for critical path analysis"""
    project_id: int
    critical_path_tasks: List[int]
    project_duration_hours: float
    total_float_by_task: Dict[int, float]
    free_float_by_task: Dict[int, float]
    earliest_dates: Dict[int, Dict[str, datetime]]
    latest_dates: Dict[int, Dict[str, datetime]]
    cache_hit: bool = False
    calculation_time_ms: Optional[float] = None


# Critical Path Endpoints
@router.get("/projects/{project_id}/critical-path", response_model=CriticalPathResponse)
async def get_critical_path(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    force_recalculate: bool = Query(False, description="Force recalculation bypassing cache")
):
    """Get critical path analysis for a project with caching."""
    import time
    start_time = time.time()
    
    try:
        # Initialize services
        task_service = TaskDependencyService()
        cache = get_critical_path_cache()
        
        # Try cache first unless force recalculation is requested
        cached_result = None
        if not force_recalculate and cache:
            cached_result = await cache.get_critical_path(project_id)
        
        if cached_result:
            # Cache hit - return cached result
            calculation_time = (time.time() - start_time) * 1000
            logger.info(
                "Critical path cache hit",
                project_id=project_id,
                calculation_time_ms=calculation_time
            )
            
            return CriticalPathResponse(
                project_id=project_id,
                critical_path_tasks=[int(task_id) for task_id in cached_result.critical_path_tasks],
                project_duration_hours=float(cached_result.project_duration_hours),
                total_float_by_task={int(k): float(v) for k, v in cached_result.total_float_by_task.items()},
                free_float_by_task={int(k): float(v) for k, v in cached_result.free_float_by_task.items()},
                earliest_dates={
                    int(k): {"start": v[0], "finish": v[1]} 
                    for k, v in cached_result.earliest_dates.items()
                },
                latest_dates={
                    int(k): {"start": v[0], "finish": v[1]} 
                    for k, v in cached_result.latest_dates.items()
                },
                cache_hit=True,
                calculation_time_ms=calculation_time
            )
        
        # Cache miss - calculate critical path
        logger.info(
            "Critical path cache miss - calculating",
            project_id=project_id,
            force_recalculate=force_recalculate
        )
        
        # Calculate critical path using the service
        result = await task_service.calculate_critical_path(str(project_id))
        
        # Cache the result
        if cache:
            await cache.set_critical_path(project_id, result)
        
        calculation_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Critical path calculated",
            project_id=project_id,
            calculation_time_ms=calculation_time,
            critical_path_length=len(result.critical_path_tasks)
        )
        
        return CriticalPathResponse(
            project_id=project_id,
            critical_path_tasks=[int(task_id) for task_id in result.critical_path_tasks],
            project_duration_hours=float(result.project_duration_hours),
            total_float_by_task={int(k): float(v) for k, v in result.total_float_by_task.items()},
            free_float_by_task={int(k): float(v) for k, v in result.free_float_by_task.items()},
            earliest_dates={
                int(k): {"start": v[0], "finish": v[1]} 
                for k, v in result.earliest_dates.items()
            },
            latest_dates={
                int(k): {"start": v[0], "finish": v[1]} 
                for k, v in result.latest_dates.items()
            },
            cache_hit=False,
            calculation_time_ms=calculation_time
        )
        
    except Exception as e:
        calculation_time = (time.time() - start_time) * 1000
        logger.error(
            "Failed to calculate critical path",
            error=str(e),
            project_id=project_id,
            calculation_time_ms=calculation_time
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate critical path"
        )


@router.delete("/projects/{project_id}/critical-path/cache", status_code=status.HTTP_204_NO_CONTENT)
async def invalidate_critical_path_cache(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Invalidate critical path cache for a project."""
    try:
        cache = get_critical_path_cache()
        if cache:
            await cache.invalidate_project_cache(project_id)
            logger.info("Critical path cache invalidated", project_id=project_id)
        else:
            logger.warning("Cache not available for invalidation", project_id=project_id)
            
    except Exception as e:
        logger.error(
            "Failed to invalidate critical path cache",
            error=str(e),
            project_id=project_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invalidate cache"
        )