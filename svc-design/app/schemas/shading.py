"""Shading schemas for the Design Service.

This module contains Pydantic schemas for shading-related request/response models,
including shading analysis, objects, results, mitigation, reports, and visualizations.
"""

import uuid
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from ..models.shading import (
    AnalysisStatus,
    AnalysisType,
    MitigationType,
    ReportFormat,
    ShadingObjectType,
    VisualizationType,
)
from .base import (
    AuditSchema,
    BaseSchema,
    FilterParams,
    GeometrySchema,
    MetadataSchema,
    OrganizationSchema,
    ProjectSchema,
    TimestampSchema,
    UUIDSchema,
)


class ShadingAnalysisBase(BaseSchema):
    """Base shading analysis schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Analysis name")
    description: Optional[str] = Field(None, description="Analysis description")
    analysis_type: AnalysisType = Field(..., description="Type of shading analysis")


class ShadingAnalysisCreate(ShadingAnalysisBase, ProjectSchema, MetadataSchema):
    """Schema for creating a new shading analysis."""
    
    design_id: Optional[uuid.UUID] = Field(None, description="Associated design ID")
    layout_id: Optional[uuid.UUID] = Field(None, description="Associated layout ID")
    
    # Analysis configuration
    analysis_config: Dict[str, Any] = Field(..., description="Analysis configuration")
    
    # Time parameters
    start_date: Optional[datetime] = Field(None, description="Analysis start date")
    end_date: Optional[datetime] = Field(None, description="Analysis end date")
    time_step_minutes: int = Field(60, gt=0, le=1440, description="Time step in minutes")
    
    # Analysis settings
    include_weather_data: bool = Field(True, description="Include weather data")
    weather_data_source: Optional[str] = Field(None, description="Weather data source")
    resolution_meters: float = Field(1.0, gt=0, description="Analysis resolution in meters")
    
    # Calculation parameters
    calculation_parameters: Optional[Dict[str, Any]] = Field(None, description="Calculation parameters")
    
    @validator('layout_id', 'design_id')
    def validate_reference(cls, v, values):
        """Validate that either design_id or layout_id is provided."""
        if not v and not values.get('design_id') and not values.get('layout_id'):
            raise ValueError('Either design_id or layout_id must be provided')
        return v


class ShadingAnalysisUpdate(BaseSchema):
    """Schema for updating a shading analysis."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Analysis name")
    description: Optional[str] = Field(None, description="Analysis description")
    status: Optional[AnalysisStatus] = Field(None, description="Analysis status")
    
    # Analysis configuration
    analysis_config: Optional[Dict[str, Any]] = Field(None, description="Analysis configuration")
    
    # Time parameters
    start_date: Optional[datetime] = Field(None, description="Analysis start date")
    end_date: Optional[datetime] = Field(None, description="Analysis end date")
    time_step_minutes: Optional[int] = Field(None, gt=0, le=1440, description="Time step in minutes")
    
    # Analysis settings
    include_weather_data: Optional[bool] = Field(None, description="Include weather data")
    weather_data_source: Optional[str] = Field(None, description="Weather data source")
    resolution_meters: Optional[float] = Field(None, gt=0, description="Analysis resolution in meters")
    
    # Calculation parameters
    calculation_parameters: Optional[Dict[str, Any]] = Field(None, description="Calculation parameters")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ShadingAnalysisResponse(
    ShadingAnalysisBase,
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    ProjectSchema,
    MetadataSchema,
):
    """Schema for shading analysis response."""
    
    design_id: Optional[uuid.UUID] = Field(None, description="Associated design ID")
    layout_id: Optional[uuid.UUID] = Field(None, description="Associated layout ID")
    
    # Analysis status
    status: AnalysisStatus = Field(..., description="Analysis status")
    
    # Analysis configuration
    analysis_config: Dict[str, Any] = Field(..., description="Analysis configuration")
    
    # Time parameters
    start_date: Optional[datetime] = Field(None, description="Analysis start date")
    end_date: Optional[datetime] = Field(None, description="Analysis end date")
    time_step_minutes: int = Field(..., description="Time step in minutes")
    
    # Analysis settings
    include_weather_data: bool = Field(..., description="Include weather data")
    weather_data_source: Optional[str] = Field(None, description="Weather data source")
    resolution_meters: float = Field(..., description="Analysis resolution in meters")
    
    # Execution tracking
    started_at: Optional[datetime] = Field(None, description="Analysis start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Analysis completion timestamp")
    progress_percent: float = Field(0, ge=0, le=100, description="Progress percentage")
    
    # Results summary
    results_summary: Optional[Dict[str, Any]] = Field(None, description="Analysis results summary")
    total_shading_loss_percent: Optional[float] = Field(None, description="Total shading loss percentage")
    peak_shading_loss_percent: Optional[float] = Field(None, description="Peak shading loss percentage")
    
    # Calculation parameters
    calculation_parameters: Optional[Dict[str, Any]] = Field(None, description="Calculation parameters")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: Optional[List[str]] = Field(None, description="Analysis warnings")
    
    # Relationships (counts)
    object_count: int = Field(0, description="Number of shading objects")
    result_count: int = Field(0, description="Number of results")
    mitigation_count: int = Field(0, description="Number of mitigation strategies")
    report_count: int = Field(0, description="Number of reports")
    visualization_count: int = Field(0, description="Number of visualizations")


