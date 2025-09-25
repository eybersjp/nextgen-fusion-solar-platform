"""BOM schemas for the Design Service.

This module contains Pydantic schemas for Bill of Materials (BOM) related
request/response models, including BOM, items, components, templates, and cost analysis.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from ..models.bom import (
    BOMStatus,
    ComponentCategory,
    ComponentType,
    CostCategory,
    PriceType,
    UnitType,
)
from .base import (
    AuditSchema,
    BaseSchema,
    FilterParams,
    MetadataSchema,
    OrganizationSchema,
    ProjectSchema,
    TimestampSchema,
    UUIDSchema,
)


class BOMBase(BaseSchema):
    """Base BOM schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="BOM name")
    description: Optional[str] = Field(None, description="BOM description")
    version: str = Field("1.0", description="BOM version")


class BOMCreate(BOMBase, ProjectSchema, MetadataSchema):
    """Schema for creating a new BOM."""
    
    design_id: Optional[uuid.UUID] = Field(None, description="Associated design ID")
    layout_id: Optional[uuid.UUID] = Field(None, description="Associated layout ID")
    template_id: Optional[uuid.UUID] = Field(None, description="BOM template ID")
    
    # System specifications
    system_capacity_kw: float = Field(..., gt=0, description="System capacity in kW")
    module_count: int = Field(..., gt=0, description="Total number of modules")
    inverter_count: int = Field(..., gt=0, description="Total number of inverters")
    
    # Cost parameters
    currency: str = Field("USD", max_length=3, description="Currency code")
    include_labor: bool = Field(True, description="Include labor costs")
    include_markup: bool = Field(True, description="Include markup")
    markup_percent: float = Field(15.0, ge=0, le=100, description="Markup percentage")
    
    # Pricing settings
    use_current_pricing: bool = Field(True, description="Use current market pricing")
    pricing_date: Optional[datetime] = Field(None, description="Pricing reference date")
    
    # Regional settings
    country_code: str = Field("US", max_length=2, description="Country code")
    region: Optional[str] = Field(None, description="Specific region/state")
    
    # Additional parameters
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional BOM parameters")


