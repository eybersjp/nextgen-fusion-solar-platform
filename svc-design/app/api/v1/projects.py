"""Project management API routes."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSummary,
    ProjectList,
    ProjectFilter,
    ProjectStats,
    ProjectLocationUpdate,
    ProjectTagsUpdate,
    ProjectCustomFieldsUpdate,
    ProjectStatusUpdate,
    ProjectStatus,
    ProjectType,
    ProjectPriority
)
from app.api.v1.auth import get_current_user

router = APIRouter(tags=["projects"])


def get_user_projects_query(db: Session, user: User, include_shared: bool = True):
    """Get base query for user's projects."""
    query = db.query(Project)
    
    if user.role == "admin":
        # Admins can see all projects
        return query
    elif include_shared:
        # Users can see their own projects and shared projects
        return query.filter(
            or_(
                Project.owner_id == user.id,
                Project.shared_with.contains([str(user.id)])
            )
        )
    else:
        # Only user's own projects
        return query.filter(Project.owner_id == user.id)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project."""
    # Create project
    db_project = Project(
        **project_data.dict(),
        owner_id=current_user.id,
        created_by=current_user.id
    )
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    return ProjectResponse.from_orm(db_project)


@router.get("/", response_model=ProjectList)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    project_type: Optional[ProjectType] = None,
    priority: Optional[ProjectPriority] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    include_shared: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List projects with filtering and pagination."""
    query = get_user_projects_query(db, current_user, include_shared)
    
    # Apply filters
    if status:
        query = query.filter(Project.status == status)
    
    if project_type:
        query = query.filter(Project.project_type == project_type)
    
    if priority:
        query = query.filter(Project.priority == priority)
    
    if search:
        search_filter = or_(
            Project.name.ilike(f"%{search}%"),
            Project.description.ilike(f"%{search}%"),
            Project.location_address.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    if tags:
        for tag in tags:
            query = query.filter(Project.tags.contains([tag]))
    
    # Get total count
    total = query.count()
    
    # Apply pagination and get results
    projects = query.offset(skip).limit(limit).all()
    
    return ProjectList(
        items=[ProjectSummary.from_orm(project) for project in projects],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/stats", response_model=ProjectStats)
async def get_project_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project statistics for the current user."""
    query = get_user_projects_query(db, current_user, include_shared=False)
    
    total_projects = query.count()
    active_projects = query.filter(Project.status == ProjectStatus.ACTIVE).count()
    completed_projects = query.filter(Project.status == ProjectStatus.COMPLETED).count()
    on_hold_projects = query.filter(Project.status == ProjectStatus.ON_HOLD).count()
    
    # Calculate total capacity and estimated value
    projects = query.all()
    total_capacity = sum(p.system_capacity_kw or 0 for p in projects)
    total_estimated_value = sum(p.estimated_cost or 0 for p in projects)
    
    return ProjectStats(
        total_projects=total_projects,
        active_projects=active_projects,
        completed_projects=completed_projects,
        on_hold_projects=on_hold_projects,
        total_capacity_kw=total_capacity,
        total_estimated_value=total_estimated_value
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific project by ID."""
    query = get_user_projects_query(db, current_user)
    project = query.filter(Project.id == str(project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return ProjectResponse.from_orm(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a project."""
    query = get_user_projects_query(db, current_user, include_shared=False)
    project = query.filter(Project.id == str(project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user can edit (owner or admin)
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this project"
        )
    
    # Update project fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(project, field):
            setattr(project, field, value)
    
    project.updated_at = datetime.utcnow()
    project.updated_by = current_user.id
    
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.patch("/{project_id}/status", response_model=ProjectResponse)
async def update_project_status(
    project_id: UUID,
    status_data: ProjectStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project status."""
    query = get_user_projects_query(db, current_user, include_shared=False)
    project = query.filter(Project.id == str(project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user can edit
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this project"
        )
    
    project.status = status_data.status
    if status_data.status_notes:
        project.status_notes = status_data.status_notes
    
    # Update completion date if completed
    if status_data.status == ProjectStatus.COMPLETED:
        project.completion_date = datetime.utcnow()
    
    project.updated_at = datetime.utcnow()
    project.updated_by = current_user.id
    
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.patch("/{project_id}/location", response_model=ProjectResponse)
async def update_project_location(
    project_id: UUID,
    location_data: ProjectLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project location."""
    query = get_user_projects_query(db, current_user, include_shared=False)
    project = query.filter(Project.id == str(project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user can edit
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this project"
        )
    
    # Update location fields
    for field, value in location_data.dict(exclude_unset=True).items():
        if hasattr(project, field):
            setattr(project, field, value)
    
    project.updated_at = datetime.utcnow()
    project.updated_by = current_user.id
    
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.patch("/{project_id}/tags", response_model=ProjectResponse)
async def update_project_tags(
    project_id: UUID,
    tags_data: ProjectTagsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project tags."""
    query = get_user_projects_query(db, current_user, include_shared=False)
    project = query.filter(Project.id == str(project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user can edit
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this project"
        )
    
    project.tags = tags_data.tags
    project.updated_at = datetime.utcnow()
    project.updated_by = current_user.id
    
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.patch("/{project_id}/custom-fields", response_model=ProjectResponse)
async def update_project_custom_fields(
    project_id: UUID,
    custom_fields_data: ProjectCustomFieldsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project custom fields."""
    query = get_user_projects_query(db, current_user, include_shared=False)
    project = query.filter(Project.id == str(project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user can edit
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this project"
        )
    
    # Merge custom fields
    current_custom_fields = project.custom_fields or {}
    current_custom_fields.update(custom_fields_data.custom_fields)
    project.custom_fields = current_custom_fields
    
    project.updated_at = datetime.utcnow()
    project.updated_by = current_user.id
    
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a project (soft delete)."""
    query = get_user_projects_query(db, current_user, include_shared=False)
    project = query.filter(Project.id == str(project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user can delete (owner or admin)
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project"
        )
    
    # Soft delete
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    project.deleted_by = current_user.id
    
    db.commit()


@router.post("/{project_id}/duplicate", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate an existing project."""
    query = get_user_projects_query(db, current_user)
    original_project = query.filter(Project.id == str(project_id)).first()
    
    if not original_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Create duplicate project
    project_data = {
        "name": f"{original_project.name} (Copy)",
        "description": original_project.description,
        "project_type": original_project.project_type,
        "priority": original_project.priority,
        "location_address": original_project.location_address,
        "location_latitude": original_project.location_latitude,
        "location_longitude": original_project.location_longitude,
        "location_timezone": original_project.location_timezone,
        "system_capacity_kw": original_project.system_capacity_kw,
        "estimated_cost": original_project.estimated_cost,
        "estimated_savings": original_project.estimated_savings,
        "payback_period_years": original_project.payback_period_years,
        "tags": original_project.tags or [],
        "custom_fields": original_project.custom_fields or {},
        "design_settings": original_project.design_settings or {},
        "status": ProjectStatus.DRAFT,
        "owner_id": current_user.id,
        "created_by": current_user.id
    }
    
    duplicate_project = Project(**project_data)
    db.add(duplicate_project)
    db.commit()
    db.refresh(duplicate_project)
    
    return ProjectResponse.from_orm(duplicate_project)