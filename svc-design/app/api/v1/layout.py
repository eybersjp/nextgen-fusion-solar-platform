#!/usr/bin/env python3
"""
Layout API endpoints for the Design Service

Provides REST API endpoints for layout management including:
- CRUD operations for layouts and zones
- Layout optimization
- Performance calculations
- Template management
- Export functionality
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import (
    get_db,
    get_current_user,
    User,
    RequireLayoutRead,
    RequireLayoutWrite,
    RequireLayoutDelete,
    RequireLayoutOptimize,
    get_logger,
    LayoutError,
    LayoutNotFoundError,
    LayoutValidationError,
    LayoutOptimizationError
)
from app.schemas import (
    LayoutCreate,
    LayoutUpdate,
    LayoutResponse,
    LayoutListResponse,
    LayoutZoneCreate,
    LayoutZoneUpdate,
    LayoutZoneResponse,
    LayoutTemplateCreate,
    LayoutTemplateUpdate,
    LayoutTemplateResponse,
    LayoutOptimization,
    LayoutValidationResult,
    LayoutPerformanceMetrics,
    LayoutComparison,
    LayoutComparisonResult,
    LayoutExportRequest,
    LayoutExportResponse
)
from app.services import LayoutService

logger = get_logger(__name__)
router = APIRouter()


# Layout CRUD Operations
@router.post(
    "/",
    response_model=LayoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new layout",
    description="Create a new solar panel layout"
)
async def create_layout(
    layout_data: LayoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutWrite)
) -> LayoutResponse:
    """Create a new layout."""
    try:
        logger.info(f"Creating new layout for user {current_user.id}")
        layout_service = LayoutService(db)
        layout = await layout_service.create_layout(layout_data, current_user.id)
        logger.info(f"Layout created successfully with ID {layout.id}")
        return layout
    except LayoutValidationError as e:
        logger.error(f"Layout validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except LayoutError as e:
        logger.error(f"Layout creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/",
    response_model=LayoutListResponse,
    summary="List layouts",
    description="Get a paginated list of layouts with optional filtering"
)
async def list_layouts(
    design_id: Optional[UUID] = Query(None, description="Filter by design ID"),
    status: Optional[str] = Query(None, description="Filter by layout status"),
    template_id: Optional[UUID] = Query(None, description="Filter by template ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> LayoutListResponse:
    """List layouts with optional filtering."""
    try:
        logger.info(f"Listing layouts for user {current_user.id}")
        layout_service = LayoutService(db)
        
        filters = {}
        if design_id:
            filters["design_id"] = design_id
        if status:
            filters["status"] = status
        if template_id:
            filters["template_id"] = template_id
            
        layouts = await layout_service.list_layouts(
            filters=filters,
            skip=skip,
            limit=limit,
            user_id=current_user.id
        )
        
        logger.info(f"Retrieved {len(layouts.items)} layouts")
        return layouts
    except LayoutError as e:
        logger.error(f"Failed to list layouts: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error listing layouts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/{layout_id}",
    response_model=LayoutResponse,
    summary="Get layout by ID",
    description="Retrieve a specific layout by its ID"
)
async def get_layout(
    layout_id: UUID = Path(..., description="Layout ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> LayoutResponse:
    """Get a layout by ID."""
    try:
        logger.info(f"Getting layout {layout_id} for user {current_user.id}")
        layout_service = LayoutService(db)
        layout = await layout_service.get_layout(layout_id, current_user.id)
        logger.info(f"Layout {layout_id} retrieved successfully")
        return layout
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/{layout_id}",
    response_model=LayoutResponse,
    summary="Update layout",
    description="Update an existing layout"
)
async def update_layout(
    layout_id: UUID = Path(..., description="Layout ID"),
    layout_data: LayoutUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutWrite)
) -> LayoutResponse:
    """Update a layout."""
    try:
        logger.info(f"Updating layout {layout_id} for user {current_user.id}")
        layout_service = LayoutService(db)
        layout = await layout_service.update_layout(layout_id, layout_data, current_user.id)
        logger.info(f"Layout {layout_id} updated successfully")
        return layout
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except LayoutValidationError as e:
        logger.error(f"Layout validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/{layout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete layout",
    description="Soft delete a layout"
)
async def delete_layout(
    layout_id: UUID = Path(..., description="Layout ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutDelete)
) -> None:
    """Delete a layout (soft delete)."""
    try:
        logger.info(f"Deleting layout {layout_id} for user {current_user.id}")
        layout_service = LayoutService(db)
        await layout_service.delete_layout(layout_id, current_user.id)
        logger.info(f"Layout {layout_id} deleted successfully")
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Layout Optimization
@router.post(
    "/{layout_id}/optimize",
    response_model=LayoutResponse,
    summary="Optimize layout",
    description="Run optimization algorithm on a layout"
)
async def optimize_layout(
    layout_id: UUID = Path(..., description="Layout ID"),
    optimization_data: LayoutOptimization = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutOptimize)
) -> LayoutResponse:
    """Optimize a layout."""
    try:
        logger.info(f"Optimizing layout {layout_id} for user {current_user.id}")
        layout_service = LayoutService(db)
        layout = await layout_service.optimize_layout(layout_id, optimization_data, current_user.id)
        logger.info(f"Layout {layout_id} optimization completed")
        return layout
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except LayoutOptimizationError as e:
        logger.error(f"Layout optimization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error optimizing layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Layout Validation and Performance
@router.post(
    "/{layout_id}/validate",
    response_model=LayoutValidationResult,
    summary="Validate layout",
    description="Validate a layout against constraints and requirements"
)
async def validate_layout(
    layout_id: UUID = Path(..., description="Layout ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> LayoutValidationResult:
    """Validate a layout."""
    try:
        logger.info(f"Validating layout {layout_id} for user {current_user.id}")
        layout_service = LayoutService(db)
        result = await layout_service.validate_layout(layout_id, current_user.id)
        logger.info(f"Layout {layout_id} validation completed")
        return result
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error validating layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/{layout_id}/performance",
    response_model=LayoutPerformanceMetrics,
    summary="Calculate layout performance",
    description="Calculate performance metrics for a layout"
)
async def calculate_layout_performance(
    layout_id: UUID = Path(..., description="Layout ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> LayoutPerformanceMetrics:
    """Calculate layout performance."""
    try:
        logger.info(f"Calculating performance for layout {layout_id}")
        layout_service = LayoutService(db)
        metrics = await layout_service.calculate_performance(layout_id, current_user.id)
        logger.info(f"Performance calculation completed for layout {layout_id}")
        return metrics
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error calculating performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Layout Comparison
@router.post(
    "/compare",
    response_model=LayoutComparisonResult,
    summary="Compare layouts",
    description="Compare multiple layouts and provide recommendations"
)
async def compare_layouts(
    comparison_data: LayoutComparison,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> LayoutComparisonResult:
    """Compare layouts."""
    try:
        logger.info(f"Comparing layouts for user {current_user.id}")
        layout_service = LayoutService(db)
        result = await layout_service.compare_layouts(comparison_data, current_user.id)
        logger.info(f"Layout comparison completed")
        return result
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error comparing layouts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Layout Export
@router.post(
    "/{layout_id}/export",
    response_model=LayoutExportResponse,
    summary="Export layout",
    description="Export a layout in various formats"
)
async def export_layout(
    layout_id: UUID = Path(..., description="Layout ID"),
    export_request: LayoutExportRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> LayoutExportResponse:
    """Export a layout."""
    try:
        logger.info(f"Exporting layout {layout_id} for user {current_user.id}")
        layout_service = LayoutService(db)
        result = await layout_service.export_layout(layout_id, export_request, current_user.id)
        logger.info(f"Layout {layout_id} export completed")
        return result
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error exporting layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Layout Zone Management
@router.post(
    "/{layout_id}/zones",
    response_model=LayoutZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create layout zone",
    description="Create a new zone within a layout"
)
async def create_layout_zone(
    layout_id: UUID = Path(..., description="Layout ID"),
    zone_data: LayoutZoneCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutWrite)
) -> LayoutZoneResponse:
    """Create a layout zone."""
    try:
        logger.info(f"Creating zone for layout {layout_id}")
        layout_service = LayoutService(db)
        zone = await layout_service.create_zone(layout_id, zone_data, current_user.id)
        logger.info(f"Zone created successfully with ID {zone.id}")
        return zone
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except LayoutValidationError as e:
        logger.error(f"Zone validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating zone: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/{layout_id}/zones",
    response_model=List[LayoutZoneResponse],
    summary="List layout zones",
    description="Get all zones for a layout"
)
async def list_layout_zones(
    layout_id: UUID = Path(..., description="Layout ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> List[LayoutZoneResponse]:
    """List layout zones."""
    try:
        logger.info(f"Listing zones for layout {layout_id}")
        layout_service = LayoutService(db)
        zones = await layout_service.list_zones(layout_id, current_user.id)
        logger.info(f"Retrieved {len(zones)} zones")
        return zones
    except LayoutNotFoundError as e:
        logger.error(f"Layout not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error listing zones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/{layout_id}/zones/{zone_id}",
    response_model=LayoutZoneResponse,
    summary="Update layout zone",
    description="Update an existing layout zone"
)
async def update_layout_zone(
    layout_id: UUID = Path(..., description="Layout ID"),
    zone_id: UUID = Path(..., description="Zone ID"),
    zone_data: LayoutZoneUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutWrite)
) -> LayoutZoneResponse:
    """Update a layout zone."""
    try:
        logger.info(f"Updating zone {zone_id} for layout {layout_id}")
        layout_service = LayoutService(db)
        zone = await layout_service.update_zone(layout_id, zone_id, zone_data, current_user.id)
        logger.info(f"Zone {zone_id} updated successfully")
        return zone
    except LayoutNotFoundError as e:
        logger.error(f"Layout or zone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except LayoutValidationError as e:
        logger.error(f"Zone validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating zone: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/{layout_id}/zones/{zone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete layout zone",
    description="Delete a layout zone"
)
async def delete_layout_zone(
    layout_id: UUID = Path(..., description="Layout ID"),
    zone_id: UUID = Path(..., description="Zone ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutWrite)
) -> None:
    """Delete a layout zone."""
    try:
        logger.info(f"Deleting zone {zone_id} for layout {layout_id}")
        layout_service = LayoutService(db)
        await layout_service.delete_zone(layout_id, zone_id, current_user.id)
        logger.info(f"Zone {zone_id} deleted successfully")
    except LayoutNotFoundError as e:
        logger.error(f"Layout or zone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting zone: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Layout Template Management
@router.post(
    "/templates",
    response_model=LayoutTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create layout template",
    description="Create a new layout template"
)
async def create_layout_template(
    template_data: LayoutTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutWrite)
) -> LayoutTemplateResponse:
    """Create a layout template."""
    try:
        logger.info(f"Creating layout template for user {current_user.id}")
        layout_service = LayoutService(db)
        template = await layout_service.create_template(template_data, current_user.id)
        logger.info(f"Template created successfully with ID {template.id}")
        return template
    except LayoutValidationError as e:
        logger.error(f"Template validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/templates",
    response_model=List[LayoutTemplateResponse],
    summary="List layout templates",
    description="Get all available layout templates"
)
async def list_layout_templates(
    category: Optional[str] = Query(None, description="Filter by template category"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutRead)
) -> List[LayoutTemplateResponse]:
    """List layout templates."""
    try:
        logger.info(f"Listing layout templates for user {current_user.id}")
        layout_service = LayoutService(db)
        
        filters = {}
        if category:
            filters["category"] = category
            
        templates = await layout_service.list_templates(filters, current_user.id)
        logger.info(f"Retrieved {len(templates)} templates")
        return templates
    except Exception as e:
        logger.error(f"Unexpected error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/templates/{template_id}/apply",
    response_model=LayoutResponse,
    summary="Apply layout template",
    description="Apply a template to create a new layout"
)
async def apply_layout_template(
    template_id: UUID = Path(..., description="Template ID"),
    design_id: UUID = Body(..., description="Design ID to apply template to"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireLayoutWrite)
) -> LayoutResponse:
    """Apply a layout template."""
    try:
        logger.info(f"Applying template {template_id} for user {current_user.id}")
        layout_service = LayoutService(db)
        layout = await layout_service.apply_template(template_id, design_id, current_user.id)
        logger.info(f"Template applied successfully, layout ID {layout.id}")
        return layout
    except LayoutNotFoundError as e:
        logger.error(f"Template not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error applying template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )