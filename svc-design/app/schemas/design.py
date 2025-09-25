"""Design schemas for the Design Service.

This module contains Pydantic schemas for design-related request/response models,
including designs, versions, approvals, comments, attachments, tags, and shares.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from ..models.design import ApprovalStatus, DesignStatus, DesignType, SharePermission
from .base import (
    AddressSchema,
    AuditSchema,
    BaseSchema,
    ContactSchema,
    FileSchema,
    FilterParams,
    GeometrySchema,
    MetadataSchema,
    OrganizationSchema,
    ProjectSchema,
    TimestampSchema,
    UUIDSchema,
)


class DesignBase(BaseSchema):
    """Base design schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Design name")
    description: Optional[str] = Field(None, description="Design description")
    design_type: DesignType = Field(..., description="Type of design")
    status: DesignStatus = Field(DesignStatus.DRAFT, description="Design status")


class DesignCreate(DesignBase, ProjectSchema, MetadataSchema):
    """Schema for creating a new design."""
    
    # Site information
    site_name: Optional[str] = Field(None, max_length=255, description="Site name")
    site_address: Optional[AddressSchema] = Field(None, description="Site address")
    site_coordinates: Optional[GeometrySchema] = Field(None, description="Site coordinates")
    site_area_sqm: Optional[float] = Field(None, gt=0, description="Site area in square meters")
    site_elevation_m: Optional[float] = Field(None, description="Site elevation in meters")
    
    # System specifications
    system_capacity_kw: Optional[float] = Field(None, gt=0, description="System capacity in kW")
    module_count: Optional[int] = Field(None, gt=0, description="Number of modules")
    module_power_w: Optional[float] = Field(None, gt=0, description="Module power in watts")
    inverter_count: Optional[int] = Field(None, gt=0, description="Number of inverters")
    inverter_power_kw: Optional[float] = Field(None, gt=0, description="Inverter power in kW")
    
    # Performance estimates
    annual_energy_kwh: Optional[float] = Field(None, gt=0, description="Annual energy production in kWh")
    capacity_factor: Optional[float] = Field(None, ge=0, le=1, description="Capacity factor")
    performance_ratio: Optional[float] = Field(None, ge=0, le=1, description="Performance ratio")
    
    # Financial estimates
    total_cost: Optional[Decimal] = Field(None, gt=0, description="Total system cost")
    cost_per_watt: Optional[Decimal] = Field(None, gt=0, description="Cost per watt")
    payback_years: Optional[float] = Field(None, gt=0, description="Payback period in years")
    irr_percent: Optional[float] = Field(None, description="Internal rate of return")
    npv: Optional[Decimal] = Field(None, description="Net present value")
    
    # Design data
    design_data: Optional[Dict[str, Any]] = Field(None, description="Design-specific data")
    
    # Client information
    client_contact: Optional[ContactSchema] = Field(None, description="Client contact information")
    
    # Tags
    tags: Optional[List[str]] = Field(None, description="Design tags")


