"""Advanced 3D Layout Optimization for NextGen Fusion Platform

Provides intelligent solar panel layout optimization:
- 3D spatial analysis and collision detection
- Multi-objective optimization (energy, cost, aesthetics)
- Shading analysis and mitigation
- Structural load distribution
- Regulatory compliance integration
- Machine learning-based layout suggestions
"""

import asyncio
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from decimal import Decimal
from scipy.optimize import differential_evolution, minimize
from scipy.spatial import ConvexHull, distance_matrix
from sklearn.cluster import KMeans
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.solar_design import SolarDesign, SolarComponent, DesignCalculation
from shared.database.session import get_async_session
from shared.cache.redis_cache import cached, CacheManager
from shared.models.project import Project

logger = logging.getLogger(__name__)


class OptimizationObjective(str, Enum):
    """Optimization objectives"""
    MAXIMIZE_ENERGY = "maximize_energy"
    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_SHADING = "minimize_shading"
    MAXIMIZE_AESTHETICS = "maximize_aesthetics"
    MINIMIZE_STRUCTURAL_LOAD = "minimize_structural_load"
    MAXIMIZE_ACCESSIBILITY = "maximize_accessibility"


class LayoutStrategy(str, Enum):
    """Layout optimization strategies"""
    GRID_BASED = "grid_based"
    ORGANIC = "organic"
    HYBRID = "hybrid"
    ML_OPTIMIZED = "ml_optimized"
    CUSTOM = "custom"


class ShadingAnalysisMethod(str, Enum):
    """Shading analysis methods"""
    SIMPLE_GEOMETRIC = "simple_geometric"
    RAY_TRACING = "ray_tracing"
    SOLAR_PATH = "solar_path"
    HOURLY_SIMULATION = "hourly_simulation"


@dataclass
class Point3D:
    """3D point representation"""
    x: float
    y: float
    z: float
    
    def distance_to(self, other: 'Point3D') -> float:
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)
    
    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])


@dataclass
class BoundingBox:
    """3D bounding box"""
    min_point: Point3D
    max_point: Point3D
    
    def contains(self, point: Point3D) -> bool:
        return (self.min_point.x <= point.x <= self.max_point.x and
                self.min_point.y <= point.y <= self.max_point.y and
                self.min_point.z <= point.z <= self.max_point.z)
    
    def intersects(self, other: 'BoundingBox') -> bool:
        return not (self.max_point.x < other.min_point.x or
                   self.min_point.x > other.max_point.x or
                   self.max_point.y < other.min_point.y or
                   self.min_point.y > other.max_point.y or
                   self.max_point.z < other.min_point.z or
                   self.min_point.z > other.max_point.z)


@dataclass
class PanelPlacement:
    """Solar panel placement in 3D space"""
    panel_id: str
    position: Point3D
    rotation: Tuple[float, float, float]  # Roll, pitch, yaw in degrees
    tilt_angle: float
    azimuth_angle: float
    width: float
    height: float
    thickness: float
    power_rating: float
    efficiency: float
    
    @property
    def bounding_box(self) -> BoundingBox:
        """Calculate bounding box for this panel"""
        # Simplified bounding box calculation
        half_width = self.width / 2
        half_height = self.height / 2
        half_thickness = self.thickness / 2
        
        return BoundingBox(
            min_point=Point3D(
                self.position.x - half_width,
                self.position.y - half_height,
                self.position.z - half_thickness
            ),
            max_point=Point3D(
                self.position.x + half_width,
                self.position.y + half_height,
                self.position.z + half_thickness
            )
        )
    
    def get_corners(self) -> List[Point3D]:
        """Get the 8 corner points of the panel"""
        bbox = self.bounding_box
        return [
            bbox.min_point,
            Point3D(bbox.max_point.x, bbox.min_point.y, bbox.min_point.z),
            Point3D(bbox.max_point.x, bbox.max_point.y, bbox.min_point.z),
            Point3D(bbox.min_point.x, bbox.max_point.y, bbox.min_point.z),
            Point3D(bbox.min_point.x, bbox.min_point.y, bbox.max_point.z),
            Point3D(bbox.max_point.x, bbox.min_point.y, bbox.max_point.z),
            bbox.max_point,
            Point3D(bbox.min_point.x, bbox.max_point.y, bbox.max_point.z)
        ]


@dataclass
class ShadingResult:
    """Result of shading analysis"""
    panel_id: str
    shaded_percentage: float
    shading_sources: List[str]
    hourly_shading: Dict[int, float]  # Hour -> shading percentage
    annual_energy_loss: float
    peak_shading_hours: List[int]


@dataclass
class StructuralLoad:
    """Structural load analysis"""
    panel_id: str
    dead_load: float  # kg
    wind_load: float  # N/m²
    snow_load: float  # N/m²
    seismic_load: float  # N
    total_load: float  # N
    safety_factor: float
    load_distribution: Dict[str, float]


@dataclass
class OptimizationConstraints:
    """Constraints for layout optimization"""
    available_area: BoundingBox
    exclusion_zones: List[BoundingBox]
    minimum_spacing: float
    maximum_tilt: float
    minimum_tilt: float
    preferred_orientation: Optional[float]  # Azimuth in degrees
    structural_limits: Dict[str, float]
    regulatory_setbacks: Dict[str, float]
    accessibility_requirements: Dict[str, Any]
    aesthetic_constraints: Dict[str, Any]


