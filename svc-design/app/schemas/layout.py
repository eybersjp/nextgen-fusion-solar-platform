"""Layout schemas for the Design Service.

This module contains Pydantic schemas for layout-related request/response models,
including layouts, zones, modules, optimizations, templates, and constraints.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from ..models.layout import (
    ConstraintType,
    LayoutStatus,
    ModuleOrientation,
    OptimizationObjective,
    OptimizationStatus,
    ZoneType,
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


class LayoutBase(BaseSchema):
    """Base layout schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Layout name")
    description: Optional[str] = Field(None, description="Layout description")
    status: LayoutStatus = Field(LayoutStatus.DRAFT, description="Layout status")


class LayoutCreate(LayoutBase, ProjectSchema, MetadataSchema):
    """Schema for creating a new layout."""
    
    design_id: uuid.UUID = Field(..., description="Associated design ID")
    
    # Layout specifications
    total_area_sqm: Optional[float] = Field(None, gt=0, description="Total layout area")
    usable_area_sqm: Optional[float] = Field(None, gt=0, description="Usable area")
    module_count: Optional[int] = Field(None, gt=0, description="Total number of modules")
    total_capacity_kw: Optional[float] = Field(None, gt=0, description="Total capacity")
    
    # Geometry
    boundary_geometry: Optional[GeometrySchema] = Field(None, description="Layout boundary")
    site_geometry: Optional[GeometrySchema] = Field(None, description="Site geometry")
    
    # Performance metrics
    ground_coverage_ratio: Optional[float] = Field(None, ge=0, le=1, description="Ground coverage ratio")
    dc_ac_ratio: Optional[float] = Field(None, gt=0, description="DC/AC ratio")
    specific_yield_kwh_kwp: Optional[float] = Field(None, gt=0, description="Specific yield")
    
    # Layout data
    layout_data: Optional[Dict[str, Any]] = Field(None, description="Layout-specific data")
    
    # Template reference
    template_id: Optional[uuid.UUID] = Field(None, description="Layout template ID")


class LayoutUpdate(BaseSchema):
    """Schema for updating an existing layout."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Layout name")
    description: Optional[str] = Field(None, description="Layout description")
    status: Optional[LayoutStatus] = Field(None, description="Layout status")
    
    # Layout specifications
    total_area_sqm: Optional[float] = Field(None, gt=0, description="Total layout area")
    usable_area_sqm: Optional[float] = Field(None, gt=0, description="Usable area")
    module_count: Optional[int] = Field(None, gt=0, description="Total number of modules")
    total_capacity_kw: Optional[float] = Field(None, gt=0, description="Total capacity")
    
    # Geometry
    boundary_geometry: Optional[GeometrySchema] = Field(None, description="Layout boundary")
    site_geometry: Optional[GeometrySchema] = Field(None, description="Site geometry")
    
    # Performance metrics
    ground_coverage_ratio: Optional[float] = Field(None, ge=0, le=1, description="Ground coverage ratio")
    dc_ac_ratio: Optional[float] = Field(None, gt=0, description="DC/AC ratio")
    specific_yield_kwh_kwp: Optional[float] = Field(None, gt=0, description="Specific yield")
    
    # Layout data
    layout_data: Optional[Dict[str, Any]] = Field(None, description="Layout-specific data")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class LayoutResponse(
    LayoutBase,
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    ProjectSchema,
    MetadataSchema,
):
    """Schema for layout response."""
    
    design_id: uuid.UUID = Field(..., description="Associated design ID")
    
    # Layout specifications
    total_area_sqm: Optional[float] = Field(None, description="Total layout area")
    usable_area_sqm: Optional[float] = Field(None, description="Usable area")
    module_count: Optional[int] = Field(None, description="Total number of modules")
    total_capacity_kw: Optional[float] = Field(None, description="Total capacity")
    
    # Geometry
    boundary_geometry: Optional[GeometrySchema] = Field(None, description="Layout boundary")
    site_geometry: Optional[GeometrySchema] = Field(None, description="Site geometry")
    
    # Performance metrics
    ground_coverage_ratio: Optional[float] = Field(None, description="Ground coverage ratio")
    dc_ac_ratio: Optional[float] = Field(None, description="DC/AC ratio")
    specific_yield_kwh_kwp: Optional[float] = Field(None, description="Specific yield")
    
    # Optimization results
    optimization_score: Optional[float] = Field(None, description="Optimization score")
    optimization_results: Optional[Dict[str, Any]] = Field(None, description="Optimization results")
    
    # Layout data
    layout_data: Optional[Dict[str, Any]] = Field(None, description="Layout-specific data")
    
    # Template reference
    template_id: Optional[uuid.UUID] = Field(None, description="Layout template ID")
    
    # Relationships (counts)
    zone_count: int = Field(0, description="Number of zones")
    module_count_actual: int = Field(0, description="Actual number of modules placed")
    constraint_count: int = Field(0, description="Number of constraints")
    optimization_count: int = Field(0, description="Number of optimizations run")


class LayoutZoneCreate(BaseSchema):
    """Schema for creating a layout zone."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Zone name")
    zone_type: ZoneType = Field(..., description="Type of zone")
    description: Optional[str] = Field(None, description="Zone description")
    
    # Geometry
    geometry: GeometrySchema = Field(..., description="Zone geometry")
    
    # Zone specifications
    area_sqm: Optional[float] = Field(None, gt=0, description="Zone area")
    module_count: Optional[int] = Field(None, gt=0, description="Number of modules in zone")
    capacity_kw: Optional[float] = Field(None, gt=0, description="Zone capacity")
    
    # Zone properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Zone-specific properties")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Zone metadata")


