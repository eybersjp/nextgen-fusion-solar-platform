"""Bill of Materials (BOM) models for the Design Service.

This module contains SQLAlchemy models for component tracking,
pricing, procurement, and BOM generation.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    Boolean, Column, DateTime, Date, Enum, Float, ForeignKey, Integer, 
    String, Text, Numeric, Index
)
from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.dialects.postgresql import ARRAY  # Disabled for SQLite compatibility
from sqlalchemy import JSON
from sqlalchemy.orm import relationship, backref
# from geoalchemy2 import Geometry  # Disabled for SQLite compatibility

from .base import FullBaseModel


class BOMStatus(PyEnum):
    """BOM status enumeration."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUIRED = "revision_required"


class ComponentCategory(PyEnum):
    """Component category enumeration."""
    PV_MODULES = "pv_modules"
    INVERTERS = "inverters"
    MOUNTING = "mounting"
    ELECTRICAL = "electrical"
    MONITORING = "monitoring"
    SAFETY = "safety"
    STRUCTURAL = "structural"
    OTHER = "other"


class ComponentType(PyEnum):
    """Component type enumeration."""
    SOLAR_PANEL = "solar_panel"
    INVERTER = "inverter"
    OPTIMIZER = "optimizer"
    MICROINVERTER = "microinverter"
    MOUNTING_RAIL = "mounting_rail"
    CLAMP = "clamp"
    CABLE = "cable"
    CONNECTOR = "connector"
    COMBINER_BOX = "combiner_box"
    DISCONNECT = "disconnect"
    METER = "meter"
    MONITORING_DEVICE = "monitoring_device"
    CONDUIT = "conduit"
    GROUNDING = "grounding"
    FASTENER = "fastener"
    OTHER = "other"


class CostCategory(PyEnum):
    """Cost category enumeration."""
    MATERIAL = "material"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    SHIPPING = "shipping"
    TAX = "tax"
    MARKUP = "markup"
    OTHER = "other"


class PriceType(PyEnum):
    """Price type enumeration."""
    LIST = "list"
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    CONTRACT = "contract"
    QUOTE = "quote"
    MARKET = "market"


class UnitType(PyEnum):
    """Unit type enumeration."""
    EACH = "each"
    METER = "meter"
    FOOT = "foot"
    KILOGRAM = "kilogram"
    POUND = "pound"
    LITER = "liter"
    GALLON = "gallon"
    HOUR = "hour"
    DAY = "day"
    LOT = "lot"
    SET = "set"


