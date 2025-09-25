"""Shading models for the Design Service.

This module contains SQLAlchemy models for shading analysis,
obstacles, solar calculations, and irradiance modeling.
"""

import uuid
from datetime import datetime, time
from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Time
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import relationship, backref
from geoalchemy2 import Geometry

from .base import FullBaseModel


# Enums for shading analysis
class ShadingAnalysisType(PyEnum):
    """Types of shading analysis."""
    ANNUAL = "annual"
    MONTHLY = "monthly"
    DAILY = "daily"
    HOURLY = "hourly"
    SEASONAL = "seasonal"
    CUSTOM = "custom"


class ShadingAnalysisStatus(PyEnum):
    """Status of shading analysis."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShadingMethod(PyEnum):
    """Methods for shading calculation."""
    RAY_TRACING = "ray_tracing"
    SHADOW_MAPPING = "shadow_mapping"
    GEOMETRIC = "geometric"
    SIMPLIFIED = "simplified"


class AnalysisStatus(PyEnum):
    """Analysis status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisType(PyEnum):
    """Analysis type enumeration."""
    ANNUAL = "annual"
    SEASONAL = "seasonal"
    MONTHLY = "monthly"
    DAILY = "daily"
    HOURLY = "hourly"
    CUSTOM = "custom"


class ShadingObjectType(PyEnum):
    """Shading object type enumeration."""
    BUILDING = "building"
    TREE = "tree"
    POLE = "pole"
    CHIMNEY = "chimney"
    VENT = "vent"
    EQUIPMENT = "equipment"
    TERRAIN = "terrain"
    VEGETATION = "vegetation"
    STRUCTURE = "structure"
    OTHER = "other"


class MitigationType(PyEnum):
    """Mitigation type enumeration."""
    RELOCATION = "relocation"
    TRIMMING = "trimming"
    REMOVAL = "removal"
    SHIELDING = "shielding"
    DESIGN_CHANGE = "design_change"
    ACCEPTANCE = "acceptance"


class ReportFormat(PyEnum):
    """Report format enumeration."""
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"


class VisualizationType(PyEnum):
    """Visualization type enumeration."""
    HEATMAP = "heatmap"
    CONTOUR = "contour"
    THREE_D = "3d"
    ANIMATION = "animation"
    CHART = "chart"


