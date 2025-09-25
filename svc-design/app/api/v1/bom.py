"""Bill of Materials (BOM) API endpoints for the Design Service.

Provides CRUD operations for BOMs, components, suppliers,
pricing, and BOM templates.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.dependencies import (
    get_current_active_user,
    get_db_session,
    get_pagination_params,
    validate_uuid,
)
from ...core.exceptions import (
    DesignServiceException,
    NotFoundError,
    ValidationError,
    PermissionError,
)
from ...models.bom import (
    BillOfMaterials,
    BOMItem,
    Component,
    Supplier,
    PriceList,
    PriceListItem,
    BOMTemplate,
)
from ...schemas.bom import (
    BOMCreate,
    BOMUpdate,
    BOMResponse,
    BOMListResponse,
    BOMItemCreate,
    BOMItemUpdate,
    BOMItemResponse,
    ComponentCreate,
    ComponentUpdate,
    ComponentResponse,
    ComponentListResponse,
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    SupplierListResponse,
    PriceListCreate,
    PriceListUpdate,
    PriceListResponse,
    PriceListItemCreate,
    PriceListItemUpdate,
    PriceListItemResponse,
    BOMTemplateCreate,
    BOMTemplateUpdate,
    BOMTemplateResponse,
    BOMTemplateListResponse,
)
from ...services.bom import BOMService

router = APIRouter()


# Bill of Materials endpoints
@router.get("/", response_model=BOMListResponse)
async def list_boms(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    design_id: Optional[UUID] = Query(None, description="Filter by design ID"),
    layout_id: Optional[UUID] = Query(None, description="Filter by layout ID"),
    bom_type: Optional[str] = Query(None, description="Filter by BOM type"),
    status: Optional[str] = Query(None, description="Filter by BOM status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List BOMs with filtering and pagination."""
    try:
        bom_service = BOMService(db)
        
        filters = {}
        if design_id:
            filters["design_id"] = design_id
        if layout_id:
            filters["layout_id"] = layout_id
        if bom_type:
            filters["bom_type"] = bom_type
        if status:
            filters["status"] = status
        
        boms, total = await bom_service.list_boms(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return BOMListResponse(
            boms=boms,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list BOMs: {str(e)}"
        )


@router.post("/", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def create_bom(
    bom_data: BOMCreate,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new Bill of Materials."""
    try:
        bom_service = BOMService(db)
        
        bom = await bom_service.create_bom(
            bom_data=bom_data,
            user_id=current_user.id,
        )
        
        return BOMResponse.from_orm(bom)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create BOM: {str(e)}"
        )


@router.get("/{bom_id}", response_model=BOMResponse)
async def get_bom(
    bom_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get a specific BOM by ID."""
    try:
        bom_service = BOMService(db)
        
        bom = await bom_service.get_bom(
            bom_id=bom_id,
            user_id=current_user.id,
        )
        
        if not bom:
            raise NotFoundError(f"BOM {bom_id} not found")
        
        return BOMResponse.from_orm(bom)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get BOM: {str(e)}"
        )


@router.put("/{bom_id}", response_model=BOMResponse)
async def update_bom(
    bom_id: UUID = Depends(validate_uuid),
    bom_data: BOMUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific BOM."""
    try:
        bom_service = BOMService(db)
        
        bom = await bom_service.update_bom(
            bom_id=bom_id,
            bom_data=bom_data,
            user_id=current_user.id,
        )
        
        return BOMResponse.from_orm(bom)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update BOM: {str(e)}"
        )


@router.delete("/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bom(
    bom_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Delete a specific BOM."""
    try:
        bom_service = BOMService(db)
        
        await bom_service.delete_bom(
            bom_id=bom_id,
            user_id=current_user.id,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete BOM: {str(e)}"
        )


# BOM Items endpoints
@router.get("/{bom_id}/items", response_model=List[BOMItemResponse])
async def list_bom_items(
    bom_id: UUID = Depends(validate_uuid),
    category: Optional[str] = Query(None, description="Filter by component category"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List all items in a BOM."""
    try:
        bom_service = BOMService(db)
        
        items = await bom_service.list_bom_items(
            bom_id=bom_id,
            category=category,
            user_id=current_user.id,
        )
        
        return [BOMItemResponse.from_orm(item) for item in items]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list BOM items: {str(e)}"
        )


@router.post("/{bom_id}/items", response_model=BOMItemResponse, status_code=status.HTTP_201_CREATED)
async def create_bom_item(
    bom_id: UUID = Depends(validate_uuid),
    item_data: BOMItemCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new item in a BOM."""
    try:
        bom_service = BOMService(db)
        
        item = await bom_service.create_bom_item(
            bom_id=bom_id,
            item_data=item_data,
            user_id=current_user.id,
        )
        
        return BOMItemResponse.from_orm(item)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create BOM item: {str(e)}"
        )


@router.put("/items/{item_id}", response_model=BOMItemResponse)
async def update_bom_item(
    item_id: UUID = Depends(validate_uuid),
    item_data: BOMItemUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific BOM item."""
    try:
        bom_service = BOMService(db)
        
        item = await bom_service.update_bom_item(
            item_id=item_id,
            item_data=item_data,
            user_id=current_user.id,
        )
        
        return BOMItemResponse.from_orm(item)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update BOM item: {str(e)}"
        )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bom_item(
    item_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Delete a specific BOM item."""
    try:
        bom_service = BOMService(db)
        
        await bom_service.delete_bom_item(
            item_id=item_id,
            user_id=current_user.id,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete BOM item: {str(e)}"
        )


# Components endpoints
@router.get("/components", response_model=ComponentListResponse)
async def list_components(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    category: Optional[str] = Query(None, description="Filter by component category"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    status: Optional[str] = Query(None, description="Filter by component status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List components with filtering and pagination."""
    try:
        bom_service = BOMService(db)
        
        filters = {}
        if category:
            filters["category"] = category
        if manufacturer:
            filters["manufacturer"] = manufacturer
        if status:
            filters["status"] = status
        if search:
            filters["search"] = search
        
        components, total = await bom_service.list_components(
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return ComponentListResponse(
            components=components,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list components: {str(e)}"
        )


@router.post("/components", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(
    component_data: ComponentCreate,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new component."""
    try:
        bom_service = BOMService(db)
        
        component = await bom_service.create_component(
            component_data=component_data,
            user_id=current_user.id,
        )
        
        return ComponentResponse.from_orm(component)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create component: {str(e)}"
        )


@router.get("/components/{component_id}", response_model=ComponentResponse)
async def get_component(
    component_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get a specific component by ID."""
    try:
        bom_service = BOMService(db)
        
        component = await bom_service.get_component(
            component_id=component_id,
        )
        
        if not component:
            raise NotFoundError(f"Component {component_id} not found")
        
        return ComponentResponse.from_orm(component)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get component: {str(e)}"
        )


@router.put("/components/{component_id}", response_model=ComponentResponse)
async def update_component(
    component_id: UUID = Depends(validate_uuid),
    component_data: ComponentUpdate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Update a specific component."""
    try:
        bom_service = BOMService(db)
        
        component = await bom_service.update_component(
            component_id=component_id,
            component_data=component_data,
            user_id=current_user.id,
        )
        
        return ComponentResponse.from_orm(component)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update component: {str(e)}"
        )


# Suppliers endpoints
@router.get("/suppliers", response_model=SupplierListResponse)
async def list_suppliers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    country: Optional[str] = Query(None, description="Filter by country"),
    status: Optional[str] = Query(None, description="Filter by supplier status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List suppliers with filtering and pagination."""
    try:
        bom_service = BOMService(db)
        
        filters = {}
        if country:
            filters["country"] = country
        if status:
            filters["status"] = status
        if search:
            filters["search"] = search
        
        suppliers, total = await bom_service.list_suppliers(
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return SupplierListResponse(
            suppliers=suppliers,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list suppliers: {str(e)}"
        )


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new supplier."""
    try:
        bom_service = BOMService(db)
        
        supplier = await bom_service.create_supplier(
            supplier_data=supplier_data,
            user_id=current_user.id,
        )
        
        return SupplierResponse.from_orm(supplier)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create supplier: {str(e)}"
        )


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get a specific supplier by ID."""
    try:
        bom_service = BOMService(db)
        
        supplier = await bom_service.get_supplier(
            supplier_id=supplier_id,
        )
        
        if not supplier:
            raise NotFoundError(f"Supplier {supplier_id} not found")
        
        return SupplierResponse.from_orm(supplier)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supplier: {str(e)}"
        )


# Price Lists endpoints
@router.get("/suppliers/{supplier_id}/pricelists", response_model=List[PriceListResponse])
async def list_supplier_price_lists(
    supplier_id: UUID = Depends(validate_uuid),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    active_only: bool = Query(True, description="Show only active price lists"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List price lists for a supplier."""
    try:
        bom_service = BOMService(db)
        
        price_lists = await bom_service.list_supplier_price_lists(
            supplier_id=supplier_id,
            currency=currency,
            active_only=active_only,
        )
        
        return [PriceListResponse.from_orm(price_list) for price_list in price_lists]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list price lists: {str(e)}"
        )


@router.post("/suppliers/{supplier_id}/pricelists", response_model=PriceListResponse, status_code=status.HTTP_201_CREATED)
async def create_price_list(
    supplier_id: UUID = Depends(validate_uuid),
    price_list_data: PriceListCreate = None,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new price list for a supplier."""
    try:
        bom_service = BOMService(db)
        
        price_list = await bom_service.create_price_list(
            supplier_id=supplier_id,
            price_list_data=price_list_data,
            user_id=current_user.id,
        )
        
        return PriceListResponse.from_orm(price_list)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create price list: {str(e)}"
        )


# BOM Templates endpoints
@router.get("/templates", response_model=BOMTemplateListResponse)
async def list_bom_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    category: Optional[str] = Query(None, description="Filter by template category"),
    system_type: Optional[str] = Query(None, description="Filter by system type"),
    status: Optional[str] = Query(None, description="Filter by template status"),
    sort_by: str = Query("name", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """List BOM templates with filtering and pagination."""
    try:
        bom_service = BOMService(db)
        
        filters = {}
        if category:
            filters["category"] = category
        if system_type:
            filters["system_type"] = system_type
        if status:
            filters["status"] = status
        
        templates, total = await bom_service.list_bom_templates(
            skip=skip,
            limit=limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        
        return BOMTemplateListResponse(
            templates=templates,
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list BOM templates: {str(e)}"
        )


@router.post("/templates", response_model=BOMTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_bom_template(
    template_data: BOMTemplateCreate,
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Create a new BOM template."""
    try:
        bom_service = BOMService(db)
        
        template = await bom_service.create_bom_template(
            template_data=template_data,
            user_id=current_user.id,
        )
        
        return BOMTemplateResponse.from_orm(template)
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except DesignServiceException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create BOM template: {str(e)}"
        )


@router.get("/templates/{template_id}", response_model=BOMTemplateResponse)
async def get_bom_template(
    template_id: UUID = Depends(validate_uuid),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Get a specific BOM template by ID."""
    try:
        bom_service = BOMService(db)
        
        template = await bom_service.get_bom_template(
            template_id=template_id,
        )
        
        if not template:
            raise NotFoundError(f"BOM template {template_id} not found")
        
        return BOMTemplateResponse.from_orm(template)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get BOM template: {str(e)}"
        )


@router.post("/templates/{template_id}/generate", response_model=BOMResponse, status_code=status.HTTP_201_CREATED)
async def generate_bom_from_template(
    template_id: UUID = Depends(validate_uuid),
    design_id: UUID = Query(..., description="Design ID to generate BOM for"),
    layout_id: Optional[UUID] = Query(None, description="Layout ID to generate BOM for"),
    db: Session = Depends(get_db_session),
    current_user = Depends(get_current_active_user),
):
    """Generate a BOM from a template."""
    try:
        bom_service = BOMService(db)
        
        bom = await bom_service.generate_bom_from_template(
            template_id=template_id,
            design_id=design_id,
            layout_id=layout_id,
            user_id=current_user.id,
        )
        
        return BOMResponse.from_orm(bom)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.detail)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate BOM from template: {str(e)}"
        )