class BillOfMaterials(FullBaseModel):
    """Bill of Materials model for complete system BOMs."""
    
    __tablename__ = 'bills_of_materials'
    
    # References
    design_id = Column(UUID(as_uuid=True), nullable=False, index=True, doc="Design ID")
    layout_id = Column(UUID(as_uuid=True), index=True, doc="Layout ID")
    
    # BOM information
    name = Column(String(255), nullable=False, doc="BOM name")
    description = Column(Text, doc="BOM description")
    version = Column(String(50), nullable=False, default='1.0', doc="BOM version")
    
    # BOM type and purpose
    bom_type = Column(
        Enum(
            'preliminary', 'detailed', 'procurement', 'installation', 
            'maintenance', 'warranty', name='bom_type_enum'
        ),
        nullable=False,
        default='detailed',
        doc="BOM type"
    )
    
    purpose = Column(
        Enum(
            'design', 'quotation', 'procurement', 'construction', 
            'commissioning', 'maintenance', name='bom_purpose_enum'
        ),
        nullable=False,
        default='design',
        doc="BOM purpose"
    )
    
    # System information
    system_capacity_kw = Column(Float, doc="System capacity in kW")
    system_voltage = Column(Float, doc="System voltage")
    system_type = Column(String(100), doc="System type")
    
    # Pricing information
    currency = Column(String(3), nullable=False, default='USD', doc="Currency code")
    total_cost = Column(Numeric(15, 2), doc="Total BOM cost")
    material_cost = Column(Numeric(15, 2), doc="Material cost")
    labor_cost = Column(Numeric(15, 2), doc="Labor cost")
    equipment_cost = Column(Numeric(15, 2), doc="Equipment cost")
    shipping_cost = Column(Numeric(15, 2), doc="Shipping cost")
    tax_amount = Column(Numeric(15, 2), doc="Tax amount")
    
    # Cost breakdown by category
    pv_modules_cost = Column(Numeric(15, 2), doc="PV modules cost")
    inverters_cost = Column(Numeric(15, 2), doc="Inverters cost")
    mounting_cost = Column(Numeric(15, 2), doc="Mounting system cost")
    electrical_cost = Column(Numeric(15, 2), doc="Electrical components cost")
    monitoring_cost = Column(Numeric(15, 2), doc="Monitoring system cost")
    
    # Pricing validity
    pricing_date = Column(Date, doc="Pricing date")
    pricing_valid_until = Column(Date, doc="Pricing validity end date")
    
    # Supplier information
    primary_supplier_id = Column(UUID(as_uuid=True), doc="Primary supplier ID")
    supplier_quote_reference = Column(String(255), doc="Supplier quote reference")
    
    # Lead times
    estimated_lead_time_days = Column(Integer, doc="Estimated lead time in days")
    critical_path_items = Column(JSON, doc="Critical path items")
    
    # Delivery and logistics
    delivery_address = Column(JSON, doc="Delivery address")
    delivery_requirements = Column(Text, doc="Special delivery requirements")
    
    # Quality and compliance
    quality_requirements = Column(JSON, doc="Quality requirements")
    compliance_standards = Column(JSON, doc="Compliance standards")
    certifications_required = Column(JSON, doc="Required certifications")
    
    # Status and approval
    approval_status = Column(
        Enum(
            'draft', 'pending_review', 'approved', 'rejected', 
            'revision_required', name='approval_status_enum'
        ),
        nullable=False,
        default='draft',
        doc="Approval status"
    )
    
    approved_by = Column(UUID(as_uuid=True), doc="Approved by user ID")
    approved_at = Column(DateTime(timezone=True), doc="Approval timestamp")
    
    # Generation information
    generation_method = Column(
        Enum('manual', 'automated', 'template', 'imported', name='generation_method_enum'),
        doc="BOM generation method"
    )
    
    generation_parameters = Column(JSON, doc="Generation parameters")
    
    # File references
    excel_file_path = Column(String(500), doc="Excel BOM file path")
    pdf_file_path = Column(String(500), doc="PDF BOM file path")
    csv_file_path = Column(String(500), doc="CSV BOM file path")
    
    def __repr__(self) -> str:
        return f"<BillOfMaterials(id={self.id}, name='{self.name}', type='{self.bom_type}')>"
    
    @property
    def cost_per_watt(self) -> Optional[float]:
        """Calculate cost per watt.
        
        Returns:
            Optional[float]: Cost per watt or None
        """
        if self.total_cost and self.system_capacity_kw:
            return float(self.total_cost) / (self.system_capacity_kw * 1000)
        return None
    
    @property
    def is_pricing_valid(self) -> bool:
        """Check if pricing is still valid.
        
        Returns:
            bool: True if pricing is valid
        """
        if self.pricing_valid_until:
            return date.today() <= self.pricing_valid_until
        return True


