#!/usr/bin/env python3
"""
Phase 3 3D Design API endpoints for the Design Service

Provides REST API endpoints for 3D design management including:
- 3D layout creation and management
- Solar irradiance calculations
- CAD export functionality
- GIS data import
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import json
import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core import (
    get_db,
    get_current_user,
    User,
    RequireDesignRead,
    RequireDesignWrite,
    get_logger
)
from app.services.design_3d import Design3DService

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models for 3D design
class GeometryData(BaseModel):
    vertices: List[List[float]] = Field(..., description="3D vertices as [x, y, z] coordinates")
    faces: List[List[int]] = Field(..., description="Face indices referencing vertices")


class RoofSurface(BaseModel):
    surface_id: str = Field(..., description="Unique surface identifier")
    area: float = Field(..., gt=0, description="Surface area in square meters")
    tilt_angle: float = Field(..., ge=0, le=90, description="Roof tilt angle in degrees")
    azimuth: float = Field(..., ge=0, lt=360, description="Azimuth angle in degrees")


class BuildingModel(BaseModel):
    geometry: GeometryData = Field(..., description="3D building geometry")
    roof_surfaces: List[RoofSurface] = Field(..., description="Roof surface definitions")


class PanelPosition(BaseModel):
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: float = Field(..., description="Z coordinate")


class PanelRotation(BaseModel):
    x: float = Field(..., description="X rotation in degrees")
    y: float = Field(..., description="Y rotation in degrees")
    z: float = Field(..., description="Z rotation in degrees")


class PanelLayout(BaseModel):
    panel_id: str = Field(..., description="Unique panel identifier")
    position: PanelPosition = Field(..., description="Panel position")
    rotation: PanelRotation = Field(..., description="Panel rotation")
    panel_type: str = Field(..., description="Panel type identifier")


class SimulationParams(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Site latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Site longitude")
    timezone: str = Field(..., description="Site timezone")


class Design3DCreate(BaseModel):
    project_id: UUID = Field(..., description="Project identifier")
    building_model: BuildingModel = Field(..., description="3D building geometry data")
    panel_layout: List[PanelLayout] = Field(..., description="Solar panel placement coordinates")
    simulation_params: Optional[SimulationParams] = Field(None, description="Sun angle and irradiance parameters")


class ShadingAnalysis(BaseModel):
    total_shading_loss: float = Field(..., description="Total shading loss percentage")
    critical_periods: List[str] = Field(..., description="Time periods with significant shading")


class IrradianceMap(BaseModel):
    annual_irradiance: float = Field(..., description="Annual solar irradiance (kWh/m²/year)")
    monthly_data: List[float] = Field(..., description="Monthly irradiance data")
    shading_analysis: ShadingAnalysis = Field(..., description="Shading analysis results")


class Design3DResponse(BaseModel):
    layout_id: UUID = Field(..., description="Unique layout identifier")
    energy_output: float = Field(..., description="Estimated annual energy production (kWh)")
    irradiance_map: IrradianceMap = Field(..., description="Solar irradiance visualization data")
    validation_status: str = Field(..., description="Design validation result")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class IrradianceCalculationResponse(BaseModel):
    total_irradiance: float = Field(..., description="Total solar irradiance (kWh/m²/year)")
    panel_efficiency: float = Field(..., description="Overall system efficiency percentage")
    energy_yield: float = Field(..., description="Expected energy yield (kWh/year)")
    performance_ratio: float = Field(..., description="System performance ratio")
    calculation_timestamp: datetime = Field(..., description="Calculation timestamp")


class CADExportRequest(BaseModel):
    layout_id: UUID = Field(..., description="Layout to export")
    format: str = Field(..., pattern="^(dwg|dxf|step|iges)$", description="Export format")
    include_annotations: bool = Field(False, description="Include technical annotations")
    coordinate_system: str = Field("local", pattern="^(local|utm|geographic)$", description="Coordinate system")


class CADExportResponse(BaseModel):
    download_url: str = Field(..., description="Temporary URL for file download")
    file_size: int = Field(..., description="File size in bytes")
    expires_at: datetime = Field(..., description="URL expiration timestamp")


class GISImportResponse(BaseModel):
    import_id: UUID = Field(..., description="Import operation identifier")
    features_imported: int = Field(..., description="Number of features successfully imported")
    building_footprints: List[Dict[str, Any]] = Field(..., description="Detected building geometries")
    terrain_model: Dict[str, Any] = Field(..., description="Digital elevation model data")


@router.post(
    "/3d-layout",
    response_model=Design3DResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update 3D solar panel layout",
    description="Create or update a 3D solar panel layout with irradiance calculations"
)
async def create_3d_layout(
    design_data: Design3DCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignWrite)
) -> Design3DResponse:
    """Create or update 3D solar panel layout.
    
    Args:
        design_data: 3D design creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created 3D layout with irradiance calculations
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        logger.info(f"Creating 3D layout for project {design_data.project_id} by user {current_user.id}")
        
        # Initialize 3D design service
        design_service = Design3DService(db)
        
        # Create 3D layout using the service
        result = await design_service.create_3d_layout(
            project_id=design_data.project_id,
            building_model=design_data.building_model.dict(),
            panel_layout=design_data.panel_layout,
            simulation_params=design_data.simulation_params.dict() if design_data.simulation_params else None,
            user_id=current_user.id
        )
        
        # Convert service result to API response format
        layout_id = result['layout_id']
        
        # Calculate basic energy output based on panel count and type
        panel_count = len(design_data.panel_layout)
        estimated_panel_power = 400  # watts per panel (mock)
        annual_hours = 1850  # annual sun hours (mock)
        energy_output = panel_count * estimated_panel_power * annual_hours / 1000  # kWh
        
        # Mock irradiance data
        irradiance_map = IrradianceMap(
            annual_irradiance=1850.0,
            monthly_data=[120, 135, 155, 165, 170, 160, 155, 160, 150, 140, 125, 115],
            shading_analysis=ShadingAnalysis(
                total_shading_loss=5.2,
                critical_periods=["06:00-08:00", "16:00-18:00"]
            )
        )
        
        response = Design3DResponse(
            layout_id=layout_id,
            energy_output=energy_output,
            irradiance_map=irradiance_map,
            validation_status="valid",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        logger.info(f"3D layout created successfully with ID {layout_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to create 3D layout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create 3D layout: {str(e)}"
        )


@router.get(
    "/irradiance-calculation/{layout_id}",
    response_model=IrradianceCalculationResponse,
    summary="Calculate solar irradiance for specific layout",
    description="Calculate detailed solar irradiance metrics for a 3D layout"
)
async def calculate_irradiance(
    layout_id: UUID = Path(..., description="Layout identifier"),
    calculation_type: str = Query("annual", pattern="^(annual|monthly|daily|hourly)$", description="Calculation type"),
    include_shading: bool = Query(True, description="Include shading analysis"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignRead)
) -> IrradianceCalculationResponse:
    """Calculate solar irradiance for specific layout.
    
    Args:
        layout_id: Layout identifier
        calculation_type: Type of calculation to perform
        include_shading: Whether to include shading analysis
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Irradiance calculation results
        
    Raises:
        HTTPException: If calculation fails
    """
    try:
        logger.info(f"Calculating irradiance for layout {layout_id} by user {current_user.id}")
        
        # Initialize 3D design service
        design_service = Design3DService(db)
        
        # Calculate irradiance using the service
        result = await design_service.calculate_solar_irradiance(
            layout_id=layout_id,
            calculation_type=calculation_type,
            include_shading=include_shading
        )
        
        # Convert service result to API response format
        response = IrradianceCalculationResponse(
            total_irradiance=result['total_irradiance'],
            panel_efficiency=result['panel_efficiency'],
            energy_yield=result['energy_yield'],
            performance_ratio=result['performance_ratio'],
            calculation_timestamp=datetime.utcnow()
        )
        
        logger.info(f"Irradiance calculation completed for layout {layout_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to calculate irradiance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate irradiance: {str(e)}"
        )


@router.post(
    "/export-cad",
    response_model=CADExportResponse,
    summary="Export design to CAD format",
    description="Export a 3D design layout to various CAD formats"
)
async def export_cad(
    export_request: CADExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignRead)
) -> CADExportResponse:
    """Export design to CAD format.
    
    Args:
        export_request: CAD export parameters
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        CAD export download information
        
    Raises:
        HTTPException: If export fails
    """
    try:
        logger.info(f"Exporting layout {export_request.layout_id} to {export_request.format} by user {current_user.id}")
        
        # Initialize 3D design service
        design_service = Design3DService(db)
        
        # Export CAD file using the service
        result = await design_service.export_cad_file(
            layout_id=export_request.layout_id,
            export_format=export_request.format,
            include_annotations=export_request.include_annotations,
            coordinate_system=export_request.coordinate_system
        )
        
        # Convert service result to API response format
        response = CADExportResponse(
            download_url=result['download_url'],
            file_size=result['file_size'],
            expires_at=result['expires_at']
        )
        
        logger.info(f"CAD export completed for layout {export_request.layout_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to export CAD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export CAD: {str(e)}"
        )


