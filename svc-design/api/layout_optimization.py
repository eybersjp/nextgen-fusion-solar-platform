"""Layout Optimization API Endpoints for NextGen Fusion Platform

Provides REST API endpoints for advanced 3D solar panel layout optimization:
- Layout optimization with multiple strategies
- Shading analysis and visualization
- Structural load analysis
- Performance metrics and reporting
- ML-based layout suggestions
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..services.layout_optimizer import (
    layout_optimizer,
    OptimizationObjective,
    LayoutStrategy,
    ShadingAnalysisMethod,
    OptimizationConstraints,
    BoundingBox,
    Point3D,
    PanelPlacement,
    OptimizationResult,
    ShadingResult,
    StructuralLoad,
    LayoutSuggestion
)
from ..models.solar_design import SolarDesign
from shared.database.session import get_async_session
from shared.auth.dependencies import get_current_user
from shared.models.user import User
from shared.cache.redis_cache import cached

router = APIRouter(prefix="/layout-optimization", tags=["Layout Optimization"])


# Request Models
class Point3DRequest(BaseModel):
    """3D point request model"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: float = Field(..., description="Z coordinate")


class BoundingBoxRequest(BaseModel):
    """Bounding box request model"""
    min_point: Point3DRequest = Field(..., description="Minimum point")
    max_point: Point3DRequest = Field(..., description="Maximum point")
    
    @validator('max_point')
    def validate_max_point(cls, v, values):
        if 'min_point' in values:
            min_p = values['min_point']
            if v.x <= min_p.x or v.y <= min_p.y or v.z <= min_p.z:
                raise ValueError("Max point must be greater than min point in all dimensions")
        return v


class OptimizationConstraintsRequest(BaseModel):
    """Optimization constraints request model"""
    available_area: BoundingBoxRequest = Field(..., description="Available installation area")
    exclusion_zones: List[BoundingBoxRequest] = Field(default=[], description="Areas to exclude from installation")
    minimum_spacing: float = Field(default=2.0, ge=0.5, le=10.0, description="Minimum spacing between panels (meters)")
    maximum_tilt: float = Field(default=45.0, ge=0, le=90, description="Maximum panel tilt angle (degrees)")
    minimum_tilt: float = Field(default=15.0, ge=0, le=90, description="Minimum panel tilt angle (degrees)")
    preferred_orientation: Optional[float] = Field(default=180.0, ge=0, le=360, description="Preferred azimuth angle (degrees)")
    structural_limits: Dict[str, float] = Field(default={}, description="Structural load limits")
    regulatory_setbacks: Dict[str, float] = Field(default={}, description="Required setbacks from boundaries")
    accessibility_requirements: Dict[str, Any] = Field(default={}, description="Accessibility requirements")
    aesthetic_constraints: Dict[str, Any] = Field(default={}, description="Aesthetic constraints")
    
    @validator('minimum_tilt')
    def validate_tilt_range(cls, v, values):
        if 'maximum_tilt' in values and v >= values['maximum_tilt']:
            raise ValueError("Minimum tilt must be less than maximum tilt")
        return v


class LayoutOptimizationRequest(BaseModel):
    """Layout optimization request model"""
    design_id: str = Field(..., description="Solar design ID")
    objectives: List[OptimizationObjective] = Field(..., min_items=1, description="Optimization objectives")
    strategy: LayoutStrategy = Field(default=LayoutStrategy.HYBRID, description="Optimization strategy")
    constraints: Optional[OptimizationConstraintsRequest] = Field(default=None, description="Optimization constraints")
    shading_method: ShadingAnalysisMethod = Field(default=ShadingAnalysisMethod.SOLAR_PATH, description="Shading analysis method")
    latitude: float = Field(default=40.0, ge=-90, le=90, description="Site latitude")
    longitude: float = Field(default=-74.0, ge=-180, le=180, description="Site longitude")


