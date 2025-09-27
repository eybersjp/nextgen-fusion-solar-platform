"""Rules Engine API Endpoints for NextGen Fusion Platform

Provides REST API for:
- Rule set management and execution
- Individual rule evaluation
- Entity validation against compliance rules
- Rule performance monitoring
- Dynamic rule configuration
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload

from ..models.rules_engine import (
    ComplianceRule, RuleSet, RuleExecution, RuleViolation,
    ComplianceJurisdiction, RuleStatus, ExecutionResult
)
from ..services.rules_engine_service import (
    rules_engine_service, EvaluationContext, ExecutionStrategy,
    RuleResult, RuleSetResult
)
from shared.database.session import get_async_session
from shared.auth.dependencies import get_current_user
from shared.models.user import User

router = APIRouter(prefix="/rules-engine", tags=["Rules Engine"])


# Request/Response Models
class EntityValidationRequest(BaseModel):
    """Request for entity validation"""
    entity_type: str = Field(..., description="Type of entity to validate")
    entity_id: str = Field(..., description="Unique identifier of the entity")
    entity_data: Dict[str, Any] = Field(..., description="Entity data to validate")
    jurisdiction_codes: List[str] = Field(..., description="Applicable jurisdiction codes")
    rule_types: Optional[List[str]] = Field(None, description="Specific rule types to apply")
    execution_context: str = Field("api_validation", description="Context for execution")


class RuleSetExecutionRequest(BaseModel):
    """Request for rule set execution"""
    rule_set_id: str = Field(..., description="ID of the rule set to execute")
    entity_type: str = Field(..., description="Type of entity being evaluated")
    entity_id: str = Field(..., description="Unique identifier of the entity")
    entity_data: Dict[str, Any] = Field(..., description="Entity data for evaluation")
    jurisdiction_codes: List[str] = Field(..., description="Applicable jurisdiction codes")
    execution_strategy: ExecutionStrategy = Field(
        ExecutionStrategy.SEQUENTIAL, 
        description="Strategy for rule execution"
    )
    execution_context: str = Field("api_execution", description="Context for execution")


class RuleExecutionRequest(BaseModel):
    """Request for single rule execution"""
    rule_id: str = Field(..., description="ID of the rule to execute")
    entity_type: str = Field(..., description="Type of entity being evaluated")
    entity_id: str = Field(..., description="Unique identifier of the entity")
    entity_data: Dict[str, Any] = Field(..., description="Entity data for evaluation")
    jurisdiction_codes: List[str] = Field(..., description="Applicable jurisdiction codes")
    execution_context: str = Field("api_execution", description="Context for execution")


class ConditionResultResponse(BaseModel):
    """Response model for condition result"""
    condition_id: str
    passed: bool
    actual_value: Any
    expected_value: Any
    message: str
    field_path: str


class RuleResultResponse(BaseModel):
    """Response model for rule result"""
    rule_id: str
    rule_code: str
    passed: bool
    result: ExecutionResult
    execution_time_ms: int
    condition_results: List[ConditionResultResponse]
    violations: List[Dict[str, Any]]
    actions_executed: List[Dict[str, Any]]
    error_message: Optional[str] = None


class RuleSetResultResponse(BaseModel):
    """Response model for rule set result"""
    rule_set_id: str
    rule_set_name: str
    overall_passed: bool
    total_rules: int
    passed_rules: int
    failed_rules: int
    execution_time_ms: int
    rule_results: List[RuleResultResponse]
    stopped_early: bool = False


class RuleExecutionHistoryResponse(BaseModel):
    """Response model for rule execution history"""
    execution_id: str
    rule_id: str
    rule_code: str
    execution_context: str
    target_entity_type: str
    target_entity_id: str
    result: ExecutionResult
    passed_conditions: int
    failed_conditions: int
    execution_time_ms: int
    executed_at: datetime
    executed_by_user_id: Optional[str]
    violations_count: int


class RulePerformanceResponse(BaseModel):
    """Response model for rule performance metrics"""
    rule_id: str
    rule_code: str
    total_executions: int
    success_rate: float
    average_execution_time_ms: float
    last_executed: Optional[datetime]
    total_violations: int


class JurisdictionRulesResponse(BaseModel):
    """Response model for jurisdiction rules"""
    jurisdiction_code: str
    jurisdiction_name: str
    active_rules_count: int
    rule_types: List[str]
    last_updated: Optional[datetime]


# API Endpoints
@router.post("/validate-entity", response_model=RuleSetResultResponse)
async def validate_entity(
    request: EntityValidationRequest,
    current_user: User = Depends(get_current_user)
) -> RuleSetResultResponse:
    """Validate an entity against applicable compliance rules"""
    try:
        result = await rules_engine_service.validate_entity(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_data=request.entity_data,
            jurisdiction_codes=request.jurisdiction_codes,
            rule_types=request.rule_types,
            user_id=str(current_user.id)
        )
        
        return RuleSetResultResponse(
            rule_set_id=result.rule_set_id,
            rule_set_name=result.rule_set_name,
            overall_passed=result.overall_passed,
            total_rules=result.total_rules,
            passed_rules=result.passed_rules,
            failed_rules=result.failed_rules,
            execution_time_ms=result.execution_time_ms,
            rule_results=[
                RuleResultResponse(
                    rule_id=rr.rule_id,
                    rule_code=rr.rule_code,
                    passed=rr.passed,
                    result=rr.result,
                    execution_time_ms=rr.execution_time_ms,
                    condition_results=[
                        ConditionResultResponse(
                            condition_id=cr.condition_id,
                            passed=cr.passed,
                            actual_value=cr.actual_value,
                            expected_value=cr.expected_value,
                            message=cr.message,
                            field_path=cr.field_path
                        ) for cr in rr.condition_results
                    ],
                    violations=rr.violations,
                    actions_executed=rr.actions_executed,
                    error_message=rr.error_message
                ) for rr in result.rule_results
            ],
            stopped_early=result.stopped_early
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity validation failed: {str(e)}")


@router.post("/execute-rule-set", response_model=RuleSetResultResponse)
async def execute_rule_set(
    request: RuleSetExecutionRequest,
    current_user: User = Depends(get_current_user)
) -> RuleSetResultResponse:
    """Execute a specific rule set against an entity"""
    try:
        context = EvaluationContext(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_data=request.entity_data,
            jurisdiction_codes=request.jurisdiction_codes,
            user_id=str(current_user.id),
            execution_context=request.execution_context
        )
        
        result = await rules_engine_service.evaluate_rule_set(
            rule_set_id=request.rule_set_id,
            context=context,
            strategy=request.execution_strategy
        )
        
        return RuleSetResultResponse(
            rule_set_id=result.rule_set_id,
            rule_set_name=result.rule_set_name,
            overall_passed=result.overall_passed,
            total_rules=result.total_rules,
            passed_rules=result.passed_rules,
            failed_rules=result.failed_rules,
            execution_time_ms=result.execution_time_ms,
            rule_results=[
                RuleResultResponse(
                    rule_id=rr.rule_id,
                    rule_code=rr.rule_code,
                    passed=rr.passed,
                    result=rr.result,
                    execution_time_ms=rr.execution_time_ms,
                    condition_results=[
                        ConditionResultResponse(
                            condition_id=cr.condition_id,
                            passed=cr.passed,
                            actual_value=cr.actual_value,
                            expected_value=cr.expected_value,
                            message=cr.message,
                            field_path=cr.field_path
                        ) for cr in rr.condition_results
                    ],
                    violations=rr.violations,
                    actions_executed=rr.actions_executed,
                    error_message=rr.error_message
                ) for rr in result.rule_results
            ],
            stopped_early=result.stopped_early
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule set execution failed: {str(e)}")


@router.post("/execute-rule", response_model=RuleResultResponse)
async def execute_rule(
    request: RuleExecutionRequest,
    current_user: User = Depends(get_current_user)
) -> RuleResultResponse:
    """Execute a single compliance rule"""
    try:
        context = EvaluationContext(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            entity_data=request.entity_data,
            jurisdiction_codes=request.jurisdiction_codes,
            user_id=str(current_user.id),
            execution_context=request.execution_context
        )
        
        result = await rules_engine_service.evaluate_rule(
            rule_id=request.rule_id,
            context=context
        )
        
        return RuleResultResponse(
            rule_id=result.rule_id,
            rule_code=result.rule_code,
            passed=result.passed,
            result=result.result,
            execution_time_ms=result.execution_time_ms,
            condition_results=[
                ConditionResultResponse(
                    condition_id=cr.condition_id,
                    passed=cr.passed,
                    actual_value=cr.actual_value,
                    expected_value=cr.expected_value,
                    message=cr.message,
                    field_path=cr.field_path
                ) for cr in result.condition_results
            ],
            violations=result.violations,
            actions_executed=result.actions_executed,
            error_message=result.error_message
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule execution failed: {str(e)}")


@router.get("/jurisdictions/{jurisdiction_code}/rules", response_model=List[Dict[str, Any]])
async def get_jurisdiction_rules(
    jurisdiction_code: str,
    rule_types: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get active rules for a specific jurisdiction"""
    try:
        rules = await rules_engine_service.get_rules_for_jurisdiction(
            jurisdiction_codes=[jurisdiction_code],
            rule_types=rule_types
        )
        
        return [
            {
                "rule_id": str(rule.id),
                "rule_code": rule.rule_code,
                "rule_name": rule.rule_name,
                "rule_type": rule.rule_type,
                "severity": rule.severity,
                "description": rule.description,
                "effective_date": rule.effective_date,
                "expiry_date": rule.expiry_date,
                "version": rule.version,
                "execution_order": rule.execution_order
            }
            for rule in rules
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jurisdiction rules: {str(e)}")


@router.get("/executions/history", response_model=List[RuleExecutionHistoryResponse])
async def get_execution_history(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    result: Optional[ExecutionResult] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[RuleExecutionHistoryResponse]:
    """Get rule execution history with filtering"""
    try:
        query = select(RuleExecution).join(ComplianceRule)
        
        # Apply filters
        filters = []
        if entity_type:
            filters.append(RuleExecution.target_entity_type == entity_type)
        if entity_id:
            filters.append(RuleExecution.target_entity_id == entity_id)
        if rule_id:
            filters.append(RuleExecution.rule_id == UUID(rule_id))
        if result:
            filters.append(RuleExecution.result == result)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Add ordering and pagination
        query = query.order_by(desc(RuleExecution.executed_at)).offset(offset).limit(limit)
        
        # Load violations count
        query = query.options(
            selectinload(RuleExecution.violations)
        )
        
        result = await session.execute(query)
        executions = result.scalars().all()
        
        return [
            RuleExecutionHistoryResponse(
                execution_id=str(execution.id),
                rule_id=str(execution.rule_id),
                rule_code=execution.rule.rule_code,
                execution_context=execution.execution_context,
                target_entity_type=execution.target_entity_type,
                target_entity_id=execution.target_entity_id,
                result=execution.result,
                passed_conditions=execution.passed_conditions,
                failed_conditions=execution.failed_conditions,
                execution_time_ms=execution.execution_time_ms,
                executed_at=execution.executed_at,
                executed_by_user_id=execution.executed_by_user_id,
                violations_count=len(execution.violations)
            )
            for execution in executions
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution history: {str(e)}")


@router.get("/performance/rules", response_model=List[RulePerformanceResponse])
async def get_rule_performance(
    jurisdiction_code: Optional[str] = Query(None),
    rule_type: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[RulePerformanceResponse]:
    """Get rule performance metrics"""
    try:
        # Calculate date range
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query for performance metrics
        query = select(
            ComplianceRule.id,
            ComplianceRule.rule_code,
            func.count(RuleExecution.id).label('total_executions'),
            func.avg(
                func.case(
                    (RuleExecution.result == ExecutionResult.PASS, 1.0),
                    else_=0.0
                )
            ).label('success_rate'),
            func.avg(RuleExecution.execution_time_ms).label('avg_execution_time'),
            func.max(RuleExecution.executed_at).label('last_executed'),
            func.count(RuleViolation.id).label('total_violations')
        ).select_from(
            ComplianceRule
        ).outerjoin(
            RuleExecution, and_(
                RuleExecution.rule_id == ComplianceRule.id,
                RuleExecution.executed_at >= since_date
            )
        ).outerjoin(
            RuleViolation, RuleViolation.execution_id == RuleExecution.id
        )
        
        # Apply filters
        filters = [ComplianceRule.status == RuleStatus.ACTIVE]
        if jurisdiction_code:
            query = query.join(ComplianceJurisdiction)
            filters.append(ComplianceJurisdiction.code == jurisdiction_code)
        if rule_type:
            filters.append(ComplianceRule.rule_type == rule_type)
        
        query = query.where(and_(*filters))
        query = query.group_by(ComplianceRule.id, ComplianceRule.rule_code)
        query = query.order_by(desc('total_executions'))
        
        result = await session.execute(query)
        performance_data = result.all()
        
        return [
            RulePerformanceResponse(
                rule_id=str(row.id),
                rule_code=row.rule_code,
                total_executions=row.total_executions or 0,
                success_rate=float(row.success_rate or 0.0),
                average_execution_time_ms=float(row.avg_execution_time or 0.0),
                last_executed=row.last_executed,
                total_violations=row.total_violations or 0
            )
            for row in performance_data
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rule performance: {str(e)}")


@router.get("/jurisdictions", response_model=List[JurisdictionRulesResponse])
async def get_jurisdictions(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[JurisdictionRulesResponse]:
    """Get all jurisdictions with rule counts"""
    try:
        query = select(
            ComplianceJurisdiction.code,
            ComplianceJurisdiction.name,
            func.count(ComplianceRule.id).label('active_rules_count'),
            func.array_agg(func.distinct(ComplianceRule.rule_type)).label('rule_types'),
            func.max(ComplianceRule.updated_at).label('last_updated')
        ).select_from(
            ComplianceJurisdiction
        ).outerjoin(
            ComplianceRule, and_(
                ComplianceRule.jurisdiction_id == ComplianceJurisdiction.id,
                ComplianceRule.status == RuleStatus.ACTIVE
            )
        ).group_by(
            ComplianceJurisdiction.code,
            ComplianceJurisdiction.name
        ).order_by(
            ComplianceJurisdiction.name
        )
        
        result = await session.execute(query)
        jurisdictions = result.all()
        
        return [
            JurisdictionRulesResponse(
                jurisdiction_code=row.code,
                jurisdiction_name=row.name,
                active_rules_count=row.active_rules_count or 0,
                rule_types=[rt for rt in (row.rule_types or []) if rt is not None],
                last_updated=row.last_updated
            )
            for row in jurisdictions
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jurisdictions: {str(e)}")


@router.get("/rule-sets", response_model=List[Dict[str, Any]])
async def get_rule_sets(
    active_only: bool = Query(True),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get available rule sets"""
    try:
        query = select(RuleSet)
        
        if active_only:
            query = query.where(RuleSet.is_active == True)
        
        query = query.order_by(RuleSet.name)
        
        result = await session.execute(query)
        rule_sets = result.scalars().all()
        
        return [
            {
                "rule_set_id": str(rule_set.id),
                "name": rule_set.name,
                "description": rule_set.description,
                "is_active": rule_set.is_active,
                "stop_on_first_failure": rule_set.stop_on_first_failure,
                "created_at": rule_set.created_at,
                "updated_at": rule_set.updated_at
            }
            for rule_set in rule_sets
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rule sets: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for rules engine"""
    try:
        # Test database connectivity
        async with get_async_session() as session:
            result = await session.execute(select(func.count(ComplianceRule.id)))
            total_rules = result.scalar()
        
        # Test cache connectivity
        cache_healthy = True
        try:
            await rules_engine_service.cache_manager.health_check()
        except Exception:
            cache_healthy = False
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "cache": "connected" if cache_healthy else "disconnected",
            "total_rules": total_rules,
            "service_version": "1.0.0"
        }
    
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")