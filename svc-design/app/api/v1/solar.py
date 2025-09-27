"""Solar design API routes."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.solar import SolarDesign, SolarComponent, DesignCalculation
from app.schemas.solar import (
    SolarDesignCreate,
    SolarDesignUpdate,
    SolarDesignResponse,
    SolarDesignSummary,
    SolarDesignList,
    SolarComponentCreate,
    SolarComponentUpdate,
    SolarComponentResponse,
    SolarComponentList,
    DesignCalculationCreate,
    DesignCalculationUpdate,
    DesignCalculationResponse,
    DesignCalculationSummary,
    DesignCalculationList,
    CalculationRequest,
    CalculationResult,
    SolarDesignFilter,
    ComponentFilter,
    SolarDesignStatus,
    SolarDesignType,
    ComponentType,
    CalculationType,
    CalculationStatus
)
from app.api.v1.auth import get_current_user

router = APIRouter(tags=["solar-design"])


def get_user_designs_query(db: Session, user: User):
    """Get base query for user's solar designs."""
    if user.role == "admin":
        return db.query(SolarDesign)
    else:
        # Users can see designs from their projects
        return db.query(SolarDesign).join(Project).filter(
            or_(
                Project.owner_id == user.id,
                Project.shared_with.contains([str(user.id)])
            )
        )


def check_project_access(db: Session, user: User, project_id: str):
    """Check if user has access to the project."""
    if user.role == "admin":
        project = db.query(Project).filter(Project.id == project_id).first()
    else:
        project = db.query(Project).filter(
            and_(
                Project.id == project_id,
                or_(
                    Project.owner_id == user.id,
                    Project.shared_with.contains([str(user.id)])
                )
            )
        ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    
    return project


# Solar Design Endpoints

@router.post("/designs", response_model=SolarDesignResponse, status_code=status.HTTP_201_CREATED)
async def create_solar_design(
    design_data: SolarDesignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new solar design."""
    # Check project access
    project = check_project_access(db, current_user, design_data.project_id)
    
    # Create solar design
    db_design = SolarDesign(
        **design_data.dict(),
        created_by=current_user.id
    )
    
    db.add(db_design)
    db.commit()
    db.refresh(db_design)
    
    return SolarDesignResponse.from_orm(db_design)


@router.get("/designs", response_model=SolarDesignList)
async def list_solar_designs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_id: Optional[UUID] = None,
    status: Optional[SolarDesignStatus] = None,
    design_type: Optional[SolarDesignType] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List solar designs with filtering and pagination."""
    query = get_user_designs_query(db, current_user)
    
    # Apply filters
    if project_id:
        query = query.filter(SolarDesign.project_id == str(project_id))
    
    if status:
        query = query.filter(SolarDesign.status == status)
    
    if design_type:
        query = query.filter(SolarDesign.design_type == design_type)
    
    if search:
        search_filter = or_(
            SolarDesign.name.ilike(f"%{search}%"),
            SolarDesign.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and get results
    designs = query.offset(skip).limit(limit).all()
    
    return SolarDesignList(
        items=[SolarDesignSummary.from_orm(design) for design in designs],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/designs/{design_id}", response_model=SolarDesignResponse)
async def get_solar_design(
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific solar design by ID."""
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == str(design_id)).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar design not found"
        )
    
    return SolarDesignResponse.from_orm(design)


@router.put("/designs/{design_id}", response_model=SolarDesignResponse)
async def update_solar_design(
    design_id: UUID,
    design_data: SolarDesignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a solar design."""
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == str(design_id)).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar design not found"
        )
    
    # Check if user can edit (project owner or admin)
    project = db.query(Project).filter(Project.id == design.project_id).first()
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this design"
        )
    
    # Update design fields
    update_data = design_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(design, field):
            setattr(design, field, value)
    
    design.updated_at = datetime.utcnow()
    design.updated_by = current_user.id
    
    db.commit()
    db.refresh(design)
    
    return SolarDesignResponse.from_orm(design)


@router.delete("/designs/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_solar_design(
    design_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a solar design (soft delete)."""
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == str(design_id)).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar design not found"
        )
    
    # Check if user can delete (project owner or admin)
    project = db.query(Project).filter(Project.id == design.project_id).first()
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this design"
        )
    
    # Soft delete
    design.is_deleted = True
    design.deleted_at = datetime.utcnow()
    design.deleted_by = current_user.id
    
    db.commit()


# Solar Component Endpoints

@router.post("/designs/{design_id}/components", response_model=SolarComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_solar_component(
    design_id: UUID,
    component_data: SolarComponentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new solar component for a design."""
    # Check design access
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == str(design_id)).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar design not found"
        )
    
    # Create component
    db_component = SolarComponent(
        **component_data.dict(),
        design_id=str(design_id),
        created_by=current_user.id
    )
    
    db.add(db_component)
    db.commit()
    db.refresh(db_component)
    
    return SolarComponentResponse.from_orm(db_component)


@router.get("/designs/{design_id}/components", response_model=SolarComponentList)
async def list_solar_components(
    design_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    component_type: Optional[ComponentType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List solar components for a design."""
    # Check design access
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == str(design_id)).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar design not found"
        )
    
    # Query components
    components_query = db.query(SolarComponent).filter(SolarComponent.design_id == str(design_id))
    
    if component_type:
        components_query = components_query.filter(SolarComponent.component_type == component_type)
    
    total = components_query.count()
    components = components_query.offset(skip).limit(limit).all()
    
    return SolarComponentList(
        items=[SolarComponentResponse.from_orm(component) for component in components],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/components/{component_id}", response_model=SolarComponentResponse)
async def get_solar_component(
    component_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific solar component by ID."""
    component = db.query(SolarComponent).filter(SolarComponent.id == str(component_id)).first()
    
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar component not found"
        )
    
    # Check design access
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == component.design_id).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access denied"
        )
    
    return SolarComponentResponse.from_orm(component)