class LayoutZoneUpdate(BaseSchema):
    """Schema for updating a layout zone."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Zone name")
    zone_type: Optional[ZoneType] = Field(None, description="Type of zone")
    description: Optional[str] = Field(None, description="Zone description")
    
    # Geometry
    geometry: Optional[GeometrySchema] = Field(None, description="Zone geometry")
    
    # Zone specifications
    area_sqm: Optional[float] = Field(None, gt=0, description="Zone area")
    module_count: Optional[int] = Field(None, gt=0, description="Number of modules in zone")
    capacity_kw: Optional[float] = Field(None, gt=0, description="Zone capacity")
    
    # Zone properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Zone-specific properties")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Zone metadata")


class LayoutZoneResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for layout zone response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., description="Zone name")
    zone_type: ZoneType = Field(..., description="Type of zone")
    description: Optional[str] = Field(None, description="Zone description")
    
    # Geometry
    geometry: GeometrySchema = Field(..., description="Zone geometry")
    
    # Zone specifications
    area_sqm: Optional[float] = Field(None, description="Zone area")
    module_count: Optional[int] = Field(None, description="Number of modules in zone")
    capacity_kw: Optional[float] = Field(None, description="Zone capacity")
    
    # Zone properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Zone-specific properties")
    
    # Module count
    actual_module_count: int = Field(0, description="Actual number of modules placed")


class LayoutModuleCreate(BaseSchema):
    """Schema for creating a layout module."""
    
    zone_id: Optional[uuid.UUID] = Field(None, description="Zone ID (if in a zone)")
    
    # Module position and orientation
    position: GeometrySchema = Field(..., description="Module position")
    orientation: ModuleOrientation = Field(..., description="Module orientation")
    tilt_angle: float = Field(..., ge=0, le=90, description="Tilt angle in degrees")
    azimuth_angle: float = Field(..., ge=0, lt=360, description="Azimuth angle in degrees")
    
    # Module specifications
    module_type: str = Field(..., max_length=100, description="Module type/model")
    power_rating_w: float = Field(..., gt=0, description="Module power rating in watts")
    efficiency: Optional[float] = Field(None, ge=0, le=1, description="Module efficiency")
    
    # Module properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Module-specific properties")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Module metadata")


class LayoutModuleUpdate(BaseSchema):
    """Schema for updating a layout module."""
    
    zone_id: Optional[uuid.UUID] = Field(None, description="Zone ID (if in a zone)")
    
    # Module position and orientation
    position: Optional[GeometrySchema] = Field(None, description="Module position")
    orientation: Optional[ModuleOrientation] = Field(None, description="Module orientation")
    tilt_angle: Optional[float] = Field(None, ge=0, le=90, description="Tilt angle in degrees")
    azimuth_angle: Optional[float] = Field(None, ge=0, lt=360, description="Azimuth angle in degrees")
    
    # Module specifications
    module_type: Optional[str] = Field(None, max_length=100, description="Module type/model")
    power_rating_w: Optional[float] = Field(None, gt=0, description="Module power rating in watts")
    efficiency: Optional[float] = Field(None, ge=0, le=1, description="Module efficiency")
    
    # Module properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Module-specific properties")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Module metadata")


class LayoutModuleResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for layout module response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    zone_id: Optional[uuid.UUID] = Field(None, description="Zone ID (if in a zone)")
    
    # Module position and orientation
    position: GeometrySchema = Field(..., description="Module position")
    orientation: ModuleOrientation = Field(..., description="Module orientation")
    tilt_angle: float = Field(..., description="Tilt angle in degrees")
    azimuth_angle: float = Field(..., description="Azimuth angle in degrees")
    
    # Module specifications
    module_type: str = Field(..., description="Module type/model")
    power_rating_w: float = Field(..., description="Module power rating in watts")
    efficiency: Optional[float] = Field(None, description="Module efficiency")
    
    # Module properties
    properties: Optional[Dict[str, Any]] = Field(None, description="Module-specific properties")
    
    # Performance metrics
    annual_energy_kwh: Optional[float] = Field(None, description="Annual energy production")
    capacity_factor: Optional[float] = Field(None, description="Capacity factor")
    shading_factor: Optional[float] = Field(None, description="Shading factor")


class LayoutOptimizationCreate(BaseSchema):
    """Schema for creating a layout optimization."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Optimization name")
    description: Optional[str] = Field(None, description="Optimization description")
    
    # Optimization configuration
    objective: OptimizationObjective = Field(..., description="Optimization objective")
    parameters: Dict[str, Any] = Field(..., description="Optimization parameters")
    constraints: Optional[List[Dict[str, Any]]] = Field(None, description="Optimization constraints")
    
    # Execution settings
    max_iterations: int = Field(100, gt=0, le=10000, description="Maximum iterations")
    convergence_threshold: float = Field(0.001, gt=0, description="Convergence threshold")
    timeout_minutes: int = Field(60, gt=0, le=1440, description="Timeout in minutes")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optimization metadata")


