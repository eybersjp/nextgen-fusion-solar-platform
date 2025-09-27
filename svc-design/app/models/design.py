"""Design models for the Design Service.

This module contains SQLAlchemy models for design-related entities
including designs, versions, approvals, comments, attachments, and sharing.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
# from geoalchemy2 import Geometry  # Disabled for SQLite compatibility

from .base import FullBaseModel


class DesignType(PyEnum):
    """Design type enumeration."""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    UTILITY = "utility"


class DesignStatus(PyEnum):
    """Design status enumeration."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ApprovalStatus(PyEnum):
    """Approval status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUIRED = "revision_required"


class SharePermission(PyEnum):
    """Share permission enumeration."""
    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"


class Design(FullBaseModel):
    """Design model for solar system designs."""
    
    __tablename__ = 'designs'
    
    # Basic information
    name = Column(String(255), nullable=False, doc="Design name")
    description = Column(Text, doc="Design description")
    
    # Project and organization references
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True, doc="Project ID")
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True, doc="Organization ID")
    
    # Site information
    site_name = Column(String(255), doc="Site name")
    site_address = Column(Text, doc="Site address")
    # site_coordinates = Column(Geometry('POINT', srid=4326), doc="Site coordinates (WGS84)")  # Disabled for SQLite
    site_latitude = Column(Float, doc="Site latitude (WGS84)")
    site_longitude = Column(Float, doc="Site longitude (WGS84)")
    site_area = Column(Float, doc="Site area in square meters")
    site_elevation = Column(Float, doc="Site elevation in meters")
    
    # System specifications
    system_type = Column(
        Enum('grid_tied', 'off_grid', 'hybrid', name='system_type_enum'),
        nullable=False,
        default='grid_tied',
        doc="System type"
    )
    system_capacity_kw = Column(Float, doc="System capacity in kW")
    system_voltage = Column(Float, doc="System voltage")
    
    # Performance metrics
    annual_energy_kwh = Column(Float, doc="Annual energy production in kWh")
    capacity_factor = Column(Float, doc="Capacity factor")
    performance_ratio = Column(Float, doc="Performance ratio")
    specific_yield = Column(Float, doc="Specific yield in kWh/kWp")
    
    # Financial information
    total_cost = Column(Float, doc="Total system cost")
    cost_per_watt = Column(Float, doc="Cost per watt")
    payback_period_years = Column(Float, doc="Payback period in years")
    irr_percent = Column(Float, doc="Internal rate of return")
    npv = Column(Float, doc="Net present value")
    lcoe = Column(Float, doc="Levelized cost of energy")
    
    # Client information
    client_name = Column(String(255), doc="Client name")
    client_email = Column(String(255), doc="Client email")
    client_phone = Column(String(50), doc="Client phone")
    client_company = Column(String(255), doc="Client company")
    
    # Design workflow
    design_stage = Column(
        Enum(
            'concept', 'preliminary', 'detailed', 'final', 'approved', 'construction',
            name='design_stage_enum'
        ),
        nullable=False,
        default='concept',
        doc="Design stage"
    )
    
    approval_status = Column(
        Enum('pending', 'approved', 'rejected', 'revision_required', name='approval_status_enum'),
        nullable=False,
        default='pending',
        doc="Approval status"
    )
    
    # Version tracking
    version_number = Column(String(50), nullable=False, default='1.0', doc="Version number")
    is_current_version = Column(Boolean, nullable=False, default=True, doc="Is current version")
    parent_design_id = Column(UUID(as_uuid=True), ForeignKey('designs.id'), doc="Parent design ID")
    
    # Compliance and standards
    compliance_standards = Column(JSON, doc="Compliance standards and requirements")
    permit_requirements = Column(JSON, doc="Permit requirements")
    
    # Weather and environmental data
    weather_data_source = Column(String(100), doc="Weather data source")
    irradiance_data = Column(JSON, doc="Irradiance data")
    temperature_data = Column(JSON, doc="Temperature data")
    wind_data = Column(JSON, doc="Wind data")
    
    # Loss analysis
    shading_losses = Column(Float, doc="Shading losses percentage")
    soiling_losses = Column(Float, doc="Soiling losses percentage")
    system_losses = Column(Float, doc="System losses percentage")
    inverter_losses = Column(Float, doc="Inverter losses percentage")
    dc_losses = Column(Float, doc="DC losses percentage")
    ac_losses = Column(Float, doc="AC losses percentage")
    
    # Relationships
    versions = relationship(
        "DesignVersion",
        back_populates="design",
        cascade="all, delete-orphan",
        order_by="DesignVersion.created_at.desc()"
    )
    
    approvals = relationship(
        "DesignApproval",
        back_populates="design",
        cascade="all, delete-orphan",
        order_by="DesignApproval.created_at.desc()"
    )
    
    comments = relationship(
        "DesignComment",
        back_populates="design",
        cascade="all, delete-orphan",
        order_by="DesignComment.created_at.desc()"
    )
    
    attachments = relationship(
        "DesignAttachment",
        back_populates="design",
        cascade="all, delete-orphan"
    )
    
    shares = relationship(
        "DesignShare",
        back_populates="design",
        cascade="all, delete-orphan"
    )
    
    # Self-referential relationship for versions
    child_designs = relationship(
        "Design",
        backref=backref("parent_design", remote_side="Design.id")
    )
    
    def __repr__(self) -> str:
        return f"<Design(id={self.id}, name='{self.name}', version='{self.version_number}')>"
    
    @property
    def site_coordinates_lat_lon(self) -> Optional[tuple]:
        """Get site coordinates as (latitude, longitude) tuple.
        
        Returns:
            Optional[tuple]: (latitude, longitude) or None
        """
        if self.site_coordinates:
            # Extract coordinates from PostGIS point
            from geoalchemy2.shape import to_shape
            point = to_shape(self.site_coordinates)
            return (point.y, point.x)  # (latitude, longitude)
        return None
    
    def set_site_coordinates(self, latitude: float, longitude: float):
        """Set site coordinates from latitude and longitude.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
        """
        from geoalchemy2.elements import WKTElement
        self.site_coordinates = WKTElement(f'POINT({longitude} {latitude})', srid=4326)
    
    def calculate_performance_metrics(self):
        """Calculate derived performance metrics."""
        if self.annual_energy_kwh and self.system_capacity_kw:
            # Capacity factor = Annual Energy / (Capacity * 8760)
            self.capacity_factor = self.annual_energy_kwh / (self.system_capacity_kw * 8760)
            
            # Specific yield = Annual Energy / Capacity
            self.specific_yield = self.annual_energy_kwh / self.system_capacity_kw
        
        if self.total_cost and self.system_capacity_kw:
            # Cost per watt
            self.cost_per_watt = self.total_cost / (self.system_capacity_kw * 1000)


class DesignVersion(FullBaseModel):
    """Design version model for tracking design changes."""
    
    __tablename__ = 'design_versions'
    
    # References
    design_id = Column(UUID(as_uuid=True), ForeignKey('designs.id'), nullable=False, index=True)
    
    # Version information
    version_number = Column(String(50), nullable=False, doc="Version number")
    version_name = Column(String(255), doc="Version name")
    change_description = Column(Text, doc="Description of changes")
    
    # Snapshot data
    design_data = Column(JSON, nullable=False, doc="Complete design data snapshot")
    layout_data = Column(JSON, doc="Layout data snapshot")
    performance_data = Column(JSON, doc="Performance data snapshot")
    financial_data = Column(JSON, doc="Financial data snapshot")
    
    # Version metadata
    is_major_version = Column(Boolean, nullable=False, default=False, doc="Is major version")
    is_published = Column(Boolean, nullable=False, default=False, doc="Is published version")
    
    # Relationships
    design = relationship("Design", back_populates="versions")
    
    def __repr__(self) -> str:
        return f"<DesignVersion(id={self.id}, design_id={self.design_id}, version='{self.version_number}')>"


class DesignApproval(FullBaseModel):
    """Design approval model for tracking approval workflow."""
    
    __tablename__ = 'design_approvals'
    
    # References
    design_id = Column(UUID(as_uuid=True), ForeignKey('designs.id'), nullable=False, index=True)
    
    # Approval information
    approval_type = Column(
        Enum('technical', 'financial', 'regulatory', 'client', name='approval_type_enum'),
        nullable=False,
        doc="Approval type"
    )
    
    approval_status = Column(
        Enum('pending', 'approved', 'rejected', 'revision_required', name='approval_status_enum'),
        nullable=False,
        default='pending',
        doc="Approval status"
    )
    
    # Approver information
    approver_id = Column(UUID(as_uuid=True), nullable=False, doc="Approver user ID")
    approver_name = Column(String(255), doc="Approver name")
    approver_role = Column(String(100), doc="Approver role")
    
    # Approval details
    approval_date = Column(DateTime(timezone=True), doc="Approval date")
    comments = Column(Text, doc="Approval comments")
    conditions = Column(Text, doc="Approval conditions")
    
    # Required changes
    required_changes = Column(JSON, doc="Required changes for approval")
    
    # Relationships
    design = relationship("Design", back_populates="approvals")
    
    def __repr__(self) -> str:
        return f"<DesignApproval(id={self.id}, design_id={self.design_id}, status='{self.approval_status}')>"


class DesignComment(FullBaseModel):
    """Design comment model for collaboration and feedback."""
    
    __tablename__ = 'design_comments'
    
    # References
    design_id = Column(UUID(as_uuid=True), ForeignKey('designs.id'), nullable=False, index=True)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey('design_comments.id'), doc="Parent comment ID")
    
    # Comment information
    comment_text = Column(Text, nullable=False, doc="Comment text")
    comment_type = Column(
        Enum('general', 'technical', 'financial', 'regulatory', 'question', 'issue', name='comment_type_enum'),
        nullable=False,
        default='general',
        doc="Comment type"
    )
    
    # Author information
    author_id = Column(UUID(as_uuid=True), nullable=False, doc="Author user ID")
    author_name = Column(String(255), doc="Author name")
    author_role = Column(String(100), doc="Author role")
    
    # Comment metadata
    is_resolved = Column(Boolean, nullable=False, default=False, doc="Is comment resolved")
    resolved_by = Column(UUID(as_uuid=True), doc="User who resolved the comment")
    resolved_at = Column(DateTime(timezone=True), doc="Resolution timestamp")
    
    # Location reference (for spatial comments)
    location_data = Column(JSON, doc="Location data for spatial comments")
    
    # Relationships
    design = relationship("Design", back_populates="comments")
    
    # Self-referential relationship for threaded comments
    replies = relationship(
        "DesignComment",
        backref=backref("parent_comment", remote_side="DesignComment.id"),
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<DesignComment(id={self.id}, design_id={self.design_id}, type='{self.comment_type}')>"


class DesignAttachment(FullBaseModel):
    """Design attachment model for file attachments."""
    
    __tablename__ = 'design_attachments'
    
    # References
    design_id = Column(UUID(as_uuid=True), ForeignKey('designs.id'), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False, doc="Original filename")
    file_path = Column(String(500), nullable=False, doc="File storage path")
    file_size = Column(Integer, doc="File size in bytes")
    file_type = Column(String(100), doc="File MIME type")
    file_hash = Column(String(64), doc="File hash for integrity")
    
    # Attachment metadata
    attachment_type = Column(
        Enum(
            'drawing', 'specification', 'report', 'image', 'document', 'calculation', 'other',
            name='attachment_type_enum'
        ),
        nullable=False,
        default='document',
        doc="Attachment type"
    )
    
    title = Column(String(255), doc="Attachment title")
    description = Column(Text, doc="Attachment description")
    
    # Access control
    is_public = Column(Boolean, nullable=False, default=False, doc="Is publicly accessible")
    access_level = Column(
        Enum('public', 'organization', 'project', 'private', name='access_level_enum'),
        nullable=False,
        default='project',
        doc="Access level"
    )
    
    # Upload information
    uploaded_by = Column(UUID(as_uuid=True), nullable=False, doc="Uploader user ID")
    uploaded_at = Column(DateTime(timezone=True), nullable=False, doc="Upload timestamp")
    
    # Relationships
    design = relationship("Design", back_populates="attachments")
    
    def __repr__(self) -> str:
        return f"<DesignAttachment(id={self.id}, filename='{self.filename}', type='{self.attachment_type}')>"


class DesignTag(FullBaseModel):
    """Design tag model for categorization and search."""
    
    __tablename__ = 'design_tags'
    
    # Tag information
    name = Column(String(100), nullable=False, unique=True, index=True, doc="Tag name")
    description = Column(Text, doc="Tag description")
    color = Column(String(7), doc="Tag color (hex code)")
    
    # Tag metadata
    tag_type = Column(
        Enum('system', 'custom', 'auto', name='tag_type_enum'),
        nullable=False,
        default='custom',
        doc="Tag type"
    )
    
    category = Column(String(100), doc="Tag category")
    
    # Usage statistics
    usage_count = Column(Integer, nullable=False, default=0, doc="Number of times used")
    
    # Organization scope
    organization_id = Column(UUID(as_uuid=True), index=True, doc="Organization ID (null for global tags)")
    
    def __repr__(self) -> str:
        return f"<DesignTag(id={self.id}, name='{self.name}', type='{self.tag_type}')>"


class DesignShare(FullBaseModel):
    """Design share model for sharing designs with external parties."""
    
    __tablename__ = 'design_shares'
    
    # References
    design_id = Column(UUID(as_uuid=True), ForeignKey('designs.id'), nullable=False, index=True)
    
    # Share information
    share_token = Column(String(255), nullable=False, unique=True, index=True, doc="Unique share token")
    share_type = Column(
        Enum('view', 'comment', 'download', name='share_type_enum'),
        nullable=False,
        default='view',
        doc="Share type"
    )
    
    # Target information
    target_type = Column(
        Enum('email', 'link', 'user', 'organization', name='target_type_enum'),
        nullable=False,
        doc="Share target type"
    )
    
    target_identifier = Column(String(255), doc="Target identifier (email, user ID, etc.)")
    target_name = Column(String(255), doc="Target name")
    
    # Access control
    expires_at = Column(DateTime(timezone=True), doc="Share expiration")
    is_password_protected = Column(Boolean, nullable=False, default=False, doc="Requires password")
    password_hash = Column(String(255), doc="Password hash")
    
    # Usage tracking
    access_count = Column(Integer, nullable=False, default=0, doc="Number of accesses")
    last_accessed_at = Column(DateTime(timezone=True), doc="Last access timestamp")
    last_accessed_ip = Column(String(45), doc="Last access IP address")
    
    # Share settings
    allow_download = Column(Boolean, nullable=False, default=False, doc="Allow file downloads")
    allow_comments = Column(Boolean, nullable=False, default=False, doc="Allow comments")
    watermark_enabled = Column(Boolean, nullable=False, default=True, doc="Enable watermarks")
    
    # Notification settings
    notify_on_access = Column(Boolean, nullable=False, default=True, doc="Notify on access")
    
    # Relationships
    design = relationship("Design", back_populates="shares")
    
    def __repr__(self) -> str:
        return f"<DesignShare(id={self.id}, design_id={self.design_id}, type='{self.share_type}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if share is expired.
        
        Returns:
            bool: True if expired
        """
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def increment_access_count(self, ip_address: Optional[str] = None):
        """Increment access count and update last access info.
        
        Args:
            ip_address: Client IP address
        """
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()
        if ip_address:
            self.last_accessed_ip = ip_address