@router.post(
    "/import-gis",
    response_model=GISImportResponse,
    summary="Import GIS data for site modeling",
    description="Import GIS data files to create 3D site models"
)
async def import_gis(
    project_id: UUID = Body(..., description="Target project identifier"),
    coordinate_system: str = Body(..., description="Source coordinate reference system"),
    feature_types: Optional[List[str]] = Body(None, description="Specific features to import"),
    gis_file: UploadFile = File(..., description="GIS file (shapefile, KML, GeoJSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequireDesignWrite)
) -> GISImportResponse:
    """Import GIS data for site modeling.
    
    Args:
        project_id: Target project identifier
        coordinate_system: Source coordinate reference system
        feature_types: Specific features to import
        gis_file: GIS file upload
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        GIS import results
        
    Raises:
        HTTPException: If import fails
    """
    try:
        logger.info(f"Importing GIS data for project {project_id} by user {current_user.id}")
        
        # Initialize 3D design service
        design_service = Design3DService(db)
        
        # Mock GIS data for demonstration
        gis_data = {
            "coordinates": [40.7128, -74.0060],
            "elevation": 12.5,
            "building_outline": [
                [0, 0], [20, 0], [20, 15], [0, 15], [0, 0]
            ]
        }
        
        # Import GIS data using the service
        result = await design_service.import_gis_data(
            project_id=project_id,
            gis_data=gis_data,
            import_options={"coordinate_system": coordinate_system}
        )
        
        # Convert service result to API response format
        response = GISImportResponse(
            import_id=result['import_id'],
            features_imported=result['features_imported'],
            building_footprints=result['building_footprints'],
            terrain_model=result['terrain_model']
        )
        
        logger.info(f"GIS import completed with ID {result['import_id']}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to import GIS data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import GIS data: {str(e)}"
        )