class DesignUpdate(BaseSchema):
    """Schema for updating an existing design."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Design name")
    description: Optional[str] = Field(None, description="Design description")
    status: Optional[DesignStatus] = Field(None, description="Design status")
    
    # Site information
    site_name: Optional[str] = Field(None, max_length=255, description="Site name")
    site_address: Optional[AddressSchema] = Field(None, description="Site address")
    site_coordinates: Optional[GeometrySchema] = Field(None, description="Site coordinates")
    site_area_sqm: Optional[float] = Field(None, gt=0, description="Site area in square meters")
    site_elevation_m: Optional[float] = Field(None, description="Site elevation in meters")
    
    # System specifications
    system_capacity_kw: Optional[float] = Field(None, gt=0, description="System capacity in kW")
    module_count: Optional[int] = Field(None, gt=0, description="Number of modules")
    module_power_w: Optional[float] = Field(None, gt=0, description="Module power in watts")
    inverter_count: Optional[int] = Field(None, gt=0, description="Number of inverters")
    inverter_power_kw: Optional[float] = Field(None, gt=0, description="Inverter power in kW")
    
    # Performance estimates
    annual_energy_kwh: Optional[float] = Field(None, gt=0, description="Annual energy production in kWh")
    capacity_factor: Optional[float] = Field(None, ge=0, le=1, description="Capacity factor")
    performance_ratio: Optional[float] = Field(None, ge=0, le=1, description="Performance ratio")
    
    # Financial estimates
    total_cost: Optional[Decimal] = Field(None, gt=0, description="Total system cost")
    cost_per_watt: Optional[Decimal] = Field(None, gt=0, description="Cost per watt")
    payback_years: Optional[float] = Field(None, gt=0, description="Payback period in years")
    irr_percent: Optional[float] = Field(None, description="Internal rate of return")
    npv: Optional[Decimal] = Field(None, description="Net present value")
    
    # Design data
    design_data: Optional[Dict[str, Any]] = Field(None, description="Design-specific data")
    
    # Client information
    client_contact: Optional[ContactSchema] = Field(None, description="Client contact information")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DesignResponse(
    DesignBase,
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    ProjectSchema,
    MetadataSchema,
):
    """Schema for design response."""
    
    # Site information
    site_name: Optional[str] = Field(None, description="Site name")
    site_address: Optional[AddressSchema] = Field(None, description="Site address")
    site_coordinates: Optional[GeometrySchema] = Field(None, description="Site coordinates")
    site_area_sqm: Optional[float] = Field(None, description="Site area in square meters")
    site_elevation_m: Optional[float] = Field(None, description="Site elevation in meters")
    
    # System specifications
    system_capacity_kw: Optional[float] = Field(None, description="System capacity in kW")
    module_count: Optional[int] = Field(None, description="Number of modules")
    module_power_w: Optional[float] = Field(None, description="Module power in watts")
    inverter_count: Optional[int] = Field(None, description="Number of inverters")
    inverter_power_kw: Optional[float] = Field(None, description="Inverter power in kW")
    
    # Performance estimates
    annual_energy_kwh: Optional[float] = Field(None, description="Annual energy production in kWh")
    capacity_factor: Optional[float] = Field(None, description="Capacity factor")
    performance_ratio: Optional[float] = Field(None, description="Performance ratio")
    
    # Financial estimates
    total_cost: Optional[Decimal] = Field(None, description="Total system cost")
    cost_per_watt: Optional[Decimal] = Field(None, description="Cost per watt")
    payback_years: Optional[float] = Field(None, description="Payback period in years")
    irr_percent: Optional[float] = Field(None, description="Internal rate of return")
    npv: Optional[Decimal] = Field(None, description="Net present value")
    
    # Design data
    design_data: Optional[Dict[str, Any]] = Field(None, description="Design-specific data")
    
    # Client information
    client_contact: Optional[ContactSchema] = Field(None, description="Client contact information")
    
    # Workflow
    is_approved: bool = Field(False, description="Whether design is approved")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    approved_by: Optional[uuid.UUID] = Field(None, description="User who approved")
    
    # Version tracking
    current_version: str = Field("1.0", description="Current version")
    version_count: int = Field(1, description="Number of versions")
    
    # Relationships (counts)
    comment_count: int = Field(0, description="Number of comments")
    attachment_count: int = Field(0, description="Number of attachments")
    tag_count: int = Field(0, description="Number of tags")
    share_count: int = Field(0, description="Number of shares")


class DesignVersionCreate(BaseSchema):
    """Schema for creating a design version."""
    
    version_notes: Optional[str] = Field(None, description="Version notes")
    design_data: Optional[Dict[str, Any]] = Field(None, description="Version-specific design data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Version metadata")


class DesignVersionResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for design version response."""
    
    design_id: uuid.UUID = Field(..., description="Parent design ID")
    version: str = Field(..., description="Version number")
    version_notes: Optional[str] = Field(None, description="Version notes")
    design_data: Optional[Dict[str, Any]] = Field(None, description="Version-specific design data")
    is_current: bool = Field(False, description="Whether this is the current version")
    parent_version_id: Optional[uuid.UUID] = Field(None, description="Parent version ID")


class DesignApprovalCreate(BaseSchema):
    """Schema for creating a design approval."""
    
    approval_type: str = Field(..., max_length=100, description="Type of approval")
    notes: Optional[str] = Field(None, description="Approval notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Approval metadata")


