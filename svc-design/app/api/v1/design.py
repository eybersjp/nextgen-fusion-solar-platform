#!/usr/bin/env python3
"""
Design API endpoints for the Design Service

Provides REST API endpoints for design management including:
- CRUD operations
- Design validation
- Performance calculations
- Design comparison
- Approval workflows
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    get_db,
    get_current_user,
    User,
    RequireDesignRead,
    RequireDesignWrite,
    RequireDesignDelete,
    RequireDesignApprove,
    get_logger,
    DesignError,
    DesignNotFoundError,
    DesignValidationError,
    DesignPermissionError
)
from app.schemas import (
    DesignCreate,
    DesignUpdate,
    DesignResponse,
    DesignListResponse,
    DesignValidationResult,
    DesignPerformanceMetrics,
    DesignComparison,
    DesignComparisonResult
)
from app.services import DesignService

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=DesignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new design",
    description="Create a new solar design with specifications and layout"
)
async def create_design(
    design_data: DesignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignWrite)
) -> DesignResponse:
    """Create a new design.
    
    Args:
        design_data: Design creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created design
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        logger.info(f"Creating new design for user {current_user.id}")
        design_service = DesignService(db)
        design = await design_service.create_design(design_data, current_user.id)
        logger.info(f"Design created successfully with ID {design.id}")
        return design
    except DesignValidationError as e:
        logger.error(f"Design validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except DesignError as e:
        logger.error(f"Design creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/",
    response_model=DesignListResponse,
    summary="List designs",
    description="Get a paginated list of designs with optional filtering"
)
async def list_designs(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by design status"),
    created_by: Optional[UUID] = Query(None, description="Filter by creator user ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignRead)
) -> DesignListResponse:
    """List designs with optional filtering.
    
    Args:
        project_id: Optional project ID filter
        status: Optional status filter
        created_by: Optional creator filter
        skip: Number of records to skip
        limit: Number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Paginated list of designs
    """
    try:
        logger.info(f"Listing designs for user {current_user.id}")
        design_service = DesignService(db)
        
        filters = {}
        if project_id:
            filters["project_id"] = project_id
        if status:
            filters["status"] = status
        if created_by:
            filters["created_by"] = created_by
            
        designs = await design_service.list_designs(
            filters=filters,
            skip=skip,
            limit=limit,
            user_id=current_user.id
        )
        
        logger.info(f"Retrieved {len(designs.items)} designs")
        return designs
    except DesignError as e:
        logger.error(f"Failed to list designs: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error listing designs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/{design_id}",
    response_model=DesignResponse,
    summary="Get design by ID",
    description="Retrieve a specific design by its ID"
)
async def get_design(
    design_id: UUID = Path(..., description="Design ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignRead)
) -> DesignResponse:
    """Get a design by ID.
    
    Args:
        design_id: Design ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Design details
        
    Raises:
        HTTPException: If design not found or access denied
    """
    try:
        logger.info(f"Getting design {design_id} for user {current_user.id}")
        design_service = DesignService(db)
        design = await design_service.get_design(design_id, current_user.id)
        logger.info(f"Design {design_id} retrieved successfully")
        return design
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design access denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/{design_id}",
    response_model=DesignResponse,
    summary="Update design",
    description="Update an existing design"
)
async def update_design(
    design_id: UUID = Path(..., description="Design ID"),
    design_data: DesignUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignWrite)
) -> DesignResponse:
    """Update a design.
    
    Args:
        design_id: Design ID
        design_data: Design update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated design
        
    Raises:
        HTTPException: If update fails
    """
    try:
        logger.info(f"Updating design {design_id} for user {current_user.id}")
        design_service = DesignService(db)
        design = await design_service.update_design(design_id, design_data, current_user.id)
        logger.info(f"Design {design_id} updated successfully")
        return design
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignValidationError as e:
        logger.error(f"Design validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design update denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/{design_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete design",
    description="Soft delete a design (marks as deleted)"
)
async def delete_design(
    design_id: UUID = Path(..., description="Design ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignDelete)
) -> None:
    """Delete a design (soft delete).
    
    Args:
        design_id: Design ID
        db: Database session
        current_user: Current authenticated user
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        logger.info(f"Deleting design {design_id} for user {current_user.id}")
        design_service = DesignService(db)
        await design_service.delete_design(design_id, current_user.id)
        logger.info(f"Design {design_id} deleted successfully")
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design deletion denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/{design_id}/duplicate",
    response_model=DesignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate design",
    description="Create a copy of an existing design"
)
async def duplicate_design(
    design_id: UUID = Path(..., description="Design ID to duplicate"),
    name: Optional[str] = Body(None, description="Name for the duplicated design"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignWrite)
) -> DesignResponse:
    """Duplicate a design.
    
    Args:
        design_id: Design ID to duplicate
        name: Optional name for the duplicated design
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Duplicated design
        
    Raises:
        HTTPException: If duplication fails
    """
    try:
        logger.info(f"Duplicating design {design_id} for user {current_user.id}")
        design_service = DesignService(db)
        design = await design_service.duplicate_design(design_id, current_user.id, name)
        logger.info(f"Design duplicated successfully with ID {design.id}")
        return design
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design duplication denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error duplicating design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/{design_id}/approve",
    response_model=DesignResponse,
    summary="Approve design",
    description="Approve a design for implementation"
)
async def approve_design(
    design_id: UUID = Path(..., description="Design ID"),
    comments: Optional[str] = Body(None, description="Approval comments"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignApprove)
) -> DesignResponse:
    """Approve a design.
    
    Args:
        design_id: Design ID
        comments: Optional approval comments
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Approved design
        
    Raises:
        HTTPException: If approval fails
    """
    try:
        logger.info(f"Approving design {design_id} by user {current_user.id}")
        design_service = DesignService(db)
        design = await design_service.approve_design(design_id, current_user.id, comments)
        logger.info(f"Design {design_id} approved successfully")
        return design
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design approval denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error approving design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/{design_id}/reject",
    response_model=DesignResponse,
    summary="Reject design",
    description="Reject a design with comments"
)
async def reject_design(
    design_id: UUID = Path(..., description="Design ID"),
    comments: str = Body(..., description="Rejection comments"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignApprove)
) -> DesignResponse:
    """Reject a design.
    
    Args:
        design_id: Design ID
        comments: Rejection comments
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Rejected design
        
    Raises:
        HTTPException: If rejection fails
    """
    try:
        logger.info(f"Rejecting design {design_id} by user {current_user.id}")
        design_service = DesignService(db)
        design = await design_service.reject_design(design_id, current_user.id, comments)
        logger.info(f"Design {design_id} rejected successfully")
        return design
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design rejection denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error rejecting design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/{design_id}/validate",
    response_model=DesignValidationResult,
    summary="Validate design",
    description="Validate a design against requirements and standards"
)
async def validate_design(
    design_id: UUID = Path(..., description="Design ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignRead)
) -> DesignValidationResult:
    """Validate a design.
    
    Args:
        design_id: Design ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Validation results
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        logger.info(f"Validating design {design_id} for user {current_user.id}")
        design_service = DesignService(db)
        result = await design_service.validate_design(design_id, current_user.id)
        logger.info(f"Design {design_id} validation completed")
        return result
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design validation denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error validating design: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/{design_id}/performance",
    response_model=DesignPerformanceMetrics,
    summary="Calculate design performance",
    description="Calculate performance metrics for a design"
)
async def calculate_performance(
    design_id: UUID = Path(..., description="Design ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignRead)
) -> DesignPerformanceMetrics:
    """Calculate design performance.
    
    Args:
        design_id: Design ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Performance metrics
        
    Raises:
        HTTPException: If calculation fails
    """
    try:
        logger.info(f"Calculating performance for design {design_id}")
        design_service = DesignService(db)
        metrics = await design_service.calculate_performance(design_id, current_user.id)
        logger.info(f"Performance calculation completed for design {design_id}")
        return metrics
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Performance calculation denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error calculating performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/compare",
    response_model=DesignComparisonResult,
    summary="Compare designs",
    description="Compare multiple designs and provide recommendations"
)
async def compare_designs(
    comparison_data: DesignComparison,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignRead)
) -> DesignComparisonResult:
    """Compare designs.
    
    Args:
        comparison_data: Design comparison data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Comparison results
        
    Raises:
        HTTPException: If comparison fails
    """
    try:
        logger.info(f"Comparing designs for user {current_user.id}")
        design_service = DesignService(db)
        result = await design_service.compare_designs(comparison_data, current_user.id)
        logger.info(f"Design comparison completed")
        return result
    except DesignNotFoundError as e:
        logger.error(f"Design not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DesignPermissionError as e:
        logger.error(f"Design comparison denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error comparing designs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )