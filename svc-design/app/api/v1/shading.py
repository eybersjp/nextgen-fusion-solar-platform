"""Shading Analysis API endpoints for the Design Service.

Provides CRUD operations for shading analysis, obstacles,
solar position calculations, and irradiance mapping.
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
from ...models.shading import (
    ShadingAnalysis,
    Obstacle,
    SolarPosition,
    ShadingResult,
    IrradianceMap,
    SunPath,
    ShadingReport,
)
from ...schemas.shading import (
    ShadingAnalysisCreate,
    ShadingAnalysisUpdate,
    ShadingAnalysisResponse,
    ShadingAnalysisListResponse,
    ObstacleCreate,
    ObstacleUpdate,
    ObstacleResponse,
    SolarPositionCreate,
    SolarPositionResponse,
    ShadingResultResponse,
    IrradianceMapCreate,
    IrradianceMapResponse,
    SunPathCreate,
    SunPathResponse,
    ShadingReportResponse,
)
from ...services.shading import ShadingService

router = APIRouter()


# Shading Analysis endpoints
@router.get("/", response_model=ShadingAnalysisListResponse)
async def list_shading_analyses(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    design_id: Optional[UUID] = Query(None, description="Filter by design ID"),
    layout_id: Optional[UUID] = Query(None, description="Filter by layout ID"),
    analysis_type: Optional[str] = Query(None, description="Filter by analysis type"),
    status: Optional[str] = Query(None, description="Filter by analysis status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List shading analyses with filtering and pagination."""
    try:
        shading_service = ShadingService(db)
        
        filters = {}
        if design_id:
            filters["design_id"] = design_id
        if layout_id:
            filters["layout_id"] = layout_id
        if analysis_type:
            filters["analysis_type"] = analysis_type
        if status:
            filters["status"] = status
        
        analyses, total = await shading_service.list_shading_analyses(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return ShadingAnalysisListResponse(
            analyses=analyses,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list shading analyses: {str(e)}"
        )


@router.post("/", response_model=ShadingAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_shading_analysis(
    analysis_data: ShadingAnalysisCreate,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        analysis = await shading_service.create_shading_analysis(
            analysis_data=analysis_data,
            user_id=current_user.id,
        )
        
        return ShadingAnalysisResponse.from_orm(analysis)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create shading analysis: {str(e)}"
        )


@router.get("/{analysis_id}", response_model=ShadingAnalysisResponse)
async def get_shading_analysis(
    analysis_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get a specific shading analysis by ID."""
    try:
        shading_service = ShadingService(db)
        
        analysis = await shading_service.get_shading_analysis(
            analysis_id=analysis_id,
            user_id=current_user.id,
        )
        
        if not analysis:
            raise NotFoundError(f"Shading analysis {analysis_id} not found")
        
        return ShadingAnalysisResponse.from_orm(analysis)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shading analysis: {str(e)}"
        )


@router.put("/{analysis_id}", response_model=ShadingAnalysisResponse)
async def update_shading_analysis(
    analysis_id: UUID = Depends(validate_uuid),
    analysis_data: ShadingAnalysisUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        analysis = await shading_service.update_shading_analysis(
            analysis_id=analysis_id,
            analysis_data=analysis_data,
            user_id=current_user.id,
        )
        
        return ShadingAnalysisResponse.from_orm(analysis)
        
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
            detail=f"Failed to update shading analysis: {str(e)}"
        )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shading_analysis(
    analysis_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Delete a specific shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        await shading_service.delete_shading_analysis(
            analysis_id=analysis_id,
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
            detail=f"Failed to delete shading analysis: {str(e)}"
        )


# Obstacle endpoints
@router.get("/{analysis_id}/obstacles", response_model=List[ObstacleResponse])
async def list_obstacles(
    analysis_id: UUID = Depends(validate_uuid),
    obstacle_type: Optional[str] = Query(None, description="Filter by obstacle type"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all obstacles in a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        obstacles = await shading_service.list_obstacles(
            analysis_id=analysis_id,
            obstacle_type=obstacle_type,
            user_id=current_user.id,
        )
        
        return [ObstacleResponse.from_orm(obstacle) for obstacle in obstacles]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list obstacles: {str(e)}"
        )


@router.post("/{analysis_id}/obstacles", response_model=ObstacleResponse, status_code=status.HTTP_201_CREATED)
async def create_obstacle(
    analysis_id: UUID = Depends(validate_uuid),
    obstacle_data: ObstacleCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new obstacle in a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        obstacle = await shading_service.create_obstacle(
            analysis_id=analysis_id,
            obstacle_data=obstacle_data,
            user_id=current_user.id,
        )
        
        return ObstacleResponse.from_orm(obstacle)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create obstacle: {str(e)}"
        )


@router.put("/obstacles/{obstacle_id}", response_model=ObstacleResponse)
async def update_obstacle(
    obstacle_id: UUID = Depends(validate_uuid),
    obstacle_data: ObstacleUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific obstacle."""
    try:
        shading_service = ShadingService(db)
        
        obstacle = await shading_service.update_obstacle(
            obstacle_id=obstacle_id,
            obstacle_data=obstacle_data,
            user_id=current_user.id,
        )
        
        return ObstacleResponse.from_orm(obstacle)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update obstacle: {str(e)}"
        )


@router.delete("/obstacles/{obstacle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_obstacle(
    obstacle_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Delete a specific obstacle."""
    try:
        shading_service = ShadingService(db)
        
        await shading_service.delete_obstacle(
            obstacle_id=obstacle_id,
            user_id=current_user.id,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete obstacle: {str(e)}"
        )


# Solar Position endpoints
@router.post("/{analysis_id}/solar-positions", response_model=List[SolarPositionResponse], status_code=status.HTTP_201_CREATED)
async def calculate_solar_positions(
    analysis_id: UUID = Depends(validate_uuid),
    position_data: SolarPositionCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Calculate solar positions for a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        positions = await shading_service.calculate_solar_positions(
            analysis_id=analysis_id,
            position_data=position_data,
            user_id=current_user.id,
        )
        
        return [SolarPositionResponse.from_orm(position) for position in positions]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate solar positions: {str(e)}"
        )


@router.get("/{analysis_id}/solar-positions", response_model=List[SolarPositionResponse])
async def get_solar_positions(
    analysis_id: UUID = Depends(validate_uuid),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get solar positions for a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        positions = await shading_service.get_solar_positions(
            analysis_id=analysis_id,
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id,
        )
        
        return [SolarPositionResponse.from_orm(position) for position in positions]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get solar positions: {str(e)}"
        )


# Shading Results endpoints
@router.get("/{analysis_id}/results", response_model=List[ShadingResultResponse])
async def get_shading_results(
    analysis_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get shading results for an analysis."""
    try:
        shading_service = ShadingService(db)
        
        results = await shading_service.get_shading_results(
            analysis_id=analysis_id,
            user_id=current_user.id,
        )
        
        return [ShadingResultResponse.from_orm(result) for result in results]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shading results: {str(e)}"
        )


# Irradiance Map endpoints
@router.post("/{analysis_id}/irradiance-maps", response_model=IrradianceMapResponse, status_code=status.HTTP_201_CREATED)
async def create_irradiance_map(
    analysis_id: UUID = Depends(validate_uuid),
    map_data: IrradianceMapCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create an irradiance map for a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        irradiance_map = await shading_service.create_irradiance_map(
            analysis_id=analysis_id,
            map_data=map_data,
            user_id=current_user.id,
        )
        
        return IrradianceMapResponse.from_orm(irradiance_map)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create irradiance map: {str(e)}"
        )


@router.get("/{analysis_id}/irradiance-maps", response_model=List[IrradianceMapResponse])
async def list_irradiance_maps(
    analysis_id: UUID = Depends(validate_uuid),
    map_type: Optional[str] = Query(None, description="Filter by map type"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List irradiance maps for a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        maps = await shading_service.list_irradiance_maps(
            analysis_id=analysis_id,
            map_type=map_type,
            user_id=current_user.id,
        )
        
        return [IrradianceMapResponse.from_orm(map_obj) for map_obj in maps]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list irradiance maps: {str(e)}"
        )


# Sun Path endpoints
@router.post("/{analysis_id}/sun-path", response_model=SunPathResponse, status_code=status.HTTP_201_CREATED)
async def create_sun_path(
    analysis_id: UUID = Depends(validate_uuid),
    sun_path_data: SunPathCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a sun path diagram for a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        sun_path = await shading_service.create_sun_path(
            analysis_id=analysis_id,
            sun_path_data=sun_path_data,
            user_id=current_user.id,
        )
        
        return SunPathResponse.from_orm(sun_path)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sun path: {str(e)}"
        )


@router.get("/{analysis_id}/sun-path", response_model=SunPathResponse)
async def get_sun_path(
    analysis_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get the sun path diagram for a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        sun_path = await shading_service.get_sun_path(
            analysis_id=analysis_id,
            user_id=current_user.id,
        )
        
        if not sun_path:
            raise NotFoundError(f"Sun path for analysis {analysis_id} not found")
        
        return SunPathResponse.from_orm(sun_path)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sun path: {str(e)}"
        )


# Shading Report endpoints
@router.post("/{analysis_id}/reports", response_model=ShadingReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_shading_report(
    analysis_id: UUID = Depends(validate_uuid),
    report_type: str = Query("comprehensive", description="Type of report to generate"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Generate a shading analysis report."""
    try:
        shading_service = ShadingService(db)
        
        report = await shading_service.generate_shading_report(
            analysis_id=analysis_id,
            report_type=report_type,
            user_id=current_user.id,
        )
        
        return ShadingReportResponse.from_orm(report)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate shading report: {str(e)}"
        )


@router.get("/{analysis_id}/reports", response_model=List[ShadingReportResponse])
async def list_shading_reports(
    analysis_id: UUID = Depends(validate_uuid),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List shading reports for an analysis."""
    try:
        shading_service = ShadingService(db)
        
        reports = await shading_service.list_shading_reports(
            analysis_id=analysis_id,
            report_type=report_type,
            user_id=current_user.id,
        )
        
        return [ShadingReportResponse.from_orm(report) for report in reports]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list shading reports: {str(e)}"
        )


# Analysis execution endpoints
@router.post("/{analysis_id}/execute", response_model=ShadingAnalysisResponse)
async def execute_shading_analysis(
    analysis_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Execute a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        analysis = await shading_service.execute_shading_analysis(
            analysis_id=analysis_id,
            user_id=current_user.id,
        )
        
        return ShadingAnalysisResponse.from_orm(analysis)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute shading analysis: {str(e)}"
        )


@router.get("/{analysis_id}/status", response_model=dict)
async def get_analysis_status(
    analysis_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get the execution status of a shading analysis."""
    try:
        shading_service = ShadingService(db)
        
        status_info = await shading_service.get_analysis_status(
            analysis_id=analysis_id,
            user_id=current_user.id,
        )
        
        return status_info
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analysis status: {str(e)}"
        )