class ShadingAnalysis(FullBaseModel):
    """Shading analysis model for comprehensive shading studies."""
    
    __tablename__ = 'shading_analyses'
    
    # References
    design_id = Column(UUID(as_uuid=True), nullable=False, index=True, doc="Design ID")
    layout_id = Column(UUID(as_uuid=True), nullable=False, index=True, doc="Layout ID")
    
    # Analysis information
    name = Column(String(255), nullable=False, doc="Analysis name")
    description = Column(Text, doc="Analysis description")
    
    # Analysis type and method
    analysis_type = Column(
        Enum('annual', 'seasonal', 'monthly', 'daily', 'hourly', 'custom', name='analysis_type_enum'),
        nullable=False,
        default='annual',
        doc="Analysis type"
    )
    
    calculation_method = Column(
        Enum('geometric', 'ray_tracing', 'solar_path', 'hybrid', name='calculation_method_enum'),
        nullable=False,
        default='geometric',
        doc="Calculation method"
    )
    
    # Time parameters
    start_date = Column(DateTime(timezone=True), doc="Analysis start date")
    end_date = Column(DateTime(timezone=True), doc="Analysis end date")
    time_step_minutes = Column(Integer, default=60, doc="Time step in minutes")
    
    # Solar position parameters
    latitude = Column(Float, nullable=False, doc="Site latitude")
    longitude = Column(Float, nullable=False, doc="Site longitude")
    timezone_offset = Column(Float, doc="Timezone offset from UTC")
    
    # Analysis parameters
    grid_resolution_meters = Column(Float, default=1.0, doc="Analysis grid resolution in meters")
    include_diffuse = Column(Boolean, nullable=False, default=True, doc="Include diffuse irradiance")
    include_reflected = Column(Boolean, nullable=False, default=True, doc="Include reflected irradiance")
    
    # Weather data
    weather_data_source = Column(String(100), doc="Weather data source")
    weather_file_path = Column(String(500), doc="Weather file path")
    
    # Results summary
    total_shading_loss_percent = Column(Float, doc="Total shading loss percentage")
    near_shading_loss_percent = Column(Float, doc="Near shading loss percentage")
    far_shading_loss_percent = Column(Float, doc="Far shading loss percentage")
    
    # Temporal shading patterns
    morning_shading_percent = Column(Float, doc="Morning shading percentage")
    midday_shading_percent = Column(Float, doc="Midday shading percentage")
    evening_shading_percent = Column(Float, doc="Evening shading percentage")
    
    # Seasonal variations
    winter_shading_percent = Column(Float, doc="Winter shading percentage")
    spring_shading_percent = Column(Float, doc="Spring shading percentage")
    summer_shading_percent = Column(Float, doc="Summer shading percentage")
    autumn_shading_percent = Column(Float, doc="Autumn shading percentage")
    
    # Analysis status
    analysis_status = Column(
        Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='analysis_status_enum'),
        nullable=False,
        default='pending',
        doc="Analysis status"
    )
    
    progress_percent = Column(Float, default=0.0, doc="Analysis progress percentage")
    
    # Execution information
    started_at = Column(DateTime(timezone=True), doc="Analysis start time")
    completed_at = Column(DateTime(timezone=True), doc="Analysis completion time")
    execution_time_seconds = Column(Float, doc="Execution time in seconds")
    
    # Error handling
    error_message = Column(Text, doc="Error message if failed")
    warnings = Column(JSONB, doc="Analysis warnings")
    
    # Results data
    hourly_results = Column(JSONB, doc="Hourly shading results")
    monthly_results = Column(JSONB, doc="Monthly shading summary")
    annual_results = Column(JSONB, doc="Annual shading summary")
    
    # Spatial results
    shading_map_data = Column(JSONB, doc="Spatial shading map data")
    irradiance_map_data = Column(JSONB, doc="Irradiance map data")
    
    def __repr__(self) -> str:
        return f"<ShadingAnalysis(id={self.id}, name='{self.name}', status='{self.analysis_status}')>"
    
    @property
    def is_completed(self) -> bool:
        """Check if analysis is completed.
        
        Returns:
            bool: True if completed
        """
        return self.analysis_status == 'completed'
    
    def get_shading_loss_by_month(self, month: int) -> Optional[float]:
        """Get shading loss for specific month.
        
        Args:
            month: Month number (1-12)
            
        Returns:
            Optional[float]: Shading loss percentage or None
        """
        if self.monthly_results and isinstance(self.monthly_results, dict):
            return self.monthly_results.get(str(month), {}).get('shading_loss_percent')
        return None


class Obstacle(FullBaseModel):
    """Obstacle model for shading objects."""
    
    __tablename__ = 'obstacles'
    
    # References
    design_id = Column(UUID(as_uuid=True), nullable=False, index=True, doc="Design ID")
    shading_analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('shading_analyses.id'), 
        index=True, 
        doc="Shading analysis ID"
    )
    
    # Obstacle information
    name = Column(String(255), nullable=False, doc="Obstacle name")
    description = Column(Text, doc="Obstacle description")
    
    # Obstacle type
    obstacle_type = Column(
        Enum(
            'building', 'tree', 'pole', 'chimney', 'vent', 'equipment', 'terrain', 
            'vegetation', 'structure', 'other', name='obstacle_type_enum'
        ),
        nullable=False,
        doc="Obstacle type"
    )
    
    # Geometry
    geometry = Column(Geometry('POLYGON', srid=4326), nullable=False, doc="Obstacle geometry")
    height_meters = Column(Float, nullable=False, doc="Obstacle height in meters")
    base_elevation_meters = Column(Float, default=0.0, doc="Base elevation in meters")
    
    # Physical properties
    material_type = Column(String(100), doc="Material type")
    transparency = Column(Float, default=0.0, doc="Transparency factor (0-1)")
    reflectance = Column(Float, default=0.2, doc="Surface reflectance (0-1)")
    
    # Seasonal variations
    is_seasonal = Column(Boolean, nullable=False, default=False, doc="Has seasonal variations")
    seasonal_data = Column(JSONB, doc="Seasonal height/transparency variations")
    
    # Tree-specific properties
    tree_species = Column(String(100), doc="Tree species (if applicable)")
    canopy_diameter_meters = Column(Float, doc="Canopy diameter in meters")
    trunk_diameter_meters = Column(Float, doc="Trunk diameter in meters")
    leaf_area_index = Column(Float, doc="Leaf area index")
    
    # Building-specific properties
    building_type = Column(String(100), doc="Building type (if applicable)")
    roof_type = Column(String(100), doc="Roof type")
    wall_material = Column(String(100), doc="Wall material")
    
    # Status and validation
    is_active = Column(Boolean, nullable=False, default=True, doc="Is obstacle active")
    is_validated = Column(Boolean, nullable=False, default=False, doc="Is geometry validated")
    validation_errors = Column(JSONB, doc="Geometry validation errors")
    
    # Data source
    data_source = Column(
        Enum('manual', 'lidar', 'photogrammetry', 'survey', 'satellite', 'imported', name='data_source_enum'),
        doc="Data source"
    )
    
    data_accuracy_meters = Column(Float, doc="Data accuracy in meters")
    
    # Relationships
    shading_analysis = relationship("ShadingAnalysis", backref="obstacles")
    
    def __repr__(self) -> str:
        return f"<Obstacle(id={self.id}, name='{self.name}', type='{self.obstacle_type}')>"
    
    @property
    def top_elevation_meters(self) -> float:
        """Calculate top elevation.
        
        Returns:
            float: Top elevation in meters
        """
        return self.base_elevation_meters + self.height_meters
    
    def get_seasonal_height(self, month: int) -> float:
        """Get height for specific month considering seasonal variations.
        
        Args:
            month: Month number (1-12)
            
        Returns:
            float: Height in meters
        """
        if self.is_seasonal and self.seasonal_data:
            seasonal_factor = self.seasonal_data.get(str(month), {}).get('height_factor', 1.0)
            return self.height_meters * seasonal_factor
        return self.height_meters