class LayoutOptimizationUpdate(BaseSchema):
    """Schema for updating a layout optimization."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Optimization name")
    description: Optional[str] = Field(None, description="Optimization description")
    status: Optional[OptimizationStatus] = Field(None, description="Optimization status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optimization metadata")


class LayoutOptimizationResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for layout optimization response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., description="Optimization name")
    description: Optional[str] = Field(None, description="Optimization description")
    
    # Optimization configuration
    objective: OptimizationObjective = Field(..., description="Optimization objective")
    status: OptimizationStatus = Field(..., description="Optimization status")
    parameters: Dict[str, Any] = Field(..., description="Optimization parameters")
    constraints: Optional[List[Dict[str, Any]]] = Field(None, description="Optimization constraints")
    
    # Execution settings
    max_iterations: int = Field(..., description="Maximum iterations")
    convergence_threshold: float = Field(..., description="Convergence threshold")
    timeout_minutes: int = Field(..., description="Timeout in minutes")
    
    # Execution tracking
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    progress_percent: float = Field(0, ge=0, le=100, description="Progress percentage")
    current_iteration: int = Field(0, description="Current iteration")
    
    # Results
    results: Optional[Dict[str, Any]] = Field(None, description="Optimization results")
    best_score: Optional[float] = Field(None, description="Best optimization score")
    convergence_history: Optional[List[float]] = Field(None, description="Convergence history")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: Optional[List[str]] = Field(None, description="Optimization warnings")


class LayoutTemplateCreate(BaseSchema):
    """Schema for creating a layout template."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(..., max_length=100, description="Template category")
    
    # Template configuration
    template_data: Dict[str, Any] = Field(..., description="Template configuration data")
    default_parameters: Optional[Dict[str, Any]] = Field(None, description="Default parameters")
    
    # Applicability
    min_area_sqm: Optional[float] = Field(None, gt=0, description="Minimum applicable area")
    max_area_sqm: Optional[float] = Field(None, gt=0, description="Maximum applicable area")
    applicable_regions: Optional[List[str]] = Field(None, description="Applicable regions")
    
    # Template properties
    is_public: bool = Field(False, description="Whether template is public")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")


class LayoutTemplateUpdate(BaseSchema):
    """Schema for updating a layout template."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: Optional[str] = Field(None, max_length=100, description="Template category")
    
    # Template configuration
    template_data: Optional[Dict[str, Any]] = Field(None, description="Template configuration data")
    default_parameters: Optional[Dict[str, Any]] = Field(None, description="Default parameters")
    
    # Applicability
    min_area_sqm: Optional[float] = Field(None, gt=0, description="Minimum applicable area")
    max_area_sqm: Optional[float] = Field(None, gt=0, description="Maximum applicable area")
    applicable_regions: Optional[List[str]] = Field(None, description="Applicable regions")
    
    # Template properties
    is_public: Optional[bool] = Field(None, description="Whether template is public")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")


class LayoutTemplateResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    MetadataSchema,
):
    """Schema for layout template response."""
    
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(..., description="Template category")
    
    # Template configuration
    template_data: Dict[str, Any] = Field(..., description="Template configuration data")
    default_parameters: Optional[Dict[str, Any]] = Field(None, description="Default parameters")
    
    # Applicability
    min_area_sqm: Optional[float] = Field(None, description="Minimum applicable area")
    max_area_sqm: Optional[float] = Field(None, description="Maximum applicable area")
    applicable_regions: Optional[List[str]] = Field(None, description="Applicable regions")
    
    # Template properties
    is_public: bool = Field(..., description="Whether template is public")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    
    # Usage statistics
    usage_count: int = Field(0, description="Number of times used")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    rating: Optional[float] = Field(None, description="Average user rating")
    rating_count: int = Field(0, description="Number of ratings")


class LayoutConstraintCreate(BaseSchema):
    """Schema for creating a layout constraint."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Constraint name")
    constraint_type: ConstraintType = Field(..., description="Type of constraint")
    description: Optional[str] = Field(None, description="Constraint description")
    
    # Constraint configuration
    parameters: Dict[str, Any] = Field(..., description="Constraint parameters")
    geometry: Optional[GeometrySchema] = Field(None, description="Constraint geometry")
    
    # Constraint properties
    is_hard_constraint: bool = Field(True, description="Whether constraint is hard or soft")
    priority: int = Field(1, ge=1, le=10, description="Constraint priority (1-10)")
    weight: float = Field(1.0, gt=0, description="Constraint weight for optimization")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Constraint metadata")