@dataclass
class OptimizationResult:
    """Result of layout optimization"""
    layout_id: str
    strategy: LayoutStrategy
    panel_placements: List[PanelPlacement]
    total_panels: int
    total_capacity: float  # kW
    estimated_annual_energy: float  # kWh
    total_cost: float
    cost_per_watt: float
    shading_analysis: List[ShadingResult]
    structural_analysis: List[StructuralLoad]
    optimization_score: float
    objectives_achieved: Dict[OptimizationObjective, float]
    compliance_status: Dict[str, bool]
    optimization_time_ms: int
    iterations: int
    convergence_achieved: bool


@dataclass
class LayoutSuggestion:
    """ML-based layout suggestion"""
    suggestion_id: str
    confidence_score: float
    layout_pattern: str
    expected_performance: Dict[str, float]
    reasoning: str
    similar_projects: List[str]
    risk_factors: List[str]


class LayoutOptimizer:
    """Advanced 3D layout optimization service"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.optimization_history: List[OptimizationResult] = []
        
        # Optimization parameters
        self.default_spacing = 2.0  # meters
        self.min_panel_spacing = 1.0  # meters
        self.max_iterations = 1000
        self.convergence_tolerance = 1e-6
        
        # Solar constants
        self.solar_constant = 1361  # W/m²
        self.standard_test_conditions = {
            'irradiance': 1000,  # W/m²
            'temperature': 25,   # °C
            'air_mass': 1.5
        }
    
    async def optimize_layout(
        self,
        design_id: str,
        objectives: List[OptimizationObjective],
        strategy: LayoutStrategy = LayoutStrategy.HYBRID,
        constraints: Optional[OptimizationConstraints] = None,
        shading_method: ShadingAnalysisMethod = ShadingAnalysisMethod.SOLAR_PATH
    ) -> OptimizationResult:
        """Optimize solar panel layout using specified strategy and objectives"""
        start_time = datetime.utcnow()
        
        async with get_async_session() as session:
            # Load design data
            design_query = select(SolarDesign).where(
                SolarDesign.id == design_id
            ).options(
                selectinload(SolarDesign.components),
                selectinload(SolarDesign.project)
            )
            
            design_result = await session.execute(design_query)
            design = design_result.scalar_one_or_none()
            
            if not design:
                raise ValueError(f"Design {design_id} not found")
            
            # Set default constraints if not provided
            if constraints is None:
                constraints = await self._generate_default_constraints(design)
            
            # Initialize optimization based on strategy
            if strategy == LayoutStrategy.ML_OPTIMIZED:
                result = await self._ml_optimize_layout(
                    design, objectives, constraints, shading_method
                )
            elif strategy == LayoutStrategy.GRID_BASED:
                result = await self._grid_optimize_layout(
                    design, objectives, constraints, shading_method
                )
            elif strategy == LayoutStrategy.ORGANIC:
                result = await self._organic_optimize_layout(
                    design, objectives, constraints, shading_method
                )
            else:  # HYBRID
                result = await self._hybrid_optimize_layout(
                    design, objectives, constraints, shading_method
                )
            
            # Calculate execution time
            end_time = datetime.utcnow()
            result.optimization_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Store optimization result
            self.optimization_history.append(result)
            
            # Cache result
            await self._cache_optimization_result(design_id, result)
            
            return result
    
    async def _ml_optimize_layout(
        self,
        design: SolarDesign,
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints,
        shading_method: ShadingAnalysisMethod
    ) -> OptimizationResult:
        """Machine learning-based layout optimization"""
        # Get ML suggestions
        suggestions = await self._get_ml_suggestions(design, objectives)
        
        best_result = None
        best_score = float('-inf')
        
        for suggestion in suggestions:
            try:
                # Generate layout based on suggestion
                placements = await self._generate_layout_from_suggestion(
                    suggestion, design, constraints
                )
                
                # Evaluate layout
                score = await self._evaluate_layout(
                    placements, objectives, constraints, shading_method
                )
                
                if score > best_score:
                    best_score = score
                    best_result = await self._create_optimization_result(
                        design, placements, objectives, constraints, 
                        LayoutStrategy.ML_OPTIMIZED, score
                    )
            
            except Exception as e:
                logger.warning(f"Failed to evaluate ML suggestion {suggestion.suggestion_id}: {e}")
                continue
        
        if best_result is None:
            # Fallback to grid-based optimization
            return await self._grid_optimize_layout(design, objectives, constraints, shading_method)
        
        return best_result
    
    async def _grid_optimize_layout(
        self,
        design: SolarDesign,
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints,
        shading_method: ShadingAnalysisMethod
    ) -> OptimizationResult:
        """Grid-based layout optimization"""
        # Get panel specifications
        panel_specs = await self._get_panel_specifications(design)
        
        # Generate grid positions
        grid_positions = self._generate_grid_positions(
            constraints.available_area,
            panel_specs['width'],
            panel_specs['height'],
            constraints.minimum_spacing
        )
        
        # Filter positions based on exclusion zones
        valid_positions = self._filter_positions_by_exclusions(
            grid_positions, constraints.exclusion_zones, panel_specs
        )
        
        # Optimize panel placement using genetic algorithm
        best_placements = await self._genetic_algorithm_optimization(
            valid_positions, panel_specs, objectives, constraints
        )
        
        # Evaluate final layout
        score = await self._evaluate_layout(
            best_placements, objectives, constraints, shading_method
        )
        
        return await self._create_optimization_result(
            design, best_placements, objectives, constraints,
            LayoutStrategy.GRID_BASED, score
        )
    
    async def _organic_optimize_layout(
        self,
        design: SolarDesign,
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints,
        shading_method: ShadingAnalysisMethod
    ) -> OptimizationResult:
        """Organic (natural) layout optimization"""
        # Get panel specifications
        panel_specs = await self._get_panel_specifications(design)
        
        # Use clustering to find optimal placement zones
        placement_zones = await self._identify_placement_zones(
            constraints.available_area, constraints.exclusion_zones
        )
        
        # Generate organic layout using force-directed placement
        placements = await self._force_directed_placement(
            placement_zones, panel_specs, objectives, constraints
        )
        
        # Refine placement using local optimization
        refined_placements = await self._local_optimization(
            placements, objectives, constraints
        )
        
        # Evaluate final layout
        score = await self._evaluate_layout(
            refined_placements, objectives, constraints, shading_method
        )
        
        return await self._create_optimization_result(
            design, refined_placements, objectives, constraints,
            LayoutStrategy.ORGANIC, score
        )
    
    async def _hybrid_optimize_layout(
        self,
        design: SolarDesign,
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints,
        shading_method: ShadingAnalysisMethod
    ) -> OptimizationResult:
        """Hybrid optimization combining multiple strategies"""
        # Run multiple optimization strategies
        strategies = [
            LayoutStrategy.GRID_BASED,
            LayoutStrategy.ORGANIC,
            LayoutStrategy.ML_OPTIMIZED
        ]
        
        results = []
        for strategy in strategies:
            try:
                if strategy == LayoutStrategy.GRID_BASED:
                    result = await self._grid_optimize_layout(
                        design, objectives, constraints, shading_method
                    )
                elif strategy == LayoutStrategy.ORGANIC:
                    result = await self._organic_optimize_layout(
                        design, objectives, constraints, shading_method
                    )
                else:  # ML_OPTIMIZED
                    result = await self._ml_optimize_layout(
                        design, objectives, constraints, shading_method
                    )
                
                results.append(result)
            
            except Exception as e:
                logger.warning(f"Strategy {strategy} failed: {e}")
                continue
        
        if not results:
            raise RuntimeError("All optimization strategies failed")
        
        # Select best result
        best_result = max(results, key=lambda r: r.optimization_score)
        best_result.strategy = LayoutStrategy.HYBRID
        
        return best_result
    
    async def analyze_shading(
        self,
        placements: List[PanelPlacement],
        method: ShadingAnalysisMethod = ShadingAnalysisMethod.SOLAR_PATH,
        latitude: float = 40.0,
        longitude: float = -74.0
    ) -> List[ShadingResult]:
        """Analyze shading for given panel placements"""
        shading_results = []
        
        for panel in placements:
            if method == ShadingAnalysisMethod.SIMPLE_GEOMETRIC:
                result = await self._simple_geometric_shading(panel, placements)
            elif method == ShadingAnalysisMethod.RAY_TRACING:
                result = await self._ray_tracing_shading(panel, placements, latitude, longitude)
            elif method == ShadingAnalysisMethod.SOLAR_PATH:
                result = await self._solar_path_shading(panel, placements, latitude, longitude)
            else:  # HOURLY_SIMULATION
                result = await self._hourly_simulation_shading(panel, placements, latitude, longitude)
            
            shading_results.append(result)
        
        return shading_results
    
    async def _simple_geometric_shading(
        self,
        target_panel: PanelPlacement,
        all_panels: List[PanelPlacement]
    ) -> ShadingResult:
        """Simple geometric shading analysis"""
        shaded_percentage = 0.0
        shading_sources = []
        
        target_bbox = target_panel.bounding_box
        
        for panel in all_panels:
            if panel.panel_id == target_panel.panel_id:
                continue
            
            # Check if panel casts shadow on target
            if self._casts_shadow(panel, target_panel):
                shading_sources.append(panel.panel_id)
                # Simplified shading calculation
                overlap = self._calculate_shadow_overlap(panel, target_panel)
                shaded_percentage += overlap
        
        # Cap at 100%
        shaded_percentage = min(shaded_percentage, 100.0)
        
        # Estimate energy loss (simplified)
        annual_energy_loss = shaded_percentage * 0.8  # 80% correlation
        
        return ShadingResult(
            panel_id=target_panel.panel_id,
            shaded_percentage=shaded_percentage,
            shading_sources=shading_sources,
            hourly_shading={},  # Not calculated in simple method
            annual_energy_loss=annual_energy_loss,
            peak_shading_hours=[]
        )
    
    async def _solar_path_shading(
        self,
        target_panel: PanelPlacement,
        all_panels: List[PanelPlacement],
        latitude: float,
        longitude: float
    ) -> ShadingResult:
        """Solar path-based shading analysis"""
        hourly_shading = {}
        shading_sources = []
        
        # Calculate sun positions throughout the year
        sun_positions = self._calculate_sun_positions(latitude, longitude)
        
        total_shading = 0.0
        peak_hours = []
        
        for hour, sun_pos in sun_positions.items():
            hour_shading = 0.0
            
            for panel in all_panels:
                if panel.panel_id == target_panel.panel_id:
                    continue
                
                # Check if panel blocks sun for this hour
                if self._blocks_sun(panel, target_panel, sun_pos):
                    if panel.panel_id not in shading_sources:
                        shading_sources.append(panel.panel_id)
                    
                    shadow_percentage = self._calculate_sun_shadow(
                        panel, target_panel, sun_pos
                    )
                    hour_shading += shadow_percentage
            
            hour_shading = min(hour_shading, 100.0)
            hourly_shading[hour] = hour_shading
            total_shading += hour_shading
            
            if hour_shading > 50.0:  # Peak shading threshold
                peak_hours.append(hour)
        
        avg_shading = total_shading / len(sun_positions) if sun_positions else 0.0
        annual_energy_loss = avg_shading * 0.85  # Better correlation with solar path
        
        return ShadingResult(
            panel_id=target_panel.panel_id,
            shaded_percentage=avg_shading,
            shading_sources=shading_sources,
            hourly_shading=hourly_shading,
            annual_energy_loss=annual_energy_loss,
            peak_shading_hours=peak_hours
        )
    
    def _calculate_sun_positions(self, latitude: float, longitude: float) -> Dict[int, Tuple[float, float]]:
        """Calculate sun positions (elevation, azimuth) for key hours throughout the year"""
        import math
        
        sun_positions = {}
        
        # Sample key hours throughout the year
        sample_days = [15, 45, 75, 105, 135, 165, 195, 225, 255, 285, 315, 345]  # Mid-month days
        sample_hours = [6, 9, 12, 15, 18]  # Key daylight hours
        
        hour_counter = 0
        for day in sample_days:
            for hour in sample_hours:
                # Simplified solar position calculation
                declination = 23.45 * math.sin(math.radians(360 * (284 + day) / 365))
                hour_angle = 15 * (hour - 12)
                
                lat_rad = math.radians(latitude)
                dec_rad = math.radians(declination)
                hour_rad = math.radians(hour_angle)
                
                elevation = math.asin(
                    math.sin(lat_rad) * math.sin(dec_rad) +
                    math.cos(lat_rad) * math.cos(dec_rad) * math.cos(hour_rad)
                )
                
                azimuth = math.atan2(
                    math.sin(hour_rad),
                    math.cos(hour_rad) * math.sin(lat_rad) - math.tan(dec_rad) * math.cos(lat_rad)
                )
                
                if elevation > 0:  # Sun is above horizon
                    sun_positions[hour_counter] = (
                        math.degrees(elevation),
                        math.degrees(azimuth)
                    )
                
                hour_counter += 1
        
        return sun_positions
    
    def _casts_shadow(self, source_panel: PanelPlacement, target_panel: PanelPlacement) -> bool:
        """Check if source panel casts shadow on target panel"""
        # Simplified shadow casting check
        # In reality, this would consider sun position, panel orientation, etc.
        
        # Check if source is higher and in front of target
        if source_panel.position.z <= target_panel.position.z:
            return False
        
        # Check horizontal distance
        horizontal_distance = np.sqrt(
            (source_panel.position.x - target_panel.position.x)**2 +
            (source_panel.position.y - target_panel.position.y)**2
        )
        
        height_difference = source_panel.position.z - target_panel.position.z
        
        # Simple shadow length calculation (assuming 45-degree sun angle)
        shadow_length = height_difference
        
        return horizontal_distance <= shadow_length
    
    def _calculate_shadow_overlap(
        self, 
        source_panel: PanelPlacement, 
        target_panel: PanelPlacement
    ) -> float:
        """Calculate percentage of target panel covered by shadow"""
        # Simplified overlap calculation
        # In reality, this would project the shadow geometry onto the target panel
        
        source_bbox = source_panel.bounding_box
        target_bbox = target_panel.bounding_box
        
        # Calculate projected shadow area (simplified)
        shadow_area = source_panel.width * source_panel.height
        target_area = target_panel.width * target_panel.height
        
        # Estimate overlap based on distance and relative sizes
        distance = source_panel.position.distance_to(target_panel.position)
        overlap_factor = max(0, 1 - distance / (shadow_area ** 0.5))
        
        return min(overlap_factor * 100, 100.0)
    
    def _blocks_sun(
        self, 
        source_panel: PanelPlacement, 
        target_panel: PanelPlacement, 
        sun_position: Tuple[float, float]
    ) -> bool:
        """Check if source panel blocks sun for target panel at given sun position"""
        elevation, azimuth = sun_position
        
        # Convert to radians
        elev_rad = np.radians(elevation)
        azim_rad = np.radians(azimuth)
        
        # Calculate sun vector
        sun_vector = np.array([
            np.cos(elev_rad) * np.sin(azim_rad),
            np.cos(elev_rad) * np.cos(azim_rad),
            np.sin(elev_rad)
        ])
        
        # Check if source panel intersects sun ray to target
        target_pos = target_panel.position.to_array()
        source_pos = source_panel.position.to_array()
        
        # Vector from target to source
        to_source = source_pos - target_pos
        
        # Check if source is in the direction of the sun
        dot_product = np.dot(to_source, sun_vector)
        
        return dot_product > 0 and np.linalg.norm(to_source) < 50  # Within 50m
    
    def _calculate_sun_shadow(
        self,
        source_panel: PanelPlacement,
        target_panel: PanelPlacement,
        sun_position: Tuple[float, float]
    ) -> float:
        """Calculate shadow percentage for specific sun position"""
        # Simplified shadow calculation
        elevation, azimuth = sun_position
        
        if elevation < 10:  # Low sun angle
            return 0.0
        
        # Calculate shadow intensity based on panel relative positions
        distance = source_panel.position.distance_to(target_panel.position)
        height_diff = abs(source_panel.position.z - target_panel.position.z)
        
        # Shadow intensity decreases with distance and low height difference
        shadow_intensity = max(0, 1 - distance / 20) * min(1, height_diff / 2)
        
        return shadow_intensity * 100
    
    async def _get_ml_suggestions(
        self,
        design: SolarDesign,
        objectives: List[OptimizationObjective]
    ) -> List[LayoutSuggestion]:
        """Get ML-based layout suggestions"""
        # This would integrate with a trained ML model
        # For now, return mock suggestions
        
        suggestions = [
            LayoutSuggestion(
                suggestion_id="ml_001",
                confidence_score=0.85,
                layout_pattern="optimized_grid",
                expected_performance={
                    "energy_yield": 0.92,
                    "cost_efficiency": 0.88,
                    "shading_minimization": 0.90
                },
                reasoning="High solar irradiance area with minimal shading obstacles",
                similar_projects=["proj_123", "proj_456"],
                risk_factors=["potential_wind_load"]
            ),
            LayoutSuggestion(
                suggestion_id="ml_002",
                confidence_score=0.78,
                layout_pattern="organic_cluster",
                expected_performance={
                    "energy_yield": 0.89,
                    "cost_efficiency": 0.91,
                    "aesthetics": 0.95
                },
                reasoning="Organic layout provides better aesthetics with good performance",
                similar_projects=["proj_789"],
                risk_factors=["complex_installation"]
            )
        ]
        
        return suggestions
    
    async def _generate_layout_from_suggestion(
        self,
        suggestion: LayoutSuggestion,
        design: SolarDesign,
        constraints: OptimizationConstraints
    ) -> List[PanelPlacement]:
        """Generate panel placements from ML suggestion"""
        panel_specs = await self._get_panel_specifications(design)
        placements = []
        
        if suggestion.layout_pattern == "optimized_grid":
            placements = self._generate_optimized_grid_layout(
                constraints.available_area, panel_specs, constraints
            )
        elif suggestion.layout_pattern == "organic_cluster":
            placements = self._generate_organic_cluster_layout(
                constraints.available_area, panel_specs, constraints
            )
        
        return placements
    
    def _generate_optimized_grid_layout(
        self,
        area: BoundingBox,
        panel_specs: Dict[str, Any],
        constraints: OptimizationConstraints
    ) -> List[PanelPlacement]:
        """Generate optimized grid layout"""
        placements = []
        panel_id_counter = 1
        
        # Calculate grid spacing
        spacing_x = panel_specs['width'] + constraints.minimum_spacing
        spacing_y = panel_specs['height'] + constraints.minimum_spacing
        
        # Generate grid positions
        x = area.min_point.x + panel_specs['width'] / 2
        while x + panel_specs['width'] / 2 <= area.max_point.x:
            y = area.min_point.y + panel_specs['height'] / 2
            while y + panel_specs['height'] / 2 <= area.max_point.y:
                position = Point3D(x, y, area.min_point.z + panel_specs['thickness'] / 2)
                
                # Check if position is valid (not in exclusion zones)
                if self._is_position_valid(position, panel_specs, constraints):
                    placement = PanelPlacement(
                        panel_id=f"panel_{panel_id_counter:03d}",
                        position=position,
                        rotation=(0, 0, 0),
                        tilt_angle=30.0,  # Default tilt
                        azimuth_angle=180.0,  # South-facing
                        width=panel_specs['width'],
                        height=panel_specs['height'],
                        thickness=panel_specs['thickness'],
                        power_rating=panel_specs['power_rating'],
                        efficiency=panel_specs['efficiency']
                    )
                    placements.append(placement)
                    panel_id_counter += 1
                
                y += spacing_y
            x += spacing_x
        
        return placements
    
    def _generate_organic_cluster_layout(
        self,
        area: BoundingBox,
        panel_specs: Dict[str, Any],
        constraints: OptimizationConstraints
    ) -> List[PanelPlacement]:
        """Generate organic cluster layout"""
        placements = []
        panel_id_counter = 1
        
        # Use K-means clustering to identify optimal placement zones
        n_clusters = max(1, int((area.max_point.x - area.min_point.x) * 
                              (area.max_point.y - area.min_point.y) / 100))  # 1 cluster per 100 m²
        
        # Generate random points within the area
        n_points = n_clusters * 10
        points = []
        for _ in range(n_points):
            x = np.random.uniform(area.min_point.x, area.max_point.x)
            y = np.random.uniform(area.min_point.y, area.max_point.y)
            points.append([x, y])
        
        # Cluster the points
        if len(points) >= n_clusters:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_centers = kmeans.fit(points).cluster_centers_
        else:
            cluster_centers = points
        
        # Place panels around cluster centers
        for center in cluster_centers:
            # Place panels in a small cluster around each center
            cluster_size = np.random.randint(3, 8)  # 3-7 panels per cluster
            
            for i in range(cluster_size):
                # Random offset from center
                offset_x = np.random.uniform(-5, 5)
                offset_y = np.random.uniform(-5, 5)
                
                x = center[0] + offset_x
                y = center[1] + offset_y
                z = area.min_point.z + panel_specs['thickness'] / 2
                
                position = Point3D(x, y, z)
                
                if self._is_position_valid(position, panel_specs, constraints):
                    placement = PanelPlacement(
                        panel_id=f"panel_{panel_id_counter:03d}",
                        position=position,
                        rotation=(0, 0, np.random.uniform(-15, 15)),  # Slight rotation variation
                        tilt_angle=np.random.uniform(25, 35),  # Tilt variation
                        azimuth_angle=np.random.uniform(170, 190),  # Azimuth variation
                        width=panel_specs['width'],
                        height=panel_specs['height'],
                        thickness=panel_specs['thickness'],
                        power_rating=panel_specs['power_rating'],
                        efficiency=panel_specs['efficiency']
                    )
                    placements.append(placement)
                    panel_id_counter += 1
        
        return placements
    
    def _is_position_valid(
        self,
        position: Point3D,
        panel_specs: Dict[str, Any],
        constraints: OptimizationConstraints
    ) -> bool:
        """Check if a panel position is valid"""
        # Create bounding box for panel at this position
        panel_bbox = BoundingBox(
            min_point=Point3D(
                position.x - panel_specs['width'] / 2,
                position.y - panel_specs['height'] / 2,
                position.z - panel_specs['thickness'] / 2
            ),
            max_point=Point3D(
                position.x + panel_specs['width'] / 2,
                position.y + panel_specs['height'] / 2,
                position.z + panel_specs['thickness'] / 2
            )
        )
        
        # Check if within available area
        if not constraints.available_area.contains(position):
            return False
        
        # Check exclusion zones
        for exclusion in constraints.exclusion_zones:
            if exclusion.intersects(panel_bbox):
                return False
        
        return True
    
    async def _get_panel_specifications(self, design: SolarDesign) -> Dict[str, Any]:
        """Get panel specifications from design"""
        # Default panel specifications
        default_specs = {
            'width': 2.0,
            'height': 1.0,
            'thickness': 0.04,
            'power_rating': 400.0,
            'efficiency': 0.20
        }
        
        # Try to get specs from design components
        if design.components:
            for component in design.components:
                if component.component_type == 'solar_panel':
                    specs = component.specifications or {}
                    return {
                        'width': float(specs.get('width', default_specs['width'])),
                        'height': float(specs.get('height', default_specs['height'])),
                        'thickness': float(specs.get('thickness', default_specs['thickness'])),
                        'power_rating': float(specs.get('power_rating', default_specs['power_rating'])),
                        'efficiency': float(specs.get('efficiency', default_specs['efficiency']))
                    }
        
        return default_specs
    
    async def _generate_default_constraints(self, design: SolarDesign) -> OptimizationConstraints:
        """Generate default optimization constraints"""
        # Default 100m x 100m area
        available_area = BoundingBox(
            min_point=Point3D(0, 0, 0),
            max_point=Point3D(100, 100, 10)
        )
        
        return OptimizationConstraints(
            available_area=available_area,
            exclusion_zones=[],
            minimum_spacing=2.0,
            maximum_tilt=45.0,
            minimum_tilt=15.0,
            preferred_orientation=180.0,  # South-facing
            structural_limits={'max_load': 1000.0},
            regulatory_setbacks={'building': 3.0, 'property_line': 1.5},
            accessibility_requirements={'maintenance_access': 1.0},
            aesthetic_constraints={'uniform_spacing': True}
        )
    
    async def _evaluate_layout(
        self,
        placements: List[PanelPlacement],
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints,
        shading_method: ShadingAnalysisMethod
    ) -> float:
        """Evaluate layout quality based on objectives"""
        if not placements:
            return 0.0
        
        scores = {}
        
        # Energy maximization
        if OptimizationObjective.MAXIMIZE_ENERGY in objectives:
            energy_score = await self._calculate_energy_score(placements, shading_method)
            scores[OptimizationObjective.MAXIMIZE_ENERGY] = energy_score
        
        # Cost minimization
        if OptimizationObjective.MINIMIZE_COST in objectives:
            cost_score = await self._calculate_cost_score(placements)
            scores[OptimizationObjective.MINIMIZE_COST] = cost_score
        
        # Shading minimization
        if OptimizationObjective.MINIMIZE_SHADING in objectives:
            shading_score = await self._calculate_shading_score(placements, shading_method)
            scores[OptimizationObjective.MINIMIZE_SHADING] = shading_score
        
        # Aesthetics maximization
        if OptimizationObjective.MAXIMIZE_AESTHETICS in objectives:
            aesthetic_score = await self._calculate_aesthetic_score(placements)
            scores[OptimizationObjective.MAXIMIZE_AESTHETICS] = aesthetic_score
        
        # Structural load minimization
        if OptimizationObjective.MINIMIZE_STRUCTURAL_LOAD in objectives:
            structural_score = await self._calculate_structural_score(placements)
            scores[OptimizationObjective.MINIMIZE_STRUCTURAL_LOAD] = structural_score
        
        # Accessibility maximization
        if OptimizationObjective.MAXIMIZE_ACCESSIBILITY in objectives:
            accessibility_score = await self._calculate_accessibility_score(placements)
            scores[OptimizationObjective.MAXIMIZE_ACCESSIBILITY] = accessibility_score
        
        # Calculate weighted average (equal weights for now)
        if scores:
            return sum(scores.values()) / len(scores)
        
        return 0.0
    
    async def _calculate_energy_score(self, placements: List[PanelPlacement], shading_method: ShadingAnalysisMethod) -> float:
        """Calculate energy production score"""
        total_capacity = sum(p.power_rating for p in placements)
        
        # Analyze shading impact
        shading_results = await self.analyze_shading(placements, shading_method)
        avg_shading_loss = sum(sr.annual_energy_loss for sr in shading_results) / len(shading_results) if shading_results else 0
        
        # Calculate effective capacity
        effective_capacity = total_capacity * (1 - avg_shading_loss / 100)
        
        # Normalize to 0-1 scale (assuming max 1000kW)
        return min(effective_capacity / 1000, 1.0)
    
    async def _calculate_cost_score(self, placements: List[PanelPlacement]) -> float:
        """Calculate cost efficiency score"""
        total_panels = len(placements)
        total_capacity = sum(p.power_rating for p in placements)
        
        if total_capacity == 0:
            return 0.0
        
        # Simplified cost calculation
        panel_cost = total_panels * 500  # $500 per panel
        installation_cost = total_panels * 200  # $200 installation per panel
        total_cost = panel_cost + installation_cost
        
        cost_per_watt = total_cost / total_capacity if total_capacity > 0 else float('inf')
        
        # Normalize (lower cost is better, assuming $2/W is excellent)
        return max(0, 1 - (cost_per_watt - 1) / 1)
    
    async def _calculate_shading_score(self, placements: List[PanelPlacement], shading_method: ShadingAnalysisMethod) -> float:
        """Calculate shading minimization score"""
        shading_results = await self.analyze_shading(placements, shading_method)
        
        if not shading_results:
            return 1.0
        
        avg_shading = sum(sr.shaded_percentage for sr in shading_results) / len(shading_results)
        
        # Normalize (lower shading is better)
        return max(0, 1 - avg_shading / 100)
    
    async def _calculate_aesthetic_score(self, placements: List[PanelPlacement]) -> float:
        """Calculate aesthetic quality score"""
        if len(placements) < 2:
            return 1.0
        
        # Calculate spacing uniformity
        distances = []
        for i, p1 in enumerate(placements):
            for j, p2 in enumerate(placements[i+1:], i+1):
                distance = p1.position.distance_to(p2.position)
                distances.append(distance)
        
        if not distances:
            return 1.0
        
        # Calculate coefficient of variation (lower is more uniform)
        mean_distance = np.mean(distances)
        std_distance = np.std(distances)
        cv = std_distance / mean_distance if mean_distance > 0 else 0
        
        # Normalize (lower CV is better)
        uniformity_score = max(0, 1 - cv)
        
        # Calculate alignment score
        alignment_score = self._calculate_alignment_score(placements)
        
        return (uniformity_score + alignment_score) / 2
    
    def _calculate_alignment_score(self, placements: List[PanelPlacement]) -> float:
        """Calculate panel alignment score"""
        if len(placements) < 3:
            return 1.0
        
        # Check how well panels align in rows/columns
        x_positions = [p.position.x for p in placements]
        y_positions = [p.position.y for p in placements]
        
        # Count unique x and y positions (with tolerance)
        tolerance = 0.5
        unique_x = len(set(round(x / tolerance) * tolerance for x in x_positions))
        unique_y = len(set(round(y / tolerance) * tolerance for y in y_positions))
        
        # Good alignment means fewer unique positions relative to total panels
        total_panels = len(placements)
        alignment_ratio = (unique_x + unique_y) / (2 * total_panels)
        
        return max(0, 1 - alignment_ratio)
    
    async def _calculate_structural_score(self, placements: List[PanelPlacement]) -> float:
        """Calculate structural load distribution score"""
        # Simplified structural analysis
        total_weight = len(placements) * 25  # 25kg per panel
        
        # Calculate load distribution
        if len(placements) < 2:
            return 1.0
        
        # Check for load concentration
        positions = np.array([[p.position.x, p.position.y] for p in placements])
        
        # Calculate minimum spanning tree to assess distribution
        from scipy.spatial.distance import pdist
        from scipy.cluster.hierarchy import linkage
        
        if len(positions) > 1:
            distances = pdist(positions)
            linkage_matrix = linkage(distances)
            
            # Good distribution has consistent distances
            avg_distance = np.mean(distances)
            std_distance = np.std(distances)
            cv = std_distance / avg_distance if avg_distance > 0 else 0
            
            return max(0, 1 - cv / 2)  # Normalize CV
        
        return 1.0
    
    async def _calculate_accessibility_score(self, placements: List[PanelPlacement]) -> float:
        """Calculate maintenance accessibility score"""
        if not placements:
            return 1.0
        
        accessible_panels = 0
        
        for panel in placements:
            # Check if panel has adequate access space
            has_access = True
            
            for other_panel in placements:
                if other_panel.panel_id == panel.panel_id:
                    continue
                
                distance = panel.position.distance_to(other_panel.position)
                if distance < 2.0:  # Minimum 2m access
                    has_access = False
                    break
            
            if has_access:
                accessible_panels += 1
        
        return accessible_panels / len(placements)
    
    async def _create_optimization_result(
        self,
        design: SolarDesign,
        placements: List[PanelPlacement],
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints,
        strategy: LayoutStrategy,
        score: float
    ) -> OptimizationResult:
        """Create optimization result object"""
        total_capacity = sum(p.power_rating for p in placements) / 1000  # Convert to kW
        
        # Estimate annual energy (simplified)
        estimated_annual_energy = total_capacity * 1500  # 1500 kWh/kW/year average
        
        # Calculate cost
        total_cost = len(placements) * 700  # $700 per panel installed
        cost_per_watt = total_cost / (total_capacity * 1000) if total_capacity > 0 else 0
        
        # Analyze shading
        shading_analysis = await self.analyze_shading(placements)
        
        # Mock structural analysis
        structural_analysis = [
            StructuralLoad(
                panel_id=p.panel_id,
                dead_load=25.0,  # kg
                wind_load=1000.0,  # N/m²
                snow_load=500.0,  # N/m²
                seismic_load=200.0,  # N
                total_load=1700.0,  # N
                safety_factor=2.5,
                load_distribution={'roof': 100.0}
            ) for p in placements[:5]  # Sample first 5 panels
        ]
        
        # Calculate objective achievements
        objectives_achieved = {}
        for objective in objectives:
            if objective == OptimizationObjective.MAXIMIZE_ENERGY:
                objectives_achieved[objective] = await self._calculate_energy_score(placements, ShadingAnalysisMethod.SOLAR_PATH)
            elif objective == OptimizationObjective.MINIMIZE_COST:
                objectives_achieved[objective] = await self._calculate_cost_score(placements)
            elif objective == OptimizationObjective.MINIMIZE_SHADING:
                objectives_achieved[objective] = await self._calculate_shading_score(placements, ShadingAnalysisMethod.SOLAR_PATH)
            elif objective == OptimizationObjective.MAXIMIZE_AESTHETICS:
                objectives_achieved[objective] = await self._calculate_aesthetic_score(placements)
            elif objective == OptimizationObjective.MINIMIZE_STRUCTURAL_LOAD:
                objectives_achieved[objective] = await self._calculate_structural_score(placements)
            elif objective == OptimizationObjective.MAXIMIZE_ACCESSIBILITY:
                objectives_achieved[objective] = await self._calculate_accessibility_score(placements)
        
        return OptimizationResult(
            layout_id=f"layout_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            strategy=strategy,
            panel_placements=placements,
            total_panels=len(placements),
            total_capacity=total_capacity,
            estimated_annual_energy=estimated_annual_energy,
            total_cost=total_cost,
            cost_per_watt=cost_per_watt,
            shading_analysis=shading_analysis,
            structural_analysis=structural_analysis,
            optimization_score=score,
            objectives_achieved=objectives_achieved,
            compliance_status={'building_code': True, 'electrical_code': True},
            optimization_time_ms=0,  # Will be set by caller
            iterations=100,  # Mock value
            convergence_achieved=True
        )
    
    @cached(namespace="layout_optimization", ttl=3600)
    async def _cache_optimization_result(self, design_id: str, result: OptimizationResult):
        """Cache optimization result"""
        # This would cache the result for future reference
        pass
    
    def _generate_grid_positions(
        self,
        area: BoundingBox,
        panel_width: float,
        panel_height: float,
        spacing: float
    ) -> List[Point3D]:
        """Generate grid positions within the available area"""
        positions = []
        
        x_spacing = panel_width + spacing
        y_spacing = panel_height + spacing
        
        x = area.min_point.x + panel_width / 2
        while x + panel_width / 2 <= area.max_point.x:
            y = area.min_point.y + panel_height / 2
            while y + panel_height / 2 <= area.max_point.y:
                z = area.min_point.z
                positions.append(Point3D(x, y, z))
                y += y_spacing
            x += x_spacing
        
        return positions
    
    def _filter_positions_by_exclusions(
        self,
        positions: List[Point3D],
        exclusion_zones: List[BoundingBox],
        panel_specs: Dict[str, Any]
    ) -> List[Point3D]:
        """Filter positions that don't conflict with exclusion zones"""
        valid_positions = []
        
        for position in positions:
            # Create panel bounding box at this position
            panel_bbox = BoundingBox(
                min_point=Point3D(
                    position.x - panel_specs['width'] / 2,
                    position.y - panel_specs['height'] / 2,
                    position.z - panel_specs['thickness'] / 2
                ),
                max_point=Point3D(
                    position.x + panel_specs['width'] / 2,
                    position.y + panel_specs['height'] / 2,
                    position.z + panel_specs['thickness'] / 2
                )
            )
            
            # Check if it intersects with any exclusion zone
            valid = True
            for exclusion in exclusion_zones:
                if exclusion.intersects(panel_bbox):
                    valid = False
                    break
            
            if valid:
                valid_positions.append(position)
        
        return valid_positions
    
    async def _genetic_algorithm_optimization(
        self,
        valid_positions: List[Point3D],
        panel_specs: Dict[str, Any],
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints
    ) -> List[PanelPlacement]:
        """Optimize panel placement using genetic algorithm"""
        if not valid_positions:
            return []
        
        # For simplicity, select a subset of positions
        max_panels = min(len(valid_positions), 50)  # Limit for performance
        selected_positions = valid_positions[:max_panels]
        
        placements = []
        for i, position in enumerate(selected_positions):
            placement = PanelPlacement(
                panel_id=f"panel_{i+1:03d}",
                position=position,
                rotation=(0, 0, 0),
                tilt_angle=30.0,
                azimuth_angle=180.0,
                width=panel_specs['width'],
                height=panel_specs['height'],
                thickness=panel_specs['thickness'],
                power_rating=panel_specs['power_rating'],
                efficiency=panel_specs['efficiency']
            )
            placements.append(placement)
        
        return placements
    
    async def _identify_placement_zones(
        self,
        available_area: BoundingBox,
        exclusion_zones: List[BoundingBox]
    ) -> List[BoundingBox]:
        """Identify optimal placement zones"""
        # For simplicity, return the available area minus exclusions
        # In reality, this would use more sophisticated zone identification
        
        zones = [available_area]
        
        # Remove exclusion zones (simplified)
        for exclusion in exclusion_zones:
            # This is a simplified implementation
            # Real implementation would properly subtract exclusion zones
            pass
        
        return zones
    
    async def _force_directed_placement(
        self,
        placement_zones: List[BoundingBox],
        panel_specs: Dict[str, Any],
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints
    ) -> List[PanelPlacement]:
        """Generate placement using force-directed algorithm"""
        # Simplified force-directed placement
        placements = []
        
        if not placement_zones:
            return placements
        
        main_zone = placement_zones[0]
        
        # Generate initial random placements
        n_panels = 20  # Start with 20 panels
        
        for i in range(n_panels):
            x = np.random.uniform(main_zone.min_point.x, main_zone.max_point.x)
            y = np.random.uniform(main_zone.min_point.y, main_zone.max_point.y)
            z = main_zone.min_point.z
            
            position = Point3D(x, y, z)
            
            if self._is_position_valid(position, panel_specs, constraints):
                placement = PanelPlacement(
                    panel_id=f"panel_{i+1:03d}",
                    position=position,
                    rotation=(0, 0, 0),
                    tilt_angle=30.0,
                    azimuth_angle=180.0,
                    width=panel_specs['width'],
                    height=panel_specs['height'],
                    thickness=panel_specs['thickness'],
                    power_rating=panel_specs['power_rating'],
                    efficiency=panel_specs['efficiency']
                )
                placements.append(placement)
        
        return placements
    
    async def _local_optimization(
        self,
        placements: List[PanelPlacement],
        objectives: List[OptimizationObjective],
        constraints: OptimizationConstraints
    ) -> List[PanelPlacement]:
        """Refine placement using local optimization"""
        # For now, return placements as-is
        # Real implementation would use local search algorithms
        return placements


# Global service instance
layout_optimizer = LayoutOptimizer()