class BOMUpdate(BaseSchema):
    """Schema for updating a BOM."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="BOM name")
    description: Optional[str] = Field(None, description="BOM description")
    version: Optional[str] = Field(None, description="BOM version")
    status: Optional[BOMStatus] = Field(None, description="BOM status")
    
    # System specifications
    system_capacity_kw: Optional[float] = Field(None, gt=0, description="System capacity in kW")
    module_count: Optional[int] = Field(None, gt=0, description="Total number of modules")
    inverter_count: Optional[int] = Field(None, gt=0, description="Total number of inverters")
    
    # Cost parameters
    currency: Optional[str] = Field(None, max_length=3, description="Currency code")
    include_labor: Optional[bool] = Field(None, description="Include labor costs")
    include_markup: Optional[bool] = Field(None, description="Include markup")
    markup_percent: Optional[float] = Field(None, ge=0, le=100, description="Markup percentage")
    
    # Pricing settings
    use_current_pricing: Optional[bool] = Field(None, description="Use current market pricing")
    pricing_date: Optional[datetime] = Field(None, description="Pricing reference date")
    
    # Regional settings
    country_code: Optional[str] = Field(None, max_length=2, description="Country code")
    region: Optional[str] = Field(None, description="Specific region/state")
    
    # Approval workflow
    approved_by: Optional[uuid.UUID] = Field(None, description="Approved by user ID")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    approval_notes: Optional[str] = Field(None, description="Approval notes")
    
    # Additional parameters
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional BOM parameters")
    metadata: Optional[Dict[str, Any]] = Field(None, description="BOM metadata")


class BOMResponse(
    BOMBase,
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    ProjectSchema,
    MetadataSchema,
):
    """Schema for BOM response."""
    
    design_id: Optional[uuid.UUID] = Field(None, description="Associated design ID")
    layout_id: Optional[uuid.UUID] = Field(None, description="Associated layout ID")
    template_id: Optional[uuid.UUID] = Field(None, description="BOM template ID")
    
    # Status
    status: BOMStatus = Field(..., description="BOM status")
    
    # System specifications
    system_capacity_kw: float = Field(..., description="System capacity in kW")
    module_count: int = Field(..., description="Total number of modules")
    inverter_count: int = Field(..., description="Total number of inverters")
    
    # Cost summary
    total_cost: Decimal = Field(..., description="Total BOM cost")
    material_cost: Decimal = Field(..., description="Total material cost")
    labor_cost: Decimal = Field(..., description="Total labor cost")
    markup_amount: Decimal = Field(..., description="Markup amount")
    
    # Cost breakdown
    cost_per_watt: Decimal = Field(..., description="Cost per watt")
    cost_breakdown: Dict[str, Decimal] = Field(..., description="Cost breakdown by category")
    
    # Cost parameters
    currency: str = Field(..., description="Currency code")
    include_labor: bool = Field(..., description="Include labor costs")
    include_markup: bool = Field(..., description="Include markup")
    markup_percent: float = Field(..., description="Markup percentage")
    
    # Pricing settings
    use_current_pricing: bool = Field(..., description="Use current market pricing")
    pricing_date: Optional[datetime] = Field(None, description="Pricing reference date")
    
    # Regional settings
    country_code: str = Field(..., description="Country code")
    region: Optional[str] = Field(None, description="Specific region/state")
    
    # Approval workflow
    approved_by: Optional[uuid.UUID] = Field(None, description="Approved by user ID")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    approval_notes: Optional[str] = Field(None, description="Approval notes")
    
    # Generation tracking
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    generation_time_seconds: Optional[float] = Field(None, description="Generation time in seconds")
    
    # Additional parameters
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional BOM parameters")
    
    # Relationships (counts)
    item_count: int = Field(0, description="Number of BOM items")
    cost_analysis_count: int = Field(0, description="Number of cost analyses")


class BOMItemCreate(BaseSchema):
    """Schema for creating a BOM item."""
    
    component_id: uuid.UUID = Field(..., description="Component ID")
    quantity: float = Field(..., gt=0, description="Item quantity")
    unit_type: UnitType = Field(..., description="Unit type")
    
    # Pricing
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    price_type: PriceType = Field(..., description="Price type")
    
    # Cost allocation
    cost_category: CostCategory = Field(..., description="Cost category")
    
    # Item details
    description: Optional[str] = Field(None, description="Item description")
    manufacturer_part_number: Optional[str] = Field(None, description="Manufacturer part number")
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    
    # Installation details
    installation_time_hours: Optional[float] = Field(None, ge=0, description="Installation time in hours")
    labor_rate_per_hour: Optional[Decimal] = Field(None, ge=0, description="Labor rate per hour")
    
    # Specifications
    specifications: Optional[Dict[str, Any]] = Field(None, description="Item specifications")
    
    # Notes and metadata
    notes: Optional[str] = Field(None, description="Item notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Item metadata")


class BOMItemUpdate(BaseSchema):
    """Schema for updating a BOM item."""
    
    component_id: Optional[uuid.UUID] = Field(None, description="Component ID")
    quantity: Optional[float] = Field(None, gt=0, description="Item quantity")
    unit_type: Optional[UnitType] = Field(None, description="Unit type")
    
    # Pricing
    unit_price: Optional[Decimal] = Field(None, ge=0, description="Unit price")
    price_type: Optional[PriceType] = Field(None, description="Price type")
    
    # Cost allocation
    cost_category: Optional[CostCategory] = Field(None, description="Cost category")
    
    # Item details
    description: Optional[str] = Field(None, description="Item description")
    manufacturer_part_number: Optional[str] = Field(None, description="Manufacturer part number")
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    
    # Installation details
    installation_time_hours: Optional[float] = Field(None, ge=0, description="Installation time in hours")
    labor_rate_per_hour: Optional[Decimal] = Field(None, ge=0, description="Labor rate per hour")
    
    # Specifications
    specifications: Optional[Dict[str, Any]] = Field(None, description="Item specifications")
    
    # Notes and metadata
    notes: Optional[str] = Field(None, description="Item notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Item metadata")


class BOMItemResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for BOM item response."""
    
    bom_id: uuid.UUID = Field(..., description="Parent BOM ID")
    component_id: uuid.UUID = Field(..., description="Component ID")
    quantity: float = Field(..., description="Item quantity")
    unit_type: UnitType = Field(..., description="Unit type")
    
    # Pricing
    unit_price: Decimal = Field(..., description="Unit price")
    total_price: Decimal = Field(..., description="Total price (quantity * unit_price)")
    price_type: PriceType = Field(..., description="Price type")
    
    # Cost allocation
    cost_category: CostCategory = Field(..., description="Cost category")
    
    # Item details
    description: Optional[str] = Field(None, description="Item description")
    manufacturer_part_number: Optional[str] = Field(None, description="Manufacturer part number")
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    
    # Installation details
    installation_time_hours: Optional[float] = Field(None, description="Installation time in hours")
    labor_rate_per_hour: Optional[Decimal] = Field(None, description="Labor rate per hour")
    total_labor_cost: Optional[Decimal] = Field(None, description="Total labor cost")
    
    # Specifications
    specifications: Optional[Dict[str, Any]] = Field(None, description="Item specifications")
    
    # Notes
    notes: Optional[str] = Field(None, description="Item notes")
    
    # Component information (from relationship)
    component_name: str = Field(..., description="Component name")
    component_category: ComponentCategory = Field(..., description="Component category")
    component_type: ComponentType = Field(..., description="Component type")


