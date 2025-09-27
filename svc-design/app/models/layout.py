"""Layout models for the Design Service.

This module contains SQLAlchemy models for layout-related entities
including panel layouts, arrays, inverters, electrical components, and spatial data.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.orm import relationship, backref
# from geoalchemy2 import Geometry  # Disabled for SQLite compatibility

from .base import FullBaseModel


class LayoutStatus(PyEnum):
    """Layout status enumeration."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ZoneType(PyEnum):
    """Zone type enumeration."""
    PANEL_AREA = "panel_area"
    EXCLUSION = "exclusion"
    SETBACK = "setback"
    ACCESS_ROAD = "access_road"
    BUILDING = "building"
    VEGETATION = "vegetation"


class ConstraintType(PyEnum):
    """Constraint type enumeration."""
    SETBACK = "setback"
    HEIGHT_LIMIT = "height_limit"
    SHADING = "shading"
    ACCESS = "access"
    STRUCTURAL = "structural"
    REGULATORY = "regulatory"


class ModuleOrientation(PyEnum):
    """Module orientation enumeration."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class OptimizationObjective(PyEnum):
    """Optimization objective enumeration."""
    MAXIMIZE_CAPACITY = "maximize_capacity"
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_ENERGY = "maximize_energy"
    MINIMIZE_SHADING = "minimize_shading"


class OptimizationStatus(PyEnum):
    """Optimization status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Layout(FullBaseModel):
    """Layout model for solar panel layouts."""
    
    __tablename__ = 'layouts'
    
    # Basic information
    name = Column(String(255), nullable=False, doc="Layout name")
    description = Column(Text, doc="Layout description")
    
    # Design reference
    design_id = Column(UUID(as_uuid=True), nullable=False, index=True, doc="Design ID")
    
    # Layout type and configuration
    layout_type = Column(
        Enum('rooftop', 'ground_mount', 'carport', 'floating', 'agrivoltaic', name='layout_type_enum'),
        nullable=False,
        doc="Layout type"
    )
    
    mounting_type = Column(
        Enum('fixed_tilt', 'single_axis', 'dual_axis', 'flush_mount', name='mounting_type_enum'),
        nullable=False,
        default='fixed_tilt',
        doc="Mounting type"
    )
    
    # Spatial information
    # site_boundary = Column(Geometry('POLYGON', srid=4326), doc="Site boundary polygon")  # Disabled for SQLite
    # usable_area = Column(Geometry('MULTIPOLYGON', srid=4326), doc="Usable area polygons")  # Disabled for SQLite
    # exclusion_zones = Column(Geometry('MULTIPOLYGON', srid=4326), doc="Exclusion zone polygons")  # Disabled for SQLite
    site_boundary_json = Column(JSON, doc="Site boundary polygon as GeoJSON")
    usable_area_json = Column(JSON, doc="Usable area polygons as GeoJSON")
    exclusion_zones_json = Column(JSON, doc="Exclusion zone polygons as GeoJSON")
    
    # Layout parameters
    panel_tilt_degrees = Column(Float, doc="Panel tilt angle in degrees")
    panel_azimuth_degrees = Column(Float, doc="Panel azimuth angle in degrees")
    row_spacing_meters = Column(Float, doc="Row spacing in meters")
    panel_spacing_meters = Column(Float, doc="Panel spacing in meters")
    
    # Setback requirements
    front_setback_meters = Column(Float, doc="Front setback in meters")
    rear_setback_meters = Column(Float, doc="Rear setback in meters")
    side_setback_meters = Column(Float, doc="Side setback in meters")
    
    # Layout statistics
    total_panels = Column(Integer, doc="Total number of panels")
    total_capacity_kw = Column(Float, doc="Total capacity in kW")
    panel_density = Column(Float, doc="Panels per square meter")
    ground_coverage_ratio = Column(Float, doc="Ground coverage ratio")
    
    # Performance metrics
    shading_factor = Column(Float, doc="Inter-row shading factor")
    tilt_factor = Column(Float, doc="Tilt optimization factor")
    orientation_factor = Column(Float, doc="Orientation optimization factor")
    
    # Layout optimization
    is_optimized = Column(Boolean, nullable=False, default=False, doc="Is layout optimized")
    optimization_criteria = Column(JSON, doc="Optimization criteria and weights")
    optimization_results = Column(JSON, doc="Optimization results and metrics")
    
    # Generation information
    generation_method = Column(
        Enum('manual', 'auto', 'ai_assisted', 'imported', name='generation_method_enum'),
        nullable=False,
        default='manual',
        doc="Layout generation method"
    )
    
    generation_parameters = Column(JSON, doc="Generation parameters and settings")
    
    # Validation and compliance
    is_valid = Column(Boolean, nullable=False, default=True, doc="Is layout valid")
    validation_errors = Column(JSON, doc="Validation errors and warnings")
    compliance_checks = Column(JSON, doc="Compliance check results")
    
    def __repr__(self) -> str:
        return f"<Layout(id={self.id}, name='{self.name}', type='{self.layout_type}')>"
    
    @property
    def site_area_sqm(self) -> Optional[float]:
        """Calculate site area in square meters.
        
        Returns:
            Optional[float]: Site area or None
        """
        if self.site_boundary:
            from geoalchemy2.shape import to_shape
            polygon = to_shape(self.site_boundary)
            # Convert to appropriate projection for area calculation
            # This is a simplified calculation - in production, use proper projection
            return polygon.area * 111319.9 ** 2  # Rough conversion from degrees to meters
        return None
    
    def calculate_layout_metrics(self):
        """Calculate derived layout metrics."""
        if self.total_panels and self.site_area_sqm:
            self.panel_density = self.total_panels / self.site_area_sqm
        
        # Calculate ground coverage ratio if panel dimensions are available
        # This would need panel specifications from related arrays


