"""Solar design and calculation Pydantic schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from .base import BaseSchema, TimestampSchema


class SolarDesignStatus(str, Enum):
    """Solar design status enumeration."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FINALIZED = "finalized"


class SolarDesignType(str, Enum):
    """Solar design type enumeration."""
    ROOFTOP = "rooftop"
    GROUND_MOUNT = "ground_mount"
    CARPORT = "carport"
    FLOATING = "floating"
    AGRIVOLTAIC = "agrivoltaic"
    BUILDING_INTEGRATED = "building_integrated"


class ComponentType(str, Enum):
    """Solar component type enumeration."""
    PANEL = "panel"
    INVERTER = "inverter"
    MOUNTING = "mounting"
    CABLE = "cable"
    COMBINER_BOX = "combiner_box"
    MONITORING = "monitoring"
    BATTERY = "battery"
    TRANSFORMER = "transformer"
    SWITCHGEAR = "switchgear"
    OTHER = "other"


class CalculationType(str, Enum):
    """Calculation type enumeration."""
    ENERGY_YIELD = "energy_yield"
    FINANCIAL = "financial"
    SHADING = "shading"
    STRUCTURAL = "structural"
    ELECTRICAL = "electrical"
    THERMAL = "thermal"
    ENVIRONMENTAL = "environmental"


class CalculationStatus(str, Enum):
    """Calculation status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Solar Design Schemas
class SolarDesignBase(BaseModel):
    """Base solar design schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Design name")
    description: Optional[str] = Field(None, description="Design description")
    design_type: SolarDesignType = Field(..., description="Type of solar design")
    
    # System specifications
    total_capacity: float = Field(..., gt=0, description="Total system capacity in kW")
    panel_count: int = Field(..., gt=0, description="Number of solar panels")
    panel_wattage: float = Field(..., gt=0, description="Individual panel wattage")
    
    # Layout and positioning
    tilt_angle: Optional[float] = Field(None, ge=0, le=90, description="Panel tilt angle in degrees")
    azimuth_angle: Optional[float] = Field(None, ge=0, le=360, description="Panel azimuth angle in degrees")
    row_spacing: Optional[float] = Field(None, gt=0, description="Row spacing in meters")
    
    # Performance estimates
    estimated_annual_yield: Optional[float] = Field(None, gt=0, description="Estimated annual energy yield in kWh")
    performance_ratio: Optional[float] = Field(None, gt=0, le=1, description="System performance ratio")
    capacity_factor: Optional[float] = Field(None, gt=0, le=1, description="Capacity factor")
    
    # Design settings and constraints
    design_settings: Dict[str, Any] = Field(default_factory=dict, description="Design configuration settings")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Design constraints")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize design name."""
        return v.strip()
    
    @validator('total_capacity')
    def validate_capacity_consistency(cls, v, values):
        """Validate that total capacity matches panel count and wattage."""
        if 'panel_count' in values and 'panel_wattage' in values:
            expected_capacity = (values['panel_count'] * values['panel_wattage']) / 1000
            if abs(v - expected_capacity) > 0.1:  # Allow small rounding differences
                raise ValueError('Total capacity must match panel count × panel wattage')
        return v


class SolarDesignCreate(SolarDesignBase):
    """Schema for creating a solar design."""
    project_id: str = Field(..., description="Associated project ID")


class SolarDesignUpdate(BaseModel):
    """Schema for updating a solar design."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    design_type: Optional[SolarDesignType] = Field(None)
    status: Optional[SolarDesignStatus] = Field(None)
    
    # System specifications
    total_capacity: Optional[float] = Field(None, gt=0)
    panel_count: Optional[int] = Field(None, gt=0)
    panel_wattage: Optional[float] = Field(None, gt=0)
    
    # Layout and positioning
    tilt_angle: Optional[float] = Field(None, ge=0, le=90)
    azimuth_angle: Optional[float] = Field(None, ge=0, le=360)
    row_spacing: Optional[float] = Field(None, gt=0)
    
    # Performance estimates
    estimated_annual_yield: Optional[float] = Field(None, gt=0)
    performance_ratio: Optional[float] = Field(None, gt=0, le=1)
    capacity_factor: Optional[float] = Field(None, gt=0, le=1)
    
    # Design settings and constraints
    design_settings: Optional[Dict[str, Any]] = Field(None)
    constraints: Optional[Dict[str, Any]] = Field(None)
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize design name."""
        if v is not None:
            return v.strip()
        return v