class ComponentCreate(BaseSchema):
    """Schema for creating a component."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Component name")
    category: ComponentCategory = Field(..., description="Component category")
    component_type: ComponentType = Field(..., description="Component type")
    description: Optional[str] = Field(None, description="Component description")
    
    # Manufacturer information
    manufacturer: str = Field(..., min_length=1, max_length=255, description="Manufacturer name")
    model_number: str = Field(..., min_length=1, max_length=100, description="Model number")
    part_number: Optional[str] = Field(None, description="Manufacturer part number")
    
    # Specifications
    specifications: Dict[str, Any] = Field(..., description="Component specifications")
    
    # Pricing
    base_price: Decimal = Field(..., ge=0, description="Base price")
    currency: str = Field("USD", max_length=3, description="Currency code")
    price_type: PriceType = Field(..., description="Price type")
    
    # Supplier information
    primary_supplier: Optional[str] = Field(None, description="Primary supplier")
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time in days")
    minimum_order_quantity: Optional[int] = Field(None, ge=1, description="Minimum order quantity")
    
    # Availability
    is_active: bool = Field(True, description="Whether component is active")
    availability_regions: Optional[List[str]] = Field(None, description="Available regions")
    
    # Certifications and compliance
    certifications: Optional[List[str]] = Field(None, description="Component certifications")
    compliance_standards: Optional[List[str]] = Field(None, description="Compliance standards")
    
    # Physical properties
    weight_kg: Optional[float] = Field(None, ge=0, description="Weight in kg")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Dimensions (length, width, height)")
    
    # Warranty
    warranty_years: Optional[float] = Field(None, ge=0, description="Warranty period in years")
    warranty_terms: Optional[str] = Field(None, description="Warranty terms")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Component metadata")





class ComponentUpdate(BaseSchema):
    """Schema for updating a component."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Component name")
    description: Optional[str] = Field(None, description="Component description")
    
    # Manufacturer information
    manufacturer: Optional[str] = Field(None, min_length=1, max_length=255, description="Manufacturer name")
    model_number: Optional[str] = Field(None, min_length=1, max_length=100, description="Model number")
    part_number: Optional[str] = Field(None, description="Manufacturer part number")
    
    # Specifications
    specifications: Optional[Dict[str, Any]] = Field(None, description="Component specifications")
    
    # Pricing
    base_price: Optional[Decimal] = Field(None, ge=0, description="Base price")
    currency: Optional[str] = Field(None, max_length=3, description="Currency code")
    price_type: Optional[PriceType] = Field(None, description="Price type")
    
    # Supplier information
    primary_supplier: Optional[str] = Field(None, description="Primary supplier")
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time in days")
    minimum_order_quantity: Optional[int] = Field(None, ge=1, description="Minimum order quantity")
    
    # Availability
    is_active: Optional[bool] = Field(None, description="Whether component is active")
    availability_regions: Optional[List[str]] = Field(None, description="Available regions")
    
    # Certifications and compliance
    certifications: Optional[List[str]] = Field(None, description="Component certifications")
    compliance_standards: Optional[List[str]] = Field(None, description="Compliance standards")
    
    # Physical properties
    weight_kg: Optional[float] = Field(None, ge=0, description="Weight in kg")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Dimensions")
    
    # Warranty
    warranty_years: Optional[float] = Field(None, ge=0, description="Warranty period in years")
    warranty_terms: Optional[str] = Field(None, description="Warranty terms")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Component metadata")


class ComponentResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    MetadataSchema,
):
    """Schema for component response."""
    
    name: str = Field(..., description="Component name")
    category: ComponentCategory = Field(..., description="Component category")
    component_type: ComponentType = Field(..., description="Component type")
    description: Optional[str] = Field(None, description="Component description")
    
    # Manufacturer information
    manufacturer: str = Field(..., description="Manufacturer name")
    model_number: str = Field(..., description="Model number")
    part_number: Optional[str] = Field(None, description="Manufacturer part number")
    
    # Specifications
    specifications: Dict[str, Any] = Field(..., description="Component specifications")
    
    # Pricing
    base_price: Decimal = Field(..., description="Base price")
    currency: str = Field(..., description="Currency code")
    price_type: PriceType = Field(..., description="Price type")
    
    # Supplier information
    primary_supplier: Optional[str] = Field(None, description="Primary supplier")
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    lead_time_days: Optional[int] = Field(None, description="Lead time in days")
    minimum_order_quantity: Optional[int] = Field(None, description="Minimum order quantity")
    
    # Availability
    is_active: bool = Field(..., description="Whether component is active")
    availability_regions: Optional[List[str]] = Field(None, description="Available regions")
    
    # Certifications and compliance
    certifications: Optional[List[str]] = Field(None, description="Component certifications")
    compliance_standards: Optional[List[str]] = Field(None, description="Compliance standards")
    
    # Physical properties
    weight_kg: Optional[float] = Field(None, description="Weight in kg")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Dimensions")
    
    # Warranty
    warranty_years: Optional[float] = Field(None, description="Warranty period in years")
    warranty_terms: Optional[str] = Field(None, description="Warranty terms")
    
    # Usage statistics
    usage_count: int = Field(0, description="Number of times used in BOMs")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")


class SupplierCreate(BaseSchema):
    """Schema for creating a supplier."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Supplier name")
    description: Optional[str] = Field(None, description="Supplier description")
    
    # Contact information
    contact_person: Optional[str] = Field(None, description="Primary contact person")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    website: Optional[str] = Field(None, description="Supplier website")
    
    # Address information
    address: Optional[str] = Field(None, description="Supplier address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: str = Field(..., description="Country")
    postal_code: Optional[str] = Field(None, description="Postal code")
    
    # Business information
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    business_registration: Optional[str] = Field(None, description="Business registration number")
    
    # Supplier capabilities
    product_categories: List[str] = Field(..., description="Product categories")
    service_regions: List[str] = Field(..., description="Service regions")
    
    # Terms and conditions
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    shipping_terms: Optional[str] = Field(None, description="Shipping terms")
    minimum_order_value: Optional[Decimal] = Field(None, ge=0, description="Minimum order value")
    
    # Quality and certifications
    certifications: Optional[List[str]] = Field(None, description="Supplier certifications")
    quality_rating: Optional[float] = Field(None, ge=0, le=10, description="Quality rating (0-10)")
    
    # Status
    is_active: bool = Field(True, description="Whether supplier is active")
    is_preferred: bool = Field(False, description="Whether supplier is preferred")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Supplier metadata")


class SupplierUpdate(BaseSchema):
    """Schema for updating a supplier."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Supplier name")
    description: Optional[str] = Field(None, description="Supplier description")
    
    # Contact information
    contact_person: Optional[str] = Field(None, description="Primary contact person")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    website: Optional[str] = Field(None, description="Supplier website")
    
    # Address information
    address: Optional[str] = Field(None, description="Supplier address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal code")
    
    # Business information
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    business_registration: Optional[str] = Field(None, description="Business registration number")
    
    # Supplier capabilities
    product_categories: Optional[List[str]] = Field(None, description="Product categories")
    service_regions: Optional[List[str]] = Field(None, description="Service regions")
    
    # Terms and conditions
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    shipping_terms: Optional[str] = Field(None, description="Shipping terms")
    minimum_order_value: Optional[Decimal] = Field(None, ge=0, description="Minimum order value")
    
    # Quality and certifications
    certifications: Optional[List[str]] = Field(None, description="Supplier certifications")
    quality_rating: Optional[float] = Field(None, ge=0, le=10, description="Quality rating (0-10)")
    
    # Status
    is_active: Optional[bool] = Field(None, description="Whether supplier is active")
    is_preferred: Optional[bool] = Field(None, description="Whether supplier is preferred")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Supplier metadata")


class SupplierResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    MetadataSchema,
):
    """Schema for supplier response."""
    
    name: str = Field(..., description="Supplier name")
    description: Optional[str] = Field(None, description="Supplier description")
    
    # Contact information
    contact_person: Optional[str] = Field(None, description="Primary contact person")
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    website: Optional[str] = Field(None, description="Supplier website")
    
    # Address information
    address: Optional[str] = Field(None, description="Supplier address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: str = Field(..., description="Country")
    postal_code: Optional[str] = Field(None, description="Postal code")
    
    # Business information
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    business_registration: Optional[str] = Field(None, description="Business registration number")
    
    # Supplier capabilities
    product_categories: List[str] = Field(..., description="Product categories")
    service_regions: List[str] = Field(..., description="Service regions")
    
    # Terms and conditions
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    shipping_terms: Optional[str] = Field(None, description="Shipping terms")
    minimum_order_value: Optional[Decimal] = Field(None, description="Minimum order value")
    
    # Quality and certifications
    certifications: Optional[List[str]] = Field(None, description="Supplier certifications")
    quality_rating: Optional[float] = Field(None, description="Quality rating (0-10)")
    
    # Status
    is_active: bool = Field(..., description="Whether supplier is active")
    is_preferred: bool = Field(..., description="Whether supplier is preferred")
    
    # Performance metrics
    total_orders: int = Field(0, description="Total number of orders")
    on_time_delivery_rate: Optional[float] = Field(None, description="On-time delivery rate (0-1)")
    average_lead_time_days: Optional[float] = Field(None, description="Average lead time in days")
    last_order_date: Optional[datetime] = Field(None, description="Last order date")


class PriceListCreate(BaseSchema):
    """Schema for creating a price list."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Price list name")
    description: Optional[str] = Field(None, description="Price list description")
    
    # Price list details
    supplier_id: Optional[uuid.UUID] = Field(None, description="Associated supplier ID")
    currency: str = Field("USD", max_length=3, description="Currency code")
    
    # Validity period
    valid_from: datetime = Field(..., description="Valid from date")
    valid_to: Optional[datetime] = Field(None, description="Valid to date")
    
    # Price list settings
    is_active: bool = Field(True, description="Whether price list is active")
    is_default: bool = Field(False, description="Whether this is the default price list")
    
    # Regional settings
    applicable_regions: Optional[List[str]] = Field(None, description="Applicable regions")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Price list metadata")


class PriceListUpdate(BaseSchema):
    """Schema for updating a price list."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Price list name")
    description: Optional[str] = Field(None, description="Price list description")
    
    # Price list details
    supplier_id: Optional[uuid.UUID] = Field(None, description="Associated supplier ID")
    currency: Optional[str] = Field(None, max_length=3, description="Currency code")
    
    # Validity period
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_to: Optional[datetime] = Field(None, description="Valid to date")
    
    # Price list settings
    is_active: Optional[bool] = Field(None, description="Whether price list is active")
    is_default: Optional[bool] = Field(None, description="Whether this is the default price list")
    
    # Regional settings
    applicable_regions: Optional[List[str]] = Field(None, description="Applicable regions")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Price list metadata")


class PriceListResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    MetadataSchema,
):
    """Schema for price list response."""
    
    name: str = Field(..., description="Price list name")
    description: Optional[str] = Field(None, description="Price list description")
    
    # Price list details
    supplier_id: Optional[uuid.UUID] = Field(None, description="Associated supplier ID")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    currency: str = Field(..., description="Currency code")
    
    # Validity period
    valid_from: datetime = Field(..., description="Valid from date")
    valid_to: Optional[datetime] = Field(None, description="Valid to date")
    
    # Price list settings
    is_active: bool = Field(..., description="Whether price list is active")
    is_default: bool = Field(..., description="Whether this is the default price list")
    
    # Regional settings
    applicable_regions: Optional[List[str]] = Field(None, description="Applicable regions")
    
    # Statistics
    total_items: int = Field(0, description="Total number of items in price list")
    last_updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class PriceListItemCreate(BaseSchema):
    """Schema for creating a price list item."""
    
    price_list_id: uuid.UUID = Field(..., description="Price list ID")
    component_id: uuid.UUID = Field(..., description="Component ID")
    
    # Pricing details
    unit_price: Decimal = Field(..., ge=0, description="Unit price")
    currency: str = Field("USD", max_length=3, description="Currency code")
    
    # Quantity breaks
    minimum_quantity: int = Field(1, ge=1, description="Minimum quantity")
    maximum_quantity: Optional[int] = Field(None, description="Maximum quantity")
    
    # Supplier details
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time in days")
    
    # Validity
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_to: Optional[datetime] = Field(None, description="Valid to date")
    
    # Additional details
    notes: Optional[str] = Field(None, description="Item notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Item metadata")