class PanelArray(FullBaseModel):
    """Panel array model for groups of panels."""
    
    __tablename__ = 'panel_arrays'
    
    # References
    layout_id = Column(UUID(as_uuid=True), ForeignKey('layouts.id'), nullable=False, index=True)
    
    # Array information
    name = Column(String(255), nullable=False, doc="Array name")
    array_type = Column(
        Enum('string', 'block', 'subarray', name='array_type_enum'),
        nullable=False,
        default='string',
        doc="Array type"
    )
    
    # Spatial data
    # array_geometry = Column(Geometry('POLYGON', srid=4326), doc="Array boundary polygon")  # Disabled for SQLite
    array_geometry_json = Column(JSON, doc="Array boundary polygon as GeoJSON")
    panel_positions = Column(JSON, nullable=False, doc="Individual panel positions and orientations")
    
    # Array configuration
    panels_per_string = Column(Integer, doc="Panels per string")
    strings_per_array = Column(Integer, doc="Strings per array")
    total_panels = Column(Integer, nullable=False, doc="Total panels in array")
    
    # Electrical configuration
    dc_capacity_kw = Column(Float, doc="DC capacity in kW")
    operating_voltage = Column(Float, doc="Operating voltage")
    operating_current = Column(Float, doc="Operating current")
    
    # Panel specifications
    panel_model = Column(String(255), doc="Panel model")
    panel_manufacturer = Column(String(255), doc="Panel manufacturer")
    panel_power_watts = Column(Float, doc="Panel power rating in watts")
    panel_efficiency = Column(Float, doc="Panel efficiency percentage")
    panel_width_mm = Column(Float, doc="Panel width in millimeters")
    panel_height_mm = Column(Float, doc="Panel height in millimeters")
    panel_thickness_mm = Column(Float, doc="Panel thickness in millimeters")
    
    # Mounting and orientation
    tilt_degrees = Column(Float, doc="Tilt angle in degrees")
    azimuth_degrees = Column(Float, doc="Azimuth angle in degrees")
    mounting_height_mm = Column(Float, doc="Mounting height in millimeters")
    
    # Performance data
    shading_losses = Column(Float, doc="Shading losses percentage")
    soiling_losses = Column(Float, doc="Soiling losses percentage")
    mismatch_losses = Column(Float, doc="Mismatch losses percentage")
    
    # Array status
    is_active = Column(Boolean, nullable=False, default=True, doc="Is array active")
    installation_date = Column(DateTime(timezone=True), doc="Installation date")
    
    # Relationships
    layout = relationship("Layout", backref="arrays")
    
    def __repr__(self) -> str:
        return f"<PanelArray(id={self.id}, name='{self.name}', panels={self.total_panels})>"
    
    @property
    def panel_area_sqm(self) -> Optional[float]:
        """Calculate total panel area in square meters.
        
        Returns:
            Optional[float]: Panel area or None
        """
        if self.panel_width_mm and self.panel_height_mm and self.total_panels:
            panel_area = (self.panel_width_mm / 1000) * (self.panel_height_mm / 1000)
            return panel_area * self.total_panels
        return None