class SolarPosition(FullBaseModel):
    """Solar position model for sun path calculations."""
    
    __tablename__ = 'solar_positions'
    
    # References
    shading_analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('shading_analyses.id'), 
        nullable=False, 
        index=True
    )
    
    # Time information
    timestamp = Column(DateTime(timezone=True), nullable=False, doc="Timestamp")
    day_of_year = Column(Integer, nullable=False, doc="Day of year (1-365/366)")
    hour_of_day = Column(Float, nullable=False, doc="Hour of day (0-24)")
    
    # Solar position
    solar_elevation_degrees = Column(Float, nullable=False, doc="Solar elevation angle in degrees")
    solar_azimuth_degrees = Column(Float, nullable=False, doc="Solar azimuth angle in degrees")
    solar_zenith_degrees = Column(Float, nullable=False, doc="Solar zenith angle in degrees")
    
    # Solar irradiance
    direct_normal_irradiance = Column(Float, doc="Direct normal irradiance (W/m²)")
    diffuse_horizontal_irradiance = Column(Float, doc="Diffuse horizontal irradiance (W/m²)")
    global_horizontal_irradiance = Column(Float, doc="Global horizontal irradiance (W/m²)")
    
    # Atmospheric conditions
    air_mass = Column(Float, doc="Air mass")
    atmospheric_pressure = Column(Float, doc="Atmospheric pressure (Pa)")
    precipitable_water = Column(Float, doc="Precipitable water (cm)")
    
    # Sun visibility
    is_sun_up = Column(Boolean, nullable=False, doc="Is sun above horizon")
    sunrise_time = Column(Time, doc="Sunrise time")
    sunset_time = Column(Time, doc="Sunset time")
    
    # Relationships
    shading_analysis = relationship("ShadingAnalysis", backref="solar_positions")
    
    def __repr__(self) -> str:
        return f"<SolarPosition(timestamp={self.timestamp}, elevation={self.solar_elevation_degrees:.1f}°)>"
    
    @property
    def is_daylight(self) -> bool:
        """Check if it's daylight hours.
        
        Returns:
            bool: True if sun is up and elevation > 0
        """
        return self.is_sun_up and self.solar_elevation_degrees > 0


class ShadingResult(FullBaseModel):
    """Shading result model for detailed shading calculations."""
    
    __tablename__ = 'shading_results'
    
    # References
    shading_analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('shading_analyses.id'), 
        nullable=False, 
        index=True
    )
    
    solar_position_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('solar_positions.id'), 
        nullable=False, 
        index=True
    )
    
    # Spatial reference
    panel_array_id = Column(UUID(as_uuid=True), index=True, doc="Panel array ID (if applicable)")
    grid_point_id = Column(String(100), doc="Grid point identifier")
    coordinates = Column(Geometry('POINT', srid=4326), doc="Point coordinates")
    
    # Shading calculations
    is_shaded = Column(Boolean, nullable=False, doc="Is point shaded")
    shading_factor = Column(Float, nullable=False, default=0.0, doc="Shading factor (0-1)")
    
    # Irradiance components
    direct_irradiance = Column(Float, doc="Direct irradiance (W/m²)")
    diffuse_irradiance = Column(Float, doc="Diffuse irradiance (W/m²)")
    reflected_irradiance = Column(Float, doc="Reflected irradiance (W/m²)")
    total_irradiance = Column(Float, doc="Total irradiance (W/m²)")
    
    # Shading sources
    shading_obstacles = Column(JSONB, doc="List of obstacles causing shading")
    primary_obstacle_id = Column(UUID(as_uuid=True), doc="Primary shading obstacle ID")
    
    # Shadow geometry
    shadow_length_meters = Column(Float, doc="Shadow length in meters")
    shadow_azimuth_degrees = Column(Float, doc="Shadow azimuth in degrees")
    
    # Performance impact
    energy_loss_factor = Column(Float, doc="Energy loss factor due to shading")
    
    # Relationships
    shading_analysis = relationship("ShadingAnalysis", backref="shading_results")
    solar_position = relationship("SolarPosition", backref="shading_results")
    
    def __repr__(self) -> str:
        return f"<ShadingResult(analysis_id={self.shading_analysis_id}, shaded={self.is_shaded})>"