class BOMItem(FullBaseModel):
    """BOM item model for individual components."""
    
    __tablename__ = 'bom_items'
    
    # References
    bom_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('bills_of_materials.id'), 
        nullable=False, 
        index=True
    )
    
    component_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('components.id'), 
        nullable=False, 
        index=True
    )
    
    # Item information
    line_number = Column(Integer, nullable=False, doc="Line number in BOM")
    item_code = Column(String(100), doc="Internal item code")
    
    # Quantity and units
    quantity = Column(Float, nullable=False, doc="Quantity required")
    unit_of_measure = Column(String(20), nullable=False, default='each', doc="Unit of measure")
    
    # Pricing
    unit_price = Column(Numeric(12, 4), doc="Unit price")
    total_price = Column(Numeric(15, 2), doc="Total line price")
    discount_percent = Column(Float, default=0.0, doc="Discount percentage")
    discount_amount = Column(Numeric(12, 2), doc="Discount amount")
    
    # Supplier information
    supplier_id = Column(UUID(as_uuid=True), doc="Supplier ID")
    supplier_part_number = Column(String(255), doc="Supplier part number")
    supplier_lead_time_days = Column(Integer, doc="Supplier lead time")
    
    # Installation information
    installation_zone = Column(String(100), doc="Installation zone/area")
    installation_sequence = Column(Integer, doc="Installation sequence")
    installation_notes = Column(Text, doc="Installation notes")
    
    # Quality and compliance
    quality_grade = Column(String(50), doc="Quality grade")
    compliance_notes = Column(Text, doc="Compliance notes")
    
    # Status
    item_status = Column(
        Enum(
            'active', 'substituted', 'discontinued', 'on_hold', 
            'ordered', 'received', name='item_status_enum'
        ),
        nullable=False,
        default='active',
        doc="Item status"
    )
    
    # Relationships
    bom = relationship("BillOfMaterials", backref="items")
    component = relationship("Component", backref="bom_items")
    
    # Indexes
    __table_args__ = (
        Index('ix_bom_items_bom_line', 'bom_id', 'line_number'),
    )
    
    def __repr__(self) -> str:
        return f"<BOMItem(bom_id={self.bom_id}, line={self.line_number}, qty={self.quantity})>"
    
    @property
    def extended_price(self) -> Optional[Decimal]:
        """Calculate extended price (quantity × unit price - discount).
        
        Returns:
            Optional[Decimal]: Extended price or None
        """
        if self.unit_price and self.quantity:
            base_price = Decimal(str(self.unit_price)) * Decimal(str(self.quantity))
            if self.discount_amount:
                return base_price - self.discount_amount
            return base_price
        return None


class Component(FullBaseModel):
    """Component model for system components and parts."""
    
    __tablename__ = 'components'
    
    # Component identification
    name = Column(String(255), nullable=False, doc="Component name")
    description = Column(Text, doc="Component description")
    manufacturer = Column(String(255), doc="Manufacturer name")
    model_number = Column(String(255), doc="Model number")
    part_number = Column(String(255), doc="Part number")
    
    # Component category
    category = Column(
        Enum(
            'pv_module', 'inverter', 'mounting', 'electrical', 'monitoring', 
            'safety', 'grounding', 'conduit', 'wire', 'connector', 
            'combiner_box', 'transformer', 'meter', 'disconnect', 
            'breaker', 'fuse', 'surge_protector', 'other', 
            name='component_category_enum'
        ),
        nullable=False,
        doc="Component category"
    )
    
    subcategory = Column(String(100), doc="Component subcategory")
    
    # Technical specifications
    specifications = Column(JSON, doc="Technical specifications")
    electrical_specs = Column(JSON, doc="Electrical specifications")
    mechanical_specs = Column(JSON, doc="Mechanical specifications")
    environmental_specs = Column(JSON, doc="Environmental specifications")
    
    # Physical properties
    weight_kg = Column(Float, doc="Weight in kg")
    dimensions = Column(JSON, doc="Dimensions (length, width, height)")
    color = Column(String(50), doc="Color")
    material = Column(String(100), doc="Primary material")
    
    # Performance characteristics
    efficiency_percent = Column(Float, doc="Efficiency percentage")
    power_rating_w = Column(Float, doc="Power rating in watts")
    voltage_rating_v = Column(Float, doc="Voltage rating in volts")
    current_rating_a = Column(Float, doc="Current rating in amperes")
    
    # Certifications and compliance
    certifications = Column(JSON, doc="Certifications")
    standards_compliance = Column(JSON, doc="Standards compliance")
    country_approvals = Column(JSON, doc="Country approvals")
    
    # Warranty information
    warranty_years = Column(Integer, doc="Warranty period in years")
    warranty_terms = Column(Text, doc="Warranty terms")
    performance_warranty_years = Column(Integer, doc="Performance warranty years")
    
    # Pricing and availability
    list_price = Column(Numeric(12, 4), doc="List price")
    currency = Column(String(3), default='USD', doc="Currency code")
    price_valid_until = Column(Date, doc="Price validity end date")
    
    # Supplier information
    primary_supplier_id = Column(UUID(as_uuid=True), doc="Primary supplier ID")
    alternative_suppliers = Column(JSON, doc="Alternative suppliers")
    
    # Availability
    is_available = Column(Boolean, nullable=False, default=True, doc="Is available")
    lead_time_days = Column(Integer, doc="Lead time in days")
    minimum_order_quantity = Column(Integer, default=1, doc="Minimum order quantity")
    
    # Lifecycle status
    lifecycle_status = Column(
        Enum(
            'active', 'new', 'mature', 'declining', 'discontinued', 
            'obsolete', name='lifecycle_status_enum'
        ),
        nullable=False,
        default='active',
        doc="Lifecycle status"
    )
    
    # Data sources
    data_source = Column(String(100), doc="Data source")
    last_updated_from_source = Column(DateTime(timezone=True), doc="Last update from source")
    
    # File references
    datasheet_url = Column(String(500), doc="Datasheet URL")
    image_url = Column(String(500), doc="Product image URL")
    cad_file_url = Column(String(500), doc="CAD file URL")
    
    def __repr__(self) -> str:
        return f"<Component(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    @property
    def full_name(self) -> str:
        """Get full component name including manufacturer and model.
        
        Returns:
            str: Full component name
        """
        parts = [self.manufacturer, self.model_number, self.name]
        return ' '.join(filter(None, parts))
    
    def get_specification(self, key: str) -> Any:
        """Get specification value by key.
        
        Args:
            key: Specification key
            
        Returns:
            Any: Specification value or None
        """
        if self.specifications and isinstance(self.specifications, dict):
            return self.specifications.get(key)
        return None