class Inverter(FullBaseModel):
    """Inverter model for power conversion equipment."""
    
    __tablename__ = 'inverters'
    
    # References
    layout_id = Column(UUID(as_uuid=True), ForeignKey('layouts.id'), nullable=False, index=True)
    
    # Inverter information
    name = Column(String(255), nullable=False, doc="Inverter name")
    inverter_type = Column(
        Enum('string', 'central', 'power_optimizer', 'microinverter', name='inverter_type_enum'),
        nullable=False,
        doc="Inverter type"
    )
    
    # Manufacturer and model
    manufacturer = Column(String(255), doc="Inverter manufacturer")
    model = Column(String(255), doc="Inverter model")
    serial_number = Column(String(255), doc="Serial number")
    
    # Electrical specifications
    ac_power_rating_kw = Column(Float, nullable=False, doc="AC power rating in kW")
    dc_power_rating_kw = Column(Float, doc="DC power rating in kW")
    efficiency_percent = Column(Float, doc="Efficiency percentage")
    
    # Voltage specifications
    ac_voltage_nominal = Column(Float, doc="Nominal AC voltage")
    ac_voltage_range_min = Column(Float, doc="Minimum AC voltage")
    ac_voltage_range_max = Column(Float, doc="Maximum AC voltage")
    dc_voltage_nominal = Column(Float, doc="Nominal DC voltage")
    dc_voltage_range_min = Column(Float, doc="Minimum DC voltage")
    dc_voltage_range_max = Column(Float, doc="Maximum DC voltage")
    
    # Current specifications
    ac_current_max = Column(Float, doc="Maximum AC current")
    dc_current_max = Column(Float, doc="Maximum DC current")
    
    # Physical specifications
    weight_kg = Column(Float, doc="Weight in kilograms")
    dimensions_mm = Column(JSON, doc="Dimensions in millimeters (width, height, depth)")
    
    # Environmental specifications
    operating_temp_min = Column(Float, doc="Minimum operating temperature")
    operating_temp_max = Column(Float, doc="Maximum operating temperature")
    ip_rating = Column(String(10), doc="IP protection rating")
    
    # Location and installation
    # location_coordinates = Column(Geometry('POINT', srid=4326), doc="Inverter location")  # Disabled for SQLite
    location_latitude = Column(Float, doc="Inverter latitude")
    location_longitude = Column(Float, doc="Inverter longitude")
    installation_type = Column(
        Enum('indoor', 'outdoor', 'ground_mount', 'wall_mount', name='installation_type_enum'),
        doc="Installation type"
    )
    
    # Connected arrays
    connected_arrays = Column(JSON, doc="Connected array IDs and configurations")
    
    # Performance monitoring
    monitoring_enabled = Column(Boolean, nullable=False, default=True, doc="Monitoring enabled")
    communication_protocol = Column(String(50), doc="Communication protocol")
    
    # Status and maintenance
    operational_status = Column(
        Enum('operational', 'maintenance', 'fault', 'offline', name='operational_status_enum'),
        nullable=False,
        default='operational',
        doc="Operational status"
    )
    
    last_maintenance_date = Column(DateTime(timezone=True), doc="Last maintenance date")
    next_maintenance_date = Column(DateTime(timezone=True), doc="Next maintenance date")
    
    # Relationships
    layout = relationship("Layout", backref="inverters")
    
    def __repr__(self) -> str:
        return f"<Inverter(id={self.id}, name='{self.name}', type='{self.inverter_type}')>"
    
    @property
    def dc_ac_ratio(self) -> Optional[float]:
        """Calculate DC to AC ratio.
        
        Returns:
            Optional[float]: DC/AC ratio or None
        """
        if self.dc_power_rating_kw and self.ac_power_rating_kw:
            return self.dc_power_rating_kw / self.ac_power_rating_kw
        return None


