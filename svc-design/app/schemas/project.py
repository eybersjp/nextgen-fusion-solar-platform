"""Project management Pydantic schemas."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from .base import BaseSchema, TimestampSchema


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectType(str, Enum):
    """Project type enumeration."""
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    UTILITY = "utility"
    RESIDENTIAL = "residential"


class ProjectPriority(str, Enum):
    """Project priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectBase(BaseModel):
    """Base project schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    project_type: ProjectType = Field(..., description="Type of project")
    priority: ProjectPriority = Field(default=ProjectPriority.MEDIUM, description="Project priority")
    
    # Location information
    address: Optional[str] = Field(None, max_length=500, description="Project address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State/Province")
    country: str = Field(..., max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    
    # Project specifications
    site_area: Optional[float] = Field(None, gt=0, description="Site area in square meters")
    roof_area: Optional[float] = Field(None, gt=0, description="Available roof area in square meters")
    target_capacity: Optional[float] = Field(None, gt=0, description="Target system capacity in kW")
    annual_energy_consumption: Optional[float] = Field(None, gt=0, description="Annual energy consumption in kWh")
    
    # Financial information
    budget: Optional[Decimal] = Field(None, gt=0, description="Project budget")
    currency: str = Field(default="USD", max_length=3, description="Currency code")
    
    # Timeline
    start_date: Optional[date] = Field(None, description="Project start date")
    target_completion_date: Optional[date] = Field(None, description="Target completion date")
    
    # Compliance and requirements
    regulatory_requirements: Optional[str] = Field(None, description="Regulatory requirements")
    environmental_constraints: Optional[str] = Field(None, description="Environmental constraints")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize project name."""
        return v.strip()
    
    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code."""
        allowed_currencies = ['USD', 'EUR', 'GBP', 'AUD', 'ZAR']
        if v.upper() not in allowed_currencies:
            raise ValueError(f'Currency must be one of: {", ".join(allowed_currencies)}')
        return v.upper()
    
    @validator('target_completion_date')
    def validate_completion_date(cls, v, values):
        """Validate that completion date is after start date."""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('Target completion date must be after start date')
        return v


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating project information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    project_type: Optional[ProjectType] = Field(None)
    priority: Optional[ProjectPriority] = Field(None)
    status: Optional[ProjectStatus] = Field(None)
    
    # Location information
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Project specifications
    site_area: Optional[float] = Field(None, gt=0)
    roof_area: Optional[float] = Field(None, gt=0)
    target_capacity: Optional[float] = Field(None, gt=0)
    annual_energy_consumption: Optional[float] = Field(None, gt=0)
    
    # Financial information
    budget: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=3)
    
    # Timeline
    start_date: Optional[date] = Field(None)
    target_completion_date: Optional[date] = Field(None)
    actual_completion_date: Optional[date] = Field(None)
    
    # Compliance and requirements
    regulatory_requirements: Optional[str] = Field(None)
    environmental_constraints: Optional[str] = Field(None)
    
    @validator('name')
    def validate_name(cls, v):
        """Validate and normalize project name."""
        if v is not None:
            return v.strip()
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code."""
        if v is not None:
            allowed_currencies = ['USD', 'EUR', 'GBP', 'AUD', 'ZAR']
            if v.upper() not in allowed_currencies:
                raise ValueError(f'Currency must be one of: {", ".join(allowed_currencies)}')
            return v.upper()
        return v


class ProjectResponse(ProjectBase, TimestampSchema):
    """Schema for project response data."""
    id: str = Field(..., description="Project ID")
    owner_id: str = Field(..., description="Project owner ID")
    status: ProjectStatus = Field(..., description="Project status")
    
    # Additional computed fields
    progress_percentage: Optional[float] = Field(None, ge=0, le=100, description="Project progress percentage")
    actual_completion_date: Optional[date] = Field(None, description="Actual completion date")
    
    # Design and calculation counts
    design_count: int = Field(default=0, description="Number of solar designs")
    calculation_count: int = Field(default=0, description="Number of calculations")
    
    # Financial calculations
    estimated_roi: Optional[float] = Field(None, description="Estimated ROI percentage")
    payback_period: Optional[float] = Field(None, description="Payback period in years")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Project tags")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom fields")
    
    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    """Schema for project summary information."""
    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    status: ProjectStatus = Field(..., description="Project status")
    project_type: ProjectType = Field(..., description="Project type")
    priority: ProjectPriority = Field(..., description="Project priority")
    progress_percentage: Optional[float] = Field(None, description="Progress percentage")
    target_capacity: Optional[float] = Field(None, description="Target capacity in kW")
    budget: Optional[Decimal] = Field(None, description="Project budget")
    currency: str = Field(..., description="Currency code")
    start_date: Optional[date] = Field(None, description="Start date")
    target_completion_date: Optional[date] = Field(None, description="Target completion date")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    """Schema for paginated project list."""
    projects: List[ProjectSummary]
    total: int = Field(..., description="Total number of projects")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


class ProjectFilter(BaseModel):
    """Schema for project filtering and search."""
    search: Optional[str] = Field(None, description="Search term for name/description")
    status: Optional[List[ProjectStatus]] = Field(None, description="Filter by status")
    project_type: Optional[List[ProjectType]] = Field(None, description="Filter by type")
    priority: Optional[List[ProjectPriority]] = Field(None, description="Filter by priority")
    owner_id: Optional[str] = Field(None, description="Filter by owner")
    country: Optional[str] = Field(None, description="Filter by country")
    min_budget: Optional[Decimal] = Field(None, description="Minimum budget")
    max_budget: Optional[Decimal] = Field(None, description="Maximum budget")
    start_date_from: Optional[date] = Field(None, description="Start date from")
    start_date_to: Optional[date] = Field(None, description="Start date to")
    completion_date_from: Optional[date] = Field(None, description="Completion date from")
    completion_date_to: Optional[date] = Field(None, description="Completion date to")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    
    # Sorting
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", description="Sort order (asc/desc)")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v.lower() not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v.lower()


class ProjectStats(BaseModel):
    """Schema for project statistics."""
    total_projects: int = Field(..., description="Total number of projects")
    active_projects: int = Field(..., description="Number of active projects")
    completed_projects: int = Field(..., description="Number of completed projects")
    draft_projects: int = Field(..., description="Number of draft projects")
    total_capacity: Optional[float] = Field(None, description="Total capacity across all projects")
    total_budget: Optional[Decimal] = Field(None, description="Total budget across all projects")
    average_project_size: Optional[float] = Field(None, description="Average project capacity")
    projects_by_type: Dict[str, int] = Field(default_factory=dict, description="Projects grouped by type")
    projects_by_status: Dict[str, int] = Field(default_factory=dict, description="Projects grouped by status")
    projects_by_country: Dict[str, int] = Field(default_factory=dict, description="Projects grouped by country")


class ProjectLocationUpdate(BaseModel):
    """Schema for updating project location."""
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class ProjectTagsUpdate(BaseModel):
    """Schema for updating project tags."""
    tags: List[str] = Field(..., description="List of tags")
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate and normalize tags."""
        # Remove duplicates and normalize
        normalized_tags = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and tag not in normalized_tags:
                normalized_tags.append(tag)
        return normalized_tags


class ProjectCustomFieldsUpdate(BaseModel):
    """Schema for updating project custom fields."""
    custom_fields: Dict[str, Any] = Field(..., description="Custom fields dictionary")


class ProjectStatusUpdate(BaseModel):
    """Schema for updating project status."""
    status: ProjectStatus = Field(..., description="New project status")
    reason: Optional[str] = Field(None, description="Reason for status change")