class PriceListItemUpdate(BaseSchema):
    """Schema for updating a price list item."""
    
    # Pricing details
    unit_price: Optional[Decimal] = Field(None, ge=0, description="Unit price")
    currency: Optional[str] = Field(None, max_length=3, description="Currency code")
    
    # Quantity breaks
    minimum_quantity: Optional[int] = Field(None, ge=1, description="Minimum quantity")
    maximum_quantity: Optional[int] = Field(None, description="Maximum quantity")
    
    # Supplier details
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    lead_time_days: Optional[int] = Field(None, ge=0, description="Lead time in days")
    
    # Validity
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_to: Optional[datetime] = Field(None, description="Valid to date")
    
    # Additional details
    notes: Optional[str] = Field(None, description="Item notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Item metadata")


class PriceListItemResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for price list item response."""
    
    price_list_id: uuid.UUID = Field(..., description="Price list ID")
    component_id: uuid.UUID = Field(..., description="Component ID")
    
    # Pricing details
    unit_price: Decimal = Field(..., description="Unit price")
    currency: str = Field(..., description="Currency code")
    
    # Quantity breaks
    minimum_quantity: int = Field(..., description="Minimum quantity")
    maximum_quantity: Optional[int] = Field(None, description="Maximum quantity")
    
    # Supplier details
    supplier_part_number: Optional[str] = Field(None, description="Supplier part number")
    lead_time_days: Optional[int] = Field(None, description="Lead time in days")
    
    # Validity
    valid_from: Optional[datetime] = Field(None, description="Valid from date")
    valid_to: Optional[datetime] = Field(None, description="Valid to date")
    
    # Component information (from relationship)
    component_name: str = Field(..., description="Component name")
    component_category: str = Field(..., description="Component category")
    manufacturer: str = Field(..., description="Manufacturer name")
    model_number: str = Field(..., description="Model number")
    
    # Additional details
    notes: Optional[str] = Field(None, description="Item notes")


class BOMTemplateCreate(BaseSchema):
    """Schema for creating a BOM template."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    
    # Template categorization
    system_type: str = Field(..., description="System type (residential, commercial, utility)")
    capacity_range_min_kw: float = Field(..., gt=0, description="Minimum capacity range in kW")
    capacity_range_max_kw: float = Field(..., gt=0, description="Maximum capacity range in kW")
    
    # Regional applicability
    applicable_regions: List[str] = Field(..., description="Applicable regions/countries")
    
    # Template configuration
    default_components: List[Dict[str, Any]] = Field(..., description="Default component list")
    variable_components: Optional[List[Dict[str, Any]]] = Field(None, description="Variable components")
    
    # Cost parameters
    default_markup_percent: float = Field(15.0, ge=0, le=100, description="Default markup percentage")
    include_labor_by_default: bool = Field(True, description="Include labor by default")
    
    # Template settings
    is_public: bool = Field(False, description="Whether template is public")
    is_active: bool = Field(True, description="Whether template is active")
    
    # Validation rules
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Template validation rules")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")
    
    @validator('capacity_range_max_kw')
    def validate_capacity_range(cls, v, values):
        """Validate that max capacity is greater than min capacity."""
        min_capacity = values.get('capacity_range_min_kw')
        if min_capacity and v <= min_capacity:
            raise ValueError('Maximum capacity must be greater than minimum capacity')
        return v


class BOMTemplateResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    OrganizationSchema,
    MetadataSchema,
):
    """Schema for BOM template response."""
    
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    
    # Template categorization
    system_type: str = Field(..., description="System type")
    capacity_range_min_kw: float = Field(..., description="Minimum capacity range in kW")
    capacity_range_max_kw: float = Field(..., description="Maximum capacity range in kW")
    
    # Regional applicability
    applicable_regions: List[str] = Field(..., description="Applicable regions/countries")
    
    # Template configuration
    default_components: List[Dict[str, Any]] = Field(..., description="Default component list")
    variable_components: Optional[List[Dict[str, Any]]] = Field(None, description="Variable components")
    
    # Cost parameters
    default_markup_percent: float = Field(..., description="Default markup percentage")
    include_labor_by_default: bool = Field(..., description="Include labor by default")
    
    # Template settings
    is_public: bool = Field(..., description="Whether template is public")
    is_active: bool = Field(..., description="Whether template is active")
    
    # Validation rules
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Template validation rules")
    
    # Usage statistics
    usage_count: int = Field(0, description="Number of times used")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")


class BOMTemplateUpdate(BaseSchema):
    """Schema for updating a BOM template."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    
    # Template categorization
    system_type: Optional[str] = Field(None, description="System type (residential, commercial, utility)")
    capacity_range_min_kw: Optional[float] = Field(None, gt=0, description="Minimum capacity range in kW")
    capacity_range_max_kw: Optional[float] = Field(None, gt=0, description="Maximum capacity range in kW")
    
    # Regional applicability
    applicable_regions: Optional[List[str]] = Field(None, description="Applicable regions/countries")
    
    # Template configuration
    default_components: Optional[List[Dict[str, Any]]] = Field(None, description="Default component list")
    variable_components: Optional[List[Dict[str, Any]]] = Field(None, description="Variable components")
    
    # Cost parameters
    default_markup_percent: Optional[float] = Field(None, ge=0, le=100, description="Default markup percentage")
    include_labor_by_default: Optional[bool] = Field(None, description="Include labor by default")
    
    # Template settings
    is_public: Optional[bool] = Field(None, description="Whether template is public")
    is_active: Optional[bool] = Field(None, description="Whether template is active")
    
    # Validation rules
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Template validation rules")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")
    
    @validator('capacity_range_max_kw')
    def validate_capacity_range(cls, v, values):
        """Validate that max capacity is greater than min capacity."""
        min_capacity = values.get('capacity_range_min_kw')
        if min_capacity and v and v <= min_capacity:
            raise ValueError('Maximum capacity must be greater than minimum capacity')
        return v


class BOMCostAnalysisCreate(BaseSchema):
    """Schema for creating a BOM cost analysis."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Analysis name")
    description: Optional[str] = Field(None, description="Analysis description")
    
    # Analysis parameters
    analysis_parameters: Dict[str, Any] = Field(..., description="Analysis parameters")
    
    # Scenarios
    base_scenario: Dict[str, Any] = Field(..., description="Base scenario configuration")
    alternative_scenarios: Optional[List[Dict[str, Any]]] = Field(None, description="Alternative scenarios")
    
    # Analysis settings
    include_sensitivity_analysis: bool = Field(True, description="Include sensitivity analysis")
    include_risk_analysis: bool = Field(False, description="Include risk analysis")
    
    # Currency and regional settings
    currency: str = Field("USD", max_length=3, description="Analysis currency")
    region: Optional[str] = Field(None, description="Analysis region")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Analysis metadata")