class ElectricalComponent(FullBaseModel):
    """Electrical component model for other electrical equipment."""
    
    __tablename__ = 'electrical_components'
    
    # References
    layout_id = Column(UUID(as_uuid=True), ForeignKey('layouts.id'), nullable=False, index=True)
    
    # Component information
    name = Column(String(255), nullable=False, doc="Component name")
    component_type = Column(
        Enum(
            'combiner_box', 'disconnect_switch', 'meter', 'transformer', 'breaker',
            'fuse', 'surge_protector', 'monitoring_device', 'other',
            name='component_type_enum'
        ),
        nullable=False,
        doc="Component type"
    )
    
    # Manufacturer and model
    manufacturer = Column(String(255), doc="Component manufacturer")
    model = Column(String(255), doc="Component model")
    part_number = Column(String(255), doc="Part number")
    serial_number = Column(String(255), doc="Serial number")
    
    # Electrical specifications
    voltage_rating = Column(Float, doc="Voltage rating")
    current_rating = Column(Float, doc="Current rating")
    power_rating = Column(Float, doc="Power rating")
    
    # Physical specifications
    weight_kg = Column(Float, doc="Weight in kilograms")
    dimensions_mm = Column(JSON, doc="Dimensions in millimeters")
    
    # Location and installation
    # location_coordinates = Column(Geometry('POINT', srid=4326), doc="Component location")  # Disabled for SQLite
    location_latitude = Column(Float, doc="Component latitude")
    location_longitude = Column(Float, doc="Component longitude")
    installation_type = Column(String(100), doc="Installation type")
    
    # Connections
    input_connections = Column(JSON, doc="Input connection specifications")
    output_connections = Column(JSON, doc="Output connection specifications")
    
    # Status and maintenance
    operational_status = Column(
        Enum('operational', 'maintenance', 'fault', 'offline', name='operational_status_enum'),
        nullable=False,
        default='operational',
        doc="Operational status"
    )
    
    installation_date = Column(DateTime(timezone=True), doc="Installation date")
    warranty_expiry_date = Column(DateTime(timezone=True), doc="Warranty expiry date")
    
    # Relationships
    layout = relationship("Layout", backref="electrical_components")
    
    def __repr__(self) -> str:
        return f"<ElectricalComponent(id={self.id}, name='{self.name}', type='{self.component_type}')>"