class DesignApprovalUpdate(BaseSchema):
    """Schema for updating a design approval."""
    
    status: ApprovalStatus = Field(..., description="Approval status")
    notes: Optional[str] = Field(None, description="Approval notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Approval metadata")


class DesignApprovalResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for design approval response."""
    
    design_id: uuid.UUID = Field(..., description="Design ID")
    approval_type: str = Field(..., description="Type of approval")
    status: ApprovalStatus = Field(..., description="Approval status")
    notes: Optional[str] = Field(None, description="Approval notes")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    rejected_at: Optional[datetime] = Field(None, description="Rejection timestamp")


class DesignCommentCreate(BaseSchema):
    """Schema for creating a design comment."""
    
    content: str = Field(..., min_length=1, description="Comment content")
    comment_type: str = Field("general", max_length=50, description="Type of comment")
    parent_comment_id: Optional[uuid.UUID] = Field(None, description="Parent comment ID for replies")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Comment metadata")


class DesignCommentUpdate(BaseSchema):
    """Schema for updating a design comment."""
    
    content: str = Field(..., min_length=1, description="Comment content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Comment metadata")


class DesignCommentResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for design comment response."""
    
    design_id: uuid.UUID = Field(..., description="Design ID")
    content: str = Field(..., description="Comment content")
    comment_type: str = Field(..., description="Type of comment")
    parent_comment_id: Optional[uuid.UUID] = Field(None, description="Parent comment ID")
    is_resolved: bool = Field(False, description="Whether comment is resolved")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    resolved_by: Optional[uuid.UUID] = Field(None, description="User who resolved")
    
    # Reply count
    reply_count: int = Field(0, description="Number of replies")


class DesignAttachmentCreate(BaseSchema):
    """Schema for creating a design attachment."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Attachment name")
    description: Optional[str] = Field(None, description="Attachment description")
    attachment_type: str = Field("document", max_length=50, description="Type of attachment")
    file_info: FileSchema = Field(..., description="File information")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Attachment metadata")


class DesignAttachmentResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for design attachment response."""
    
    design_id: uuid.UUID = Field(..., description="Design ID")
    name: str = Field(..., description="Attachment name")
    description: Optional[str] = Field(None, description="Attachment description")
    attachment_type: str = Field(..., description="Type of attachment")
    file_info: FileSchema = Field(..., description="File information")
    download_count: int = Field(0, description="Number of downloads")
    last_downloaded_at: Optional[datetime] = Field(None, description="Last download timestamp")


class DesignTagCreate(BaseSchema):
    """Schema for creating a design tag."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")
    color: Optional[str] = Field(None, max_length=7, description="Tag color (hex)")
    description: Optional[str] = Field(None, description="Tag description")


class DesignTagResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
):
    """Schema for design tag response."""
    
    design_id: uuid.UUID = Field(..., description="Design ID")
    name: str = Field(..., description="Tag name")
    color: Optional[str] = Field(None, description="Tag color (hex)")
    description: Optional[str] = Field(None, description="Tag description")


class DesignShareCreate(BaseSchema):
    """Schema for creating a design share."""
    
    shared_with_user_id: Optional[uuid.UUID] = Field(None, description="User to share with")
    shared_with_email: Optional[str] = Field(None, description="Email to share with")
    permission: SharePermission = Field(..., description="Share permission level")
    expires_at: Optional[datetime] = Field(None, description="Share expiration")
    message: Optional[str] = Field(None, description="Share message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Share metadata")
    
    @validator('shared_with_user_id', 'shared_with_email')
    def validate_share_target(cls, v, values):
        """Validate that either user_id or email is provided."""
        if not v and not values.get('shared_with_email') and not values.get('shared_with_user_id'):
            raise ValueError('Either shared_with_user_id or shared_with_email must be provided')
        return v


class DesignShareUpdate(BaseSchema):
    """Schema for updating a design share."""
    
    permission: Optional[SharePermission] = Field(None, description="Share permission level")
    expires_at: Optional[datetime] = Field(None, description="Share expiration")
    is_active: Optional[bool] = Field(None, description="Whether share is active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Share metadata")


class DesignShareResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for design share response."""
    
    design_id: uuid.UUID = Field(..., description="Design ID")
    shared_with_user_id: Optional[uuid.UUID] = Field(None, description="User shared with")
    shared_with_email: Optional[str] = Field(None, description="Email shared with")
    permission: SharePermission = Field(..., description="Share permission level")
    is_active: bool = Field(True, description="Whether share is active")
    expires_at: Optional[datetime] = Field(None, description="Share expiration")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access timestamp")
    access_count: int = Field(0, description="Number of accesses")
    message: Optional[str] = Field(None, description="Share message")