class ShadingAnalysisRequest(BaseModel):
    """Shading analysis request model"""
    design_id: str = Field(..., description="Solar design ID")
    layout_id: Optional[str] = Field(default=None, description="Specific layout ID to analyze")
    method: ShadingAnalysisMethod = Field(default=ShadingAnalysisMethod.SOLAR_PATH, description="Analysis method")
    latitude: float = Field(default=40.0, ge=-90, le=90, description="Site latitude")
    longitude: float = Field(default=-74.0, ge=-180, le=180, description="Site longitude")
    time_range: Optional[Dict[str, str]] = Field(default=None, description="Time range for analysis")


class LayoutComparisonRequest(BaseModel):
    """Layout comparison request model"""
    layout_ids: List[str] = Field(..., min_items=2, max_items=5, description="Layout IDs to compare")
    comparison_metrics: List[str] = Field(default=[], description="Specific metrics to compare")


# Response Models
class Point3DResponse(BaseModel):
    """3D point response model"""
    x: float
    y: float
    z: float


class PanelPlacementResponse(BaseModel):
    """Panel placement response model"""
    panel_id: str
    position: Point3DResponse
    rotation: List[float]  # [roll, pitch, yaw]
    tilt_angle: float
    azimuth_angle: float
    width: float
    height: float
    thickness: float
    power_rating: float
    efficiency: float


class ShadingResultResponse(BaseModel):
    """Shading result response model"""
    panel_id: str
    shaded_percentage: float
    shading_sources: List[str]
    hourly_shading: Dict[int, float]
    annual_energy_loss: float
    peak_shading_hours: List[int]


class StructuralLoadResponse(BaseModel):
    """Structural load response model"""
    panel_id: str
    dead_load: float
    wind_load: float
    snow_load: float
    seismic_load: float
    total_load: float
    safety_factor: float
    load_distribution: Dict[str, float]


class OptimizationResultResponse(BaseModel):
    """Optimization result response model"""
    layout_id: str
    strategy: LayoutStrategy
    panel_placements: List[PanelPlacementResponse]
    total_panels: int
    total_capacity: float
    estimated_annual_energy: float
    total_cost: float
    cost_per_watt: float
    shading_analysis: List[ShadingResultResponse]
    structural_analysis: List[StructuralLoadResponse]
    optimization_score: float
    objectives_achieved: Dict[OptimizationObjective, float]
    compliance_status: Dict[str, bool]
    optimization_time_ms: int
    iterations: int
    convergence_achieved: bool
    created_at: datetime


class LayoutSuggestionResponse(BaseModel):
    """Layout suggestion response model"""
    suggestion_id: str
    confidence_score: float
    layout_pattern: str
    expected_performance: Dict[str, float]
    reasoning: str
    similar_projects: List[str]
    risk_factors: List[str]


class OptimizationSummaryResponse(BaseModel):
    """Optimization summary response model"""
    total_optimizations: int
    successful_optimizations: int
    average_optimization_time_ms: float
    best_performing_strategy: LayoutStrategy
    common_objectives: List[OptimizationObjective]
    performance_trends: Dict[str, float]


class LayoutComparisonResponse(BaseModel):
    """Layout comparison response model"""
    comparison_id: str
    layouts: List[OptimizationResultResponse]
    performance_comparison: Dict[str, Dict[str, float]]
    recommendations: List[str]
    best_layout_id: str
    comparison_metrics: Dict[str, Any]


