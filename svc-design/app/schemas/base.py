"""Base schemas for the Design Service.

This module contains base Pydantic schemas that are used across
all other schema modules for consistent request/response handling.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# Type variable for generic responses
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )


class UUIDSchema(BaseSchema):
    """Schema with UUID field."""
    
    id: uuid.UUID = Field(..., description="Unique identifier")


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SoftDeleteSchema(BaseSchema):
    """Schema with soft delete fields."""
    
    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    is_deleted: bool = Field(False, description="Soft delete flag")


class AuditSchema(BaseSchema):
    """Schema with audit fields."""
    
    created_by: uuid.UUID = Field(..., description="User who created the record")
    updated_by: Optional[uuid.UUID] = Field(None, description="User who last updated the record")
    deleted_by: Optional[uuid.UUID] = Field(None, description="User who deleted the record")


class OrganizationSchema(BaseSchema):
    """Schema with organization field."""
    
    organization_id: uuid.UUID = Field(..., description="Organization identifier")


class ProjectSchema(BaseSchema):
    """Schema with project field."""
    
    project_id: uuid.UUID = Field(..., description="Project identifier")


class MetadataSchema(BaseSchema):
    """Schema with metadata field."""
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BaseResponse(BaseSchema, Generic[T]):
    """Base response schema."""
    
    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[T] = Field(None, description="Response data")


class SuccessResponse(BaseResponse[T]):
    """Success response schema."""
    
    success: bool = Field(True, description="Operation success status")


class ErrorResponse(BaseSchema):
    """Error response schema."""
    
    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class ListResponse(BaseResponse[List[T]]):
    """List response schema."""
    
    count: int = Field(..., description="Total number of items")
    data: List[T] = Field(..., description="List of items")


class PaginatedResponse(BaseResponse[List[T]]):
    """Paginated response schema."""
    
    count: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    data: List[T] = Field(..., description="List of items for current page")


class PaginationParams(BaseSchema):
    """Pagination parameters schema."""
    
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size


# Alias for backward compatibility
PaginationSchema = PaginationParams


class SortParams(BaseSchema):
    """Sorting parameters schema."""
    
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class FilterParams(BaseSchema):
    """Base filtering parameters schema."""
    
    search: Optional[str] = Field(None, description="Search query")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date (after)")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date (before)")
    updated_after: Optional[datetime] = Field(None, description="Filter by update date (after)")
    updated_before: Optional[datetime] = Field(None, description="Filter by update date (before)")
    include_deleted: bool = Field(False, description="Include soft-deleted records")


class GeometrySchema(BaseSchema):
    """Geometry schema for spatial data."""
    
    type: str = Field(..., description="Geometry type (Point, Polygon, etc.)")
    coordinates: List[Any] = Field(..., description="Geometry coordinates")
    crs: Optional[Dict[str, Any]] = Field(None, description="Coordinate reference system")


class AddressSchema(BaseSchema):
    """Address schema."""
    
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State or province")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: str = Field(..., description="Country code (ISO 3166-1 alpha-2)")
    formatted: Optional[str] = Field(None, description="Formatted address string")


class ContactSchema(BaseSchema):
    """Contact information schema."""
    
    name: Optional[str] = Field(None, description="Contact name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    company: Optional[str] = Field(None, description="Company name")
    title: Optional[str] = Field(None, description="Job title")


class FileSchema(BaseSchema):
    """File information schema."""
    
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="File storage path")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    file_hash: Optional[str] = Field(None, description="File hash (SHA-256)")
    upload_date: datetime = Field(..., description="Upload timestamp")


class HealthCheckResponse(BaseSchema):
    """Health check response schema."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    checks: Dict[str, Any] = Field(..., description="Individual health checks")


class ServiceInfoResponse(BaseSchema):
    """Service information response schema."""
    
    name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    description: str = Field(..., description="Service description")
    environment: str = Field(..., description="Environment (dev, staging, prod)")
    build_info: Dict[str, Any] = Field(..., description="Build information")
    configuration: Dict[str, Any] = Field(..., description="Service configuration")
    features: List[str] = Field(..., description="Enabled features")


class ValidationErrorDetail(BaseSchema):
    """Validation error detail schema."""
    
    field: str = Field(..., description="Field name")
    message: str = Field(..., description="Error message")
    value: Any = Field(None, description="Invalid value")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response schema."""
    
    error_code: str = Field("VALIDATION_ERROR", description="Error code")
    validation_errors: List[ValidationErrorDetail] = Field(
        ..., description="List of validation errors"
    )


class BulkOperationRequest(BaseSchema, Generic[T]):
    """Bulk operation request schema."""
    
    items: List[T] = Field(..., description="List of items to process")
    options: Optional[Dict[str, Any]] = Field(None, description="Operation options")


class BulkOperationResponse(BaseSchema):
    """Bulk operation response schema."""
    
    total_items: int = Field(..., description="Total number of items processed")
    successful_items: int = Field(..., description="Number of successfully processed items")
    failed_items: int = Field(..., description="Number of failed items")
    errors: List[Dict[str, Any]] = Field(..., description="List of errors for failed items")
    results: List[Any] = Field(..., description="Results for successful items")


class AsyncOperationResponse(BaseSchema):
    """Asynchronous operation response schema."""
    
    operation_id: uuid.UUID = Field(..., description="Operation identifier")
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    progress_percent: Optional[float] = Field(None, description="Progress percentage")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    result_url: Optional[str] = Field(None, description="URL to retrieve results")