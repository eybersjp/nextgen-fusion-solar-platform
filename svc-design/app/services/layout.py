#!/usr/bin/env python3
"""
Business logic for Layout operations
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.layout import Layout, LayoutOptimization, LayoutStatus
from app.schemas.layout import (
    LayoutCreate,
    LayoutUpdate,
    LayoutValidationResult,
    LayoutPerformanceMetrics,
    LayoutComparison,
    LayoutComparisonResult,
    LayoutExportRequest,
    LayoutExportResponse,
)
from app.core.exceptions import (
    LayoutNotFoundError,
    LayoutValidationError,
    LayoutPermissionError,
    LayoutBusinessLogicError,
)


class LayoutService:
    """Service class for Layout business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_layout(
        self,
        layout_data: LayoutCreate,
        user_id: UUID,
        organization_id: UUID
    ) -> Layout:
        """Create a new layout"""
        # Validate layout data
        await self._validate_layout_data(layout_data)
        
        # Create layout instance
        layout = Layout(
            **layout_data.model_dump(exclude_unset=True),
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            status=LayoutStatus.DRAFT,
        )
        
        # Set default values
        if not layout.layout_type:
            layout.layout_type = 'fixed_tilt'
        
        # Calculate initial geometry if not provided
        if not layout.geometry:
            layout.geometry = await self._calculate_initial_geometry(layout)
        
        # Calculate initial performance if not provided
        if not layout.performance_metrics:
            layout.performance_metrics = await self._calculate_initial_performance(layout)
        
        self.db.add(layout)
        await self.db.commit()
        await self.db.refresh(layout)
        
        return layout
    
    async def get_layout(
        self,
        layout_id: UUID,
        user_id: UUID,
        include_zones: bool = False,
        include_optimization: bool = False
    ) -> Optional[Layout]:
        """Get a layout by ID with optional related data"""
        query = select(Layout).where(Layout.id == layout_id)
        
        # Add eager loading for related data
        if include_zones:
            query = query.options(selectinload(Layout.zones))
        if include_optimization:
            query = query.options(selectinload(Layout.optimizations))
        
        result = await self.db.execute(query)
        layout = result.scalar_one_or_none()
        
        if not layout:
            raise LayoutNotFoundError(f"Layout {layout_id} not found")
        
        # Check permissions
        await self._check_layout_permissions(layout, user_id, "read")
        
        return layout
    
    async def list_layouts(
        self,
        user_id: UUID,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[LayoutStatus] = None,
        layout_type: Optional[str] = None,
        design_id: Optional[UUID] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Layout], int]:
        """List layouts with filtering and pagination"""
        query = select(Layout).where(Layout.organization_id == organization_id)
        
        # Apply filters
        if status:
            query = query.where(Layout.status == status)
        if layout_type:
            query = query.where(Layout.layout_type == layout_type)
        if design_id:
            query = query.where(Layout.design_id == design_id)
        if search:
            query = query.where(
                or_(
                    Layout.name.ilike(f"%{search}%"),
                    Layout.description.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply sorting
        if hasattr(Layout, sort_by):
            order_column = getattr(Layout, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(order_column)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        layouts = result.scalars().all()
        
        return list(layouts), total
    
    async def update_layout(
        self,
        layout_id: UUID,
        layout_data: LayoutUpdate,
        user_id: UUID
    ) -> Layout:
        """Update an existing layout"""
        layout = await self.get_layout(layout_id, user_id)
        
        # Check permissions
        await self._check_layout_permissions(layout, user_id, "write")
        
        # Validate update data
        await self._validate_layout_update(layout, layout_data)
        
        # Update layout fields
        update_data = layout_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(layout, field):
                setattr(layout, field, value)
        
        layout.updated_by = user_id
        layout.updated_at = datetime.utcnow()
        
        # Recalculate geometry and performance if parameters changed
        if any(field in update_data for field in [
            'layout_parameters', 'module_specifications', 'site_boundaries'
        ]):
            layout.geometry = await self._calculate_geometry(layout)
            layout.performance_metrics = await self._calculate_performance(layout)
        
        await self.db.commit()
        await self.db.refresh(layout)
        
        return layout
    
    async def delete_layout(self, layout_id: UUID, user_id: UUID) -> bool:
        """Delete a layout (soft delete)"""
        layout = await self.get_layout(layout_id, user_id)
        
        # Check permissions
        await self._check_layout_permissions(layout, user_id, "delete")
        
        # Check if layout can be deleted
        if layout.status in [LayoutStatus.APPROVED, LayoutStatus.IN_CONSTRUCTION]:
            raise LayoutBusinessLogicError(
                "Cannot delete approved or in-construction layouts"
            )
        
        # Soft delete
        layout.status = LayoutStatus.DELETED
        layout.updated_by = user_id
        layout.updated_at = datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def optimize_layout(
        self,
        layout_id: UUID,
        user_id: UUID,
        optimization_params: Dict[str, Any]
    ) -> LayoutOptimization:
        """Start layout optimization"""
        layout = await self.get_layout(layout_id, user_id)
        
        # Check permissions
        await self._check_layout_permissions(layout, user_id, "write")
        
        # Create optimization record
        optimization = LayoutOptimization(
            layout_id=layout_id,
            optimization_type=optimization_params.get('type', 'maximize_capacity'),
            parameters=optimization_params,
            status='running',
            started_by=user_id,
            started_at=datetime.utcnow()
        )
        
        self.db.add(optimization)
        await self.db.commit()
        await self.db.refresh(optimization)
        
        # Start optimization task (would be a background task in production)
        asyncio.create_task(self._run_optimization(optimization.id))
        
        return optimization
    
    async def get_optimization_status(
        self,
        optimization_id: UUID,
        user_id: UUID
    ) -> LayoutOptimization:
        """Get optimization status"""
        query = select(LayoutOptimization).where(LayoutOptimization.id == optimization_id)
        result = await self.db.execute(query)
        optimization = result.scalar_one_or_none()
        
        if not optimization:
            raise LayoutNotFoundError(f"Optimization {optimization_id} not found")
        
        # Check permissions through layout
        layout = await self.get_layout(optimization.layout_id, user_id)
        
        return optimization
    
    async def validate_layout(
        self,
        layout_id: UUID,
        user_id: UUID
    ) -> LayoutValidationResult:
        """Validate a layout for completeness and correctness"""
        layout = await self.get_layout(layout_id, user_id)
        
        errors = []
        warnings = []
        
        # Required field validation
        if not layout.layout_parameters:
            errors.append("Layout parameters are required")
        
        if not layout.module_specifications:
            errors.append("Module specifications are required")
        
        if not layout.site_boundaries:
            errors.append("Site boundaries are required")
        
        # Geometry validation
        if layout.geometry:
            total_area = layout.geometry.get('total_area_m2', 0)
            module_area = layout.geometry.get('module_area_m2', 0)
            
            if total_area <= 0:
                errors.append("Total area must be greater than 0")
            
            if module_area > total_area:
                errors.append("Module area cannot exceed total area")
            
            # Check coverage ratio
            coverage_ratio = module_area / total_area if total_area > 0 else 0
            if coverage_ratio > 0.8:
                warnings.append(f"High coverage ratio {coverage_ratio:.1%} - verify spacing")
            elif coverage_ratio < 0.3:
                warnings.append(f"Low coverage ratio {coverage_ratio:.1%} - consider optimization")
        
        # Performance validation
        if layout.performance_metrics:
            specific_yield = layout.performance_metrics.get('specific_yield_kwh_kw', 0)
            if specific_yield < 1000:
                warnings.append(f"Low specific yield {specific_yield:.0f} kWh/kW")
            elif specific_yield > 2000:
                warnings.append(f"High specific yield {specific_yield:.0f} kWh/kW - verify calculations")
        
        # Constraint validation
        if layout.constraints:
            setbacks = layout.constraints.get('setbacks_m', {})
            if not setbacks:
                warnings.append("No setback constraints defined")
        
        return LayoutValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validation_date=datetime.utcnow()
        )
    
    async def calculate_performance(
        self,
        layout_id: UUID,
        user_id: UUID
    ) -> LayoutPerformanceMetrics:
        """Calculate detailed performance metrics for a layout"""
        layout = await self.get_layout(layout_id, user_id)
        
        # Calculate performance metrics
        performance = await self._calculate_performance(layout)
        
        # Update layout with new performance data
        layout.performance_metrics = performance
        layout.updated_by = user_id
        layout.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return LayoutPerformanceMetrics(**performance)
    
    async def compare_layouts(
        self,
        layout1_id: UUID,
        layout2_id: UUID,
        user_id: UUID
    ) -> LayoutComparisonResult:
        """Compare two layouts"""
        layout1 = await self.get_layout(layout1_id, user_id)
        layout2 = await self.get_layout(layout2_id, user_id)
        
        comparison = LayoutComparison(
            layout1_id=layout1_id,
            layout2_id=layout2_id,
            comparison_date=datetime.utcnow()
        )
        
        # Compare key metrics
        metrics_comparison = {}
        
        # Geometry comparison
        if layout1.geometry and layout2.geometry:
            geo1 = layout1.geometry
            geo2 = layout2.geometry
            
            metrics_comparison.update({
                'module_count_difference': (
                    geo2.get('module_count', 0) - geo1.get('module_count', 0)
                ),
                'total_area_difference_m2': (
                    geo2.get('total_area_m2', 0) - geo1.get('total_area_m2', 0)
                ),
                'module_area_difference_m2': (
                    geo2.get('module_area_m2', 0) - geo1.get('module_area_m2', 0)
                ),
            })
        
        # Performance comparison
        if layout1.performance_metrics and layout2.performance_metrics:
            perf1 = layout1.performance_metrics
            perf2 = layout2.performance_metrics
            
            metrics_comparison.update({
                'annual_yield_difference_kwh': (
                    perf2.get('annual_yield_kwh', 0) - perf1.get('annual_yield_kwh', 0)
                ),
                'specific_yield_difference_kwh_kw': (
                    perf2.get('specific_yield_kwh_kw', 0) - perf1.get('specific_yield_kwh_kw', 0)
                ),
                'capacity_factor_difference': (
                    perf2.get('capacity_factor', 0) - perf1.get('capacity_factor', 0)
                ),
            })
        
        return LayoutComparisonResult(
            comparison=comparison,
            metrics_comparison=metrics_comparison,
            recommendations=await self._generate_layout_recommendations(
                layout1, layout2, metrics_comparison
            )
        )
    
    async def export_layout(
        self,
        layout_id: UUID,
        user_id: UUID,
        export_request: LayoutExportRequest
    ) -> LayoutExportResponse:
        """Export layout in specified format"""
        layout = await self.get_layout(layout_id, user_id)
        
        # Check permissions
        await self._check_layout_permissions(layout, user_id, "read")
        
        # Generate export data based on format
        export_data = await self._generate_export_data(layout, export_request.format)
        
        # Create export file (would save to storage in production)
        file_name = f"layout_{layout.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_request.format.lower()}"
        file_url = f"/exports/{file_name}"  # Would be actual storage URL
        
        return LayoutExportResponse(
            file_name=file_name,
            file_url=file_url,
            format=export_request.format,
            export_date=datetime.utcnow(),
            file_size_bytes=len(str(export_data))
        )
    
    # Zone management methods
    
    # async def create_zone(
    #     self,
    #     layout_id: UUID,
    #     zone_data: Dict[str, Any],
    #     user_id: UUID
    # ) -> LayoutZone:
    #     """Create a new layout zone"""
    #     # LayoutZone model not implemented yet
    #     pass
    
    # async def list_zones(
    #     self,
    #     layout_id: UUID,
    #     user_id: UUID
    # ) -> List[LayoutZone]:
    #     """List zones for a layout"""
    #     # LayoutZone model not implemented yet
    #     pass
    
    # async def update_zone(
    #     self,
    #     zone_id: UUID,
    #     zone_data: Dict[str, Any],
    #     user_id: UUID
    # ) -> LayoutZone:
    #     """Update a layout zone"""
    #     # LayoutZone model not implemented yet
    #     pass
    
    # async def delete_zone(self, zone_id: UUID, user_id: UUID) -> bool:
    #     """Delete a layout zone"""
    #     # LayoutZone model not implemented yet
    #     pass
    
    # Template management methods
    
    # async def create_template(
    #     self,
    #     template_data: Dict[str, Any],
    #     user_id: UUID,
    #     organization_id: UUID
    # ) -> LayoutTemplate:
    #     """Create a new layout template"""
    #     # LayoutTemplate model not implemented yet
    #     pass
    
    # async def list_templates(
    #     self,
    #     user_id: UUID,
    #     organization_id: UUID,
    #     skip: int = 0,
    #     limit: int = 100
    # ) -> Tuple[List[LayoutTemplate], int]:
    #     """List layout templates"""
    #     # LayoutTemplate model not implemented yet
    #     pass
    
    # async def apply_template(
    #     self,
    #     layout_id: UUID,
    #     template_id: UUID,
    #     user_id: UUID
    # ) -> Layout:
    #     """Apply a template to a layout"""
    #     # LayoutTemplate model not implemented yet
    #     pass
    
    # Private helper methods
    
    async def _validate_layout_data(self, layout_data: LayoutCreate) -> None:
        """Validate layout creation data"""
        if layout_data.layout_parameters:
            params = layout_data.layout_parameters
            
            # Validate tilt angle
            tilt = params.get('tilt_angle_deg', 0)
            if tilt < 0 or tilt > 90:
                raise ValidationError("Tilt angle must be between 0 and 90 degrees")
            
            # Validate azimuth
            azimuth = params.get('azimuth_deg', 0)
            if azimuth < 0 or azimuth >= 360:
                raise ValidationError("Azimuth must be between 0 and 359 degrees")
    
    async def _validate_layout_update(self, layout: Layout, update_data: LayoutUpdate) -> None:
        """Validate layout update data"""
        if layout.status == LayoutStatus.APPROVED:
            # Only allow limited updates to approved layouts
            allowed_fields = {'description', 'tags', 'metadata'}
            update_fields = set(update_data.model_dump(exclude_unset=True).keys())
            if not update_fields.issubset(allowed_fields):
                raise ValidationError(
                    "Cannot modify technical parameters of approved layouts"
                )
    
    async def _check_layout_permissions(
        self,
        layout: Layout,
        user_id: UUID,
        action: str
    ) -> None:
        """Check if user has permission to perform action on layout"""
        # Basic permission check - can be extended with RBAC
        if action == "delete" and layout.created_by != user_id:
            raise PermissionError("Only layout creator can delete layout")
    
    async def _calculate_initial_geometry(self, layout: Layout) -> Dict[str, Any]:
        """Calculate initial geometry estimates"""
        # Simplified calculation - would integrate with CAD libraries
        params = layout.layout_parameters or {}
        module_specs = layout.module_specifications or {}
        
        # Default module dimensions (meters)
        module_width = module_specs.get('width_m', 2.0)
        module_height = module_specs.get('height_m', 1.0)
        module_area = module_width * module_height
        
        # Estimate module count based on site area and spacing
        site_area = 10000  # Default 1 hectare
        if layout.site_boundaries:
            # Calculate actual site area from boundaries
            site_area = layout.site_boundaries.get('area_m2', site_area)
        
        # Assume 40% coverage ratio for initial estimate
        coverage_ratio = 0.4
        total_module_area = site_area * coverage_ratio
        module_count = int(total_module_area / module_area)
        
        return {
            'module_count': module_count,
            'total_area_m2': site_area,
            'module_area_m2': total_module_area,
            'coverage_ratio': coverage_ratio,
            'row_count': max(1, int(module_count ** 0.5)),
            'modules_per_row': max(1, int(module_count ** 0.5)),
        }
    
    async def _calculate_geometry(self, layout: Layout) -> Dict[str, Any]:
        """Calculate detailed geometry"""
        # This would integrate with CAD/geometry libraries
        return await self._calculate_initial_geometry(layout)
    
    async def _calculate_initial_performance(self, layout: Layout) -> Dict[str, Any]:
        """Calculate initial performance estimates"""
        # Simplified calculation - would integrate with solar modeling
        geometry = layout.geometry or {}
        module_count = geometry.get('module_count', 0)
        
        # Assume 400W modules
        module_power_w = 400
        total_capacity_kw = (module_count * module_power_w) / 1000
        
        # Assume 1500 kWh/kW annual yield
        specific_yield = 1500
        annual_yield_kwh = total_capacity_kw * specific_yield
        
        return {
            'total_capacity_kw': total_capacity_kw,
            'annual_yield_kwh': annual_yield_kwh,
            'specific_yield_kwh_kw': specific_yield,
            'capacity_factor': 0.17,
            'performance_ratio': 0.85,
        }
    
    async def _calculate_performance(self, layout: Layout) -> Dict[str, Any]:
        """Calculate detailed performance metrics"""
        # This would integrate with pvlib or other solar modeling libraries
        return await self._calculate_initial_performance(layout)
    
    async def _run_optimization(self, optimization_id: UUID) -> None:
        """Run layout optimization (background task)"""
        try:
            # Get optimization record
            query = select(LayoutOptimization).where(LayoutOptimization.id == optimization_id)
            result = await self.db.execute(query)
            optimization = result.scalar_one_or_none()
            
            if not optimization:
                return
            
            # Simulate optimization process
            await asyncio.sleep(5)  # Simulate processing time
            
            # Generate optimization results
            results = {
                'optimized_module_count': 1000,
                'optimized_capacity_kw': 400,
                'optimized_yield_kwh': 600000,
                'improvement_percentage': 15.5,
                'optimization_metrics': {
                    'iterations': 100,
                    'convergence_time_s': 4.8,
                    'final_score': 0.95
                }
            }
            
            # Update optimization record
            optimization.status = 'completed'
            optimization.results = results
            optimization.completed_at = datetime.utcnow()
            
            await self.db.commit()
            
        except Exception as e:
            # Handle optimization failure
            optimization.status = 'failed'
            optimization.error_message = str(e)
            optimization.completed_at = datetime.utcnow()
            await self.db.commit()
    
    async def _generate_export_data(
        self,
        layout: Layout,
        format: str
    ) -> Dict[str, Any]:
        """Generate export data in specified format"""
        base_data = {
            'layout_id': str(layout.id),
            'name': layout.name,
            'description': layout.description,
            'layout_type': layout.layout_type.value if layout.layout_type else None,
            'parameters': layout.layout_parameters,
            'geometry': layout.geometry,
            'performance': layout.performance_metrics,
            'export_timestamp': datetime.utcnow().isoformat()
        }
        
        if format.upper() == 'DXF':
            # Generate DXF-specific data
            base_data['cad_entities'] = await self._generate_cad_entities(layout)
        elif format.upper() == 'KML':
            # Generate KML-specific data
            base_data['geographic_data'] = await self._generate_geographic_data(layout)
        
        return base_data
    
    async def _generate_cad_entities(self, layout: Layout) -> List[Dict[str, Any]]:
        """Generate CAD entities for DXF export"""
        # This would generate actual CAD entities
        entities = []
        
        geometry = layout.geometry or {}
        module_count = geometry.get('module_count', 0)
        
        # Generate module rectangles
        for i in range(module_count):
            entities.append({
                'type': 'RECTANGLE',
                'layer': 'MODULES',
                'x': (i % 10) * 2.5,  # Simple grid layout
                'y': (i // 10) * 1.5,
                'width': 2.0,
                'height': 1.0
            })
        
        return entities
    
    async def _generate_geographic_data(self, layout: Layout) -> Dict[str, Any]:
        """Generate geographic data for KML export"""
        # This would generate actual geographic coordinates
        return {
            'coordinates': [
                {'lat': -26.2041, 'lng': 28.0473},  # Example coordinates
                {'lat': -26.2042, 'lng': 28.0474},
                {'lat': -26.2043, 'lng': 28.0475},
            ],
            'bounds': {
                'north': -26.2040,
                'south': -26.2045,
                'east': 28.0476,
                'west': 28.0470
            }
        }
    
    async def _generate_layout_recommendations(
        self,
        layout1: Layout,
        layout2: Layout,
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on layout comparison"""
        recommendations = []
        
        # Module count comparison
        module_diff = metrics.get('module_count_difference', 0)
        if module_diff > 0:
            recommendations.append(
                f"Layout 2 has {module_diff} more modules, potentially higher capacity"
            )
        elif module_diff < 0:
            recommendations.append(
                f"Layout 1 has {abs(module_diff)} more modules, potentially higher capacity"
            )
        
        # Yield comparison
        yield_diff = metrics.get('annual_yield_difference_kwh', 0)
        if yield_diff > 1000:
            recommendations.append(
                f"Layout 2 produces {yield_diff:.0f} kWh more annually"
            )
        elif yield_diff < -1000:
            recommendations.append(
                f"Layout 1 produces {abs(yield_diff):.0f} kWh more annually"
            )
        
        # Specific yield comparison
        specific_yield_diff = metrics.get('specific_yield_difference_kwh_kw', 0)
        if abs(specific_yield_diff) > 50:
            better_layout = "Layout 2" if specific_yield_diff > 0 else "Layout 1"
            recommendations.append(
                f"{better_layout} has better specific yield - more efficient design"
            )
        
        return recommendations