class Supplier(FullBaseModel):
    """Supplier model for component suppliers and vendors."""
    
    __tablename__ = 'suppliers'
    
    # Supplier information
    name = Column(String(255), nullable=False, doc="Supplier name")
    legal_name = Column(String(255), doc="Legal company name")
    supplier_code = Column(String(50), unique=True, doc="Supplier code")
    
    # Contact information
    contact_person = Column(String(255), doc="Primary contact person")
    email = Column(String(255), doc="Email address")
    phone = Column(String(50), doc="Phone number")
    website = Column(String(255), doc="Website URL")
    
    # Address
    address = Column(JSON, doc="Address information")
    country = Column(String(2), doc="Country code")
    timezone = Column(String(50), doc="Timezone")
    
    # Business information
    business_type = Column(
        Enum(
            'manufacturer', 'distributor', 'wholesaler', 'retailer', 
            'installer', 'service_provider', name='business_type_enum'
        ),
        doc="Business type"
    )
    
    industry_focus = Column(JSON, doc="Industry focus areas")
    
    # Products and services
    product_categories = Column(JSON, doc="Product categories")
    services_offered = Column(JSON, doc="Services offered")
    geographic_coverage = Column(JSON, doc="Geographic coverage")
    
    # Financial information
    payment_terms = Column(String(100), doc="Payment terms")
    credit_limit = Column(Numeric(15, 2), doc="Credit limit")
    currency = Column(String(3), default='USD', doc="Primary currency")
    
    # Performance metrics
    quality_rating = Column(Float, doc="Quality rating (1-5)")
    delivery_rating = Column(Float, doc="Delivery rating (1-5)")
    service_rating = Column(Float, doc="Service rating (1-5)")
    overall_rating = Column(Float, doc="Overall rating (1-5)")
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, doc="Is active")
    is_preferred = Column(Boolean, nullable=False, default=False, doc="Is preferred supplier")
    
    # Compliance and certifications
    certifications = Column(JSON, doc="Supplier certifications")
    compliance_status = Column(String(50), doc="Compliance status")
    
    # Relationship management
    account_manager = Column(String(255), doc="Account manager")
    last_contact_date = Column(Date, doc="Last contact date")
    next_review_date = Column(Date, doc="Next review date")
    
    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name='{self.name}', code='{self.supplier_code}')>"
    
    @property
    def average_rating(self) -> Optional[float]:
        """Calculate average rating across all metrics.
        
        Returns:
            Optional[float]: Average rating or None
        """
        ratings = [self.quality_rating, self.delivery_rating, self.service_rating]
        valid_ratings = [r for r in ratings if r is not None]
        if valid_ratings:
            return sum(valid_ratings) / len(valid_ratings)
        return None