class BOMCostAnalysisUpdate(BaseSchema):
    """Schema for updating a BOM cost analysis."""
    
    name: Optional[str] = Field(None, description="Analysis name")
    description: Optional[str] = Field(None, description="Analysis description")
    
    # Analysis parameters
    analysis_date: Optional[datetime] = Field(None, description="Analysis date")
    currency: Optional[str] = Field(None, description="Currency code")
    exchange_rate: Optional[Decimal] = Field(None, ge=0, description="Exchange rate")
    
    # Cost breakdown
    material_cost: Optional[Decimal] = Field(None, ge=0, description="Total material cost")
    labor_cost: Optional[Decimal] = Field(None, ge=0, description="Total labor cost")
    overhead_cost: Optional[Decimal] = Field(None, ge=0, description="Total overhead cost")
    shipping_cost: Optional[Decimal] = Field(None, ge=0, description="Total shipping cost")
    tax_cost: Optional[Decimal] = Field(None, ge=0, description="Total tax cost")
    total_cost: Optional[Decimal] = Field(None, ge=0, description="Total cost")
    
    # Margins and pricing
    markup_percentage: Optional[Decimal] = Field(None, ge=0, description="Markup percentage")
    profit_margin: Optional[Decimal] = Field(None, ge=0, description="Profit margin")
    selling_price: Optional[Decimal] = Field(None, ge=0, description="Selling price")
    
    # Analysis results
    cost_per_watt: Optional[Decimal] = Field(None, ge=0, description="Cost per watt")
    cost_per_kwh: Optional[Decimal] = Field(None, ge=0, description="Cost per kWh")
    payback_period_years: Optional[float] = Field(None, ge=0, description="Payback period in years")
    roi_percentage: Optional[Decimal] = Field(None, description="ROI percentage")
    
    # Sensitivity analysis
    sensitivity_analysis: Optional[Dict[str, Any]] = Field(None, description="Sensitivity analysis results")
    
    # Notes and metadata
    notes: Optional[str] = Field(None, description="Analysis notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Analysis metadata")


class BOMCostAnalysisResponse(
    UUIDSchema,
    TimestampSchema,
    AuditSchema,
    MetadataSchema,
):
    """Schema for BOM cost analysis response."""
    
    bom_id: uuid.UUID = Field(..., description="Parent BOM ID")
    name: str = Field(..., description="Analysis name")
    description: Optional[str] = Field(None, description="Analysis description")
    
    # Analysis status
    is_completed: bool = Field(False, description="Whether analysis is completed")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Analysis parameters
    analysis_parameters: Dict[str, Any] = Field(..., description="Analysis parameters")
    
    # Results
    cost_breakdown: Dict[str, Decimal] = Field(..., description="Detailed cost breakdown")
    scenario_comparison: Optional[Dict[str, Any]] = Field(None, description="Scenario comparison results")
    sensitivity_results: Optional[Dict[str, Any]] = Field(None, description="Sensitivity analysis results")
    risk_analysis_results: Optional[Dict[str, Any]] = Field(None, description="Risk analysis results")
    
    # Key metrics
    total_cost: Decimal = Field(..., description="Total cost")
    cost_per_watt: Decimal = Field(..., description="Cost per watt")
    cost_variance_percent: Optional[float] = Field(None, description="Cost variance percentage")
    
    # Recommendations
    recommendations: List[str] = Field(..., description="Cost optimization recommendations")
    potential_savings: Optional[Decimal] = Field(None, description="Potential cost savings")
    
    # Currency and regional settings
    currency: str = Field(..., description="Analysis currency")
    region: Optional[str] = Field(None, description="Analysis region")


class BOMFilterParams(FilterParams):
    """BOM-specific filtering parameters."""
    
    status: Optional[BOMStatus] = Field(None, description="Filter by status")
    design_id: Optional[uuid.UUID] = Field(None, description="Filter by design")
    layout_id: Optional[uuid.UUID] = Field(None, description="Filter by layout")
    project_id: Optional[uuid.UUID] = Field(None, description="Filter by project")
    template_id: Optional[uuid.UUID] = Field(None, description="Filter by template")
    created_by: Optional[uuid.UUID] = Field(None, description="Filter by creator")
    currency: Optional[str] = Field(None, description="Filter by currency")
    country_code: Optional[str] = Field(None, description="Filter by country")
    min_total_cost: Optional[Decimal] = Field(None, description="Minimum total cost")
    max_total_cost: Optional[Decimal] = Field(None, description="Maximum total cost")
    min_capacity_kw: Optional[float] = Field(None, description="Minimum system capacity")
    max_capacity_kw: Optional[float] = Field(None, description="Maximum system capacity")
    has_approval: Optional[bool] = Field(None, description="Filter by approval status")