class CableRun(FullBaseModel):
    """Cable run model for electrical connections."""
    
    __tablename__ = 'cable_runs'
    
    # References
    layout_id = Column(UUID(as_uuid=True), ForeignKey('layouts.id'), nullable=False, index=True)
    
    # Cable information
    name = Column(String(255), nullable=False, doc="Cable run name")
    cable_type = Column(
        Enum('dc', 'ac', 'communication', 'grounding', name='cable_type_enum'),
        nullable=False,
        doc="Cable type"
    )
    
    # Cable specifications
    conductor_material = Column(String(50), doc="Conductor material (copper, aluminum)")
    conductor_size_awg = Column(String(20), doc="Conductor size (AWG)")
    insulation_type = Column(String(100), doc="Insulation type")
    jacket_type = Column(String(100), doc="Jacket type")
    
    # Electrical specifications
    voltage_rating = Column(Float, doc="Voltage rating")
    current_capacity = Column(Float, doc="Current carrying capacity")
    resistance_per_meter = Column(Float, doc="Resistance per meter")
    
    # Physical specifications
    cable_length_meters = Column(Float, nullable=False, doc="Cable length in meters")
    cable_diameter_mm = Column(Float, doc="Cable diameter in millimeters")
    
    # Route information
    # route_geometry = Column(Geometry('LINESTRING', srid=4326), doc="Cable route geometry")  # Disabled for SQLite
    route_geometry_json = Column(JSON, doc="Cable route geometry as GeoJSON")
    installation_method = Column(
        Enum('underground', 'overhead', 'conduit', 'tray', 'direct_burial', name='installation_method_enum'),
        doc="Installation method"
    )
    
    # Connection points
    from_component_id = Column(UUID(as_uuid=True), doc="Source component ID")
    to_component_id = Column(UUID(as_uuid=True), doc="Destination component ID")
    from_terminal = Column(String(50), doc="Source terminal")
    to_terminal = Column(String(50), doc="Destination terminal")
    
    # Performance calculations
    voltage_drop_percent = Column(Float, doc="Voltage drop percentage")
    power_loss_watts = Column(Float, doc="Power loss in watts")
    
    # Installation details
    conduit_size = Column(String(20), doc="Conduit size")
    burial_depth_mm = Column(Float, doc="Burial depth in millimeters")
    
    # Status
    installation_status = Column(
        Enum('planned', 'installed', 'tested', 'commissioned', name='installation_status_enum'),
        nullable=False,
        default='planned',
        doc="Installation status"
    )
    
    # Relationships
    layout = relationship("Layout", backref="cable_runs")
    
    def __repr__(self) -> str:
        return f"<CableRun(id={self.id}, name='{self.name}', type='{self.cable_type}')>"
    
    def calculate_voltage_drop(self, current_amps: float) -> float:
        """Calculate voltage drop for given current.
        
        Args:
            current_amps: Current in amperes
            
        Returns:
            float: Voltage drop in volts
        """
        if self.resistance_per_meter and self.cable_length_meters:
            total_resistance = self.resistance_per_meter * self.cable_length_meters
            return current_amps * total_resistance
        return 0.0


class LayoutOptimization(FullBaseModel):
    """Layout optimization model for tracking optimization runs."""
    
    __tablename__ = 'layout_optimizations'
    
    # References
    layout_id = Column(UUID(as_uuid=True), ForeignKey('layouts.id'), nullable=False, index=True)
    
    # Optimization information
    optimization_type = Column(
        Enum('energy', 'cost', 'irr', 'multi_objective', name='optimization_type_enum'),
        nullable=False,
        doc="Optimization type"
    )
    
    # Optimization parameters
    objective_function = Column(JSON, nullable=False, doc="Objective function definition")
    constraints = Column(JSON, doc="Optimization constraints")
    algorithm = Column(String(100), doc="Optimization algorithm used")
    
    # Input parameters
    input_parameters = Column(JSON, nullable=False, doc="Input parameters for optimization")
    
    # Results
    optimization_results = Column(JSON, doc="Detailed optimization results")
    best_solution = Column(JSON, doc="Best solution found")
    convergence_data = Column(JSON, doc="Convergence data and metrics")
    
    # Performance metrics
    initial_objective_value = Column(Float, doc="Initial objective function value")
    final_objective_value = Column(Float, doc="Final objective function value")
    improvement_percent = Column(Float, doc="Improvement percentage")
    
    # Execution information
    execution_time_seconds = Column(Float, doc="Execution time in seconds")
    iterations = Column(Integer, doc="Number of iterations")
    
    # Status
    optimization_status = Column(
        Enum('running', 'completed', 'failed', 'cancelled', name='optimization_status_enum'),
        nullable=False,
        default='running',
        doc="Optimization status"
    )
    
    error_message = Column(Text, doc="Error message if failed")
    
    # Relationships
    layout = relationship("Layout", backref="optimizations")
    
    def __repr__(self) -> str:
        return f"<LayoutOptimization(id={self.id}, type='{self.optimization_type}', status='{self.optimization_status}')>"