class LayoutConstraintUpdate(BaseSchema):
    """Schema for updating a layout constraint."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Constraint name")
    description: Optional[str] = Field(None, description="Constraint description")
    
    # Constraint configuration
    parameters: Optional[Dict[str, Any]] = Field(None, description="Constraint parameters")
    geometry: Optional[GeometrySchema] = Field(None, description="Constraint geometry")
    
    # Constraint properties
    is_hard_constraint: Optional[bool] = Field(None, description="Whether constraint is hard or soft")
    priority: Optional[int] = Field(None, ge=1, le=10, description="Constraint priority (1-10)")
    weight: Optional[float] = Field(None, gt=0, description="Constraint weight for optimization")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Constraint metadata")


class LayoutConstraintResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for layout constraint response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., description="Constraint name")
    constraint_type: ConstraintType = Field(..., description="Type of constraint")
    description: Optional[str] = Field(None, description="Constraint description")
    
    # Constraint configuration
    parameters: Dict[str, Any] = Field(..., description="Constraint parameters")
    geometry: Optional[GeometrySchema] = Field(None, description="Constraint geometry")
    
    # Constraint properties
    is_hard_constraint: bool = Field(..., description="Whether constraint is hard or soft")
    priority: int = Field(..., description="Constraint priority (1-10)")
    weight: float = Field(..., description="Constraint weight for optimization")
    
    # Constraint status
    is_active: bool = Field(True, description="Whether constraint is active")
    violation_count: int = Field(0, description="Number of violations")
    last_violation_at: Optional[datetime] = Field(None, description="Last violation timestamp")


class LayoutFilterParams(FilterParams):
    """Layout-specific filtering parameters."""
    
    status: Optional[LayoutStatus] = Field(None, description="Filter by status")
    design_id: Optional[uuid.UUID] = Field(None, description="Filter by design")
    project_id: Optional[uuid.UUID] = Field(None, description="Filter by project")
    created_by: Optional[uuid.UUID] = Field(None, description="Filter by creator")
    template_id: Optional[uuid.UUID] = Field(None, description="Filter by template")
    min_capacity_kw: Optional[float] = Field(None, gt=0, description="Minimum capacity")
    max_capacity_kw: Optional[float] = Field(None, gt=0, description="Maximum capacity")
    min_module_count: Optional[int] = Field(None, gt=0, description="Minimum module count")
    max_module_count: Optional[int] = Field(None, gt=0, description="Maximum module count")


class LayoutGenerationRequest(BaseSchema):
    """Schema for layout generation request."""
    
    design_id: uuid.UUID = Field(..., description="Design ID")
    template_id: Optional[uuid.UUID] = Field(None, description="Template to use")
    
    # Generation parameters
    target_capacity_kw: Optional[float] = Field(None, gt=0, description="Target capacity")
    module_type: Optional[str] = Field(None, description="Module type to use")
    optimization_objective: OptimizationObjective = Field(
        OptimizationObjective.MAXIMIZE_CAPACITY, description="Optimization objective"
    )
    
    # Generation constraints
    constraints: Optional[List[Dict[str, Any]]] = Field(None, description="Generation constraints")
    setbacks: Optional[Dict[str, float]] = Field(None, description="Setback requirements")
    
    # Generation settings
    auto_optimize: bool = Field(True, description="Auto-optimize after generation")
    include_shading_analysis: bool = Field(False, description="Include shading analysis")
    
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class LayoutGenerationResponse(BaseSchema):
    """Schema for layout generation response."""
    
    layout_id: uuid.UUID = Field(..., description="Generated layout ID")
    generation_summary: Dict[str, Any] = Field(..., description="Generation summary")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")
    warnings: List[str] = Field(..., description="Generation warnings")
    recommendations: List[str] = Field(..., description="Optimization recommendations")


class LayoutAnalysisRequest(BaseSchema):
    """Schema for layout analysis request."""
    
    analysis_types: List[str] = Field(..., description="Types of analysis to perform")
    include_shading: bool = Field(True, description="Include shading analysis")
    include_performance: bool = Field(True, description="Include performance analysis")
    include_financial: bool = Field(False, description="Include financial analysis")
    weather_data_source: Optional[str] = Field(None, description="Weather data source")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Analysis parameters")


class LayoutAnalysisResponse(BaseSchema):
    """Schema for layout analysis response."""
    
    analysis_results: Dict[str, Any] = Field(..., description="Analysis results")
    performance_summary: Dict[str, Any] = Field(..., description="Performance summary")
    issues: List[Dict[str, Any]] = Field(..., description="Identified issues")
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    confidence_score: Optional[float] = Field(None, description="Analysis confidence score")


class LayoutComparisonRequest(BaseSchema):
    """Schema for layout comparison request."""
    
    layout_ids: List[uuid.UUID] = Field(..., min_items=2, max_items=5, description="Layouts to compare")
    comparison_metrics: Optional[List[str]] = Field(None, description="Metrics to compare")
    include_financial: bool = Field(True, description="Include financial comparison")
    include_performance: bool = Field(True, description="Include performance comparison")
    normalize_by_capacity: bool = Field(True, description="Normalize by capacity")


class LayoutComparisonResponse(BaseSchema):
    """Schema for layout comparison response."""
    
    layouts: List[LayoutResponse] = Field(..., description="Compared layouts")
    comparison_matrix: Dict[str, Any] = Field(..., description="Comparison matrix")
    rankings: Dict[str, List[uuid.UUID]] = Field(..., description="Rankings by metric")
    summary: Dict[str, Any] = Field(..., description="Comparison summary")
    recommendations: List[str] = Field(..., description="Recommendations")


class LayoutValidationResult(BaseSchema):
    """Schema for layout validation results."""
    
    is_valid: bool = Field(..., description="Whether layout is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    validation_score: Optional[float] = Field(None, ge=0, le=1, description="Validation score")
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed validation results")


class LayoutPerformanceMetrics(BaseSchema):
    """Schema for layout performance metrics."""
    
    annual_energy_kwh: Optional[float] = Field(None, gt=0, description="Annual energy production")
    specific_yield_kwh_kwp: Optional[float] = Field(None, gt=0, description="Specific yield")
    performance_ratio: Optional[float] = Field(None, ge=0, le=1, description="Performance ratio")
    capacity_factor: Optional[float] = Field(None, ge=0, le=1, description="Capacity factor")
    shading_losses_percent: Optional[float] = Field(None, ge=0, le=100, description="Shading losses")
    soiling_losses_percent: Optional[float] = Field(None, ge=0, le=100, description="Soiling losses")
    system_losses_percent: Optional[float] = Field(None, ge=0, le=100, description="System losses")
    irradiation_kwh_m2: Optional[float] = Field(None, gt=0, description="Annual irradiation")
    temperature_coefficient: Optional[float] = Field(None, description="Temperature coefficient")
    degradation_rate_percent: Optional[float] = Field(None, ge=0, le=10, description="Annual degradation rate")


class LayoutComparison(BaseSchema):
    """Schema for layout comparison data."""
    
    layout_id: uuid.UUID = Field(..., description="Layout ID")
    layout_name: str = Field(..., description="Layout name")
    metrics: LayoutPerformanceMetrics = Field(..., description="Performance metrics")
    financial_metrics: Optional[Dict[str, Any]] = Field(None, description="Financial metrics")
    ranking_score: Optional[float] = Field(None, description="Overall ranking score")
    strengths: List[str] = Field(default_factory=list, description="Layout strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Layout weaknesses")


class LayoutComparisonResult(BaseSchema):
    """Schema for detailed layout comparison results."""
    
    comparison_id: uuid.UUID = Field(..., description="Comparison ID")
    layouts: List[LayoutComparison] = Field(..., description="Compared layouts")
    best_layout_id: Optional[uuid.UUID] = Field(None, description="Best performing layout ID")
    comparison_summary: Dict[str, Any] = Field(..., description="Comparison summary")
    methodology: str = Field(..., description="Comparison methodology")
    confidence_level: Optional[float] = Field(None, ge=0, le=1, description="Confidence level")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Comparison timestamp")


class LayoutExportRequest(BaseSchema):
    """Schema for layout export request."""
    
    export_format: str = Field(..., description="Export format (dwg, pdf, json, etc.)")
    include_zones: bool = Field(True, description="Include zones in export")
    include_modules: bool = Field(True, description="Include module details")
    include_constraints: bool = Field(False, description="Include constraints")
    include_performance: bool = Field(False, description="Include performance data")
    coordinate_system: Optional[str] = Field(None, description="Target coordinate system")
    scale: Optional[float] = Field(None, gt=0, description="Export scale")
    additional_options: Optional[Dict[str, Any]] = Field(None, description="Format-specific options")


class LayoutExportResponse(BaseSchema):
    """Schema for layout export response."""
    
    export_id: uuid.UUID = Field(..., description="Export ID")
    download_url: str = Field(..., description="Download URL")
    file_name: str = Field(..., description="Generated file name")
    file_size_bytes: int = Field(..., description="File size in bytes")
    export_format: str = Field(..., description="Export format")
    expires_at: datetime = Field(..., description="Download link expiration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Export metadata")


class LayoutListResponse(BaseSchema):
    """Schema for layout list response."""
    
    layouts: List[LayoutResponse] = Field(..., description="List of layouts")
    total_count: int = Field(..., description="Total number of layouts")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")
    filters_applied: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(None, description="Sort order (asc/desc)")


# Panel Array Schemas
class PanelArrayCreate(BaseSchema):
    """Schema for creating panel arrays."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., min_length=1, max_length=255, description="Array name")
    array_type: str = Field(..., description="Type of panel array")
    
    # Array configuration
    module_type: str = Field(..., description="Solar module type")
    module_count: int = Field(..., gt=0, description="Number of modules")
    rows: int = Field(..., gt=0, description="Number of rows")
    columns: int = Field(..., gt=0, description="Number of columns")
    
    # Positioning and orientation
    position: GeometrySchema = Field(..., description="Array position")
    tilt_angle: float = Field(..., ge=0, le=90, description="Tilt angle in degrees")
    azimuth_angle: float = Field(..., ge=0, lt=360, description="Azimuth angle in degrees")
    
    # Spacing and layout
    row_spacing: float = Field(..., gt=0, description="Row spacing in meters")
    module_spacing: float = Field(..., gt=0, description="Module spacing in meters")
    
    # Electrical configuration
    strings_per_inverter: Optional[int] = Field(None, gt=0, description="Strings per inverter")
    modules_per_string: Optional[int] = Field(None, gt=0, description="Modules per string")
    
    # Performance parameters
    dc_capacity_kw: Optional[float] = Field(None, gt=0, description="DC capacity in kW")
    expected_yield_kwh: Optional[float] = Field(None, gt=0, description="Expected annual yield")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Array metadata")