# Helper functions
def convert_constraints_to_internal(constraints_req: OptimizationConstraintsRequest) -> OptimizationConstraints:
    """Convert request constraints to internal format"""
    available_area = BoundingBox(
        min_point=Point3D(
            constraints_req.available_area.min_point.x,
            constraints_req.available_area.min_point.y,
            constraints_req.available_area.min_point.z
        ),
        max_point=Point3D(
            constraints_req.available_area.max_point.x,
            constraints_req.available_area.max_point.y,
            constraints_req.available_area.max_point.z
        )
    )
    
    exclusion_zones = [
        BoundingBox(
            min_point=Point3D(zone.min_point.x, zone.min_point.y, zone.min_point.z),
            max_point=Point3D(zone.max_point.x, zone.max_point.y, zone.max_point.z)
        )
        for zone in constraints_req.exclusion_zones
    ]
    
    return OptimizationConstraints(
        available_area=available_area,
        exclusion_zones=exclusion_zones,
        minimum_spacing=constraints_req.minimum_spacing,
        maximum_tilt=constraints_req.maximum_tilt,
        minimum_tilt=constraints_req.minimum_tilt,
        preferred_orientation=constraints_req.preferred_orientation,
        structural_limits=constraints_req.structural_limits,
        regulatory_setbacks=constraints_req.regulatory_setbacks,
        accessibility_requirements=constraints_req.accessibility_requirements,
        aesthetic_constraints=constraints_req.aesthetic_constraints
    )


def convert_result_to_response(result: OptimizationResult) -> OptimizationResultResponse:
    """Convert internal result to response format"""
    panel_placements = [
        PanelPlacementResponse(
            panel_id=p.panel_id,
            position=Point3DResponse(x=p.position.x, y=p.position.y, z=p.position.z),
            rotation=list(p.rotation),
            tilt_angle=p.tilt_angle,
            azimuth_angle=p.azimuth_angle,
            width=p.width,
            height=p.height,
            thickness=p.thickness,
            power_rating=p.power_rating,
            efficiency=p.efficiency
        )
        for p in result.panel_placements
    ]
    
    shading_analysis = [
        ShadingResultResponse(
            panel_id=s.panel_id,
            shaded_percentage=s.shaded_percentage,
            shading_sources=s.shading_sources,
            hourly_shading=s.hourly_shading,
            annual_energy_loss=s.annual_energy_loss,
            peak_shading_hours=s.peak_shading_hours
        )
        for s in result.shading_analysis
    ]
    
    structural_analysis = [
        StructuralLoadResponse(
            panel_id=s.panel_id,
            dead_load=s.dead_load,
            wind_load=s.wind_load,
            snow_load=s.snow_load,
            seismic_load=s.seismic_load,
            total_load=s.total_load,
            safety_factor=s.safety_factor,
            load_distribution=s.load_distribution
        )
        for s in result.structural_analysis
    ]
    
    return OptimizationResultResponse(
        layout_id=result.layout_id,
        strategy=result.strategy,
        panel_placements=panel_placements,
        total_panels=result.total_panels,
        total_capacity=result.total_capacity,
        estimated_annual_energy=result.estimated_annual_energy,
        total_cost=result.total_cost,
        cost_per_watt=result.cost_per_watt,
        shading_analysis=shading_analysis,
        structural_analysis=structural_analysis,
        optimization_score=result.optimization_score,
        objectives_achieved=result.objectives_achieved,
        compliance_status=result.compliance_status,
        optimization_time_ms=result.optimization_time_ms,
        iterations=result.iterations,
        convergence_achieved=result.convergence_achieved,
        created_at=datetime.utcnow()
    )