class BOMGenerationRequest(BaseSchema):
    """Schema for BOM generation request."""
    
    design_id: Optional[uuid.UUID] = Field(None, description="Design ID")
    layout_id: Optional[uuid.UUID] = Field(None, description="Layout ID")
    template_id: Optional[uuid.UUID] = Field(None, description="Template ID")
    
    # Generation parameters
    include_labor: bool = Field(True, description="Include labor costs")
    include_markup: bool = Field(True, description="Include markup")
    markup_percent: float = Field(15.0, ge=0, le=100, description="Markup percentage")
    
    # Regional settings
    country_code: str = Field("US", max_length=2, description="Country code")
    region: Optional[str] = Field(None, description="Specific region")
    currency: str = Field("USD", max_length=3, description="Currency code")
    
    # Component preferences
    preferred_manufacturers: Optional[List[str]] = Field(None, description="Preferred manufacturers")
    component_preferences: Optional[Dict[str, Any]] = Field(None, description="Component preferences")
    
    # Pricing settings
    use_current_pricing: bool = Field(True, description="Use current pricing")
    pricing_date: Optional[datetime] = Field(None, description="Pricing reference date")
    
    # Additional parameters
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")
    
    @validator('layout_id', 'design_id')
    def validate_reference(cls, v, values):
        """Validate that either design_id or layout_id is provided."""
        if not v and not values.get('design_id') and not values.get('layout_id'):
            raise ValueError('Either design_id or layout_id must be provided')
        return v


class BOMGenerationResponse(BaseSchema):
    """Schema for BOM generation response."""
    
    bom_id: uuid.UUID = Field(..., description="Generated BOM ID")
    generation_status: str = Field(..., description="Generation status")
    total_cost: Decimal = Field(..., description="Total BOM cost")
    item_count: int = Field(..., description="Number of items")
    generation_time_seconds: float = Field(..., description="Generation time")
    warnings: List[str] = Field(..., description="Generation warnings")
    recommendations: List[str] = Field(..., description="Optimization recommendations")


class BOMComparisonRequest(BaseSchema):
    """Schema for BOM comparison request."""
    
    bom_ids: List[uuid.UUID] = Field(..., min_items=2, max_items=5, description="BOMs to compare")
    comparison_criteria: List[str] = Field(..., description="Comparison criteria")
    include_detailed_breakdown: bool = Field(True, description="Include detailed breakdown")
    normalize_by_capacity: bool = Field(True, description="Normalize by system capacity")


class BOMComparisonResponse(BaseSchema):
    """Schema for BOM comparison response."""
    
    comparison_id: uuid.UUID = Field(..., description="Comparison ID")
    bom_summaries: List[Dict[str, Any]] = Field(..., description="BOM summaries")
    cost_comparison: Dict[str, Any] = Field(..., description="Cost comparison")
    component_comparison: Dict[str, Any] = Field(..., description="Component comparison")
    recommendations: List[str] = Field(..., description="Comparison recommendations")
    best_value_bom_id: Optional[uuid.UUID] = Field(None, description="Best value BOM ID")


class BOMComparisonResult(BaseSchema):
    """Schema for detailed BOM comparison result."""
    
    comparison_id: uuid.UUID = Field(..., description="Comparison ID")
    bom1_id: uuid.UUID = Field(..., description="First BOM ID")
    bom2_id: uuid.UUID = Field(..., description="Second BOM ID")
    
    # Cost analysis
    cost_difference: Decimal = Field(..., description="Total cost difference")
    cost_difference_percentage: Decimal = Field(..., description="Cost difference percentage")
    material_cost_difference: Decimal = Field(..., description="Material cost difference")
    labor_cost_difference: Decimal = Field(..., description="Labor cost difference")
    
    # Item analysis
    items_added: List[Dict[str, Any]] = Field(..., description="Items added in second BOM")
    items_removed: List[Dict[str, Any]] = Field(..., description="Items removed from first BOM")
    items_modified: List[Dict[str, Any]] = Field(..., description="Items with quantity/price changes")
    items_unchanged: List[Dict[str, Any]] = Field(..., description="Items that remained the same")
    
    # Summary statistics
    total_items_bom1: int = Field(..., description="Total items in first BOM")
    total_items_bom2: int = Field(..., description="Total items in second BOM")
    items_added_count: int = Field(..., description="Number of items added")
    items_removed_count: int = Field(..., description="Number of items removed")
    items_modified_count: int = Field(..., description="Number of items modified")
    
    # Performance metrics
    efficiency_improvement: Optional[Decimal] = Field(None, description="Efficiency improvement percentage")
    sustainability_score_change: Optional[Decimal] = Field(None, description="Sustainability score change")
    
    # Metadata
    comparison_date: datetime = Field(..., description="When comparison was performed")
    comparison_notes: Optional[str] = Field(None, description="Additional comparison notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional comparison metadata")


class BOMExportRequest(BaseSchema):
    """Schema for BOM export request."""
    
    format: str = Field(..., description="Export format (pdf, excel, csv)")
    include_detailed_breakdown: bool = Field(True, description="Include detailed breakdown")
    include_specifications: bool = Field(True, description="Include component specifications")
    include_pricing_details: bool = Field(True, description="Include pricing details")
    include_supplier_info: bool = Field(False, description="Include supplier information")
    template_id: Optional[uuid.UUID] = Field(None, description="Export template ID")
    custom_fields: Optional[List[str]] = Field(None, description="Custom fields to include")