class PanelArrayUpdate(BaseSchema):
    """Schema for updating panel arrays."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Array name")
    array_type: Optional[str] = Field(None, description="Type of panel array")
    
    # Array configuration
    module_type: Optional[str] = Field(None, description="Solar module type")
    module_count: Optional[int] = Field(None, gt=0, description="Number of modules")
    rows: Optional[int] = Field(None, gt=0, description="Number of rows")
    columns: Optional[int] = Field(None, gt=0, description="Number of columns")
    
    # Positioning and orientation
    position: Optional[GeometrySchema] = Field(None, description="Array position")
    tilt_angle: Optional[float] = Field(None, ge=0, le=90, description="Tilt angle in degrees")
    azimuth_angle: Optional[float] = Field(None, ge=0, lt=360, description="Azimuth angle in degrees")
    
    # Spacing and layout
    row_spacing: Optional[float] = Field(None, gt=0, description="Row spacing in meters")
    module_spacing: Optional[float] = Field(None, gt=0, description="Module spacing in meters")
    
    # Electrical configuration
    strings_per_inverter: Optional[int] = Field(None, gt=0, description="Strings per inverter")
    modules_per_string: Optional[int] = Field(None, gt=0, description="Modules per string")
    
    # Performance parameters
    dc_capacity_kw: Optional[float] = Field(None, gt=0, description="DC capacity in kW")
    expected_yield_kwh: Optional[float] = Field(None, gt=0, description="Expected annual yield")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Array metadata")


class PanelArrayResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for panel array response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., description="Array name")
    array_type: str = Field(..., description="Type of panel array")
    
    # Array configuration
    module_type: str = Field(..., description="Solar module type")
    module_count: int = Field(..., description="Number of modules")
    rows: int = Field(..., description="Number of rows")
    columns: int = Field(..., description="Number of columns")
    
    # Positioning and orientation
    position: GeometrySchema = Field(..., description="Array position")
    tilt_angle: float = Field(..., description="Tilt angle in degrees")
    azimuth_angle: float = Field(..., description="Azimuth angle in degrees")
    
    # Spacing and layout
    row_spacing: float = Field(..., description="Row spacing in meters")
    module_spacing: float = Field(..., description="Module spacing in meters")
    
    # Electrical configuration
    strings_per_inverter: Optional[int] = Field(None, description="Strings per inverter")
    modules_per_string: Optional[int] = Field(None, description="Modules per string")
    
    # Performance parameters
    dc_capacity_kw: Optional[float] = Field(None, description="DC capacity in kW")
    expected_yield_kwh: Optional[float] = Field(None, description="Expected annual yield")
    
    # Status
    is_active: bool = Field(True, description="Whether array is active")
    validation_status: str = Field(..., description="Validation status")
    performance_score: Optional[float] = Field(None, description="Performance score")


# Inverter Schemas
class InverterCreate(BaseSchema):
    """Schema for creating inverters."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., min_length=1, max_length=255, description="Inverter name")
    inverter_type: str = Field(..., description="Type of inverter")
    
    # Technical specifications
    manufacturer: str = Field(..., description="Inverter manufacturer")
    model: str = Field(..., description="Inverter model")
    rated_power_kw: float = Field(..., gt=0, description="Rated power in kW")
    max_dc_voltage: float = Field(..., gt=0, description="Maximum DC voltage")
    mppt_channels: int = Field(..., gt=0, description="Number of MPPT channels")
    
    # Installation details
    position: GeometrySchema = Field(..., description="Inverter position")
    installation_type: str = Field(..., description="Installation type (indoor/outdoor)")
    
    # Electrical configuration
    ac_voltage: float = Field(..., gt=0, description="AC output voltage")
    frequency: float = Field(..., gt=0, description="Output frequency")
    efficiency: Optional[float] = Field(None, ge=0, le=1, description="Inverter efficiency")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Inverter metadata")