class SolarDesignResponse(SolarDesignBase, TimestampSchema):
    """Schema for solar design response."""
    id: str = Field(..., description="Design ID")
    project_id: str = Field(..., description="Associated project ID")
    status: SolarDesignStatus = Field(..., description="Design status")
    version: int = Field(..., description="Design version number")
    
    # Component and calculation counts
    component_count: int = Field(default=0, description="Number of components")
    calculation_count: int = Field(default=0, description="Number of calculations")
    
    # Financial estimates
    estimated_cost: Optional[Decimal] = Field(None, description="Estimated system cost")
    estimated_savings: Optional[Decimal] = Field(None, description="Estimated annual savings")
    payback_period: Optional[float] = Field(None, description="Payback period in years")
    
    class Config:
        from_attributes = True


class SolarDesignSummary(BaseModel):
    """Schema for solar design summary."""
    id: str = Field(..., description="Design ID")
    name: str = Field(..., description="Design name")
    design_type: SolarDesignType = Field(..., description="Design type")
    status: SolarDesignStatus = Field(..., description="Design status")
    total_capacity: float = Field(..., description="Total capacity in kW")
    panel_count: int = Field(..., description="Number of panels")
    estimated_annual_yield: Optional[float] = Field(None, description="Estimated annual yield")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class SolarDesignList(BaseModel):
    """Schema for paginated solar design list."""
    designs: List[SolarDesignSummary]
    total: int = Field(..., description="Total number of designs")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


# Solar Component Schemas
class SolarComponentBase(BaseModel):
    """Base solar component schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Component name")
    component_type: ComponentType = Field(..., description="Type of component")
    manufacturer: Optional[str] = Field(None, max_length=255, description="Manufacturer name")
    model: Optional[str] = Field(None, max_length=255, description="Model number")
    
    # Technical specifications
    specifications: Dict[str, Any] = Field(default_factory=dict, description="Technical specifications")
    
    # Quantity and positioning
    quantity: int = Field(..., gt=0, description="Number of components")
    unit_cost: Optional[Decimal] = Field(None, gt=0, description="Cost per unit")
    total_cost: Optional[Decimal] = Field(None, gt=0, description="Total cost")
    
    # Installation details
    installation_notes: Optional[str] = Field(None, description="Installation notes")
    warranty_years: Optional[int] = Field(None, gt=0, description="Warranty period in years")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize component name."""
        return v.strip()
    
    @validator('total_cost')
    def validate_total_cost(cls, v, values):
        """Validate total cost consistency."""
        if v and 'quantity' in values and 'unit_cost' in values and values['unit_cost']:
            expected_total = values['quantity'] * values['unit_cost']
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError('Total cost must equal quantity × unit cost')
        return v


class SolarComponentCreate(SolarComponentBase):
    """Schema for creating a solar component."""
    design_id: str = Field(..., description="Associated design ID")


class SolarComponentUpdate(BaseModel):
    """Schema for updating a solar component."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    component_type: Optional[ComponentType] = Field(None)
    manufacturer: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    specifications: Optional[Dict[str, Any]] = Field(None)
    quantity: Optional[int] = Field(None, gt=0)
    unit_cost: Optional[Decimal] = Field(None, gt=0)
    total_cost: Optional[Decimal] = Field(None, gt=0)
    installation_notes: Optional[str] = Field(None)
    warranty_years: Optional[int] = Field(None, gt=0)
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize component name."""
        if v is not None:
            return v.strip()
        return v


class SolarComponentResponse(SolarComponentBase, TimestampSchema):
    """Schema for solar component response."""
    id: str = Field(..., description="Component ID")
    design_id: str = Field(..., description="Associated design ID")
    
    class Config:
        from_attributes = True


class SolarComponentList(BaseModel):
    """Schema for solar component list."""
    components: List[SolarComponentResponse]
    total: int = Field(..., description="Total number of components")
    total_cost: Optional[Decimal] = Field(None, description="Total cost of all components")