# API Endpoints
@router.post("/optimize", response_model=OptimizationResultResponse)
async def optimize_layout(
    request: LayoutOptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Optimize solar panel layout using specified strategy and objectives"""
    try:
        # Verify design exists and user has access
        design_query = select(SolarDesign).where(
            SolarDesign.id == request.design_id,
            SolarDesign.created_by == current_user.id
        )
        design_result = await session.execute(design_query)
        design = design_result.scalar_one_or_none()
        
        if not design:
            raise HTTPException(
                status_code=404,
                detail="Design not found or access denied"
            )
        
        # Convert constraints if provided
        constraints = None
        if request.constraints:
            constraints = convert_constraints_to_internal(request.constraints)
        
        # Run optimization
        result = await layout_optimizer.optimize_layout(
            design_id=request.design_id,
            objectives=request.objectives,
            strategy=request.strategy,
            constraints=constraints,
            shading_method=request.shading_method
        )
        
        # Convert to response format
        response = convert_result_to_response(result)
        
        # Log optimization for analytics (background task)
        background_tasks.add_task(
            log_optimization_analytics,
            user_id=current_user.id,
            design_id=request.design_id,
            result=result
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(e)}"
        )


@router.post("/analyze-shading", response_model=List[ShadingResultResponse])
async def analyze_shading(
    request: ShadingAnalysisRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Analyze shading for a specific design or layout"""
    try:
        # Verify design access
        design_query = select(SolarDesign).where(
            SolarDesign.id == request.design_id,
            SolarDesign.created_by == current_user.id
        )
        design_result = await session.execute(design_query)
        design = design_result.scalar_one_or_none()
        
        if not design:
            raise HTTPException(
                status_code=404,
                detail="Design not found or access denied"
            )
        
        # Get panel placements (mock for now)
        # In reality, this would retrieve from stored layout or generate default
        placements = []  # Would be populated from layout_id or design
        
        # Run shading analysis
        shading_results = await layout_optimizer.analyze_shading(
            placements=placements,
            method=request.method,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        # Convert to response format
        response = [
            ShadingResultResponse(
                panel_id=s.panel_id,
                shaded_percentage=s.shaded_percentage,
                shading_sources=s.shading_sources,
                hourly_shading=s.hourly_shading,
                annual_energy_loss=s.annual_energy_loss,
                peak_shading_hours=s.peak_shading_hours
            )
            for s in shading_results
        ]
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Shading analysis failed: {str(e)}"
        )


@router.get("/suggestions/{design_id}", response_model=List[LayoutSuggestionResponse])
async def get_layout_suggestions(
    design_id: str,
    objectives: List[OptimizationObjective] = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get ML-based layout suggestions for a design"""
    try:
        # Verify design access
        design_query = select(SolarDesign).where(
            SolarDesign.id == design_id,
            SolarDesign.created_by == current_user.id
        )
        design_result = await session.execute(design_query)
        design = design_result.scalar_one_or_none()
        
        if not design:
            raise HTTPException(
                status_code=404,
                detail="Design not found or access denied"
            )
        
        # Get ML suggestions (mock implementation)
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
        
        # Convert to response format
        response = [
            LayoutSuggestionResponse(
                suggestion_id=s.suggestion_id,
                confidence_score=s.confidence_score,
                layout_pattern=s.layout_pattern,
                expected_performance=s.expected_performance,
                reasoning=s.reasoning,
                similar_projects=s.similar_projects,
                risk_factors=s.risk_factors
            )
            for s in suggestions
        ]
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.post("/compare", response_model=LayoutComparisonResponse)
async def compare_layouts(
    request: LayoutComparisonRequest,
    current_user: User = Depends(get_current_user)
):
    """Compare multiple layout optimizations"""
    try:
        # Mock comparison implementation
        # In reality, this would retrieve stored optimization results
        
        comparison_id = f"comp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Mock layouts for comparison
        layouts = []
        performance_comparison = {}
        
        for layout_id in request.layout_ids:
            # Would retrieve actual layout data
            mock_result = OptimizationResult(
                layout_id=layout_id,
                strategy=LayoutStrategy.HYBRID,
                panel_placements=[],
                total_panels=25,
                total_capacity=10.0,
                estimated_annual_energy=15000.0,
                total_cost=17500.0,
                cost_per_watt=1.75,
                shading_analysis=[],
                structural_analysis=[],
                optimization_score=0.85,
                objectives_achieved={},
                compliance_status={"building_code": True},
                optimization_time_ms=5000,
                iterations=100,
                convergence_achieved=True
            )
            
            layouts.append(convert_result_to_response(mock_result))
            
            performance_comparison[layout_id] = {
                "energy_yield": 0.85 + (len(layouts) * 0.02),
                "cost_efficiency": 0.80 + (len(layouts) * 0.03),
                "optimization_score": 0.82 + (len(layouts) * 0.01)
            }
        
        # Generate recommendations
        recommendations = [
            "Layout 1 provides the best energy yield",
            "Layout 2 offers the most cost-effective solution",
            "Consider hybrid approach combining elements from layouts 1 and 3"
        ]
        
        # Determine best layout
        best_layout_id = max(
            performance_comparison.keys(),
            key=lambda k: performance_comparison[k]["optimization_score"]
        )
        
        response = LayoutComparisonResponse(
            comparison_id=comparison_id,
            layouts=layouts,
            performance_comparison=performance_comparison,
            recommendations=recommendations,
            best_layout_id=best_layout_id,
            comparison_metrics={
                "total_layouts": len(request.layout_ids),
                "comparison_date": datetime.utcnow().isoformat(),
                "metrics_analyzed": request.comparison_metrics or ["energy", "cost", "optimization_score"]
            }
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Layout comparison failed: {str(e)}"
        )


@router.get("/optimization-history", response_model=List[OptimizationResultResponse])
async def get_optimization_history(
    design_id: Optional[str] = Query(None),
    strategy: Optional[LayoutStrategy] = Query(None),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """Get optimization history for user"""
    try:
        # Mock implementation - would query database for actual history
        history = layout_optimizer.optimization_history
        
        # Filter by design_id if provided
        if design_id:
            # Would filter by design_id in real implementation
            pass
        
        # Filter by strategy if provided
        if strategy:
            history = [r for r in history if r.strategy == strategy]
        
        # Apply pagination
        paginated_history = history[offset:offset + limit]
        
        # Convert to response format
        response = [convert_result_to_response(result) for result in paginated_history]
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get optimization history: {str(e)}"
        )


@router.get("/summary", response_model=OptimizationSummaryResponse)
@cached(namespace="layout_optimization", ttl=300)
async def get_optimization_summary(
    current_user: User = Depends(get_current_user)
):
    """Get optimization summary and analytics"""
    try:
        history = layout_optimizer.optimization_history
        
        if not history:
            return OptimizationSummaryResponse(
                total_optimizations=0,
                successful_optimizations=0,
                average_optimization_time_ms=0.0,
                best_performing_strategy=LayoutStrategy.HYBRID,
                common_objectives=[],
                performance_trends={}
            )
        
        # Calculate summary statistics
        total_optimizations = len(history)
        successful_optimizations = len([r for r in history if r.convergence_achieved])
        
        avg_time = sum(r.optimization_time_ms for r in history) / len(history)
        
        # Find best performing strategy
        strategy_scores = {}
        for result in history:
            if result.strategy not in strategy_scores:
                strategy_scores[result.strategy] = []
            strategy_scores[result.strategy].append(result.optimization_score)
        
        best_strategy = max(
            strategy_scores.keys(),
            key=lambda s: sum(strategy_scores[s]) / len(strategy_scores[s])
        ) if strategy_scores else LayoutStrategy.HYBRID
        
        # Mock common objectives and trends
        common_objectives = [OptimizationObjective.MAXIMIZE_ENERGY, OptimizationObjective.MINIMIZE_COST]
        performance_trends = {
            "energy_improvement": 0.15,
            "cost_reduction": 0.12,
            "optimization_speed": 0.08
        }
        
        response = OptimizationSummaryResponse(
            total_optimizations=total_optimizations,
            successful_optimizations=successful_optimizations,
            average_optimization_time_ms=avg_time,
            best_performing_strategy=best_strategy,
            common_objectives=common_objectives,
            performance_trends=performance_trends
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get optimization summary: {str(e)}"
        )


@router.get("/strategies", response_model=List[Dict[str, Any]])
async def get_available_strategies():
    """Get available optimization strategies and their descriptions"""
    strategies = [
        {
            "strategy": LayoutStrategy.GRID_BASED,
            "name": "Grid-Based Optimization",
            "description": "Systematic grid-based panel placement with genetic algorithm optimization",
            "best_for": ["Large open areas", "Uniform installations", "Cost optimization"],
            "complexity": "Low",
            "typical_time_ms": 3000
        },
        {
            "strategy": LayoutStrategy.ORGANIC,
            "name": "Organic Layout Optimization",
            "description": "Natural, force-directed placement for complex geometries",
            "best_for": ["Irregular areas", "Aesthetic requirements", "Complex constraints"],
            "complexity": "Medium",
            "typical_time_ms": 5000
        },
        {
            "strategy": LayoutStrategy.ML_OPTIMIZED,
            "name": "Machine Learning Optimization",
            "description": "AI-driven optimization based on historical performance data",
            "best_for": ["Performance optimization", "Similar project patterns", "Advanced analytics"],
            "complexity": "High",
            "typical_time_ms": 8000
        },
        {
            "strategy": LayoutStrategy.HYBRID,
            "name": "Hybrid Multi-Strategy",
            "description": "Combines multiple strategies to find the optimal solution",
            "best_for": ["Best overall performance", "Unknown constraints", "Critical projects"],
            "complexity": "High",
            "typical_time_ms": 12000
        }
    ]
    
    return strategies


@router.get("/objectives", response_model=List[Dict[str, Any]])
async def get_available_objectives():
    """Get available optimization objectives and their descriptions"""
    objectives = [
        {
            "objective": OptimizationObjective.MAXIMIZE_ENERGY,
            "name": "Maximize Energy Production",
            "description": "Optimize layout for maximum annual energy yield",
            "unit": "kWh/year",
            "priority": "High"
        },
        {
            "objective": OptimizationObjective.MINIMIZE_COST,
            "name": "Minimize Installation Cost",
            "description": "Optimize for lowest cost per watt installed",
            "unit": "$/W",
            "priority": "High"
        },
        {
            "objective": OptimizationObjective.MINIMIZE_SHADING,
            "name": "Minimize Shading Losses",
            "description": "Reduce inter-panel and external shading",
            "unit": "% loss",
            "priority": "Medium"
        },
        {
            "objective": OptimizationObjective.MAXIMIZE_AESTHETICS,
            "name": "Maximize Visual Appeal",
            "description": "Optimize for uniform, visually pleasing layout",
            "unit": "score",
            "priority": "Low"
        },
        {
            "objective": OptimizationObjective.MINIMIZE_STRUCTURAL_LOAD,
            "name": "Minimize Structural Load",
            "description": "Distribute load evenly across structure",
            "unit": "N/m²",
            "priority": "Medium"
        },
        {
            "objective": OptimizationObjective.MAXIMIZE_ACCESSIBILITY,
            "name": "Maximize Maintenance Access",
            "description": "Ensure adequate access for maintenance",
            "unit": "score",
            "priority": "Low"
        }
    ]
    
    return objectives


@router.get("/health")
async def health_check():
    """Health check endpoint for layout optimization service"""
    try:
        # Check service health
        service_status = "healthy"
        
        # Check optimization history
        history_count = len(layout_optimizer.optimization_history)
        
        return {
            "status": service_status,
            "service": "layout-optimization",
            "timestamp": datetime.utcnow().isoformat(),
            "optimization_history_count": history_count,
            "available_strategies": len(list(LayoutStrategy)),
            "available_objectives": len(list(OptimizationObjective))
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


# Background task functions
async def log_optimization_analytics(
    user_id: str,
    design_id: str,
    result: OptimizationResult
):
    """Log optimization analytics for reporting"""
    try:
        # This would log to analytics system
        analytics_data = {
            "user_id": user_id,
            "design_id": design_id,
            "strategy": result.strategy,
            "optimization_score": result.optimization_score,
            "total_panels": result.total_panels,
            "total_capacity": result.total_capacity,
            "optimization_time_ms": result.optimization_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log to analytics service (mock)
        print(f"Analytics logged: {analytics_data}")
    
    except Exception as e:
        print(f"Failed to log analytics: {e}")