class InverterUpdate(BaseSchema):
    """Schema for updating inverters."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Inverter name")
    inverter_type: Optional[str] = Field(None, description="Type of inverter")
    
    # Technical specifications
    manufacturer: Optional[str] = Field(None, description="Inverter manufacturer")
    model: Optional[str] = Field(None, description="Inverter model")
    rated_power_kw: Optional[float] = Field(None, gt=0, description="Rated power in kW")
    max_dc_voltage: Optional[float] = Field(None, gt=0, description="Maximum DC voltage")
    mppt_channels: Optional[int] = Field(None, gt=0, description="Number of MPPT channels")
    
    # Installation details
    position: Optional[GeometrySchema] = Field(None, description="Inverter position")
    installation_type: Optional[str] = Field(None, description="Installation type")
    
    # Electrical configuration
    ac_voltage: Optional[float] = Field(None, gt=0, description="AC output voltage")
    frequency: Optional[float] = Field(None, gt=0, description="Output frequency")
    efficiency: Optional[float] = Field(None, ge=0, le=1, description="Inverter efficiency")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Inverter metadata")


class InverterResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for inverter response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., description="Inverter name")
    inverter_type: str = Field(..., description="Type of inverter")
    
    # Technical specifications
    manufacturer: str = Field(..., description="Inverter manufacturer")
    model: str = Field(..., description="Inverter model")
    rated_power_kw: float = Field(..., description="Rated power in kW")
    max_dc_voltage: float = Field(..., description="Maximum DC voltage")
    mppt_channels: int = Field(..., description="Number of MPPT channels")
    
    # Installation details
    position: GeometrySchema = Field(..., description="Inverter position")
    installation_type: str = Field(..., description="Installation type")
    
    # Electrical configuration
    ac_voltage: float = Field(..., description="AC output voltage")
    frequency: float = Field(..., description="Output frequency")
    efficiency: Optional[float] = Field(None, description="Inverter efficiency")
    
    # Status and performance
    is_active: bool = Field(True, description="Whether inverter is active")
    status: str = Field(..., description="Inverter status")
    performance_ratio: Optional[float] = Field(None, description="Performance ratio")
    connected_arrays: List[uuid.UUID] = Field(default_factory=list, description="Connected panel arrays")


# Electrical Component Schemas
class ElectricalComponentCreate(BaseSchema):
    """Schema for creating electrical components."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., min_length=1, max_length=255, description="Component name")
    component_type: str = Field(..., description="Type of electrical component")
    
    # Component specifications
    manufacturer: Optional[str] = Field(None, description="Component manufacturer")
    model: Optional[str] = Field(None, description="Component model")
    rating: Optional[str] = Field(None, description="Component rating")
    
    # Installation details
    position: GeometrySchema = Field(..., description="Component position")
    installation_method: Optional[str] = Field(None, description="Installation method")
    
    # Electrical properties
    voltage_rating: Optional[float] = Field(None, gt=0, description="Voltage rating")
    current_rating: Optional[float] = Field(None, gt=0, description="Current rating")
    power_rating: Optional[float] = Field(None, gt=0, description="Power rating")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Component metadata")