class PriceList(FullBaseModel):
    """Price list model for supplier pricing."""
    
    __tablename__ = 'price_lists'
    
    # References
    supplier_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('suppliers.id'), 
        nullable=False, 
        index=True
    )
    
    # Price list information
    name = Column(String(255), nullable=False, doc="Price list name")
    description = Column(Text, doc="Price list description")
    version = Column(String(50), doc="Price list version")
    
    # Validity
    effective_date = Column(Date, nullable=False, doc="Effective date")
    expiry_date = Column(Date, doc="Expiry date")
    
    # Currency and terms
    currency = Column(String(3), nullable=False, doc="Currency code")
    payment_terms = Column(String(100), doc="Payment terms")
    
    # Pricing structure
    pricing_model = Column(
        Enum('fixed', 'tiered', 'volume', 'contract', name='pricing_model_enum'),
        nullable=False,
        default='fixed',
        doc="Pricing model"
    )
    
    # Discounts and terms
    base_discount_percent = Column(Float, default=0.0, doc="Base discount percentage")
    volume_discounts = Column(JSON, doc="Volume discount tiers")
    
    # Geographic applicability
    applicable_regions = Column(JSON, doc="Applicable regions")
    shipping_terms = Column(String(100), doc="Shipping terms")
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, doc="Is active")
    
    # Relationships
    supplier = relationship("Supplier", backref="price_lists")
    
    def __repr__(self) -> str:
        return f"<PriceList(id={self.id}, name='{self.name}', supplier_id={self.supplier_id})>"
    
    @property
    def is_current(self) -> bool:
        """Check if price list is currently valid.
        
        Returns:
            bool: True if current
        """
        today = date.today()
        if self.expiry_date:
            return self.effective_date <= today <= self.expiry_date
        return self.effective_date <= today


class PriceListItem(FullBaseModel):
    """Price list item model for component pricing."""
    
    __tablename__ = 'price_list_items'
    
    # References
    price_list_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('price_lists.id'), 
        nullable=False, 
        index=True
    )
    
    component_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('components.id'), 
        nullable=False, 
        index=True
    )
    
    # Pricing information
    list_price = Column(Numeric(12, 4), nullable=False, doc="List price")
    cost_price = Column(Numeric(12, 4), doc="Cost price")
    
    # Quantity breaks
    minimum_quantity = Column(Integer, default=1, doc="Minimum quantity")
    maximum_quantity = Column(Integer, doc="Maximum quantity")
    
    # Lead time
    lead_time_days = Column(Integer, doc="Lead time in days")
    
    # Supplier part information
    supplier_part_number = Column(String(255), doc="Supplier part number")
    supplier_description = Column(Text, doc="Supplier description")
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, doc="Is active")
    
    # Relationships
    price_list = relationship("PriceList", backref="items")
    component = relationship("Component", backref="price_list_items")
    
    # Indexes
    __table_args__ = (
        Index('ix_price_list_items_list_component', 'price_list_id', 'component_id'),
    )
    
    def __repr__(self) -> str:
        return f"<PriceListItem(price_list_id={self.price_list_id}, component_id={self.component_id})>"


