"""Design API endpoints for the Design Service.

Provides CRUD operations and business logic for solar design management,
including design creation, updates, approvals, and collaboration features.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ...core.dependencies import (
    get_current_active_user,
    get_db_session,
    get_pagination_params,
    get_sorting_params,
    validate_uuid,
)
from ...core.exceptions import (
    DesignServiceException,
    NotFoundError,
    ValidationError,
    PermissionError,
)
from ...models.design import (
    Design,
    DesignVersion,
    DesignApproval,
    DesignComment,
    DesignAttachment,
    DesignTag,
    DesignShare,
)
from ...schemas.design import (
    DesignCreate,
    DesignUpdate,
    DesignResponse,
    DesignListResponse,
    DesignVersionCreate,
    DesignVersionResponse,
    DesignApprovalCreate,
    DesignApprovalResponse,
    DesignCommentCreate,
    DesignCommentResponse,
    DesignAttachmentResponse,
    DesignTagResponse,
    DesignShareCreate,
    DesignShareResponse,
)
from ...services.design import DesignService

router = APIRouter()


@router.get("/", response_model=DesignListResponse)
async def list_designs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search term for design name or description"),
    status: Optional[str] = Query(None, description="Filter by design status"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    organization_id: Optional[UUID] = Query(None, description="Filter by organization ID"),
    created_after: Optional[datetime] = Query(None, description="Filter designs created after this date"),
    created_before: Optional[datetime] = Query(None, description="Filter designs created before this date"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List designs with filtering, searching, and pagination.
    
    Returns a paginated list of designs that the current user has access to.
    Supports various filters and search capabilities.
    """
    try:
        design_service = DesignService(db)
        
        # Build filters
        filters = {}
        if search:
            filters["search"] = search
        if status:
            filters["status"] = status
        if project_id:
            filters["project_id"] = project_id
        if organization_id:
            filters["organization_id"] = organization_id
        if created_after:
            filters["created_after"] = created_after
        if created_before:
            filters["created_before"] = created_before
        
        # Get designs
        designs, total = await design_service.list_designs(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return DesignListResponse(
            designs=designs,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list designs: {str(e)}"
        )


@router.post("/", response_model=DesignResponse, status_code=status.HTTP_201_CREATED)
async def create_design(
    design_data: DesignCreate,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new solar design.
    
    Creates a new design with the provided data and returns the created design.
    The current user becomes the owner of the design.
    """
    try:
        design_service = DesignService(db)
        
        design = await design_service.create_design(
            design_data=design_data,
            user_id=current_user.id,
        )
        
        return DesignResponse.from_orm(design)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create design: {str(e)}"
        )


@router.get("/{design_id}", response_model=DesignResponse)
async def get_design(
    design_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get a specific design by ID.
    
    Returns the design details if the user has access to it.
    """
    try:
        design_service = DesignService(db)
        
        design = await design_service.get_design(
            design_id=design_id,
            user_id=current_user.id,
        )
        
        if not design:
            raise NotFoundError(f"Design {design_id} not found")
        
        return DesignResponse.from_orm(design)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get design: {str(e)}"
        )


@router.put("/{design_id}", response_model=DesignResponse)
async def update_design(
    design_id: UUID = Depends(validate_uuid),
    design_data: DesignUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific design.
    
    Updates the design with the provided data and returns the updated design.
    Only users with edit permissions can update the design.
    """
    try:
        design_service = DesignService(db)
        
        design = await design_service.update_design(
            design_id=design_id,
            design_data=design_data,
            user_id=current_user.id,
        )
        
        return DesignResponse.from_orm(design)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update design: {str(e)}"
        )


@router.delete("/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_design(
    design_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Delete a specific design.
    
    Soft deletes the design if the user has delete permissions.
    """
    try:
        design_service = DesignService(db)
        
        await design_service.delete_design(
            design_id=design_id,
            user_id=current_user.id,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete design: {str(e)}"
        )


# Design Versions
@router.get("/{design_id}/versions", response_model=List[DesignVersionResponse])
async def list_design_versions(
    design_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all versions of a design."""
    try:
        design_service = DesignService(db)
        
        versions = await design_service.list_design_versions(
            design_id=design_id,
            user_id=current_user.id,
        )
        
        return [DesignVersionResponse.from_orm(version) for version in versions]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list design versions: {str(e)}"
        )


@router.post("/{design_id}/versions", response_model=DesignVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_design_version(
    design_id: UUID = Depends(validate_uuid),
    version_data: DesignVersionCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new version of a design."""
    try:
        design_service = DesignService(db)
        
        version = await design_service.create_design_version(
            design_id=design_id,
            version_data=version_data,
            user_id=current_user.id,
        )
        
        return DesignVersionResponse.from_orm(version)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create design version: {str(e)}"
        )


# Design Approvals
@router.get("/{design_id}/approvals", response_model=List[DesignApprovalResponse])
async def list_design_approvals(
    design_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all approvals for a design."""
    try:
        design_service = DesignService(db)
        
        approvals = await design_service.list_design_approvals(
            design_id=design_id,
            user_id=current_user.id,
        )
        
        return [DesignApprovalResponse.from_orm(approval) for approval in approvals]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list design approvals: {str(e)}"
        )


@router.post("/{design_id}/approvals", response_model=DesignApprovalResponse, status_code=status.HTTP_201_CREATED)
async def create_design_approval(
    design_id: UUID = Depends(validate_uuid),
    approval_data: DesignApprovalCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new approval request for a design."""
    try:
        design_service = DesignService(db)
        
        approval = await design_service.create_design_approval(
            design_id=design_id,
            approval_data=approval_data,
            user_id=current_user.id,
        )
        
        return DesignApprovalResponse.from_orm(approval)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create design approval: {str(e)}"
        )


# Design Comments
@router.get("/{design_id}/comments", response_model=List[DesignCommentResponse])
async def list_design_comments(
    design_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all comments for a design."""
    try:
        design_service = DesignService(db)
        
        comments = await design_service.list_design_comments(
            design_id=design_id,
            user_id=current_user.id,
        )
        
        return [DesignCommentResponse.from_orm(comment) for comment in comments]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list design comments: {str(e)}"
        )


@router.post("/{design_id}/comments", response_model=DesignCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_design_comment(
    design_id: UUID = Depends(validate_uuid),
    comment_data: DesignCommentCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new comment on a design."""
    try:
        design_service = DesignService(db)
        
        comment = await design_service.create_design_comment(
            design_id=design_id,
            comment_data=comment_data,
            user_id=current_user.id,
        )
        
        return DesignCommentResponse.from_orm(comment)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create design comment: {str(e)}"
        )


# Design Attachments
@router.get("/{design_id}/attachments", response_model=List[DesignAttachmentResponse])
async def list_design_attachments(
    design_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all attachments for a design."""
    try:
        design_service = DesignService(db)
        
        attachments = await design_service.list_design_attachments(
            design_id=design_id,
            user_id=current_user.id,
        )
        
        return [DesignAttachmentResponse.from_orm(attachment) for attachment in attachments]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list design attachments: {str(e)}"
        )


# Design Tags
@router.get("/tags", response_model=List[DesignTagResponse])
async def list_design_tags(
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all available design tags."""
    try:
        design_service = DesignService(db)
        
        tags = await design_service.list_design_tags()
        
        return [DesignTagResponse.from_orm(tag) for tag in tags]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list design tags: {str(e)}"
        )


# Design Sharing
@router.post("/{design_id}/share", response_model=DesignShareResponse, status_code=status.HTTP_201_CREATED)
async def share_design(
    design_id: UUID = Depends(validate_uuid),
    share_data: DesignShareCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Share a design with external parties."""
    try:
        design_service = DesignService(db)
        
        share = await design_service.share_design(
            design_id=design_id,
            share_data=share_data,
            user_id=current_user.id,
        )
        
        return DesignShareResponse.from_orm(share)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share design: {str(e)}"
        )