class BOMExportResponse(BaseSchema):
    """Schema for BOM export response."""
    
    export_id: uuid.UUID = Field(description="Export ID")
    file_url: str = Field(description="Download URL for exported file")
    file_name: str = Field(description="Exported file name")
    file_size: int = Field(description="File size in bytes")
    expires_at: datetime = Field(description="URL expiration time")


class BOMTemplateCreate(BaseSchema):
    """Schema for creating a BOM template."""
    
    name: str = Field(description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: str = Field(description="Template category")
    
    # Template configuration
    system_type: str = Field(description="Solar system type")
    capacity_range_min: Optional[float] = Field(None, ge=0, description="Minimum capacity (kW)")
    capacity_range_max: Optional[float] = Field(None, ge=0, description="Maximum capacity (kW)")
    
    # Default components
    default_components: List[Dict[str, Any]] = Field(default_factory=list, description="Default components")
    
    # Template metadata
    tags: List[str] = Field(default_factory=list, description="Template tags")
    is_public: bool = Field(default=False, description="Is template public")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")


class BOMTemplateUpdate(BaseSchema):
    """Schema for updating a BOM template."""
    
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: Optional[str] = Field(None, description="Template category")
    
    # Template configuration
    system_type: Optional[str] = Field(None, description="Solar system type")
    capacity_range_min: Optional[float] = Field(None, ge=0, description="Minimum capacity (kW)")
    capacity_range_max: Optional[float] = Field(None, ge=0, description="Maximum capacity (kW)")
    
    # Default components
    default_components: Optional[List[Dict[str, Any]]] = Field(None, description="Default components")
    
    # Template metadata
    tags: Optional[List[str]] = Field(None, description="Template tags")
    is_public: Optional[bool] = Field(None, description="Is template public")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")





class ComponentLibraryCreate(BaseSchema):
    """Schema for creating a component library entry."""
    
    name: str = Field(..., description="Component name")
    description: Optional[str] = Field(None, description="Component description")
    category: ComponentCategory = Field(..., description="Component category")
    component_type: ComponentType = Field(..., description="Component type")
    
    # Manufacturer information
    manufacturer: str = Field(..., description="Manufacturer name")
    model_number: str = Field(..., description="Model number")
    part_number: Optional[str] = Field(None, description="Part number")
    
    # Technical specifications
    specifications: Dict[str, Any] = Field(..., description="Technical specifications")
    
    # Pricing and availability
    base_price: Optional[Decimal] = Field(None, ge=0, description="Base price")
    currency: Optional[str] = Field(None, description="Currency code")
    
    # Certifications and compliance
    certifications: List[str] = Field(default_factory=list, description="Certifications")
    compliance_standards: List[str] = Field(default_factory=list, description="Compliance standards")
    
    # Documentation
    datasheet_url: Optional[str] = Field(None, description="Datasheet URL")
    manual_url: Optional[str] = Field(None, description="Manual URL")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Component tags")
    is_active: bool = Field(default=True, description="Is component active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Component metadata")


class ComponentLibraryUpdate(BaseSchema):
    """Schema for updating a component library entry."""
    
    name: Optional[str] = Field(None, description="Component name")
    description: Optional[str] = Field(None, description="Component description")
    category: Optional[ComponentCategory] = Field(None, description="Component category")
    component_type: Optional[ComponentType] = Field(None, description="Component type")
    
    # Manufacturer information
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    model_number: Optional[str] = Field(None, description="Model number")
    part_number: Optional[str] = Field(None, description="Part number")
    
    # Technical specifications
    specifications: Optional[Dict[str, Any]] = Field(None, description="Technical specifications")
    
    # Pricing and availability
    base_price: Optional[Decimal] = Field(None, ge=0, description="Base price")
    currency: Optional[str] = Field(None, description="Currency code")
    
    # Certifications and compliance
    certifications: Optional[List[str]] = Field(None, description="Certifications")
    compliance_standards: Optional[List[str]] = Field(None, description="Compliance standards")
    
    # Documentation
    datasheet_url: Optional[str] = Field(None, description="Datasheet URL")
    manual_url: Optional[str] = Field(None, description="Manual URL")
    
    # Metadata
    tags: Optional[List[str]] = Field(None, description="Component tags")
    is_active: Optional[bool] = Field(None, description="Is component active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Component metadata")


# List Response Schemas - defined at the end to ensure all referenced schemas exist

class BOMListResponse(BaseSchema):
    """Schema for BOM list response."""
    
    boms: List[BOMResponse] = Field(..., description="List of BOMs")
    total: int = Field(..., description="Total number of BOMs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(None, description="Sort order (asc/desc)")


class ComponentListResponse(BaseSchema):
    """Schema for component list response."""
    
    components: List[ComponentResponse] = Field(..., description="List of components")
    total: int = Field(..., description="Total number of components")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(None, description="Sort order (asc/desc)")


class SupplierListResponse(BaseSchema):
    """Schema for supplier list response."""
    
    suppliers: List[SupplierResponse] = Field(..., description="List of suppliers")
    total: int = Field(..., description="Total number of suppliers")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(None, description="Sort order (asc/desc)")


class BOMTemplateListResponse(BaseSchema):
    """Schema for BOM template list response."""
    
    templates: List[BOMTemplateResponse] = Field(..., description="List of BOM templates")
    total: int = Field(..., description="Total number of templates")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(None, description="Sort order (asc/desc)")