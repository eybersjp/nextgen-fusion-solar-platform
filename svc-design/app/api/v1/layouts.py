"""Layout API endpoints for the Design Service.

Provides CRUD operations for solar panel layouts, panel arrays,
inverters, electrical components, and layout optimization.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.dependencies import (
    get_current_active_user,
    get_db_session,
    get_pagination_params,
    validate_uuid,
)
from ...core.exceptions import (
    DesignServiceException,
    NotFoundError,
    ValidationError,
    PermissionError,
)
from ...models.layout import (
    Layout,
    PanelArray,
    Inverter,
    ElectricalComponent,
    CableRun,
    LayoutOptimization,
)
from ...schemas.layout import (
    LayoutCreate,
    LayoutUpdate,
    LayoutResponse,
    LayoutListResponse,
    PanelArrayCreate,
    PanelArrayUpdate,
    PanelArrayResponse,
    InverterCreate,
    InverterUpdate,
    InverterResponse,
    ElectricalComponentCreate,
    ElectricalComponentUpdate,
    ElectricalComponentResponse,
    CableRunCreate,
    CableRunUpdate,
    CableRunResponse,
    LayoutOptimizationCreate,
    LayoutOptimizationResponse,
)
from ...services.layout import LayoutService

router = APIRouter()


# Layout endpoints
@router.get("/", response_model=LayoutListResponse)
async def list_layouts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    design_id: Optional[UUID] = Query(None, description="Filter by design ID"),
    layout_type: Optional[str] = Query(None, description="Filter by layout type"),
    status: Optional[str] = Query(None, description="Filter by layout status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List layouts with filtering and pagination."""
    try:
        layout_service = LayoutService(db)
        
        filters = {}
        if design_id:
            filters["design_id"] = design_id
        if layout_type:
            filters["layout_type"] = layout_type
        if status:
            filters["status"] = status
        
        layouts, total = await layout_service.list_layouts(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return LayoutListResponse(
            layouts=layouts,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list layouts: {str(e)}"
        )


@router.post("/", response_model=LayoutResponse, status_code=status.HTTP_201_CREATED)
async def create_layout(
    layout_data: LayoutCreate,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new solar panel layout."""
    try:
        layout_service = LayoutService(db)
        
        layout = await layout_service.create_layout(
            layout_data=layout_data,
            user_id=current_user.id,
        )
        
        return LayoutResponse.from_orm(layout)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create layout: {str(e)}"
        )


@router.get("/{layout_id}", response_model=LayoutResponse)
async def get_layout(
    layout_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get a specific layout by ID."""
    try:
        layout_service = LayoutService(db)
        
        layout = await layout_service.get_layout(
            layout_id=layout_id,
            user_id=current_user.id,
        )
        
        if not layout:
            raise NotFoundError(f"Layout {layout_id} not found")
        
        return LayoutResponse.from_orm(layout)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get layout: {str(e)}"
        )


@router.put("/{layout_id}", response_model=LayoutResponse)
async def update_layout(
    layout_id: UUID = Depends(validate_uuid),
    layout_data: LayoutUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific layout."""
    try:
        layout_service = LayoutService(db)
        
        layout = await layout_service.update_layout(
            layout_id=layout_id,
            layout_data=layout_data,
            user_id=current_user.id,
        )
        
        return LayoutResponse.from_orm(layout)
        
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
            detail=f"Failed to update layout: {str(e)}"
        )


@router.delete("/{layout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layout(
    layout_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Delete a specific layout."""
    try:
        layout_service = LayoutService(db)
        
        await layout_service.delete_layout(
            layout_id=layout_id,
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
            detail=f"Failed to delete layout: {str(e)}"
        )


# Panel Array endpoints
@router.get("/{layout_id}/arrays", response_model=List[PanelArrayResponse])
async def list_panel_arrays(
    layout_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all panel arrays in a layout."""
    try:
        layout_service = LayoutService(db)
        
        arrays = await layout_service.list_panel_arrays(
            layout_id=layout_id,
            user_id=current_user.id,
        )
        
        return [PanelArrayResponse.from_orm(array) for array in arrays]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list panel arrays: {str(e)}"
        )


@router.post("/{layout_id}/arrays", response_model=PanelArrayResponse, status_code=status.HTTP_201_CREATED)
async def create_panel_array(
    layout_id: UUID = Depends(validate_uuid),
    array_data: PanelArrayCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new panel array in a layout."""
    try:
        layout_service = LayoutService(db)
        
        array = await layout_service.create_panel_array(
            layout_id=layout_id,
            array_data=array_data,
            user_id=current_user.id,
        )
        
        return PanelArrayResponse.from_orm(array)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create panel array: {str(e)}"
        )


@router.put("/arrays/{array_id}", response_model=PanelArrayResponse)
async def update_panel_array(
    array_id: UUID = Depends(validate_uuid),
    array_data: PanelArrayUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific panel array."""
    try:
        layout_service = LayoutService(db)
        
        array = await layout_service.update_panel_array(
            array_id=array_id,
            array_data=array_data,
            user_id=current_user.id,
        )
        
        return PanelArrayResponse.from_orm(array)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update panel array: {str(e)}"
        )


@router.delete("/arrays/{array_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_panel_array(
    array_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Delete a specific panel array."""
    try:
        layout_service = LayoutService(db)
        
        await layout_service.delete_panel_array(
            array_id=array_id,
            user_id=current_user.id,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete panel array: {str(e)}"
        )


# Inverter endpoints
@router.get("/{layout_id}/inverters", response_model=List[InverterResponse])
async def list_inverters(
    layout_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all inverters in a layout."""
    try:
        layout_service = LayoutService(db)
        
        inverters = await layout_service.list_inverters(
            layout_id=layout_id,
            user_id=current_user.id,
        )
        
        return [InverterResponse.from_orm(inverter) for inverter in inverters]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list inverters: {str(e)}"
        )


@router.post("/{layout_id}/inverters", response_model=InverterResponse, status_code=status.HTTP_201_CREATED)
async def create_inverter(
    layout_id: UUID = Depends(validate_uuid),
    inverter_data: InverterCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new inverter in a layout."""
    try:
        layout_service = LayoutService(db)
        
        inverter = await layout_service.create_inverter(
            layout_id=layout_id,
            inverter_data=inverter_data,
            user_id=current_user.id,
        )
        
        return InverterResponse.from_orm(inverter)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create inverter: {str(e)}"
        )


# Electrical Component endpoints
@router.get("/{layout_id}/components", response_model=List[ElectricalComponentResponse])
async def list_electrical_components(
    layout_id: UUID = Depends(validate_uuid),
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all electrical components in a layout."""
    try:
        layout_service = LayoutService(db)
        
        components = await layout_service.list_electrical_components(
            layout_id=layout_id,
            component_type=component_type,
            user_id=current_user.id,
        )
        
        return [ElectricalComponentResponse.from_orm(component) for component in components]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list electrical components: {str(e)}"
        )


@router.post("/{layout_id}/components", response_model=ElectricalComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_electrical_component(
    layout_id: UUID = Depends(validate_uuid),
    component_data: ElectricalComponentCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new electrical component in a layout."""
    try:
        layout_service = LayoutService(db)
        
        component = await layout_service.create_electrical_component(
            layout_id=layout_id,
            component_data=component_data,
            user_id=current_user.id,
        )
        
        return ElectricalComponentResponse.from_orm(component)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create electrical component: {str(e)}"
        )


# Cable Run endpoints
@router.get("/{layout_id}/cables", response_model=List[CableRunResponse])
async def list_cable_runs(
    layout_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all cable runs in a layout."""
    try:
        layout_service = LayoutService(db)
        
        cables = await layout_service.list_cable_runs(
            layout_id=layout_id,
            user_id=current_user.id,
        )
        
        return [CableRunResponse.from_orm(cable) for cable in cables]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cable runs: {str(e)}"
        )


@router.post("/{layout_id}/cables", response_model=CableRunResponse, status_code=status.HTTP_201_CREATED)
async def create_cable_run(
    layout_id: UUID = Depends(validate_uuid),
    cable_data: CableRunCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new cable run in a layout."""
    try:
        layout_service = LayoutService(db)
        
        cable = await layout_service.create_cable_run(
            layout_id=layout_id,
            cable_data=cable_data,
            user_id=current_user.id,
        )
        
        return CableRunResponse.from_orm(cable)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create cable run: {str(e)}"
        )


# Layout Optimization endpoints
@router.post("/{layout_id}/optimize", response_model=LayoutOptimizationResponse, status_code=status.HTTP_201_CREATED)
async def optimize_layout(
    layout_id: UUID = Depends(validate_uuid),
    optimization_data: LayoutOptimizationCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Start layout optimization process."""
    try:
        layout_service = LayoutService(db)
        
        optimization = await layout_service.optimize_layout(
            layout_id=layout_id,
            optimization_data=optimization_data,
            user_id=current_user.id,
        )
        
        return LayoutOptimizationResponse.from_orm(optimization)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize layout: {str(e)}"
        )


@router.get("/{layout_id}/optimizations", response_model=List[LayoutOptimizationResponse])
async def list_layout_optimizations(
    layout_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all optimization runs for a layout."""
    try:
        layout_service = LayoutService(db)
        
        optimizations = await layout_service.list_layout_optimizations(
            layout_id=layout_id,
            user_id=current_user.id,
        )
        
        return [LayoutOptimizationResponse.from_orm(opt) for opt in optimizations]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list layout optimizations: {str(e)}"
        )