class DesignListResponse(BaseSchema):
    """Schema for design list response with pagination."""
    
    items: List[DesignResponse] = Field(..., description="List of designs")
    total: int = Field(..., description="Total number of designs")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class DesignFilterParams(FilterParams):
    """Design-specific filtering parameters."""
    
    design_type: Optional[DesignType] = Field(None, description="Filter by design type")
    status: Optional[DesignStatus] = Field(None, description="Filter by status")
    project_id: Optional[uuid.UUID] = Field(None, description="Filter by project")
    created_by: Optional[uuid.UUID] = Field(None, description="Filter by creator")
    is_approved: Optional[bool] = Field(None, description="Filter by approval status")
    min_capacity_kw: Optional[float] = Field(None, gt=0, description="Minimum system capacity")
    max_capacity_kw: Optional[float] = Field(None, gt=0, description="Maximum system capacity")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


class DesignComparisonRequest(BaseSchema):
    """Schema for design comparison request."""
    
    design_ids: List[uuid.UUID] = Field(..., min_items=2, max_items=5, description="Designs to compare")
    comparison_fields: Optional[List[str]] = Field(None, description="Fields to compare")
    include_financial: bool = Field(True, description="Include financial comparison")
    include_performance: bool = Field(True, description="Include performance comparison")
    include_technical: bool = Field(True, description="Include technical comparison")


class DesignComparisonResponse(BaseSchema):
    """Schema for design comparison response."""
    
    designs: List[DesignResponse] = Field(..., description="Compared designs")
    comparison_data: Dict[str, Any] = Field(..., description="Comparison analysis")
    summary: Dict[str, Any] = Field(..., description="Comparison summary")
    recommendations: Optional[List[str]] = Field(None, description="Recommendations")


class DesignValidationRequest(BaseSchema):
    """Schema for design validation request."""
    
    validation_rules: Optional[List[str]] = Field(None, description="Specific validation rules")
    include_warnings: bool = Field(True, description="Include warnings in validation")
    strict_mode: bool = Field(False, description="Use strict validation mode")


class DesignValidationResponse(BaseSchema):
    """Schema for design validation response."""
    
    is_valid: bool = Field(..., description="Whether design is valid")
    errors: List[Dict[str, Any]] = Field(..., description="Validation errors")
    warnings: List[Dict[str, Any]] = Field(..., description="Validation warnings")
    score: Optional[float] = Field(None, description="Validation score (0-100)")
    recommendations: List[str] = Field(..., description="Improvement recommendations")


class DesignPerformanceRequest(BaseSchema):
    """Schema for design performance calculation request."""
    
    weather_data_source: Optional[str] = Field(None, description="Weather data source")
    calculation_method: str = Field("standard", description="Calculation method")
    include_losses: bool = Field(True, description="Include system losses")
    include_degradation: bool = Field(True, description="Include module degradation")
    analysis_years: int = Field(25, gt=0, le=50, description="Analysis period in years")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class DesignPerformanceResponse(BaseSchema):
    """Schema for design performance calculation response."""
    
    annual_energy_kwh: float = Field(..., description="Annual energy production")
    monthly_energy_kwh: List[float] = Field(..., description="Monthly energy production")
    capacity_factor: float = Field(..., description="Capacity factor")
    performance_ratio: float = Field(..., description="Performance ratio")
    specific_yield_kwh_kwp: float = Field(..., description="Specific yield")
    losses: Dict[str, float] = Field(..., description="System losses breakdown")
    lifetime_energy_kwh: float = Field(..., description="Lifetime energy production")
    degradation_profile: List[float] = Field(..., description="Annual degradation profile")
    calculation_details: Dict[str, Any] = Field(..., description="Detailed calculation results")