class ElectricalComponentUpdate(BaseSchema):
    """Schema for updating electrical components."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Component name")
    component_type: Optional[str] = Field(None, description="Type of electrical component")
    
    # Component specifications
    manufacturer: Optional[str] = Field(None, description="Component manufacturer")
    model: Optional[str] = Field(None, description="Component model")
    rating: Optional[str] = Field(None, description="Component rating")
    
    # Installation details
    position: Optional[GeometrySchema] = Field(None, description="Component position")
    installation_method: Optional[str] = Field(None, description="Installation method")
    
    # Electrical properties
    voltage_rating: Optional[float] = Field(None, gt=0, description="Voltage rating")
    current_rating: Optional[float] = Field(None, gt=0, description="Current rating")
    power_rating: Optional[float] = Field(None, gt=0, description="Power rating")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Component metadata")


class ElectricalComponentResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for electrical component response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., description="Component name")
    component_type: str = Field(..., description="Type of electrical component")
    
    # Component specifications
    manufacturer: Optional[str] = Field(None, description="Component manufacturer")
    model: Optional[str] = Field(None, description="Component model")
    rating: Optional[str] = Field(None, description="Component rating")
    
    # Installation details
    position: GeometrySchema = Field(..., description="Component position")
    installation_method: Optional[str] = Field(None, description="Installation method")
    
    # Electrical properties
    voltage_rating: Optional[float] = Field(None, description="Voltage rating")
    current_rating: Optional[float] = Field(None, description="Current rating")
    power_rating: Optional[float] = Field(None, description="Power rating")
    
    # Status
    is_active: bool = Field(True, description="Whether component is active")
    status: str = Field(..., description="Component status")
    installation_date: Optional[datetime] = Field(None, description="Installation date")
    last_maintenance: Optional[datetime] = Field(None, description="Last maintenance date")


# Cable Run Schemas
class CableRunCreate(BaseSchema):
    """Schema for creating cable runs."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., min_length=1, max_length=255, description="Cable run name")
    cable_type: str = Field(..., description="Type of cable")
    
    # Cable specifications
    conductor_material: str = Field(..., description="Conductor material (copper/aluminum)")
    insulation_type: str = Field(..., description="Insulation type")
    voltage_rating: float = Field(..., gt=0, description="Voltage rating")
    current_capacity: float = Field(..., gt=0, description="Current carrying capacity")
    
    # Physical properties
    cable_size_awg: Optional[str] = Field(None, description="Cable size in AWG")
    cable_size_mm2: Optional[float] = Field(None, gt=0, description="Cable size in mm²")
    length_meters: float = Field(..., gt=0, description="Cable length in meters")
    
    # Route and installation
    route_geometry: GeometrySchema = Field(..., description="Cable route geometry")
    installation_method: str = Field(..., description="Installation method")
    conduit_type: Optional[str] = Field(None, description="Conduit type if applicable")
    
    # Connection points
    start_component_id: uuid.UUID = Field(..., description="Starting component ID")
    end_component_id: uuid.UUID = Field(..., description="Ending component ID")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Cable run metadata")