class ShadingObjectCreate(BaseSchema):
    """Schema for creating a shading object."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Object name")
    object_type: ShadingObjectType = Field(..., description="Type of shading object")
    description: Optional[str] = Field(None, description="Object description")
    
    # Geometry
    geometry: GeometrySchema = Field(..., description="Object geometry")
    height_m: float = Field(..., gt=0, description="Object height in meters")
    
    # Object properties
    properties: Dict[str, Any] = Field(..., description="Object-specific properties")
    
    # Shading characteristics
    transmittance: float = Field(0.0, ge=0, le=1, description="Light transmittance (0=opaque, 1=transparent)")
    reflectance: float = Field(0.1, ge=0, le=1, description="Light reflectance")
    
    # Temporal properties
    is_seasonal: bool = Field(False, description="Whether object has seasonal variations")
    seasonal_properties: Optional[Dict[str, Any]] = Field(None, description="Seasonal property variations")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Object metadata")


# Aliases for backward compatibility
ShadingAnalysis = ShadingAnalysisResponse
ShadingResult = ShadingAnalysisResponse


class ShadingObjectUpdate(BaseSchema):
    """Schema for updating a shading object."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Object name")
    object_type: Optional[ShadingObjectType] = Field(None, description="Type of shading object")
    description: Optional[str] = Field(None, description="Object description")
    
    # Geometry
    geometry: Optional[GeometrySchema] = Field(None, description="Object geometry")
    height_m: Optional[float] = Field(None, gt=0, description="Object height in meters")
    
    # Object properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Object-specific properties")
    
    # Shading characteristics
    transmittance: Optional[float] = Field(None, ge=0, le=1, description="Light transmittance")
    reflectance: Optional[float] = Field(None, ge=0, le=1, description="Light reflectance")
    
    # Temporal properties
    is_seasonal: Optional[bool] = Field(None, description="Whether object has seasonal variations")
    seasonal_properties: Optional[Dict[str, Any]] = Field(None, description="Seasonal property variations")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Object metadata")


class ShadingObjectResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for shading object response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Object name")
    object_type: ShadingObjectType = Field(..., description="Type of shading object")
    description: Optional[str] = Field(None, description="Object description")
    
    # Geometry
    geometry: GeometrySchema = Field(..., description="Object geometry")
    height_m: float = Field(..., description="Object height in meters")
    
    # Object properties
    properties: Dict[str, Any] = Field(..., description="Object-specific properties")
    
    # Shading characteristics
    transmittance: float = Field(..., description="Light transmittance")
    reflectance: float = Field(..., description="Light reflectance")
    
    # Temporal properties
    is_seasonal: bool = Field(..., description="Whether object has seasonal variations")
    seasonal_properties: Optional[Dict[str, Any]] = Field(None, description="Seasonal property variations")
    
    # Impact metrics
    affected_module_count: int = Field(0, description="Number of affected modules")
    total_shading_impact_percent: Optional[float] = Field(None, description="Total shading impact")
    peak_shading_impact_percent: Optional[float] = Field(None, description="Peak shading impact")


class ShadingResultCreate(BaseSchema):
    """Schema for creating a shading result."""
    
    timestamp: datetime = Field(..., description="Result timestamp")
    
    # Module/zone reference
    module_id: Optional[uuid.UUID] = Field(None, description="Affected module ID")
    zone_id: Optional[uuid.UUID] = Field(None, description="Affected zone ID")
    position: Optional[GeometrySchema] = Field(None, description="Result position")
    
    # Shading metrics
    shading_factor: float = Field(..., ge=0, le=1, description="Shading factor (0=no shade, 1=full shade)")
    irradiance_reduction_percent: float = Field(..., ge=0, le=100, description="Irradiance reduction percentage")
    
    # Detailed results
    direct_irradiance_wm2: Optional[float] = Field(None, ge=0, description="Direct irradiance")
    diffuse_irradiance_wm2: Optional[float] = Field(None, ge=0, description="Diffuse irradiance")
    total_irradiance_wm2: Optional[float] = Field(None, ge=0, description="Total irradiance")
    
    # Contributing objects
    contributing_objects: Optional[List[uuid.UUID]] = Field(None, description="Contributing shading objects")
    
    # Additional data
    result_data: Optional[Dict[str, Any]] = Field(None, description="Additional result data")


