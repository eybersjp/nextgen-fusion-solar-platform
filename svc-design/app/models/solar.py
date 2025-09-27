"""Solar design models for the Design Service.

This module contains SQLAlchemy models for solar system designs,
components, calculations, and performance analysis.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Boolean, Column, DateTime, String, Text, Numeric,
    Integer, JSON, Index, ForeignKey, CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin


class SolarDesign(BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """Solar system design model."""
    
    __tablename__ = "solar_designs"
    
    # Basic design information
    name = Column(
        String(255),
        nullable=False,
        doc="Design name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Design description"
    )
    
    version = Column(
        String(50),
        nullable=False,
        default="1.0",
        doc="Design version"
    )
    
    # Project relationship
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated project ID"
    )
    
    # Design status
    status = Column(
        String(50),
        nullable=False,
        default="draft",
        doc="Design status (draft, review, approved, rejected)"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Active design flag"
    )
    
    # System specifications
    system_capacity_kw = Column(
        Numeric(precision=10, scale=3),
        nullable=True,
        doc="Total system capacity in kW"
    )
    
    panel_count = Column(
        Integer,
        nullable=True,
        doc="Total number of solar panels"
    )
    
    inverter_count = Column(
        Integer,
        nullable=True,
        doc="Total number of inverters"
    )
    
    # System layout and configuration
    array_configuration = Column(
        JSON,
        nullable=True,
        doc="Array layout and configuration data"
    )
    
    panel_layout = Column(
        JSON,
        nullable=True,
        doc="Panel positioning and layout data"
    )
    
    electrical_design = Column(
        JSON,
        nullable=True,
        doc="Electrical system design and wiring"
    )
    
    # Performance estimates
    estimated_annual_production_kwh = Column(
        Numeric(precision=12, scale=2),
        nullable=True,
        doc="Estimated annual energy production in kWh"
    )
    
    capacity_factor = Column(
        Numeric(precision=5, scale=4),
        nullable=True,
        doc="System capacity factor (0-1)"
    )
    
    performance_ratio = Column(
        Numeric(precision=5, scale=4),
        nullable=True,
        doc="System performance ratio (0-1)"
    )
    
    # Environmental and shading analysis
    shading_analysis = Column(
        JSON,
        nullable=True,
        doc="Shading analysis results"
    )
    
    irradiance_data = Column(
        JSON,
        nullable=True,
        doc="Solar irradiance data and analysis"
    )
    
    weather_data = Column(
        JSON,
        nullable=True,
        doc="Weather data used for calculations"
    )
    
    # Financial analysis
    estimated_cost = Column(
        Numeric(precision=15, scale=2),
        nullable=True,
        doc="Estimated system cost"
    )
    
    cost_per_watt = Column(
        Numeric(precision=8, scale=4),
        nullable=True,
        doc="Cost per watt installed"
    )
    
    # Compliance and standards
    compliance_standards = Column(
        JSON,
        nullable=True,
        doc="Applicable compliance standards"
    )
    
    design_validation = Column(
        JSON,
        nullable=True,
        doc="Design validation results"
    )
    
    # Design metadata
    design_parameters = Column(
        JSON,
        nullable=True,
        doc="Design input parameters and constraints"
    )
    
    optimization_results = Column(
        JSON,
        nullable=True,
        doc="Design optimization results"
    )
    
    # Relationships
    project = relationship(
        "Project",
        back_populates="designs"
    )
    
    components = relationship(
        "SolarComponent",
        back_populates="design",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    calculations = relationship(
        "DesignCalculation",
        back_populates="design",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        Index("idx_designs_project", "project_id"),
        Index("idx_designs_status", "status"),
        Index("idx_designs_active", "is_active"),
        Index("idx_designs_version", "version"),
        Index("idx_designs_capacity", "system_capacity_kw"),
        CheckConstraint(
            "system_capacity_kw > 0",
            name="ck_designs_positive_capacity"
        ),
        CheckConstraint(
            "panel_count > 0",
            name="ck_designs_positive_panels"
        ),
        CheckConstraint(
            "inverter_count > 0",
            name="ck_designs_positive_inverters"
        ),
        CheckConstraint(
            "capacity_factor >= 0 AND capacity_factor <= 1",
            name="ck_designs_capacity_factor_range"
        ),
        CheckConstraint(
            "performance_ratio >= 0 AND performance_ratio <= 1",
            name="ck_designs_performance_ratio_range"
        ),
        CheckConstraint(
            "status IN ('draft', 'review', 'approved', 'rejected', 'archived')",
            name="ck_designs_valid_status"
        ),
    )
    
    def calculate_system_metrics(self) -> Dict[str, Any]:
        """Calculate key system performance metrics.
        
        Returns:
            dict: System metrics
        """
        metrics = {}
        
        if self.system_capacity_kw and self.estimated_annual_production_kwh:
            # Capacity factor calculation
            hours_per_year = 8760
            theoretical_max = float(self.system_capacity_kw) * hours_per_year
            metrics["capacity_factor"] = float(self.estimated_annual_production_kwh) / theoretical_max
        
        if self.panel_count and self.system_capacity_kw:
            # Watts per panel
            metrics["watts_per_panel"] = float(self.system_capacity_kw) * 1000 / self.panel_count
        
        if self.estimated_cost and self.system_capacity_kw:
            # Cost per watt
            metrics["cost_per_watt"] = float(self.estimated_cost) / (float(self.system_capacity_kw) * 1000)
        
        return metrics
    
    def validate_design(self) -> Dict[str, Any]:
        """Validate design parameters and constraints.
        
        Returns:
            dict: Validation results
        """
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        if not self.system_capacity_kw:
            validation["errors"].append("System capacity is required")
        
        if not self.panel_count:
            validation["errors"].append("Panel count is required")
        
        if not self.inverter_count:
            validation["errors"].append("Inverter count is required")
        
        # Check capacity factor
        if self.capacity_factor and (self.capacity_factor < 0.1 or self.capacity_factor > 0.3):
            validation["warnings"].append(f"Capacity factor {self.capacity_factor} is outside typical range (0.1-0.3)")
        
        # Check performance ratio
        if self.performance_ratio and (self.performance_ratio < 0.7 or self.performance_ratio > 0.9):
            validation["warnings"].append(f"Performance ratio {self.performance_ratio} is outside typical range (0.7-0.9)")
        
        validation["is_valid"] = len(validation["errors"]) == 0
        
        return validation
    
    def get_component_summary(self) -> Dict[str, Any]:
        """Get summary of design components.
        
        Returns:
            dict: Component summary
        """
        components = self.components.all()
        
        summary = {
            "total_components": len(components),
            "by_type": {},
            "total_cost": Decimal("0.00")
        }
        
        for component in components:
            comp_type = component.component_type
            if comp_type not in summary["by_type"]:
                summary["by_type"][comp_type] = {
                    "count": 0,
                    "total_cost": Decimal("0.00")
                }
            
            summary["by_type"][comp_type]["count"] += component.quantity
            if component.unit_cost:
                component_cost = component.unit_cost * component.quantity
                summary["by_type"][comp_type]["total_cost"] += component_cost
                summary["total_cost"] += component_cost
        
        return summary
    
    def clone(self, new_name: Optional[str] = None) -> "SolarDesign":
        """Create a copy of this design.
        
        Args:
            new_name: Name for the cloned design
            
        Returns:
            SolarDesign: Cloned design
        """
        clone_data = self.to_dict(exclude=["id", "created_at", "updated_at"])
        clone_data["name"] = new_name or f"{self.name} (Copy)"
        clone_data["status"] = "draft"
        clone_data["is_active"] = True
        
        return SolarDesign(**clone_data)
    
    def __repr__(self) -> str:
        """String representation of design."""
        return f"<SolarDesign(id={self.id}, name={self.name}, capacity={self.system_capacity_kw}kW)>"


class SolarComponent(BaseModel, TimestampMixin, SoftDeleteMixin):
    """Solar system component model."""
    
    __tablename__ = "solar_components"
    
    # Design relationship
    design_id = Column(
        UUID(as_uuid=True),
        ForeignKey("solar_designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated design ID"
    )
    
    # Component information
    component_type = Column(
        String(50),
        nullable=False,
        doc="Component type (panel, inverter, mounting, etc.)"
    )
    
    manufacturer = Column(
        String(100),
        nullable=True,
        doc="Component manufacturer"
    )
    
    model = Column(
        String(100),
        nullable=True,
        doc="Component model number"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Component name/description"
    )
    
    # Quantity and specifications
    quantity = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Number of components"
    )
    
    specifications = Column(
        JSON,
        nullable=True,
        doc="Component technical specifications"
    )
    
    # Performance characteristics
    rated_power_w = Column(
        Numeric(precision=8, scale=2),
        nullable=True,
        doc="Rated power in watts"
    )
    
    efficiency = Column(
        Numeric(precision=5, scale=4),
        nullable=True,
        doc="Component efficiency (0-1)"
    )
    
    # Physical characteristics
    dimensions = Column(
        JSON,
        nullable=True,
        doc="Component dimensions (length, width, height)"
    )
    
    weight_kg = Column(
        Numeric(precision=8, scale=2),
        nullable=True,
        doc="Component weight in kg"
    )
    
    # Cost information
    unit_cost = Column(
        Numeric(precision=10, scale=2),
        nullable=True,
        doc="Cost per unit"
    )
    
    currency = Column(
        String(3),
        nullable=False,
        default="ZAR",
        doc="Currency code (ISO 4217)"
    )
    
    # Installation and positioning
    position_data = Column(
        JSON,
        nullable=True,
        doc="Component position and orientation data"
    )
    
    installation_notes = Column(
        Text,
        nullable=True,
        doc="Installation notes and requirements"
    )
    
    # Warranty and lifecycle
    warranty_years = Column(
        Integer,
        nullable=True,
        doc="Warranty period in years"
    )
    
    expected_life_years = Column(
        Integer,
        nullable=True,
        doc="Expected component life in years"
    )
    
    # Compliance and certifications
    certifications = Column(
        JSON,
        nullable=True,
        doc="Component certifications and standards"
    )
    
    # Relationships
    design = relationship(
        "SolarDesign",
        back_populates="components"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        Index("idx_components_design", "design_id"),
        Index("idx_components_type", "component_type"),
        Index("idx_components_manufacturer", "manufacturer"),
        Index("idx_components_model", "model"),
        CheckConstraint(
            "quantity > 0",
            name="ck_components_positive_quantity"
        ),
        CheckConstraint(
            "rated_power_w >= 0",
            name="ck_components_positive_power"
        ),
        CheckConstraint(
            "efficiency >= 0 AND efficiency <= 1",
            name="ck_components_efficiency_range"
        ),
        CheckConstraint(
            "unit_cost >= 0",
            name="ck_components_positive_cost"
        ),
        CheckConstraint(
            "warranty_years >= 0",
            name="ck_components_positive_warranty"
        ),
        CheckConstraint(
            "expected_life_years >= 0",
            name="ck_components_positive_life"
        ),
        CheckConstraint(
            "component_type IN ('panel', 'inverter', 'mounting', 'monitoring', 'electrical', 'other')",
            name="ck_components_valid_type"
        ),
    )
    
    def calculate_total_cost(self) -> Optional[Decimal]:
        """Calculate total cost for this component.
        
        Returns:
            Decimal: Total cost or None
        """
        if self.unit_cost:
            return self.unit_cost * self.quantity
        return None
    
    def calculate_total_power(self) -> Optional[Decimal]:
        """Calculate total power for this component.
        
        Returns:
            Decimal: Total power in watts or None
        """
        if self.rated_power_w:
            return self.rated_power_w * self.quantity
        return None
    
    def __repr__(self) -> str:
        """String representation of component."""
        return f"<SolarComponent(id={self.id}, type={self.component_type}, qty={self.quantity})>"


class DesignCalculation(BaseModel, TimestampMixin, SoftDeleteMixin):
    """Design calculation and analysis model."""
    
    __tablename__ = "design_calculations"
    
    # Relationships
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated project ID"
    )
    
    design_id = Column(
        UUID(as_uuid=True),
        ForeignKey("solar_designs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Associated design ID (optional)"
    )
    
    # Calculation information
    calculation_type = Column(
        String(50),
        nullable=False,
        doc="Type of calculation (energy, financial, shading, etc.)"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Calculation name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Calculation description"
    )
    
    # Calculation status
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        doc="Calculation status (pending, running, completed, failed)"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Active calculation flag"
    )
    
    # Input parameters
    input_parameters = Column(
        JSON,
        nullable=True,
        doc="Calculation input parameters"
    )
    
    # Results
    results = Column(
        JSON,
        nullable=True,
        doc="Calculation results and outputs"
    )
    
    # Execution information
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Calculation start timestamp"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Calculation completion timestamp"
    )
    
    execution_time_ms = Column(
        Integer,
        nullable=True,
        doc="Execution time in milliseconds"
    )
    
    # Error handling
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if calculation failed"
    )
    
    # Metadata
    calculation_version = Column(
        String(50),
        nullable=True,
        doc="Calculation algorithm version"
    )
    
    calculation_metadata = Column(
        JSON,
        nullable=True,
        doc="Additional calculation metadata"
    )
    
    # Relationships
    project = relationship(
        "Project",
        back_populates="calculations"
    )
    
    design = relationship(
        "SolarDesign",
        back_populates="calculations"
    )
    
    # Table constraints and indexes
    __table_args__ = (
        Index("idx_calculations_project", "project_id"),
        Index("idx_calculations_design", "design_id"),
        Index("idx_calculations_type", "calculation_type"),
        Index("idx_calculations_status", "status"),
        Index("idx_calculations_active", "is_active"),
        Index("idx_calculations_completed", "completed_at"),
        CheckConstraint(
            "execution_time_ms >= 0",
            name="ck_calculations_positive_time"
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_calculations_valid_status"
        ),
        CheckConstraint(
            "calculation_type IN ('energy', 'financial', 'shading', 'irradiance', 'performance', 'optimization')",
            name="ck_calculations_valid_type"
        ),
    )
    
    def start_calculation(self) -> None:
        """Mark calculation as started."""
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)
    
    def complete_calculation(self, results: Dict[str, Any]) -> None:
        """Mark calculation as completed with results.
        
        Args:
            results: Calculation results
        """
        self.status = "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.results = results
        
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.execution_time_ms = int(duration.total_seconds() * 1000)
    
    def fail_calculation(self, error_message: str) -> None:
        """Mark calculation as failed with error.
        
        Args:
            error_message: Error description
        """
        self.status = "failed"
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error_message
        
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.execution_time_ms = int(duration.total_seconds() * 1000)
    
    def __repr__(self) -> str:
        """String representation of calculation."""
        return f"<DesignCalculation(id={self.id}, type={self.calculation_type}, status={self.status})>"