@router.put("/components/{component_id}", response_model=SolarComponentResponse)
async def update_solar_component(
    component_id: UUID,
    component_data: SolarComponentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a solar component."""
    component = db.query(SolarComponent).filter(SolarComponent.id == str(component_id)).first()
    
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar component not found"
        )
    
    # Check design access and edit permissions
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == component.design_id).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access denied"
        )
    
    project = db.query(Project).filter(Project.id == design.project_id).first()
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this component"
        )
    
    # Update component fields
    update_data = component_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(component, field):
            setattr(component, field, value)
    
    component.updated_at = datetime.utcnow()
    component.updated_by = current_user.id
    
    db.commit()
    db.refresh(component)
    
    return SolarComponentResponse.from_orm(component)


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_solar_component(
    component_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a solar component."""
    component = db.query(SolarComponent).filter(SolarComponent.id == str(component_id)).first()
    
    if not component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar component not found"
        )
    
    # Check design access and delete permissions
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == component.design_id).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access denied"
        )
    
    project = db.query(Project).filter(Project.id == design.project_id).first()
    if project.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this component"
        )
    
    db.delete(component)
    db.commit()


# Design Calculation Endpoints

@router.post("/designs/{design_id}/calculations", response_model=DesignCalculationResponse, status_code=status.HTTP_201_CREATED)
async def create_design_calculation(
    design_id: UUID,
    calculation_data: DesignCalculationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new design calculation."""
    # Check design access
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == str(design_id)).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar design not found"
        )
    
    # Create calculation
    db_calculation = DesignCalculation(
        **calculation_data.dict(),
        design_id=str(design_id),
        created_by=current_user.id
    )
    
    db.add(db_calculation)
    db.commit()
    db.refresh(db_calculation)
    
    return DesignCalculationResponse.from_orm(db_calculation)


@router.get("/designs/{design_id}/calculations", response_model=DesignCalculationList)
async def list_design_calculations(
    design_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    calculation_type: Optional[CalculationType] = None,
    status: Optional[CalculationStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List design calculations."""
    # Check design access
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == str(design_id)).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solar design not found"
        )
    
    # Query calculations
    calculations_query = db.query(DesignCalculation).filter(DesignCalculation.design_id == str(design_id))
    
    if calculation_type:
        calculations_query = calculations_query.filter(DesignCalculation.calculation_type == calculation_type)
    
    if status:
        calculations_query = calculations_query.filter(DesignCalculation.status == status)
    
    total = calculations_query.count()
    calculations = calculations_query.offset(skip).limit(limit).all()
    
    return DesignCalculationList(
        items=[DesignCalculationSummary.from_orm(calc) for calc in calculations],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/calculations/{calculation_id}", response_model=DesignCalculationResponse)
async def get_design_calculation(
    calculation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific design calculation by ID."""
    calculation = db.query(DesignCalculation).filter(DesignCalculation.id == str(calculation_id)).first()
    
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design calculation not found"
        )
    
    # Check design access
    query = get_user_designs_query(db, current_user)
    design = query.filter(SolarDesign.id == calculation.design_id).first()
    
    if not design:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access denied"
        )
    
    return DesignCalculationResponse.from_orm(calculation)


@router.post("/calculate", response_model=CalculationResult)
async def perform_calculation(
    calculation_request: CalculationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform solar calculations."""
    # Check design access if design_id is provided
    if calculation_request.design_id:
        query = get_user_designs_query(db, current_user)
        design = query.filter(SolarDesign.id == str(calculation_request.design_id)).first()
        
        if not design:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solar design not found"
            )
    
    # Perform calculations based on type
    result_data = {}
    
    if calculation_request.calculation_type == CalculationType.ENERGY_PRODUCTION:
        # Mock energy production calculation
        system_capacity = calculation_request.parameters.get("system_capacity_kw", 10.0)
        solar_irradiance = calculation_request.parameters.get("solar_irradiance", 5.5)
        efficiency = calculation_request.parameters.get("efficiency", 0.85)
        
        annual_production = system_capacity * solar_irradiance * 365 * efficiency
        monthly_production = annual_production / 12
        
        result_data = {
            "annual_production_kwh": round(annual_production, 2),
            "monthly_production_kwh": round(monthly_production, 2),
            "daily_production_kwh": round(annual_production / 365, 2)
        }
    
    elif calculation_request.calculation_type == CalculationType.FINANCIAL_ANALYSIS:
        # Mock financial analysis calculation
        system_cost = calculation_request.parameters.get("system_cost", 50000)
        annual_savings = calculation_request.parameters.get("annual_savings", 8000)
        electricity_rate = calculation_request.parameters.get("electricity_rate", 0.12)
        
        payback_period = system_cost / annual_savings if annual_savings > 0 else 0
        roi_25_years = (annual_savings * 25 - system_cost) / system_cost * 100 if system_cost > 0 else 0
        
        result_data = {
            "payback_period_years": round(payback_period, 1),
            "roi_25_years_percent": round(roi_25_years, 1),
            "net_savings_25_years": round(annual_savings * 25 - system_cost, 2)
        }
    
    elif calculation_request.calculation_type == CalculationType.SHADING_ANALYSIS:
        # Mock shading analysis calculation
        shading_factor = calculation_request.parameters.get("shading_factor", 0.95)
        
        result_data = {
            "shading_factor": shading_factor,
            "energy_loss_percent": round((1 - shading_factor) * 100, 1),
            "recommended_mitigation": "Consider tree trimming or panel relocation" if shading_factor < 0.9 else "No action needed"
        }
    
    else:
        # Generic calculation
        result_data = {"message": "Calculation completed", "parameters": calculation_request.parameters}
    
    return CalculationResult(
        calculation_type=calculation_request.calculation_type,
        status=CalculationStatus.COMPLETED,
        results=result_data,
        calculated_at=datetime.utcnow(),
        calculated_by=current_user.id
    )