"""Project management models for the Design Service.

This module contains SQLAlchemy models for project management,
including projects, sites, and project metadata.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import (
    Boolean, Column, DateTime, String, Text, Numeric,
    Integer, JSON, Index, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin


class Project(BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """Project model for solar installation projects."""
    
    __tablename__ = "projects"
    
    # Basic project information
    name = Column(
        String(255),
        nullable=False,
        doc="Project name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Project description"
    )
    
    # Project ownership
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Project owner user ID"
    )
    
    # Project status and type
    status = Column(
        String(50),
        nullable=False,
        default="draft",
        doc="Project status (draft, active, completed, cancelled)"
    )
    
    project_type = Column(
        String(50),
        nullable=False,
        default="commercial",
        doc="Project type (residential, commercial, utility)"
    )
    
    # Location information
    site_address = Column(
        Text,
        nullable=True,
        doc="Site physical address"
    )
    
    site_city = Column(
        String(100),
        nullable=True,
        doc="Site city"
    )
    
    site_state = Column(
        String(50),
        nullable=True,
        doc="Site state/province"
    )
    
    site_country = Column(
        String(50),
        nullable=False,
        default="ZA",
        doc="Site country code (ISO 3166-1 alpha-2)"
    )
    
    site_postal_code = Column(
        String(20),
        nullable=True,
        doc="Site postal/zip code"
    )
    
    # Geographic coordinates
    latitude = Column(
        Numeric(precision=10, scale=7),
        nullable=True,
        doc="Site latitude in decimal degrees"
    )
    
    longitude = Column(
        Numeric(precision=10, scale=7),
        nullable=True,
        doc="Site longitude in decimal degrees"
    )
    
    elevation = Column(
        Numeric(precision=8, scale=2),
        nullable=True,
        doc="Site elevation in meters"
    )
    
    # Project specifications
    target_capacity_kw = Column(
        Numeric(precision=10, scale=3),
        nullable=True,
        doc="Target system capacity in kW"
    )
    
    estimated_annual_production_kwh = Column(
        Numeric(precision=12, scale=2),
        nullable=True,
        doc="Estimated annual energy production in kWh"
    )
    
    # Financial information
    budget_amount = Column(
        Numeric(precision=15, scale=2),
        nullable=True,
        doc="Project budget amount"
    )
    
    budget_currency = Column(
        String(3),
        nullable=False,
        default="ZAR",
        doc="Budget currency code (ISO 4217)"
    )
    
    # Project timeline
    start_date = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Project start date"
    )
    
    target_completion_date = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Target completion date"
    )
    
    actual_completion_date = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Actual completion date"
    )
    
    # Compliance and regulatory
    regulatory_requirements = Column(
        JSON,
        nullable=True,
        doc="Regulatory requirements and compliance data"
    )
    
    permits_required = Column(
        JSON,
        nullable=True,
        doc="Required permits and their status"
    )
    
    # Project metadata
    tags = Column(
        JSON,
        nullable=True,
        doc="Project tags for categorization"
    )
    
    custom_fields = Column(
        JSON,
        nullable=True,
        doc="Custom project fields"
    )
    
    # Design and calculation settings
    design_preferences = Column(
        JSON,
        nullable=True,
        doc="Design preferences and constraints"
    )
    
    # Relationships
    owner = relationship(
        "User",
        back_populates="projects"
    )
    
    designs = relationship(
        "SolarDesign",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    calculations = relationship(
        "DesignCalculation",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        Index("idx_projects_owner", "owner_id"),
        Index("idx_projects_status", "status"),
        Index("idx_projects_type", "project_type"),
        Index("idx_projects_country", "site_country"),
        Index("idx_projects_location", "latitude", "longitude"),
        Index("idx_projects_dates", "start_date", "target_completion_date"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="ck_projects_latitude_range"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_projects_longitude_range"
        ),
        CheckConstraint(
            "target_capacity_kw > 0",
            name="ck_projects_positive_capacity"
        ),
        CheckConstraint(
            "budget_amount >= 0",
            name="ck_projects_positive_budget"
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'on_hold', 'completed', 'cancelled')",
            name="ck_projects_valid_status"
        ),
        CheckConstraint(
            "project_type IN ('residential', 'commercial', 'utility', 'industrial')",
            name="ck_projects_valid_type"
        ),
    )
    
    def get_latest_design(self) -> Optional["SolarDesign"]:
        """Get the most recent solar design for this project.
        
        Returns:
            SolarDesign: Latest design or None
        """
        return self.designs.order_by(
            self.designs.property.mapper.class_.created_at.desc()
        ).first()
    
    def get_active_calculations(self) -> list:
        """Get all active calculations for this project.
        
        Returns:
            list: Active calculations
        """
        return self.calculations.filter_by(is_active=True).all()
    
    def calculate_progress(self) -> float:
        """Calculate project completion progress.
        
        Returns:
            float: Progress percentage (0-100)
        """
        if self.status == "completed":
            return 100.0
        elif self.status in ["cancelled", "draft"]:
            return 0.0
        
        # Calculate based on design completion and milestones
        progress = 0.0
        
        # Has designs
        if self.designs.count() > 0:
            progress += 25.0
        
        # Has calculations
        if self.calculations.count() > 0:
            progress += 25.0
        
        # Has target capacity
        if self.target_capacity_kw:
            progress += 25.0
        
        # Has timeline
        if self.start_date and self.target_completion_date:
            progress += 25.0
        
        return min(progress, 100.0)
    
    def get_estimated_roi(self) -> Optional[Dict[str, Any]]:
        """Calculate estimated return on investment.
        
        Returns:
            dict: ROI analysis or None
        """
        if not all([self.budget_amount, self.estimated_annual_production_kwh]):
            return None
        
        # Simplified ROI calculation
        # This would be expanded with real energy pricing data
        avg_electricity_rate = Decimal("1.50")  # ZAR per kWh
        annual_savings = self.estimated_annual_production_kwh * avg_electricity_rate
        
        if annual_savings > 0:
            payback_years = float(self.budget_amount / annual_savings)
            roi_20_years = float((annual_savings * 20 - self.budget_amount) / self.budget_amount * 100)
            
            return {
                "annual_savings": float(annual_savings),
                "payback_years": payback_years,
                "roi_20_years": roi_20_years,
                "currency": self.budget_currency
            }
        
        return None
    
    def update_location(self, latitude: float, longitude: float, elevation: Optional[float] = None) -> None:
        """Update project location coordinates.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            elevation: Elevation in meters
        """
        self.latitude = Decimal(str(latitude))
        self.longitude = Decimal(str(longitude))
        if elevation is not None:
            self.elevation = Decimal(str(elevation))
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the project.
        
        Args:
            tag: Tag to add
        """
        if self.tags is None:
            self.tags = []
        
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the project.
        
        Args:
            tag: Tag to remove
        """
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
    
    def to_dict(self, include_relationships: bool = False) -> dict:
        """Convert project to dictionary.
        
        Args:
            include_relationships: Include related objects
            
        Returns:
            dict: Project data
        """
        data = super().to_dict()
        
        # Add calculated fields
        data["progress"] = self.calculate_progress()
        data["estimated_roi"] = self.get_estimated_roi()
        
        if include_relationships:
            data["owner"] = self.owner.to_dict() if self.owner else None
            data["designs_count"] = self.designs.count()
            data["calculations_count"] = self.calculations.count()
        
        return data
    
    def __repr__(self) -> str:
        """String representation of project."""
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"