class BOMCostAnalysis(FullBaseModel):
    """BOM cost analysis model for detailed cost breakdowns."""
    
    __tablename__ = 'bom_cost_analyses'
    
    # References
    bom_id = Column(UUID(as_uuid=True), ForeignKey('bills_of_materials.id'), nullable=False, index=True)
    
    # Analysis information
    name = Column(String(255), nullable=False, doc="Analysis name")
    description = Column(Text, doc="Analysis description")
    analysis_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, doc="Analysis date")
    
    # Cost breakdown
    total_cost = Column(Numeric(15, 2), nullable=False, doc="Total cost")
    material_cost = Column(Numeric(15, 2), doc="Material cost")
    labor_cost = Column(Numeric(15, 2), doc="Labor cost")
    equipment_cost = Column(Numeric(15, 2), doc="Equipment cost")
    overhead_cost = Column(Numeric(15, 2), doc="Overhead cost")
    markup_cost = Column(Numeric(15, 2), doc="Markup cost")
    
    # Cost per category
    cost_by_category = Column(JSON, doc="Cost breakdown by category")
    cost_by_supplier = Column(JSON, doc="Cost breakdown by supplier")
    
    # Analysis parameters
    analysis_parameters = Column(JSON, doc="Analysis parameters")
    assumptions = Column(JSON, doc="Cost assumptions")
    
    # Currency and pricing
    currency = Column(String(3), nullable=False, default='USD', doc="Currency code")
    exchange_rates = Column(JSON, doc="Exchange rates used")
    pricing_date = Column(Date, doc="Pricing date")
    
    # Results
    cost_per_watt = Column(Numeric(8, 4), doc="Cost per watt")
    cost_variance_percent = Column(Float, doc="Cost variance percentage")
    confidence_level = Column(Float, doc="Confidence level")
    
    # Relationships
    bom = relationship("BillOfMaterials", backref="cost_analyses")
    
    def __repr__(self) -> str:
        return f"<BOMCostAnalysis(id={self.id}, name='{self.name}', total_cost={self.total_cost})>"


class ComponentLibrary(FullBaseModel):
    """Component library model for managing component collections."""
    
    __tablename__ = 'component_libraries'
    
    # Library information
    name = Column(String(255), nullable=False, doc="Library name")
    description = Column(Text, doc="Library description")
    version = Column(String(50), nullable=False, default='1.0', doc="Library version")
    
    # Library type and scope
    library_type = Column(
        Enum('public', 'private', 'shared', 'template', name='library_type_enum'),
        nullable=False,
        default='private',
        doc="Library type"
    )
    
    scope = Column(
        Enum('global', 'organization', 'project', 'user', name='library_scope_enum'),
        nullable=False,
        default='organization',
        doc="Library scope"
    )
    
    # Content
    component_count = Column(Integer, default=0, doc="Number of components")
    categories_included = Column(JSON, doc="Categories included")
    
    # Access control
    is_public = Column(Boolean, nullable=False, default=False, doc="Is public library")
    access_permissions = Column(JSON, doc="Access permissions")
    
    # Usage tracking
    usage_count = Column(Integer, default=0, doc="Usage count")
    last_used_at = Column(DateTime(timezone=True), doc="Last used timestamp")
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, doc="Is active")
    
    def __repr__(self) -> str:
        return f"<ComponentLibrary(id={self.id}, name='{self.name}', type='{self.library_type}')>"


class BOMTemplate(FullBaseModel):
    """BOM template model for standardized BOMs."""
    
    __tablename__ = 'bom_templates'
    
    # Template information
    name = Column(String(255), nullable=False, doc="Template name")
    description = Column(Text, doc="Template description")
    version = Column(String(50), nullable=False, default='1.0', doc="Template version")
    
    # Template category
    category = Column(
        Enum(
            'residential', 'commercial', 'utility', 'ground_mount', 
            'rooftop', 'carport', 'tracker', name='template_category_enum'
        ),
        doc="Template category"
    )
    
    # System parameters
    min_capacity_kw = Column(Float, doc="Minimum system capacity")
    max_capacity_kw = Column(Float, doc="Maximum system capacity")
    voltage_levels = Column(JSON, doc="Supported voltage levels")
    
    # Template structure
    template_data = Column(JSON, nullable=False, doc="Template structure and rules")
    component_rules = Column(JSON, doc="Component selection rules")
    calculation_formulas = Column(JSON, doc="Calculation formulas")
    
    # Usage tracking
    usage_count = Column(Integer, default=0, doc="Usage count")
    last_used_at = Column(DateTime(timezone=True), doc="Last used timestamp")
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, doc="Is active")
    is_public = Column(Boolean, nullable=False, default=False, doc="Is public template")
    
    def __repr__(self) -> str:
        return f"<BOMTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def increment_usage(self) -> None:
        """Increment usage count and update last used timestamp."""
        self.usage_count = (self.usage_count or 0) + 1
        self.last_used_at = datetime.utcnow()