class ShadingResultResponse(
    UUIDSchema,
    TimestampSchema,
    MetadataSchema,
):
    """Schema for shading result response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    timestamp: datetime = Field(..., description="Result timestamp")
    
    # Module/zone reference
    module_id: Optional[uuid.UUID] = Field(None, description="Affected module ID")
    zone_id: Optional[uuid.UUID] = Field(None, description="Affected zone ID")
    position: Optional[GeometrySchema] = Field(None, description="Result position")
    
    # Shading metrics
    shading_factor: float = Field(..., description="Shading factor")
    irradiance_reduction_percent: float = Field(..., description="Irradiance reduction percentage")
    
    # Detailed results
    direct_irradiance_wm2: Optional[float] = Field(None, description="Direct irradiance")
    diffuse_irradiance_wm2: Optional[float] = Field(None, description="Diffuse irradiance")
    total_irradiance_wm2: Optional[float] = Field(None, description="Total irradiance")
    
    # Contributing objects
    contributing_objects: Optional[List[uuid.UUID]] = Field(None, description="Contributing shading objects")
    
    # Additional data
    result_data: Optional[Dict[str, Any]] = Field(None, description="Additional result data")


class ShadingMitigationCreate(BaseSchema):
    """Schema for creating a shading mitigation strategy."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Mitigation name")
    mitigation_type: MitigationType = Field(..., description="Type of mitigation")
    description: Optional[str] = Field(None, description="Mitigation description")
    
    # Mitigation configuration
    configuration: Dict[str, Any] = Field(..., description="Mitigation configuration")
    
    # Target objects/areas
    target_objects: Optional[List[uuid.UUID]] = Field(None, description="Target shading objects")
    target_geometry: Optional[GeometrySchema] = Field(None, description="Target area geometry")
    
    # Cost and feasibility
    estimated_cost: Optional[float] = Field(None, ge=0, description="Estimated implementation cost")
    feasibility_score: Optional[float] = Field(None, ge=0, le=10, description="Feasibility score (0-10)")
    implementation_time_days: Optional[int] = Field(None, gt=0, description="Implementation time in days")
    
    # Impact assessment
    expected_improvement_percent: Optional[float] = Field(None, ge=0, description="Expected improvement")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Mitigation metadata")


class ShadingMitigationUpdate(BaseSchema):
    """Schema for updating a shading mitigation strategy."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Mitigation name")
    description: Optional[str] = Field(None, description="Mitigation description")
    
    # Mitigation configuration
    configuration: Optional[Dict[str, Any]] = Field(None, description="Mitigation configuration")
    
    # Target objects/areas
    target_objects: Optional[List[uuid.UUID]] = Field(None, description="Target shading objects")
    target_geometry: Optional[GeometrySchema] = Field(None, description="Target area geometry")
    
    # Cost and feasibility
    estimated_cost: Optional[float] = Field(None, ge=0, description="Estimated implementation cost")
    feasibility_score: Optional[float] = Field(None, ge=0, le=10, description="Feasibility score")
    implementation_time_days: Optional[int] = Field(None, gt=0, description="Implementation time in days")
    
    # Impact assessment
    expected_improvement_percent: Optional[float] = Field(None, ge=0, description="Expected improvement")
    actual_improvement_percent: Optional[float] = Field(None, ge=0, description="Actual improvement")
    
    # Implementation status
    is_implemented: Optional[bool] = Field(None, description="Whether mitigation is implemented")
    implementation_date: Optional[datetime] = Field(None, description="Implementation date")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Mitigation metadata")


class ShadingMitigationResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for shading mitigation response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Mitigation name")
    mitigation_type: MitigationType = Field(..., description="Type of mitigation")
    description: Optional[str] = Field(None, description="Mitigation description")
    
    # Mitigation configuration
    configuration: Dict[str, Any] = Field(..., description="Mitigation configuration")
    
    # Target objects/areas
    target_objects: Optional[List[uuid.UUID]] = Field(None, description="Target shading objects")
    target_geometry: Optional[GeometrySchema] = Field(None, description="Target area geometry")
    
    # Cost and feasibility
    estimated_cost: Optional[float] = Field(None, description="Estimated implementation cost")
    feasibility_score: Optional[float] = Field(None, description="Feasibility score")
    implementation_time_days: Optional[int] = Field(None, description="Implementation time in days")
    
    # Impact assessment
    expected_improvement_percent: Optional[float] = Field(None, description="Expected improvement")
    actual_improvement_percent: Optional[float] = Field(None, description="Actual improvement")
    
    # Implementation status
    is_implemented: bool = Field(False, description="Whether mitigation is implemented")
    implementation_date: Optional[datetime] = Field(None, description="Implementation date")
    
    # ROI calculation
    roi_years: Optional[float] = Field(None, description="Return on investment in years")
    cost_benefit_ratio: Optional[float] = Field(None, description="Cost-benefit ratio")


class ShadingReportCreate(BaseSchema):
    """Schema for creating a shading report."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Report name")
    report_format: ReportFormat = Field(..., description="Report format")
    description: Optional[str] = Field(None, description="Report description")
    
    # Report configuration
    include_summary: bool = Field(True, description="Include executive summary")
    include_detailed_results: bool = Field(True, description="Include detailed results")
    include_visualizations: bool = Field(True, description="Include visualizations")
    include_mitigation_strategies: bool = Field(True, description="Include mitigation strategies")
    include_recommendations: bool = Field(True, description="Include recommendations")
    
    # Report customization
    template_id: Optional[uuid.UUID] = Field(None, description="Report template ID")
    custom_sections: Optional[List[Dict[str, Any]]] = Field(None, description="Custom report sections")
    
    # Output settings
    language: str = Field("en", max_length=5, description="Report language")
    include_raw_data: bool = Field(False, description="Include raw data")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Report metadata")


class ShadingReportResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for shading report response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Report name")
    report_format: ReportFormat = Field(..., description="Report format")
    description: Optional[str] = Field(None, description="Report description")
    
    # Report status
    is_generated: bool = Field(False, description="Whether report is generated")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    file_path: Optional[str] = Field(None, description="Generated file path")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    
    # Report configuration
    include_summary: bool = Field(..., description="Include executive summary")
    include_detailed_results: bool = Field(..., description="Include detailed results")
    include_visualizations: bool = Field(..., description="Include visualizations")
    include_mitigation_strategies: bool = Field(..., description="Include mitigation strategies")
    include_recommendations: bool = Field(..., description="Include recommendations")
    
    # Report customization
    template_id: Optional[uuid.UUID] = Field(None, description="Report template ID")
    custom_sections: Optional[List[Dict[str, Any]]] = Field(None, description="Custom report sections")
    
    # Output settings
    language: str = Field(..., description="Report language")
    include_raw_data: bool = Field(..., description="Include raw data")
    
    # Download tracking
    download_count: int = Field(0, description="Number of downloads")
    last_downloaded_at: Optional[datetime] = Field(None, description="Last download timestamp")


class ShadingVisualizationCreate(BaseSchema):
    """Schema for creating a shading visualization."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Visualization name")
    visualization_type: VisualizationType = Field(..., description="Type of visualization")
    description: Optional[str] = Field(None, description="Visualization description")
    
    # Visualization configuration
    config: Dict[str, Any] = Field(..., description="Visualization configuration")
    
    # Time parameters
    timestamp: Optional[datetime] = Field(None, description="Specific timestamp for visualization")
    time_range_start: Optional[datetime] = Field(None, description="Time range start")
    time_range_end: Optional[datetime] = Field(None, description="Time range end")
    
    # Rendering settings
    resolution_width: int = Field(1920, gt=0, description="Image width in pixels")
    resolution_height: int = Field(1080, gt=0, description="Image height in pixels")
    quality: str = Field("high", description="Rendering quality")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Visualization metadata")


class ShadingVisualizationResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for shading visualization response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Visualization name")
    visualization_type: VisualizationType = Field(..., description="Type of visualization")
    description: Optional[str] = Field(None, description="Visualization description")
    
    # Visualization status
    is_generated: bool = Field(False, description="Whether visualization is generated")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    image_path: Optional[str] = Field(None, description="Generated image path")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    
    # Visualization configuration
    config: Dict[str, Any] = Field(..., description="Visualization configuration")
    
    # Time parameters
    timestamp: Optional[datetime] = Field(None, description="Specific timestamp for visualization")
    time_range_start: Optional[datetime] = Field(None, description="Time range start")
    time_range_end: Optional[datetime] = Field(None, description="Time range end")
    
    # Rendering settings
    resolution_width: int = Field(..., description="Image width in pixels")
    resolution_height: int = Field(..., description="Image height in pixels")
    quality: str = Field(..., description="Rendering quality")
    
    # Usage tracking
    view_count: int = Field(0, description="Number of views")
    last_viewed_at: Optional[datetime] = Field(None, description="Last view timestamp")


class ShadingFilterParams(FilterParams):
    """Shading-specific filtering parameters."""
    
    analysis_type: Optional[AnalysisType] = Field(None, description="Filter by analysis type")
    status: Optional[AnalysisStatus] = Field(None, description="Filter by status")
    design_id: Optional[uuid.UUID] = Field(None, description="Filter by design")
    layout_id: Optional[uuid.UUID] = Field(None, description="Filter by layout")
    project_id: Optional[uuid.UUID] = Field(None, description="Filter by project")
    created_by: Optional[uuid.UUID] = Field(None, description="Filter by creator")
    min_shading_loss: Optional[float] = Field(None, ge=0, description="Minimum shading loss percentage")
    max_shading_loss: Optional[float] = Field(None, ge=0, description="Maximum shading loss percentage")
    has_mitigation: Optional[bool] = Field(None, description="Filter by mitigation availability")


class ShadingAnalysisRequest(BaseSchema):
    """Schema for requesting shading analysis."""
    
    analysis_type: AnalysisType = Field(..., description="Type of analysis")
    priority: str = Field("normal", description="Analysis priority")
    
    # Time parameters
    analysis_period_days: int = Field(365, gt=0, le=365, description="Analysis period in days")
    time_step_minutes: int = Field(60, gt=0, le=1440, description="Time step in minutes")
    
    # Analysis settings
    include_weather_data: bool = Field(True, description="Include weather data")
    weather_data_source: Optional[str] = Field(None, description="Weather data source")
    resolution_meters: float = Field(1.0, gt=0, description="Analysis resolution")
    
    # Advanced settings
    include_inter_row_shading: bool = Field(True, description="Include inter-row shading")
    include_near_field_shading: bool = Field(True, description="Include near-field shading")
    include_far_field_shading: bool = Field(False, description="Include far-field shading")
    
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class ShadingAnalysisStatusResponse(BaseSchema):
    """Schema for shading analysis status response."""
    
    analysis_id: uuid.UUID = Field(..., description="Analysis ID")
    status: AnalysisStatus = Field(..., description="Current status")
    progress_percent: float = Field(..., description="Progress percentage")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    current_step: Optional[str] = Field(None, description="Current processing step")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(..., description="Analysis warnings")


class ShadingImpactSummary(BaseSchema):
    """Schema for shading impact summary."""
    
    total_modules_affected: int = Field(..., description="Total modules affected by shading")
    total_shading_loss_percent: float = Field(..., description="Total shading loss percentage")
    peak_shading_loss_percent: float = Field(..., description="Peak shading loss percentage")
    average_shading_loss_percent: float = Field(..., description="Average shading loss percentage")
    
    # Time-based analysis
    worst_shading_time: Optional[time] = Field(None, description="Time of worst shading")
    worst_shading_month: Optional[int] = Field(None, description="Month with worst shading")
    
    # Impact by object type
    impact_by_object_type: Dict[str, float] = Field(..., description="Impact breakdown by object type")
    
    # Mitigation potential
    mitigation_potential_percent: Optional[float] = Field(None, description="Potential improvement from mitigation")
    recommended_mitigations: List[str] = Field(..., description="Recommended mitigation strategies")


class ShadingTimeSeriesRequest(BaseSchema):
    """Schema for shading time series analysis request."""
    
    start_date: datetime = Field(..., description="Start date for time series")
    end_date: datetime = Field(..., description="End date for time series")
    time_step_minutes: int = Field(60, gt=0, le=1440, description="Time step in minutes")
    
    # Aggregation settings
    aggregation_level: str = Field("hourly", description="Aggregation level (hourly, daily, monthly)")
    include_weather_correlation: bool = Field(True, description="Include weather correlation")
    
    # Output format
    output_format: str = Field("json", description="Output format (json, csv)")
    include_metadata: bool = Field(True, description="Include metadata in output")


class ShadingTimeSeriesResponse(BaseSchema):
    """Schema for shading time series analysis response."""
    
    analysis_id: uuid.UUID = Field(..., description="Analysis ID")
    time_series_data: List[Dict[str, Any]] = Field(..., description="Time series data points")
    summary_statistics: Dict[str, Any] = Field(..., description="Summary statistics")
    weather_correlation: Optional[Dict[str, Any]] = Field(None, description="Weather correlation data")
    data_quality_metrics: Dict[str, Any] = Field(..., description="Data quality metrics")


class ShadingAnalysisResults(BaseSchema):
    """Schema for shading analysis results."""
    
    analysis_id: uuid.UUID = Field(..., description="Analysis ID")
    total_shading_loss_percent: float = Field(..., description="Total shading loss percentage")
    peak_shading_loss_percent: float = Field(..., description="Peak shading loss percentage")
    average_shading_loss_percent: float = Field(..., description="Average shading loss percentage")
    shading_impact_summary: ShadingImpactSummary = Field(..., description="Shading impact summary")
    detailed_results: Dict[str, Any] = Field(..., description="Detailed analysis results")
    recommendations: List[str] = Field(..., description="Analysis recommendations")
    warnings: List[str] = Field(..., description="Analysis warnings")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Results metadata")


class ShadingOptimizationRequest(BaseSchema):
    """Schema for shading optimization request."""
    
    analysis_id: uuid.UUID = Field(..., description="Base analysis ID")
    optimization_type: str = Field(..., description="Type of optimization")
    target_improvement_percent: Optional[float] = Field(None, description="Target improvement percentage")
    constraints: Dict[str, Any] = Field(..., description="Optimization constraints")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optimization parameters")
    max_iterations: int = Field(100, gt=0, description="Maximum optimization iterations")
    convergence_threshold: float = Field(0.01, gt=0, description="Convergence threshold")


class ShadingOptimizationResult(BaseSchema):
    """Schema for shading optimization result."""
    
    optimization_id: uuid.UUID = Field(..., description="Optimization ID")
    original_analysis_id: uuid.UUID = Field(..., description="Original analysis ID")
    optimized_analysis_id: Optional[uuid.UUID] = Field(None, description="Optimized analysis ID")
    improvement_percent: float = Field(..., description="Achieved improvement percentage")
    optimization_steps: List[Dict[str, Any]] = Field(..., description="Optimization steps taken")
    final_configuration: Dict[str, Any] = Field(..., description="Final optimized configuration")
    convergence_achieved: bool = Field(..., description="Whether convergence was achieved")
    iterations_completed: int = Field(..., description="Number of iterations completed")
    execution_time_seconds: float = Field(..., description="Optimization execution time")
    recommendations: List[str] = Field(..., description="Optimization recommendations")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optimization metadata")


class ShadingAnalysisListResponse(BaseSchema):
    """Schema for shading analysis list response."""
    
    analyses: List[ShadingAnalysisResponse] = Field(..., description="List of shading analyses")
    total: int = Field(..., description="Total number of analyses")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    sort_by: str = Field(..., description="Sort field")
    sort_order: str = Field(..., description="Sort order")


class ObstacleCreate(BaseSchema):
    """Schema for creating obstacles."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Obstacle name")
    obstacle_type: str = Field(..., description="Type of obstacle")
    description: Optional[str] = Field(None, description="Obstacle description")
    
    # Geometry and positioning
    geometry: GeometrySchema = Field(..., description="Obstacle geometry")
    height_m: float = Field(..., gt=0, description="Obstacle height in meters")
    elevation_m: Optional[float] = Field(None, description="Ground elevation in meters")
    
    # Physical properties
    transmittance: float = Field(0.0, ge=0, le=1, description="Light transmittance")
    reflectance: float = Field(0.1, ge=0, le=1, description="Light reflectance")
    
    # Temporal properties
    is_permanent: bool = Field(True, description="Whether obstacle is permanent")
    seasonal_variation: Optional[Dict[str, Any]] = Field(None, description="Seasonal variations")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Obstacle metadata")


