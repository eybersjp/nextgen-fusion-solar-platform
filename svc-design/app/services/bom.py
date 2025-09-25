#!/usr/bin/env python3
"""
Business logic for Bill of Materials (BOM) operations
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.bom import (
    BOMItem, BOMTemplate, BOMCostAnalysis, ComponentLibrary,
    ComponentCategory, ComponentType, BOMStatus
)
from app.models.design import Design
from app.schemas.bom import (
    BOMItemCreate,
    BOMItemUpdate,
    BOMTemplateCreate,
    BOMTemplateUpdate,
    BOMCostAnalysisCreate,
    BOMCostAnalysisUpdate,
    ComponentLibraryCreate,
    ComponentLibraryUpdate,
    BOMGenerationRequest,
    BOMExportRequest,
    BOMExportResponse,
    BOMComparisonRequest,
    BOMComparisonResult,
)
from app.core.exceptions import (
    BOMNotFoundError,
    BOMValidationError,
    BOMPermissionError,
    BOMBusinessLogicError,
)


class BOMService:
    """Service class for Bill of Materials business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # BOM Item methods
    
    async def create_bom_item(
        self,
        item_data: BOMItemCreate,
        user_id: UUID,
        organization_id: UUID
    ) -> BOMItem:
        """Create a new BOM item"""
        # Validate item data
        await self._validate_bom_item_data(item_data)
        
        # Create BOM item instance
        bom_item = BOMItem(
            **item_data.model_dump(exclude_unset=True),
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            status=BOMStatus.ACTIVE,
        )
        
        # Calculate derived fields
        if bom_item.unit_cost and bom_item.quantity:
            bom_item.total_cost = bom_item.unit_cost * bom_item.quantity
        
        # Set default values
        if not bom_item.procurement_info:
            bom_item.procurement_info = await self._get_default_procurement_info(bom_item)
        
        if not bom_item.installation_info:
            bom_item.installation_info = await self._get_default_installation_info(bom_item)
        
        self.db.add(bom_item)
        await self.db.commit()
        await self.db.refresh(bom_item)
        
        return bom_item
    
    async def get_bom_item(
        self,
        item_id: UUID,
        user_id: UUID,
        include_alternatives: bool = False
    ) -> Optional[BOMItem]:
        """Get a BOM item by ID with optional related data"""
        query = select(BOMItem).where(BOMItem.id == item_id)
        
        # Add eager loading for related data
        if include_alternatives:
            query = query.options(selectinload(BOMItem.alternatives))
        
        result = await self.db.execute(query)
        bom_item = result.scalar_one_or_none()
        
        if not bom_item:
            raise BOMNotFoundError(f"BOM item {item_id} not found")
        
        # Check permissions
        await self._check_bom_item_permissions(bom_item, user_id, "read")
        
        return bom_item
    
    async def list_bom_items(
        self,
        user_id: UUID,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        design_id: Optional[UUID] = None,
        category: Optional[ComponentCategory] = None,
        component_type: Optional[ComponentType] = None,
        status: Optional[BOMStatus] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[BOMItem], int]:
        """List BOM items with filtering and pagination"""
        query = select(BOMItem).where(BOMItem.organization_id == organization_id)
        
        # Apply filters
        if design_id:
            query = query.where(BOMItem.design_id == design_id)
        if category:
            query = query.where(BOMItem.category == category)
        if component_type:
            query = query.where(BOMItem.component_type == component_type)
        if status:
            query = query.where(BOMItem.status == status)
        if search:
            query = query.where(
                or_(
                    BOMItem.name.ilike(f"%{search}%"),
                    BOMItem.description.ilike(f"%{search}%"),
                    BOMItem.manufacturer.ilike(f"%{search}%"),
                    BOMItem.model_number.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply sorting
        if hasattr(BOMItem, sort_by):
            order_column = getattr(BOMItem, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(order_column)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total
    
    async def update_bom_item(
        self,
        item_id: UUID,
        item_data: BOMItemUpdate,
        user_id: UUID
    ) -> BOMItem:
        """Update an existing BOM item"""
        bom_item = await self.get_bom_item(item_id, user_id)
        
        # Check permissions
        await self._check_bom_item_permissions(bom_item, user_id, "write")
        
        # Validate update data
        await self._validate_bom_item_update(bom_item, item_data)
        
        # Update item fields
        update_data = item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(bom_item, field):
                setattr(bom_item, field, value)
        
        # Recalculate derived fields
        if 'unit_cost' in update_data or 'quantity' in update_data:
            if bom_item.unit_cost and bom_item.quantity:
                bom_item.total_cost = bom_item.unit_cost * bom_item.quantity
        
        bom_item.updated_by = user_id
        bom_item.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(bom_item)
        
        return bom_item
    
    async def delete_bom_item(self, item_id: UUID, user_id: UUID) -> bool:
        """Delete a BOM item (soft delete)"""
        bom_item = await self.get_bom_item(item_id, user_id)
        
        # Check permissions
        await self._check_bom_item_permissions(bom_item, user_id, "delete")
        
        # Soft delete
        bom_item.status = BOMStatus.DELETED
        bom_item.updated_by = user_id
        bom_item.updated_at = datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def duplicate_bom_item(
        self,
        item_id: UUID,
        user_id: UUID,
        new_name: Optional[str] = None
    ) -> BOMItem:
        """Duplicate an existing BOM item"""
        original_item = await self.get_bom_item(item_id, user_id)
        
        # Create duplicate
        duplicate_data = {
            'name': new_name or f"{original_item.name} (Copy)",
            'description': original_item.description,
            'category': original_item.category,
            'component_type': original_item.component_type,
            'manufacturer': original_item.manufacturer,
            'model_number': original_item.model_number,
            'part_number': original_item.part_number,
            'quantity': original_item.quantity,
            'unit': original_item.unit,
            'unit_cost': original_item.unit_cost,
            'specifications': original_item.specifications,
            'physical_properties': original_item.physical_properties,
            'procurement_info': original_item.procurement_info,
            'installation_info': original_item.installation_info,
            'quality_info': original_item.quality_info,
            'environmental_data': original_item.environmental_data,
            'tags': original_item.tags,
            'metadata': original_item.metadata,
        }
        
        duplicate_item = BOMItem(
            **duplicate_data,
            organization_id=original_item.organization_id,
            created_by=user_id,
            updated_by=user_id,
            status=BOMStatus.ACTIVE,
        )
        
        # Calculate total cost
        if duplicate_item.unit_cost and duplicate_item.quantity:
            duplicate_item.total_cost = duplicate_item.unit_cost * duplicate_item.quantity
        
        self.db.add(duplicate_item)
        await self.db.commit()
        await self.db.refresh(duplicate_item)
        
        return duplicate_item
    
    async def generate_bom_from_design(
        self,
        generation_request: BOMGenerationRequest,
        user_id: UUID,
        organization_id: UUID
    ) -> List[BOMItem]:
        """Generate BOM items from a design"""
        # Get design
        design_query = select(Design).where(Design.id == generation_request.design_id)
        design_result = await self.db.execute(design_query)
        design = design_result.scalar_one_or_none()
        
        if not design:
            raise BOMNotFoundError(f"Design {generation_request.design_id} not found")
        
        # Generate BOM items based on design
        bom_items = await self._generate_bom_items_from_design(
            design, generation_request, user_id, organization_id
        )
        
        # Save all items
        for item in bom_items:
            self.db.add(item)
        
        await self.db.commit()
        
        # Refresh all items
        for item in bom_items:
            await self.db.refresh(item)
        
        return bom_items
    
    async def export_bom(
        self,
        export_request: BOMExportRequest,
        user_id: UUID
    ) -> BOMExportResponse:
        """Export BOM to specified format"""
        # Get BOM items
        items, _ = await self.list_bom_items(
            user_id=user_id,
            organization_id=export_request.organization_id,
            design_id=export_request.design_id,
            limit=10000  # Large limit for export
        )
        
        # Generate export data
        export_data = await self._generate_export_data(
            items, export_request.format, export_request.include_fields
        )
        
        # Generate file (would be actual file generation in production)
        file_name = f"bom_{export_request.design_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_request.format}"
        download_url = f"/exports/{file_name}"
        
        return BOMExportResponse(
            file_name=file_name,
            download_url=download_url,
            format=export_request.format,
            total_items=len(items),
            export_timestamp=datetime.utcnow(),
            file_size_bytes=len(json.dumps(export_data)) if export_data else 0
        )
    
    # BOM Template methods
    
    async def create_bom_template(
        self,
        template_data: BOMTemplateCreate,
        user_id: UUID,
        organization_id: UUID
    ) -> BOMTemplate:
        """Create a new BOM template"""
        # Create template instance
        template = BOMTemplate(
            **template_data.model_dump(exclude_unset=True),
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            status='active',
        )
        
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        
        return template
    
    async def list_bom_templates(
        self,
        user_id: UUID,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[BOMTemplate], int]:
        """List BOM templates"""
        query = select(BOMTemplate).where(
            and_(
                BOMTemplate.organization_id == organization_id,
                BOMTemplate.status == 'active'
            )
        )
        
        # Apply filters
        if category:
            query = query.where(BOMTemplate.category == category)
        if search:
            query = query.where(
                or_(
                    BOMTemplate.name.ilike(f"%{search}%"),
                    BOMTemplate.description.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        return list(templates), total
    
    async def apply_bom_template(
        self,
        template_id: UUID,
        design_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        scaling_factors: Optional[Dict[str, float]] = None
    ) -> List[BOMItem]:
        """Apply a BOM template to a design"""
        # Get template
        template_query = select(BOMTemplate).where(BOMTemplate.id == template_id)
        template_result = await self.db.execute(template_query)
        template = template_result.scalar_one_or_none()
        
        if not template:
            raise BOMNotFoundError(f"BOM template {template_id} not found")
        
        # Generate BOM items from template
        bom_items = await self._generate_bom_items_from_template(
            template, design_id, user_id, organization_id, scaling_factors
        )
        
        # Save all items
        for item in bom_items:
            self.db.add(item)
        
        await self.db.commit()
        
        # Refresh all items
        for item in bom_items:
            await self.db.refresh(item)
        
        return bom_items
    
    # Cost Analysis methods
    
    async def create_cost_analysis(
        self,
        analysis_data: BOMCostAnalysisCreate,
        user_id: UUID,
        organization_id: UUID
    ) -> BOMCostAnalysis:
        """Create a new BOM cost analysis"""
        # Get BOM items for analysis
        items, _ = await self.list_bom_items(
            user_id=user_id,
            organization_id=organization_id,
            design_id=analysis_data.design_id,
            limit=10000
        )
        
        # Perform cost analysis
        analysis_results = await self._perform_cost_analysis(items, analysis_data)
        
        # Create analysis instance
        cost_analysis = BOMCostAnalysis(
            **analysis_data.model_dump(exclude_unset=True),
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            status='completed',
            **analysis_results
        )
        
        self.db.add(cost_analysis)
        await self.db.commit()
        await self.db.refresh(cost_analysis)
        
        return cost_analysis
    
    async def get_cost_analysis(
        self,
        analysis_id: UUID,
        user_id: UUID
    ) -> Optional[BOMCostAnalysis]:
        """Get a cost analysis by ID"""
        query = select(BOMCostAnalysis).where(BOMCostAnalysis.id == analysis_id)
        result = await self.db.execute(query)
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            raise BOMNotFoundError(f"Cost analysis {analysis_id} not found")
        
        # Check permissions
        await self._check_cost_analysis_permissions(analysis, user_id, "read")
        
        return analysis
    
    # Component Library methods
    
    async def create_component(
        self,
        component_data: ComponentLibraryCreate,
        user_id: UUID,
        organization_id: UUID
    ) -> ComponentLibrary:
        """Create a new component in the library"""
        # Validate component data
        await self._validate_component_data(component_data)
        
        # Create component instance
        component = ComponentLibrary(
            **component_data.model_dump(exclude_unset=True),
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            status='active',
        )
        
        self.db.add(component)
        await self.db.commit()
        await self.db.refresh(component)
        
        return component
    
    async def list_components(
        self,
        user_id: UUID,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        category: Optional[ComponentCategory] = None,
        component_type: Optional[ComponentType] = None,
        manufacturer: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[ComponentLibrary], int]:
        """List components in the library"""
        query = select(ComponentLibrary).where(
            and_(
                ComponentLibrary.organization_id == organization_id,
                ComponentLibrary.status == 'active'
            )
        )
        
        # Apply filters
        if category:
            query = query.where(ComponentLibrary.category == category)
        if component_type:
            query = query.where(ComponentLibrary.component_type == component_type)
        if manufacturer:
            query = query.where(ComponentLibrary.manufacturer.ilike(f"%{manufacturer}%"))
        if search:
            query = query.where(
                or_(
                    ComponentLibrary.name.ilike(f"%{search}%"),
                    ComponentLibrary.description.ilike(f"%{search}%"),
                    ComponentLibrary.model_number.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        components = result.scalars().all()
        
        return list(components), total
    
    async def get_component(
        self,
        component_id: UUID,
        user_id: UUID
    ) -> Optional[ComponentLibrary]:
        """Get a component by ID"""
        query = select(ComponentLibrary).where(ComponentLibrary.id == component_id)
        result = await self.db.execute(query)
        component = result.scalar_one_or_none()
        
        if not component:
            raise BOMNotFoundError(f"Component {component_id} not found")
        
        return component
    
    async def add_component_to_bom(
        self,
        component_id: UUID,
        design_id: UUID,
        quantity: int,
        user_id: UUID,
        organization_id: UUID
    ) -> BOMItem:
        """Add a component from library to BOM"""
        # Get component
        component = await self.get_component(component_id, user_id)
        
        # Create BOM item from component
        bom_item_data = {
            'design_id': design_id,
            'name': component.name,
            'description': component.description,
            'category': component.category,
            'component_type': component.component_type,
            'manufacturer': component.manufacturer,
            'model_number': component.model_number,
            'part_number': component.part_number,
            'quantity': quantity,
            'unit': 'each',
            'unit_cost': component.unit_cost,
            'specifications': component.specifications,
            'quality_info': component.quality_info,
            'library_component_id': component_id,
        }
        
        bom_item = BOMItem(
            **bom_item_data,
            organization_id=organization_id,
            created_by=user_id,
            updated_by=user_id,
            status=BOMStatus.ACTIVE,
        )
        
        # Calculate total cost
        if bom_item.unit_cost and bom_item.quantity:
            bom_item.total_cost = bom_item.unit_cost * bom_item.quantity
        
        self.db.add(bom_item)
        await self.db.commit()
        await self.db.refresh(bom_item)
        
        return bom_item
    
    # Comparison methods
    
    async def compare_boms(
        self,
        comparison_request: BOMComparisonRequest,
        user_id: UUID
    ) -> BOMComparisonResult:
        """Compare two BOMs"""
        # Get BOM items for both designs
        items_a, _ = await self.list_bom_items(
            user_id=user_id,
            organization_id=comparison_request.organization_id,
            design_id=comparison_request.design_a_id,
            limit=10000
        )
        
        items_b, _ = await self.list_bom_items(
            user_id=user_id,
            organization_id=comparison_request.organization_id,
            design_id=comparison_request.design_b_id,
            limit=10000
        )
        
        # Perform comparison
        comparison_results = await self._compare_bom_items(items_a, items_b)
        
        return BOMComparisonResult(**comparison_results)
    
    # Private helper methods
    
    async def _validate_bom_item_data(self, item_data: BOMItemCreate) -> None:
        """Validate BOM item creation data"""
        if item_data.quantity is not None and item_data.quantity <= 0:
            raise BOMValidationError("Quantity must be positive")
        
        if item_data.unit_cost is not None and item_data.unit_cost < 0:
            raise BOMValidationError("Unit cost cannot be negative")
        
        if item_data.specifications:
            # Validate specifications based on component type
            await self._validate_component_specifications(
                item_data.component_type, item_data.specifications
            )
    
    async def _validate_bom_item_update(self, bom_item: BOMItem, update_data: BOMItemUpdate) -> None:
        """Validate BOM item update data"""
        update_dict = update_data.model_dump(exclude_unset=True)
        
        if 'quantity' in update_dict and update_dict['quantity'] <= 0:
            raise BOMValidationError("Quantity must be positive")
        
        if 'unit_cost' in update_dict and update_dict['unit_cost'] < 0:
            raise BOMValidationError("Unit cost cannot be negative")
    
    async def _validate_component_data(self, component_data: ComponentLibraryCreate) -> None:
        """Validate component library data"""
        if component_data.unit_cost is not None and component_data.unit_cost < 0:
            raise BOMValidationError("Unit cost cannot be negative")
        
        # Check for duplicate components
        existing_query = select(ComponentLibrary).where(
            and_(
                ComponentLibrary.manufacturer == component_data.manufacturer,
                ComponentLibrary.model_number == component_data.model_number,
                ComponentLibrary.status == 'active'
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_component = existing_result.scalar_one_or_none()
        
        if existing_component:
            raise BOMValidationError(
                f"Component {component_data.manufacturer} {component_data.model_number} already exists"
            )
    
    async def _validate_component_specifications(
        self,
        component_type: ComponentType,
        specifications: Dict[str, Any]
    ) -> None:
        """Validate component specifications based on type"""
        required_specs = {
            ComponentType.SOLAR_MODULE: ['power_rating_w', 'efficiency_percent', 'voltage_v'],
            ComponentType.INVERTER: ['power_rating_w', 'efficiency_percent', 'input_voltage_range'],
            ComponentType.MOUNTING: ['material', 'wind_load_rating', 'snow_load_rating'],
            ComponentType.ELECTRICAL: ['voltage_rating', 'current_rating', 'wire_gauge'],
            ComponentType.MONITORING: ['communication_protocol', 'data_logging_interval'],
        }
        
        if component_type in required_specs:
            missing_specs = []
            for spec in required_specs[component_type]:
                if spec not in specifications:
                    missing_specs.append(spec)
            
            if missing_specs:
                raise BOMValidationError(
                    f"Missing required specifications for {component_type.value}: {', '.join(missing_specs)}"
                )
    
    async def _check_bom_item_permissions(
        self,
        bom_item: BOMItem,
        user_id: UUID,
        action: str
    ) -> None:
        """Check if user has permission to perform action on BOM item"""
        # Basic permission check - can be extended with RBAC
        if action == "delete" and bom_item.created_by != user_id:
            raise BOMPermissionError("Only item creator can delete BOM item")
    
    async def _check_cost_analysis_permissions(
        self,
        analysis: BOMCostAnalysis,
        user_id: UUID,
        action: str
    ) -> None:
        """Check if user has permission to perform action on cost analysis"""
        # Basic permission check
        if action == "delete" and analysis.created_by != user_id:
            raise BOMPermissionError("Only analysis creator can delete cost analysis")
    
    async def _get_default_procurement_info(self, bom_item: BOMItem) -> Dict[str, Any]:
        """Get default procurement information for BOM item"""
        return {
            'lead_time_days': 30,
            'minimum_order_quantity': 1,
            'supplier_rating': 'A',
            'procurement_method': 'purchase',
            'delivery_terms': 'FOB',
            'payment_terms': 'Net 30'
        }
    
    async def _get_default_installation_info(self, bom_item: BOMItem) -> Dict[str, Any]:
        """Get default installation information for BOM item"""
        return {
            'installation_time_hours': 1.0,
            'skill_level_required': 'intermediate',
            'tools_required': ['basic_tools'],
            'safety_requirements': ['PPE', 'electrical_safety'],
            'installation_sequence': 1
        }
    
    async def _generate_bom_items_from_design(
        self,
        design: Design,
        generation_request: BOMGenerationRequest,
        user_id: UUID,
        organization_id: UUID
    ) -> List[BOMItem]:
        """Generate BOM items from design specifications"""
        bom_items = []
        
        # Extract system specifications from design
        system_specs = design.system_specifications or {}
        layout_specs = design.layout_configuration or {}
        electrical_specs = design.electrical_configuration or {}
        
        # Generate solar modules
        if 'module_count' in system_specs and 'module_power_w' in system_specs:
            module_item = BOMItem(
                design_id=design.id,
                name=f"Solar Module - {system_specs.get('module_power_w', 0)}W",
                description="Photovoltaic solar module",
                category=ComponentCategory.SOLAR_MODULES,
                component_type=ComponentType.SOLAR_MODULE,
                manufacturer="Generic",
                model_number=f"SM-{system_specs.get('module_power_w', 0)}W",
                quantity=system_specs['module_count'],
                unit='each',
                unit_cost=Decimal('250.00'),
                specifications={
                    'power_rating_w': system_specs.get('module_power_w', 400),
                    'efficiency_percent': 20.5,
                    'voltage_v': 40.0,
                    'current_a': 10.0,
                    'dimensions_mm': [2000, 1000, 40],
                    'weight_kg': 22.5
                },
                organization_id=organization_id,
                created_by=user_id,
                updated_by=user_id,
                status=BOMStatus.ACTIVE
            )
            module_item.total_cost = module_item.unit_cost * module_item.quantity
            bom_items.append(module_item)
        
        # Generate inverters
        if 'inverter_count' in electrical_specs and 'inverter_power_w' in electrical_specs:
            inverter_item = BOMItem(
                design_id=design.id,
                name=f"String Inverter - {electrical_specs.get('inverter_power_w', 0)}W",
                description="String inverter for solar PV system",
                category=ComponentCategory.INVERTERS,
                component_type=ComponentType.INVERTER,
                manufacturer="Generic",
                model_number=f"INV-{electrical_specs.get('inverter_power_w', 0)}W",
                quantity=electrical_specs['inverter_count'],
                unit='each',
                unit_cost=Decimal('1500.00'),
                specifications={
                    'power_rating_w': electrical_specs.get('inverter_power_w', 5000),
                    'efficiency_percent': 97.5,
                    'input_voltage_range': [200, 800],
                    'output_voltage_v': 240,
                    'mppt_channels': 2
                },
                organization_id=organization_id,
                created_by=user_id,
                updated_by=user_id,
                status=BOMStatus.ACTIVE
            )
            inverter_item.total_cost = inverter_item.unit_cost * inverter_item.quantity
            bom_items.append(inverter_item)
        
        # Generate mounting system
        if 'module_count' in system_specs:
            mounting_item = BOMItem(
                design_id=design.id,
                name="Mounting Rail System",
                description="Aluminum mounting rails for solar modules",
                category=ComponentCategory.MOUNTING,
                component_type=ComponentType.MOUNTING,
                manufacturer="Generic",
                model_number="MR-4000",
                quantity=system_specs['module_count'] * 2,  # 2 rails per module
                unit='meter',
                unit_cost=Decimal('25.00'),
                specifications={
                    'material': 'Aluminum 6005-T5',
                    'length_m': 4.0,
                    'wind_load_rating': '200 km/h',
                    'snow_load_rating': '2.4 kN/m²',
                    'corrosion_resistance': 'Class C5-M'
                },
                organization_id=organization_id,
                created_by=user_id,
                updated_by=user_id,
                status=BOMStatus.ACTIVE
            )
            mounting_item.total_cost = mounting_item.unit_cost * mounting_item.quantity
            bom_items.append(mounting_item)
        
        # Generate electrical components
        if 'string_count' in electrical_specs:
            dc_cable_item = BOMItem(
                design_id=design.id,
                name="DC Cable - 4mm²",
                description="DC cable for solar string connections",
                category=ComponentCategory.ELECTRICAL,
                component_type=ComponentType.ELECTRICAL,
                manufacturer="Generic",
                model_number="DC-4MM2",
                quantity=electrical_specs['string_count'] * 50,  # 50m per string
                unit='meter',
                unit_cost=Decimal('3.50'),
                specifications={
                    'voltage_rating': '1500V DC',
                    'current_rating': '30A',
                    'wire_gauge': '4mm²',
                    'insulation': 'XLPE',
                    'temperature_rating': '-40°C to +90°C'
                },
                organization_id=organization_id,
                created_by=user_id,
                updated_by=user_id,
                status=BOMStatus.ACTIVE
            )
            dc_cable_item.total_cost = dc_cable_item.unit_cost * dc_cable_item.quantity
            bom_items.append(dc_cable_item)
        
        return bom_items
    
    async def _generate_bom_items_from_template(
        self,
        template: BOMTemplate,
        design_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        scaling_factors: Optional[Dict[str, float]] = None
    ) -> List[BOMItem]:
        """Generate BOM items from template"""
        bom_items = []
        scaling_factors = scaling_factors or {}
        
        # Process template items
        for template_item in template.template_items or []:
            # Apply scaling factors
            quantity = template_item.get('quantity', 1)
            if 'quantity' in scaling_factors:
                quantity = int(quantity * scaling_factors['quantity'])
            
            unit_cost = Decimal(str(template_item.get('unit_cost', 0)))
            if 'cost' in scaling_factors:
                unit_cost = unit_cost * Decimal(str(scaling_factors['cost']))
            
            bom_item = BOMItem(
                design_id=design_id,
                name=template_item.get('name', 'Template Item'),
                description=template_item.get('description', ''),
                category=ComponentCategory(template_item.get('category', 'other')),
                component_type=ComponentType(template_item.get('component_type', 'other')),
                manufacturer=template_item.get('manufacturer', ''),
                model_number=template_item.get('model_number', ''),
                part_number=template_item.get('part_number', ''),
                quantity=quantity,
                unit=template_item.get('unit', 'each'),
                unit_cost=unit_cost,
                specifications=template_item.get('specifications', {}),
                organization_id=organization_id,
                created_by=user_id,
                updated_by=user_id,
                status=BOMStatus.ACTIVE
            )
            
            bom_item.total_cost = bom_item.unit_cost * bom_item.quantity
            bom_items.append(bom_item)
        
        return bom_items
    
    async def _perform_cost_analysis(
        self,
        items: List[BOMItem],
        analysis_data: BOMCostAnalysisCreate
    ) -> Dict[str, Any]:
        """Perform cost analysis on BOM items"""
        total_cost = sum(item.total_cost or Decimal('0') for item in items)
        total_items = len(items)
        
        # Calculate cost breakdown by category
        cost_breakdown = {}
        for item in items:
            category = item.category.value if item.category else 'other'
            if category not in cost_breakdown:
                cost_breakdown[category] = Decimal('0')
            cost_breakdown[category] += item.total_cost or Decimal('0')
        
        # Calculate cost metrics
        cost_metrics = {
            'cost_per_watt': total_cost / Decimal('1000') if total_cost > 0 else Decimal('0'),  # Assuming 1kW system
            'average_item_cost': total_cost / total_items if total_items > 0 else Decimal('0'),
            'highest_cost_item': max((item.total_cost or Decimal('0') for item in items), default=Decimal('0')),
            'lowest_cost_item': min((item.total_cost or Decimal('0') for item in items if item.total_cost), default=Decimal('0'))
        }
        
        # Market analysis (simulated)
        market_analysis = {
            'market_price_comparison': 'Within 5% of market average',
            'cost_competitiveness': 'Competitive',
            'price_trends': 'Stable',
            'supplier_diversity': len(set(item.manufacturer for item in items if item.manufacturer))
        }
        
        # Sensitivity analysis
        sensitivity_analysis = {
            'material_cost_impact': {
                '10_percent_increase': float(total_cost * Decimal('1.1')),
                '10_percent_decrease': float(total_cost * Decimal('0.9'))
            },
            'labor_cost_impact': {
                '15_percent_increase': float(total_cost * Decimal('1.05')),  # Assuming 33% labor component
                '15_percent_decrease': float(total_cost * Decimal('0.95'))
            }
        }
        
        return {
            'total_cost': total_cost,
            'total_items': total_items,
            'cost_breakdown': {k: float(v) for k, v in cost_breakdown.items()},
            'cost_metrics': {k: float(v) for k, v in cost_metrics.items()},
            'market_analysis': market_analysis,
            'sensitivity_analysis': sensitivity_analysis
        }
    
    async def _generate_export_data(
        self,
        items: List[BOMItem],
        format: str,
        include_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate export data in specified format"""
        include_fields = include_fields or [
            'name', 'description', 'manufacturer', 'model_number',
            'quantity', 'unit', 'unit_cost', 'total_cost'
        ]
        
        export_data = {
            'metadata': {
                'export_timestamp': datetime.utcnow().isoformat(),
                'total_items': len(items),
                'format': format,
                'fields': include_fields
            },
            'items': []
        }
        
        for item in items:
            item_data = {}
            for field in include_fields:
                if hasattr(item, field):
                    value = getattr(item, field)
                    if isinstance(value, Decimal):
                        value = float(value)
                    elif isinstance(value, datetime):
                        value = value.isoformat()
                    elif hasattr(value, 'value'):  # Enum
                        value = value.value
                    item_data[field] = value
            export_data['items'].append(item_data)
        
        return export_data
    
    async def _compare_bom_items(
        self,
        items_a: List[BOMItem],
        items_b: List[BOMItem]
    ) -> Dict[str, Any]:
        """Compare two sets of BOM items"""
        # Calculate totals
        total_cost_a = sum(item.total_cost or Decimal('0') for item in items_a)
        total_cost_b = sum(item.total_cost or Decimal('0') for item in items_b)
        total_items_a = len(items_a)
        total_items_b = len(items_b)
        
        # Find common and unique items
        items_a_dict = {f"{item.manufacturer}_{item.model_number}": item for item in items_a}
        items_b_dict = {f"{item.manufacturer}_{item.model_number}": item for item in items_b}
        
        common_keys = set(items_a_dict.keys()) & set(items_b_dict.keys())
        unique_to_a = set(items_a_dict.keys()) - set(items_b_dict.keys())
        unique_to_b = set(items_b_dict.keys()) - set(items_a_dict.keys())
        
        # Calculate differences
        cost_difference = total_cost_b - total_cost_a
        cost_difference_percent = (cost_difference / total_cost_a * 100) if total_cost_a > 0 else 0
        
        return {
            'summary': {
                'total_cost_a': float(total_cost_a),
                'total_cost_b': float(total_cost_b),
                'cost_difference': float(cost_difference),
                'cost_difference_percent': float(cost_difference_percent),
                'total_items_a': total_items_a,
                'total_items_b': total_items_b,
                'items_difference': total_items_b - total_items_a
            },
            'item_analysis': {
                'common_items': len(common_keys),
                'unique_to_a': len(unique_to_a),
                'unique_to_b': len(unique_to_b),
                'similarity_percent': (len(common_keys) / max(len(items_a_dict), len(items_b_dict)) * 100) if items_a_dict or items_b_dict else 0
            },
            'detailed_differences': {
                'quantity_changes': [],
                'cost_changes': [],
                'new_items': list(unique_to_b),
                'removed_items': list(unique_to_a)
            },
            'recommendations': [
                'Review cost differences for common items',
                'Validate new items in design B',
                'Consider impact of removed items from design A'
            ]
        }