class CableRunUpdate(BaseSchema):
    """Schema for updating cable runs."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Cable run name")
    cable_type: Optional[str] = Field(None, description="Type of cable")
    
    # Cable specifications
    conductor_material: Optional[str] = Field(None, description="Conductor material")
    insulation_type: Optional[str] = Field(None, description="Insulation type")
    voltage_rating: Optional[float] = Field(None, gt=0, description="Voltage rating")
    current_capacity: Optional[float] = Field(None, gt=0, description="Current carrying capacity")
    
    # Physical properties
    cable_size_awg: Optional[str] = Field(None, description="Cable size in AWG")
    cable_size_mm2: Optional[float] = Field(None, gt=0, description="Cable size in mm²")
    length_meters: Optional[float] = Field(None, gt=0, description="Cable length in meters")
    
    # Route and installation
    route_geometry: Optional[GeometrySchema] = Field(None, description="Cable route geometry")
    installation_method: Optional[str] = Field(None, description="Installation method")
    conduit_type: Optional[str] = Field(None, description="Conduit type if applicable")
    
    # Connection points
    start_component_id: Optional[uuid.UUID] = Field(None, description="Starting component ID")
    end_component_id: Optional[uuid.UUID] = Field(None, description="Ending component ID")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Cable run metadata")


class CableRunResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for cable run response."""
    
    layout_id: uuid.UUID = Field(..., description="Parent layout ID")
    name: str = Field(..., description="Cable run name")
    cable_type: str = Field(..., description="Type of cable")
    
    # Cable specifications
    conductor_material: str = Field(..., description="Conductor material")
    insulation_type: str = Field(..., description="Insulation type")
    voltage_rating: float = Field(..., description="Voltage rating")
    current_capacity: float = Field(..., description="Current carrying capacity")
    
    # Physical properties
    cable_size_awg: Optional[str] = Field(None, description="Cable size in AWG")
    cable_size_mm2: Optional[float] = Field(None, description="Cable size in mm²")
    length_meters: float = Field(..., description="Cable length in meters")
    
    # Route and installation
    route_geometry: GeometrySchema = Field(..., description="Cable route geometry")
    installation_method: str = Field(..., description="Installation method")
    conduit_type: Optional[str] = Field(None, description="Conduit type if applicable")
    
    # Connection points
    start_component_id: uuid.UUID = Field(..., description="Starting component ID")
    end_component_id: uuid.UUID = Field(..., description="Ending component ID")
    
    # Status and performance
    is_active: bool = Field(True, description="Whether cable run is active")
    status: str = Field(..., description="Cable run status")
    voltage_drop_percent: Optional[float] = Field(None, description="Voltage drop percentage")
    power_loss_watts: Optional[float] = Field(None, description="Power loss in watts")
    installation_date: Optional[datetime] = Field(None, description="Installation date")


# Layout Optimization Schemas
class LayoutOptimizationCreate(BaseSchema):
    """Schema for creating layout optimizations."""
    
    layout_id: uuid.UUID = Field(..., description="Layout to optimize")
    optimization_type: str = Field(..., description="Type of optimization")
    objective: str = Field(..., description="Optimization objective")
    
    # Optimization parameters
    target_metrics: List[str] = Field(..., description="Target metrics to optimize")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Optimization constraints")
    weights: Optional[Dict[str, float]] = Field(None, description="Metric weights")
    
    # Algorithm settings
    algorithm: Optional[str] = Field(None, description="Optimization algorithm")
    max_iterations: Optional[int] = Field(None, gt=0, description="Maximum iterations")
    convergence_threshold: Optional[float] = Field(None, gt=0, description="Convergence threshold")
    
    # Advanced options
    preserve_existing: bool = Field(False, description="Preserve existing layout elements")
    allow_module_rotation: bool = Field(True, description="Allow module rotation")
    consider_shading: bool = Field(True, description="Consider shading effects")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optimization metadata")


class LayoutOptimizationResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for layout optimization response."""
    
    layout_id: uuid.UUID = Field(..., description="Optimized layout ID")
    original_layout_id: uuid.UUID = Field(..., description="Original layout ID")
    optimization_type: str = Field(..., description="Type of optimization")
    objective: str = Field(..., description="Optimization objective")
    
    # Optimization results
    status: str = Field(..., description="Optimization status")
    progress_percent: float = Field(..., ge=0, le=100, description="Progress percentage")
    iterations_completed: int = Field(..., description="Iterations completed")
    
    # Performance metrics
    original_metrics: Dict[str, Any] = Field(..., description="Original layout metrics")
    optimized_metrics: Dict[str, Any] = Field(..., description="Optimized layout metrics")
    improvement_percent: Dict[str, float] = Field(..., description="Improvement percentages")
    
    # Optimization details
    algorithm_used: str = Field(..., description="Algorithm used")
    convergence_achieved: bool = Field(..., description="Whether convergence was achieved")
    execution_time_seconds: float = Field(..., description="Execution time in seconds")
    
    # Results and recommendations
    changes_made: List[Dict[str, Any]] = Field(..., description="Changes made to layout")
    warnings: List[str] = Field(default_factory=list, description="Optimization warnings")
    recommendations: List[str] = Field(default_factory=list, description="Further recommendations")
    
    # Quality metrics
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="Quality score")
    feasibility_score: Optional[float] = Field(None, ge=0, le=1, description="Feasibility score")