class ObstacleUpdate(BaseSchema):
    """Schema for updating obstacles."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Obstacle name")
    obstacle_type: Optional[str] = Field(None, description="Type of obstacle")
    description: Optional[str] = Field(None, description="Obstacle description")
    
    # Geometry and positioning
    geometry: Optional[GeometrySchema] = Field(None, description="Obstacle geometry")
    height_m: Optional[float] = Field(None, gt=0, description="Obstacle height in meters")
    elevation_m: Optional[float] = Field(None, description="Ground elevation in meters")
    
    # Physical properties
    transmittance: Optional[float] = Field(None, ge=0, le=1, description="Light transmittance")
    reflectance: Optional[float] = Field(None, ge=0, le=1, description="Light reflectance")
    
    # Temporal properties
    is_permanent: Optional[bool] = Field(None, description="Whether obstacle is permanent")
    seasonal_variation: Optional[Dict[str, Any]] = Field(None, description="Seasonal variations")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Obstacle metadata")


class ObstacleResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for obstacle response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Obstacle name")
    obstacle_type: str = Field(..., description="Type of obstacle")
    description: Optional[str] = Field(None, description="Obstacle description")
    
    # Geometry and positioning
    geometry: GeometrySchema = Field(..., description="Obstacle geometry")
    height_m: float = Field(..., description="Obstacle height in meters")
    elevation_m: Optional[float] = Field(None, description="Ground elevation in meters")
    
    # Physical properties
    transmittance: float = Field(..., description="Light transmittance")
    reflectance: float = Field(..., description="Light reflectance")
    
    # Temporal properties
    is_permanent: bool = Field(..., description="Whether obstacle is permanent")
    seasonal_variation: Optional[Dict[str, Any]] = Field(None, description="Seasonal variations")
    
    # Impact analysis
    shading_impact_percent: Optional[float] = Field(None, description="Shading impact percentage")
    affected_modules_count: Optional[int] = Field(None, description="Number of affected modules")
    
    # Status
    is_active: bool = Field(True, description="Whether obstacle is active")
    status: str = Field(..., description="Obstacle status")


class SolarPositionCreate(BaseSchema):
    """Schema for creating solar position data."""
    
    timestamp: datetime = Field(..., description="Timestamp for solar position")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    timezone: str = Field(..., description="Timezone identifier")
    
    # Optional atmospheric parameters
    atmospheric_pressure_pa: Optional[float] = Field(None, gt=0, description="Atmospheric pressure in Pa")
    temperature_c: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity_percent: Optional[float] = Field(None, ge=0, le=100, description="Relative humidity percentage")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Solar position metadata")


class SolarPositionResponse(
    UUIDSchema,
    TimestampSchema,
    MetadataSchema,
):
    """Schema for solar position response."""
    
    timestamp: datetime = Field(..., description="Timestamp for solar position")
    latitude: float = Field(..., description="Latitude in degrees")
    longitude: float = Field(..., description="Longitude in degrees")
    timezone: str = Field(..., description="Timezone identifier")
    
    # Calculated solar position
    solar_elevation_deg: float = Field(..., description="Solar elevation angle in degrees")
    solar_azimuth_deg: float = Field(..., description="Solar azimuth angle in degrees")
    solar_zenith_deg: float = Field(..., description="Solar zenith angle in degrees")
    
    # Solar time
    solar_time: time = Field(..., description="Solar time")
    equation_of_time_minutes: float = Field(..., description="Equation of time in minutes")
    
    # Sun characteristics
    sunrise_time: Optional[time] = Field(None, description="Sunrise time")
    sunset_time: Optional[time] = Field(None, description="Sunset time")
    day_length_hours: Optional[float] = Field(None, description="Day length in hours")
    
    # Atmospheric parameters
    atmospheric_pressure_pa: Optional[float] = Field(None, description="Atmospheric pressure in Pa")
    temperature_c: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity_percent: Optional[float] = Field(None, description="Relative humidity percentage")
    
    # Solar irradiance
    direct_normal_irradiance: Optional[float] = Field(None, description="Direct normal irradiance")
    diffuse_horizontal_irradiance: Optional[float] = Field(None, description="Diffuse horizontal irradiance")
    global_horizontal_irradiance: Optional[float] = Field(None, description="Global horizontal irradiance")


class ShadingResultResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for shading result response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    timestamp: datetime = Field(..., description="Result timestamp")
    
    # Shading metrics
    total_shading_loss_percent: float = Field(..., description="Total shading loss percentage")
    direct_shading_loss_percent: float = Field(..., description="Direct shading loss percentage")
    diffuse_shading_loss_percent: float = Field(..., description="Diffuse shading loss percentage")
    
    # Module-level results
    module_results: List[Dict[str, Any]] = Field(..., description="Per-module shading results")
    
    # Irradiance data
    incident_irradiance: float = Field(..., description="Incident irradiance")
    shaded_irradiance: float = Field(..., description="Shaded irradiance")
    
    # Environmental conditions
    solar_elevation_deg: float = Field(..., description="Solar elevation angle")
    solar_azimuth_deg: float = Field(..., description="Solar azimuth angle")
    
    # Quality metrics
    calculation_accuracy: Optional[float] = Field(None, description="Calculation accuracy")
    confidence_level: Optional[float] = Field(None, description="Confidence level")


class IrradianceMapCreate(BaseSchema):
    """Schema for creating irradiance maps."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Map name")
    description: Optional[str] = Field(None, description="Map description")
    
    # Time parameters
    timestamp: datetime = Field(..., description="Timestamp for irradiance map")
    duration_hours: Optional[float] = Field(None, gt=0, description="Duration in hours")
    
    # Spatial parameters
    bounds: GeometrySchema = Field(..., description="Map bounds geometry")
    resolution_m: float = Field(1.0, gt=0, description="Spatial resolution in meters")
    
    # Calculation settings
    include_diffuse: bool = Field(True, description="Include diffuse irradiance")
    include_reflected: bool = Field(True, description="Include reflected irradiance")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Map metadata")


class IrradianceMapResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for irradiance map response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Map name")
    description: Optional[str] = Field(None, description="Map description")
    
    # Time parameters
    timestamp: datetime = Field(..., description="Timestamp for irradiance map")
    duration_hours: Optional[float] = Field(None, description="Duration in hours")
    
    # Spatial parameters
    bounds: GeometrySchema = Field(..., description="Map bounds geometry")
    resolution_m: float = Field(..., description="Spatial resolution in meters")
    
    # Map data
    irradiance_data: List[List[float]] = Field(..., description="2D irradiance data array")
    min_irradiance: float = Field(..., description="Minimum irradiance value")
    max_irradiance: float = Field(..., description="Maximum irradiance value")
    mean_irradiance: float = Field(..., description="Mean irradiance value")
    
    # Calculation settings
    include_diffuse: bool = Field(..., description="Include diffuse irradiance")
    include_reflected: bool = Field(..., description="Include reflected irradiance")
    
    # File information
    file_path: Optional[str] = Field(None, description="Generated file path")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    
    # Status
    is_generated: bool = Field(False, description="Whether map is generated")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")


class SunPathCreate(BaseSchema):
    """Schema for creating sun path data."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Sun path name")
    description: Optional[str] = Field(None, description="Sun path description")
    
    # Location parameters
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    timezone: str = Field(..., description="Timezone identifier")
    
    # Time parameters
    start_date: datetime = Field(..., description="Start date for sun path")
    end_date: datetime = Field(..., description="End date for sun path")
    time_step_minutes: int = Field(60, gt=0, le=1440, description="Time step in minutes")
    
    # Calculation settings
    include_analemma: bool = Field(True, description="Include analemma curves")
    include_hour_lines: bool = Field(True, description="Include hour lines")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Sun path metadata")


class SunPathResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for sun path response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Sun path name")
    description: Optional[str] = Field(None, description="Sun path description")
    
    # Location parameters
    latitude: float = Field(..., description="Latitude in degrees")
    longitude: float = Field(..., description="Longitude in degrees")
    timezone: str = Field(..., description="Timezone identifier")
    
    # Time parameters
    start_date: datetime = Field(..., description="Start date for sun path")
    end_date: datetime = Field(..., description="End date for sun path")
    time_step_minutes: int = Field(..., description="Time step in minutes")
    
    # Sun path data
    sun_positions: List[Dict[str, Any]] = Field(..., description="Sun position data points")
    analemma_curves: Optional[List[Dict[str, Any]]] = Field(None, description="Analemma curve data")
    hour_lines: Optional[List[Dict[str, Any]]] = Field(None, description="Hour line data")
    
    # Calculation settings
    include_analemma: bool = Field(..., description="Include analemma curves")
    include_hour_lines: bool = Field(..., description="Include hour lines")
    
    # Summary statistics
    total_data_points: int = Field(..., description="Total number of data points")
    min_elevation_deg: float = Field(..., description="Minimum elevation angle")
    max_elevation_deg: float = Field(..., description="Maximum elevation angle")
    
    # File information
    file_path: Optional[str] = Field(None, description="Generated file path")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    
    # Status
    is_generated: bool = Field(False, description="Whether sun path is generated")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")


class ShadingReportResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for shading report response."""
    
    analysis_id: uuid.UUID = Field(..., description="Parent analysis ID")
    name: str = Field(..., description="Report name")
    report_type: str = Field(..., description="Type of report")
    description: Optional[str] = Field(None, description="Report description")
    
    # Report content
    executive_summary: str = Field(..., description="Executive summary")
    detailed_analysis: Dict[str, Any] = Field(..., description="Detailed analysis results")
    recommendations: List[str] = Field(..., description="Recommendations")
    
    # Report format
    format: ReportFormat = Field(..., description="Report format")
    
    # File information
    file_path: Optional[str] = Field(None, description="Generated report file path")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    
    # Generation status
    is_generated: bool = Field(False, description="Whether report is generated")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    
    # Usage tracking
    download_count: int = Field(0, description="Number of downloads")
    last_downloaded_at: Optional[datetime] = Field(None, description="Last download timestamp")
    
    # Quality metrics
    completeness_score: Optional[float] = Field(None, ge=0, le=1, description="Report completeness score")
    accuracy_score: Optional[float] = Field(None, ge=0, le=1, description="Report accuracy score")