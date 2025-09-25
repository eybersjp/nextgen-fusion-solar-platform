#!/usr/bin/env python3
"""
Business logic for Design operations
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.design import Design, DesignVersion, DesignComment, DesignStatus, DesignType
from app.schemas.design import (
    DesignCreate,
    DesignUpdate,
    DesignValidationResponse,
    DesignPerformanceResponse,
    DesignComparisonRequest,
    DesignComparisonResponse,
)
from app.core.exceptions import (
    DesignNotFoundError,
    ValidationError,
    PermissionError,
    BusinessLogicError,
)


class DesignService:
    """Service class for Design business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_design(
        self,
        design_data: DesignCreate,
        user_id: UUID,
        organization_id: UUID
    ) -> Design:
        """Create a new design"""
        # Validate design data
        await self._validate_design_data(design_data)
        
        # Create design instance
        design = Design(
            **design_data.model_dump(exclude_unset=True),
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            status=DesignStatus.DRAFT,
        )
        
        # Set default values
        if not design.design_type:
            design.design_type = DesignType.COMMERCIAL
        
        # Initialize performance estimates if not provided
        if not design.performance_estimates:
            design.performance_estimates = await self._calculate_initial_performance(design)
        
        # Initialize loss analysis if not provided
        if not design.loss_analysis:
            design.loss_analysis = await self._calculate_initial_losses(design)
        
        self.db.add(design)
        await self.db.commit()
        await self.db.refresh(design)
        
        # Create initial revision
        await self._create_revision(
            design.id,
            user_id,
            "Initial design creation",
            design.model_dump()
        )
        
        return design
    
    async def get_design(
        self,
        design_id: UUID,
        user_id: UUID,
        include_revisions: bool = False,
        include_comments: bool = False
    ) -> Optional[Design]:
        """Get a design by ID with optional related data"""
        query = select(Design).where(Design.id == design_id)
        
        # Add eager loading for related data
        if include_revisions:
            query = query.options(selectinload(Design.revisions))
        if include_comments:
            query = query.options(selectinload(Design.comments))
        
        result = await self.db.execute(query)
        design = result.scalar_one_or_none()
        
        if not design:
            raise DesignNotFoundError(f"Design {design_id} not found")
        
        # Check permissions
        await self._check_design_permissions(design, user_id, "read")
        
        return design
    
    async def list_designs(
        self,
        user_id: UUID,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DesignStatus] = None,
        design_type: Optional[DesignType] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Design], int]:
        """List designs with filtering and pagination"""
        query = select(Design).where(Design.organization_id == organization_id)
        
        # Apply filters
        if status:
            query = query.where(Design.status == status)
        if design_type:
            query = query.where(Design.design_type == design_type)
        if search:
            query = query.where(
                or_(
                    Design.name.ilike(f"%{search}%"),
                    Design.description.ilike(f"%{search}%"),
                    Design.project_name.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply sorting
        if hasattr(Design, sort_by):
            order_column = getattr(Design, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(order_column)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        designs = result.scalars().all()
        
        return list(designs), total
    
    async def update_design(
        self,
        design_id: UUID,
        design_data: DesignUpdate,
        user_id: UUID
    ) -> Design:
        """Update an existing design"""
        design = await self.get_design(design_id, user_id)
        
        # Check permissions
        await self._check_design_permissions(design, user_id, "write")
        
        # Validate update data
        await self._validate_design_update(design, design_data)
        
        # Store original data for revision
        original_data = design.model_dump()
        
        # Update design fields
        update_data = design_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(design, field):
                setattr(design, field, value)
        
        design.updated_by = user_id
        design.updated_at = datetime.utcnow()
        
        # Recalculate performance if system specifications changed
        if any(field in update_data for field in [
            'system_capacity_kw', 'module_specifications', 'inverter_specifications'
        ]):
            design.performance_estimates = await self._calculate_performance(design)
            design.loss_analysis = await self._calculate_losses(design)
        
        await self.db.commit()
        await self.db.refresh(design)
        
        # Create revision for significant changes
        if self._is_significant_change(original_data, design.model_dump()):
            await self._create_revision(
                design.id,
                user_id,
                "Design updated",
                design.model_dump()
            )
        
        return design
    
    async def delete_design(self, design_id: UUID, user_id: UUID) -> bool:
        """Delete a design (soft delete)"""
        design = await self.get_design(design_id, user_id)
        
        # Check permissions
        await self._check_design_permissions(design, user_id, "delete")
        
        # Check if design can be deleted
        if design.status in [DesignStatus.APPROVED, DesignStatus.IN_CONSTRUCTION]:
            raise BusinessLogicError(
                "Cannot delete approved or in-construction designs"
            )
        
        # Soft delete
        design.status = DesignStatus.DELETED
        design.updated_by = user_id
        design.updated_at = datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def duplicate_design(
        self,
        design_id: UUID,
        user_id: UUID,
        new_name: Optional[str] = None
    ) -> Design:
        """Duplicate an existing design"""
        original_design = await self.get_design(design_id, user_id)
        
        # Check permissions
        await self._check_design_permissions(original_design, user_id, "read")
        
        # Create duplicate data
        duplicate_data = original_design.model_dump(exclude={
            'id', 'created_at', 'updated_at', 'created_by', 'updated_by'
        })
        
        # Update name
        if new_name:
            duplicate_data['name'] = new_name
        else:
            duplicate_data['name'] = f"{original_design.name} (Copy)"
        
        # Reset status to draft
        duplicate_data['status'] = DesignStatus.DRAFT
        
        # Create new design
        design_create = DesignCreate(**duplicate_data)
        return await self.create_design(design_create, user_id, original_design.organization_id)
    
    async def approve_design(self, design_id: UUID, user_id: UUID) -> Design:
        """Approve a design"""
        design = await self.get_design(design_id, user_id)
        
        # Check permissions
        await self._check_design_permissions(design, user_id, "approve")
        
        # Validate design is ready for approval
        validation_result = await self.validate_design(design_id, user_id)
        if not validation_result.is_valid:
            raise ValidationError(
                f"Design cannot be approved: {', '.join(validation_result.errors)}"
            )
        
        design.status = DesignStatus.APPROVED
        design.approved_by = user_id
        design.approved_at = datetime.utcnow()
        design.updated_by = user_id
        design.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(design)
        
        # Create approval revision
        await self._create_revision(
            design.id,
            user_id,
            "Design approved",
            design.model_dump()
        )
        
        return design
    
    async def reject_design(
        self,
        design_id: UUID,
        user_id: UUID,
        reason: str
    ) -> Design:
        """Reject a design"""
        design = await self.get_design(design_id, user_id)
        
        # Check permissions
        await self._check_design_permissions(design, user_id, "approve")
        
        design.status = DesignStatus.REJECTED
        design.updated_by = user_id
        design.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(design)
        
        # Create rejection comment
        await self._create_comment(
            design.id,
            user_id,
            f"Design rejected: {reason}",
            "rejection"
        )
        
        return design
    
    async def validate_design(self, design_id: UUID, user_id: UUID) -> DesignValidationResponse:
        """Validate a design for completeness and correctness"""
        design = await self.get_design(design_id, user_id)
        
        errors = []
        warnings = []
        
        # Required field validation
        if not design.system_capacity_kw or design.system_capacity_kw <= 0:
            errors.append("System capacity must be greater than 0")
        
        if not design.module_specifications:
            errors.append("Module specifications are required")
        
        if not design.inverter_specifications:
            errors.append("Inverter specifications are required")
        
        if not design.layout_configuration:
            errors.append("Layout configuration is required")
        
        # Business logic validation
        if design.system_capacity_kw and design.system_capacity_kw > 10000:
            warnings.append("System capacity exceeds 10MW - verify commercial requirements")
        
        # Performance validation
        if design.performance_estimates:
            annual_yield = design.performance_estimates.get('annual_yield_kwh', 0)
            if annual_yield <= 0:
                errors.append("Annual yield must be calculated")
            
            capacity_factor = design.performance_estimates.get('capacity_factor', 0)
            if capacity_factor < 0.1 or capacity_factor > 0.4:
                warnings.append(f"Capacity factor {capacity_factor:.2%} is outside typical range (10-40%)")
        
        # Loss analysis validation
        if design.loss_analysis:
            total_losses = design.total_losses
            if total_losses > 0.3:
                warnings.append(f"Total system losses {total_losses:.1%} are high")
        
        return DesignValidationResponse(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            score=100.0 if len(errors) == 0 else max(0, 100 - len(errors) * 20),
            recommendations=[]
        )
    
    async def calculate_performance(
        self,
        design_id: UUID,
        user_id: UUID
    ) -> DesignPerformanceResponse:
        """Calculate detailed performance metrics for a design"""
        design = await self.get_design(design_id, user_id)
        
        # Calculate performance metrics
        performance = await self._calculate_performance(design)
        
        # Update design with new performance data
        design.performance_estimates = performance
        design.updated_by = user_id
        design.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return DesignPerformanceResponse(
            annual_energy_kwh=performance.get('annual_yield_kwh', 0),
            monthly_energy_kwh=performance.get('monthly_yield_kwh', [0] * 12),
            capacity_factor=performance.get('capacity_factor', 0),
            performance_ratio=performance.get('performance_ratio', 0),
            specific_yield_kwh_kwp=performance.get('specific_yield_kwh_kw', 0),
            losses={},
            lifetime_energy_kwh=performance.get('annual_yield_kwh', 0) * 25,
            degradation_profile=[1.0] * 25,
            calculation_details=performance
        )
    
    async def compare_designs(
        self,
        design1_id: UUID,
        design2_id: UUID,
        user_id: UUID
    ) -> DesignComparisonResponse:
        """Compare two designs"""
        design1 = await self.get_design(design1_id, user_id)
        design2 = await self.get_design(design2_id, user_id)
        
        # Create comparison data structure
        comparison_data = {
            'design1_id': str(design1_id),
            'design2_id': str(design2_id),
            'comparison_date': datetime.utcnow().isoformat()
        }
        
        # Compare key metrics
        metrics_comparison = {
            'capacity_difference_kw': design2.system_capacity_kw - design1.system_capacity_kw,
            'module_count_difference': (
                design2.layout_configuration.get('module_count', 0) - 
                design1.layout_configuration.get('module_count', 0)
            ),
        }
        
        # Compare performance
        if design1.performance_estimates and design2.performance_estimates:
            perf1 = design1.performance_estimates
            perf2 = design2.performance_estimates
            
            metrics_comparison.update({
                'annual_yield_difference_kwh': (
                    perf2.get('annual_yield_kwh', 0) - perf1.get('annual_yield_kwh', 0)
                ),
                'capacity_factor_difference': (
                    perf2.get('capacity_factor', 0) - perf1.get('capacity_factor', 0)
                ),
            })
        
        # Compare costs (if available)
        if design1.equipment_specifications and design2.equipment_specifications:
            cost1 = design1.equipment_specifications.get('total_cost_usd', 0)
            cost2 = design2.equipment_specifications.get('total_cost_usd', 0)
            metrics_comparison['cost_difference_usd'] = cost2 - cost1
        
        return DesignComparisonResponse(
            designs=[design1, design2],
            comparison_data={**comparison_data, **metrics_comparison},
            summary=metrics_comparison,
            recommendations=await self._generate_comparison_recommendations(
                design1, design2, metrics_comparison
            )
        )
    
    # Private helper methods
    
    async def _validate_design_data(self, design_data: DesignCreate) -> None:
        """Validate design creation data"""
        if design_data.system_capacity_kw <= 0:
            raise ValidationError("System capacity must be greater than 0")
        
        if design_data.system_capacity_kw > 50000:  # 50MW limit
            raise ValidationError("System capacity exceeds maximum limit of 50MW")
    
    async def _validate_design_update(self, design: Design, update_data: DesignUpdate) -> None:
        """Validate design update data"""
        if design.status == DesignStatus.APPROVED:
            # Only allow limited updates to approved designs
            allowed_fields = {'description', 'tags', 'metadata'}
            update_fields = set(update_data.model_dump(exclude_unset=True).keys())
            if not update_fields.issubset(allowed_fields):
                raise ValidationError(
                    "Cannot modify technical specifications of approved designs"
                )
    
    async def _check_design_permissions(
        self,
        design: Design,
        user_id: UUID,
        action: str
    ) -> None:
        """Check if user has permission to perform action on design"""
        # Basic permission check - can be extended with RBAC
        if action == "delete" and design.created_by != user_id:
            raise PermissionError("Only design creator can delete design")
        
        if action == "approve" and design.created_by == user_id:
            raise PermissionError("Cannot approve own design")
    
    async def _calculate_initial_performance(self, design: Design) -> Dict[str, Any]:
        """Calculate initial performance estimates"""
        # Simplified calculation - would integrate with solar modeling libraries
        capacity_kw = design.system_capacity_kw or 0
        
        # Assume 1500 kWh/kW annual yield (typical for commercial solar)
        annual_yield_kwh = capacity_kw * 1500
        capacity_factor = 0.17  # 17% typical capacity factor
        
        return {
            'annual_yield_kwh': annual_yield_kwh,
            'capacity_factor': capacity_factor,
            'specific_yield_kwh_kw': 1500,
            'performance_ratio': 0.85,
        }
    
    async def _calculate_performance(self, design: Design) -> Dict[str, Any]:
        """Calculate detailed performance metrics"""
        # This would integrate with pvlib or other solar modeling libraries
        # For now, return enhanced estimates
        basic_performance = await self._calculate_initial_performance(design)
        
        # Add more detailed metrics
        basic_performance.update({
            'monthly_yield_kwh': [basic_performance['annual_yield_kwh'] / 12] * 12,
            'peak_power_kw': design.system_capacity_kw,
            'energy_density_kwh_m2': 200,  # Typical value
            'degradation_rate_annual': 0.005,  # 0.5% per year
        })
        
        return basic_performance
    
    async def _calculate_initial_losses(self, design: Design) -> Dict[str, Any]:
        """Calculate initial loss analysis"""
        return {
            'soiling_losses': 0.02,
            'shading_losses': 0.03,
            'mismatch_losses': 0.02,
            'dc_wiring_losses': 0.02,
            'inverter_losses': 0.04,
            'ac_wiring_losses': 0.01,
            'transformer_losses': 0.01,
        }
    
    async def _calculate_losses(self, design: Design) -> Dict[str, Any]:
        """Calculate detailed loss analysis"""
        # This would integrate with detailed loss modeling
        return await self._calculate_initial_losses(design)
    
    async def _create_revision(
        self,
        design_id: UUID,
        user_id: UUID,
        description: str,
        design_data: Dict[str, Any]
    ) -> DesignVersion:
        """Create a design revision"""
        revision = DesignVersion(
            design_id=design_id,
            revision_number=await self._get_next_revision_number(design_id),
            description=description,
            design_data=design_data,
            created_by=user_id
        )
        
        self.db.add(revision)
        await self.db.commit()
        return revision
    
    async def _create_comment(
        self,
        design_id: UUID,
        user_id: UUID,
        content: str,
        comment_type: str = "general"
    ) -> DesignComment:
        """Create a design comment"""
        comment = DesignComment(
            design_id=design_id,
            content=content,
            comment_type=comment_type,
            created_by=user_id
        )
        
        self.db.add(comment)
        await self.db.commit()
        return comment
    
    async def _get_next_revision_number(self, design_id: UUID) -> int:
        """Get the next revision number for a design"""
        query = select(func.max(DesignVersion.revision_number)).where(
            DesignVersion.design_id == design_id
        )
        result = await self.db.execute(query)
        max_revision = result.scalar() or 0
        return max_revision + 1
    
    def _is_significant_change(self, original: Dict[str, Any], updated: Dict[str, Any]) -> bool:
        """Determine if changes are significant enough to create a revision"""
        significant_fields = {
            'system_capacity_kw', 'module_specifications', 'inverter_specifications',
            'layout_configuration', 'electrical_configuration'
        }
        
        for field in significant_fields:
            if original.get(field) != updated.get(field):
                return True
        
        return False
    
    async def _generate_comparison_recommendations(
        self,
        design1: Design,
        design2: Design,
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on design comparison"""
        recommendations = []
        
        # Capacity comparison
        capacity_diff = metrics.get('capacity_difference_kw', 0)
        if capacity_diff > 0:
            recommendations.append(
                f"Design 2 has {capacity_diff:.1f} kW more capacity, "
                "potentially higher energy yield"
            )
        elif capacity_diff < 0:
            recommendations.append(
                f"Design 1 has {abs(capacity_diff):.1f} kW more capacity, "
                "potentially higher energy yield"
            )
        
        # Performance comparison
        yield_diff = metrics.get('annual_yield_difference_kwh', 0)
        if yield_diff > 1000:
            recommendations.append(
                f"Design 2 produces {yield_diff:.0f} kWh more annually"
            )
        elif yield_diff < -1000:
            recommendations.append(
                f"Design 1 produces {abs(yield_diff):.0f} kWh more annually"
            )
        
        # Cost comparison
        cost_diff = metrics.get('cost_difference_usd', 0)
        if cost_diff != 0:
            if cost_diff > 0:
                recommendations.append(
                    f"Design 2 costs ${cost_diff:,.0f} more - evaluate ROI"
                )
            else:
                recommendations.append(
                    f"Design 1 costs ${abs(cost_diff):,.0f} more - evaluate ROI"
                )
        
        return recommendations