class IrradianceMap(FullBaseModel):
    """Irradiance map model for spatial irradiance distribution."""
    
    __tablename__ = 'irradiance_maps'
    
    # References
    shading_analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('shading_analyses.id'), 
        nullable=False, 
        index=True
    )
    
    # Map information
    name = Column(String(255), nullable=False, doc="Map name")
    map_type = Column(
        Enum('annual', 'monthly', 'daily', 'hourly', name='map_type_enum'),
        nullable=False,
        doc="Map type"
    )
    
    # Time period
    time_period = Column(String(100), doc="Time period description")
    start_date = Column(DateTime(timezone=True), doc="Period start date")
    end_date = Column(DateTime(timezone=True), doc="Period end date")
    
    # Spatial parameters
    grid_resolution_meters = Column(Float, nullable=False, doc="Grid resolution in meters")
    bounds_geometry = Column(Geometry('POLYGON', srid=4326), doc="Map bounds")
    
    # Map data
    grid_data = Column(JSONB, nullable=False, doc="Grid-based irradiance data")
    statistics = Column(JSONB, doc="Map statistics (min, max, mean, std)")
    
    # Color mapping
    color_scale = Column(JSONB, doc="Color scale definition")
    legend_data = Column(JSONB, doc="Legend information")
    
    # File references
    raster_file_path = Column(String(500), doc="Raster file path")
    vector_file_path = Column(String(500), doc="Vector file path")
    
    # Generation information
    generation_method = Column(String(100), doc="Map generation method")
    generation_parameters = Column(JSONB, doc="Generation parameters")
    
    # Relationships
    shading_analysis = relationship("ShadingAnalysis", backref="irradiance_maps")
    
    def __repr__(self) -> str:
        return f"<IrradianceMap(id={self.id}, name='{self.name}', type='{self.map_type}')>"
    
    def get_irradiance_at_point(self, x: float, y: float) -> Optional[float]:
        """Get irradiance value at specific coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Optional[float]: Irradiance value or None
        """
        # This would implement spatial interpolation from grid_data
        # Simplified implementation - in practice would use spatial indexing
        if self.grid_data:
            # Find nearest grid point and return value
            # Implementation would depend on grid data structure
            pass
        return None


class SunPath(FullBaseModel):
    """Sun path model for annual sun trajectory."""
    
    __tablename__ = 'sun_paths'
    
    # References
    shading_analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('shading_analyses.id'), 
        nullable=False, 
        index=True
    )
    
    # Location information
    latitude = Column(Float, nullable=False, doc="Site latitude")
    longitude = Column(Float, nullable=False, doc="Site longitude")
    timezone_offset = Column(Float, doc="Timezone offset from UTC")
    
    # Sun path data
    path_data = Column(JSONB, nullable=False, doc="Complete sun path data")
    
    # Key solar events
    summer_solstice_data = Column(JSONB, doc="Summer solstice sun path")
    winter_solstice_data = Column(JSONB, doc="Winter solstice sun path")
    spring_equinox_data = Column(JSONB, doc="Spring equinox sun path")
    autumn_equinox_data = Column(JSONB, doc="Autumn equinox sun path")
    
    # Monthly sun paths
    monthly_paths = Column(JSONB, doc="Monthly sun path data")
    
    # Solar angles
    max_elevation_degrees = Column(Float, doc="Maximum solar elevation")
    min_elevation_degrees = Column(Float, doc="Minimum solar elevation")
    
    # Daylight hours
    longest_day_hours = Column(Float, doc="Longest day duration in hours")
    shortest_day_hours = Column(Float, doc="Shortest day duration in hours")
    
    # Generation parameters
    time_step_minutes = Column(Integer, default=15, doc="Time step for calculations")
    calculation_year = Column(Integer, doc="Year used for calculations")
    
    # Relationships
    shading_analysis = relationship("ShadingAnalysis", backref="sun_paths")
    
    def __repr__(self) -> str:
        return f"<SunPath(lat={self.latitude:.2f}, lon={self.longitude:.2f})>"
    
    def get_solar_position(self, month: int, day: int, hour: float) -> Optional[Dict[str, float]]:
        """Get solar position for specific date and time.
        
        Args:
            month: Month (1-12)
            day: Day of month
            hour: Hour of day (0-24)
            
        Returns:
            Optional[Dict[str, float]]: Solar position data or None
        """
        if self.path_data:
            # Implementation would look up or interpolate from path_data
            # This is a simplified placeholder
            pass
        return None