# Design Calculation Schemas
class DesignCalculationBase(BaseModel):
    """Base design calculation schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Calculation name")
    calculation_type: CalculationType = Field(..., description="Type of calculation")
    description: Optional[str] = Field(None, description="Calculation description")
    
    # Input parameters
    input_parameters: Dict[str, Any] = Field(default_factory=dict, description="Calculation input parameters")
    
    # Calculation settings
    calculation_settings: Dict[str, Any] = Field(default_factory=dict, description="Calculation configuration")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize calculation name."""
        return v.strip()


class DesignCalculationCreate(DesignCalculationBase):
    """Schema for creating a design calculation."""
    design_id: str = Field(..., description="Associated design ID")


class DesignCalculationUpdate(BaseModel):
    """Schema for updating a design calculation."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    calculation_type: Optional[CalculationType] = Field(None)
    description: Optional[str] = Field(None)
    status: Optional[CalculationStatus] = Field(None)
    input_parameters: Optional[Dict[str, Any]] = Field(None)
    calculation_settings: Optional[Dict[str, Any]] = Field(None)
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize calculation name."""
        if v is not None:
            return v.strip()
        return v


class DesignCalculationResponse(DesignCalculationBase, TimestampSchema):
    """Schema for design calculation response."""
    id: str = Field(..., description="Calculation ID")
    design_id: str = Field(..., description="Associated design ID")
    status: CalculationStatus = Field(..., description="Calculation status")
    
    # Results
    results: Dict[str, Any] = Field(default_factory=dict, description="Calculation results")
    
    # Execution details
    started_at: Optional[datetime] = Field(None, description="Calculation start time")
    completed_at: Optional[datetime] = Field(None, description="Calculation completion time")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Metadata
    calculation_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        from_attributes = True


class DesignCalculationSummary(BaseModel):
    """Schema for calculation summary."""
    id: str = Field(..., description="Calculation ID")
    name: str = Field(..., description="Calculation name")
    calculation_type: CalculationType = Field(..., description="Calculation type")
    status: CalculationStatus = Field(..., description="Calculation status")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    execution_time: Optional[float] = Field(None, description="Execution time")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class DesignCalculationList(BaseModel):
    """Schema for design calculation list."""
    calculations: List[DesignCalculationSummary]
    total: int = Field(..., description="Total number of calculations")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


# Calculation Request Schemas
class CalculationRequest(BaseModel):
    """Schema for requesting a calculation."""
    calculation_type: CalculationType = Field(..., description="Type of calculation")
    input_parameters: Dict[str, Any] = Field(..., description="Input parameters")
    calculation_settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Calculation settings")
    priority: Optional[str] = Field(default="normal", description="Calculation priority")
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate calculation priority."""
        allowed_priorities = ['low', 'normal', 'high', 'urgent']
        if v.lower() not in allowed_priorities:
            raise ValueError(f'Priority must be one of: {", ".join(allowed_priorities)}')
        return v.lower()


class CalculationResult(BaseModel):
    """Schema for calculation results."""
    calculation_id: str = Field(..., description="Calculation ID")
    status: CalculationStatus = Field(..., description="Calculation status")
    results: Dict[str, Any] = Field(default_factory=dict, description="Calculation results")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Calculation warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# Filter and Search Schemas
class SolarDesignFilter(BaseModel):
    """Schema for solar design filtering."""
    search: Optional[str] = Field(None, description="Search term")
    project_id: Optional[str] = Field(None, description="Filter by project")
    design_type: Optional[List[SolarDesignType]] = Field(None, description="Filter by design type")
    status: Optional[List[SolarDesignStatus]] = Field(None, description="Filter by status")
    min_capacity: Optional[float] = Field(None, description="Minimum capacity")
    max_capacity: Optional[float] = Field(None, description="Maximum capacity")
    
    # Sorting and pagination
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", description="Sort order")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")


class ComponentFilter(BaseModel):
    """Schema for component filtering."""
    design_id: Optional[str] = Field(None, description="Filter by design")
    component_type: Optional[List[ComponentType]] = Field(None, description="Filter by component type")
    manufacturer: Optional[str] = Field(None, description="Filter by manufacturer")
    
    # Sorting
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="asc", description="Sort order")