class ShadingReport(FullBaseModel):
    """Shading report model for analysis summaries."""
    
    __tablename__ = 'shading_reports'
    
    # References
    shading_analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('shading_analyses.id'), 
        nullable=False, 
        index=True
    )
    
    # Report information
    name = Column(String(255), nullable=False, doc="Report name")
    report_type = Column(
        Enum('summary', 'detailed', 'technical', 'executive', name='report_type_enum'),
        nullable=False,
        default='summary',
        doc="Report type"
    )
    
    # Report content
    executive_summary = Column(Text, doc="Executive summary")
    methodology = Column(Text, doc="Analysis methodology")
    key_findings = Column(JSONB, doc="Key findings and metrics")
    recommendations = Column(Text, doc="Recommendations")
    
    # Charts and visualizations
    charts_data = Column(JSONB, doc="Chart data and configurations")
    maps_data = Column(JSONB, doc="Map data and configurations")
    
    # File outputs
    pdf_file_path = Column(String(500), doc="PDF report file path")
    excel_file_path = Column(String(500), doc="Excel data file path")
    
    # Report metadata
    template_used = Column(String(255), doc="Report template used")
    generation_parameters = Column(JSONB, doc="Report generation parameters")
    
    # Status
    generation_status = Column(
        Enum('pending', 'generating', 'completed', 'failed', name='generation_status_enum'),
        nullable=False,
        default='pending',
        doc="Generation status"
    )
    
    # Relationships
    shading_analysis = relationship("ShadingAnalysis", backref="reports")
    
    def __repr__(self) -> str:
        return f"<ShadingReport(id={self.id}, name='{self.name}', type='{self.report_type}')>"


class ShadingMitigation(FullBaseModel):
    """Shading mitigation model for optimization strategies."""
    
    __tablename__ = 'shading_mitigations'
    
    # References
    shading_analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('shading_analyses.id'), 
        nullable=False, 
        index=True
    )
    
    # Mitigation information
    name = Column(String(255), nullable=False, doc="Mitigation name")
    description = Column(Text, doc="Mitigation description")
    
    # Mitigation type
    mitigation_type = Column(
        Enum(
            'panel_relocation', 'obstacle_removal', 'obstacle_modification', 
            'tree_trimming', 'building_modification', 'layout_optimization',
            'tilt_adjustment', 'spacing_increase', 'other', 
            name='mitigation_type_enum'
        ),
        nullable=False,
        doc="Mitigation type"
    )
    
    # Implementation details
    implementation_cost = Column(Float, doc="Implementation cost")
    implementation_time_days = Column(Integer, doc="Implementation time in days")
    feasibility_score = Column(Float, doc="Feasibility score (0-1)")
    
    # Performance impact
    energy_gain_kwh_annual = Column(Float, doc="Annual energy gain in kWh")
    energy_gain_percentage = Column(Float, doc="Energy gain percentage")
    roi_years = Column(Float, doc="Return on investment in years")
    
    # Technical details
    technical_requirements = Column(JSONB, doc="Technical requirements")
    regulatory_considerations = Column(Text, doc="Regulatory considerations")
    
    # Status
    is_recommended = Column(Boolean, nullable=False, default=False, doc="Is recommended")
    priority_score = Column(Float, doc="Priority score (0-1)")
    
    # Relationships
    shading_analysis = relationship("ShadingAnalysis", backref="mitigations")
    
    def __repr__(self) -> str:
        return f"<ShadingMitigation(id={self.id}, name='{self.name}', type='{self.mitigation_type}')>"


# Create aliases for backward compatibility
ShadingObject = Obstacle  # Alias for the service layer