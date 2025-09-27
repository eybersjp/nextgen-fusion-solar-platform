#!/usr/bin/env python3
"""
Compliance API endpoints for validation, rule management, and reporting

This module provides FastAPI endpoints for compliance validation,
rule management, and compliance reporting functionality.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel, Field, validator

from ...core import (
    get_db, get_logger, audit_logger,
    ComplianceRule, ComplianceValidation, ComplianceReport,
    ComplianceStatus, ViolationSeverity, RuleType, ReportStatus
)

logger = get_logger(__name__)
router = APIRouter()


# Pydantic Models
class ValidationRequest(BaseModel):
    """Request model for compliance validation."""
    project_id: str = Field(..., description="Project ID to validate")
    design_id: Optional[str] = Field(None, description="Design ID to validate")
    region: str = Field(..., description="Region code (e.g., 'US', 'EU', 'AU', 'ZA')")
    standards: List[str] = Field(..., description="List of standards to validate against")
    validation_data: Dict[str, Any] = Field(..., description="Data to validate")
    rule_types: Optional[List[RuleType]] = Field(None, description="Specific rule types to validate")
    
    class Config:
        schema_extra = {
            "example": {
                "project_id": "proj_123",
                "design_id": "design_456",
                "region": "US",
                "standards": ["NEC2020", "IBC2021"],
                "validation_data": {
                    "panel_count": 100,
                    "total_capacity_kw": 50.0,
                    "roof_area_sqm": 500.0,
                    "setback_distances": {
                        "front": 3.0,
                        "rear": 3.0,
                        "side": 1.5
                    },
                    "electrical_config": {
                        "inverter_count": 2,
                        "string_count": 10,
                        "max_voltage": 600
                    }
                },
                "rule_types": ["building_code", "electrical_code"]
            }
        }


class ViolationDetail(BaseModel):
    """Model for compliance violation details."""
    rule_code: str
    rule_name: str
    severity: ViolationSeverity
    description: str
    current_value: Optional[Any] = None
    required_value: Optional[Any] = None
    recommendation: Optional[str] = None


class ValidationResponse(BaseModel):
    """Response model for compliance validation."""
    validation_id: str
    project_id: str
    design_id: Optional[str]
    status: ComplianceStatus
    compliance_score: Optional[float] = Field(None, description="Overall compliance score (0.0-1.0)")
    
    rules_checked: int
    rules_passed: int
    rules_failed: int
    
    violations: List[ViolationDetail]
    recommendations: List[str]
    
    validated_at: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "validation_id": "val_789",
                "project_id": "proj_123",
                "design_id": "design_456",
                "status": "compliant",
                "compliance_score": 0.95,
                "rules_checked": 15,
                "rules_passed": 14,
                "rules_failed": 1,
                "violations": [
                    {
                        "rule_code": "NEC690.12",
                        "rule_name": "Rapid Shutdown Requirements",
                        "severity": "warning",
                        "description": "Rapid shutdown device placement could be optimized",
                        "recommendation": "Consider relocating rapid shutdown devices closer to array"
                    }
                ],
                "recommendations": [
                    "Consider increasing setback distances for better fire safety",
                    "Optimize string configuration for better performance"
                ],
                "validated_at": "2024-01-15T10:30:00Z"
            }
        }


class RuleResponse(BaseModel):
    """Response model for compliance rules."""
    id: str
    rule_code: str
    rule_name: str
    rule_type: RuleType
    region: str
    standard: str
    description: str
    severity: ViolationSeverity
    is_mandatory: bool
    is_active: bool
    effective_date: datetime
    expiry_date: Optional[datetime]


class ReportRequest(BaseModel):
    """Request model for compliance report generation."""
    project_id: str = Field(..., description="Project ID for the report")
    report_name: str = Field(..., description="Name of the report")
    report_type: str = Field("full", description="Type of report (full, summary, custom)")
    region: str = Field(..., description="Region code")
    standards: List[str] = Field(..., description="Standards to include in report")
    include_recommendations: bool = Field(True, description="Include recommendations in report")
    include_detailed_results: bool = Field(True, description="Include detailed validation results")
    
    class Config:
        schema_extra = {
            "example": {
                "project_id": "proj_123",
                "report_name": "Solar Installation Compliance Report",
                "report_type": "full",
                "region": "US",
                "standards": ["NEC2020", "IBC2021"],
                "include_recommendations": True,
                "include_detailed_results": True
            }
        }


class ReportResponse(BaseModel):
    """Response model for compliance reports."""
    report_id: str
    project_id: str
    report_name: str
    report_type: str
    overall_status: ComplianceStatus
    overall_score: Optional[float]
    violations_count: int
    critical_violations_count: int
    warnings_count: int
    report_status: ReportStatus
    file_path: Optional[str]
    generated_at: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "report_id": "rpt_456",
                "project_id": "proj_123",
                "report_name": "Solar Installation Compliance Report",
                "report_type": "full",
                "overall_status": "compliant",
                "overall_score": 0.92,
                "violations_count": 3,
                "critical_violations_count": 0,
                "warnings_count": 3,
                "report_status": "approved",
                "file_path": "/reports/compliance_report_456.pdf",
                "generated_at": "2024-01-15T11:00:00Z"
            }
        }


# Service Classes
class ComplianceValidationService:
    """Service for compliance validation operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_compliance(
        self,
        request: ValidationRequest
    ) -> ValidationResponse:
        """Perform compliance validation for a project/design."""
        validation_id = str(uuid.uuid4())
        
        try:
            # Get applicable rules
            rules_query = select(ComplianceRule).where(
                and_(
                    ComplianceRule.region == request.region,
                    ComplianceRule.standard.in_(request.standards),
                    ComplianceRule.is_active == True
                )
            )
            
            if request.rule_types:
                rules_query = rules_query.where(
                    ComplianceRule.rule_type.in_(request.rule_types)
                )
            
            result = await self.db.execute(rules_query)
            rules = result.scalars().all()
            
            if not rules:
                raise HTTPException(
                    status_code=404,
                    detail=f"No compliance rules found for region {request.region} and standards {request.standards}"
                )
            
            # Perform validation for each rule
            violations = []
            recommendations = []
            rules_passed = 0
            rules_failed = 0
            
            for rule in rules:
                validation_result = await self._validate_against_rule(
                    rule, request.validation_data
                )
                
                if validation_result["passed"]:
                    rules_passed += 1
                else:
                    rules_failed += 1
                    violations.extend(validation_result["violations"])
                    recommendations.extend(validation_result["recommendations"])
            
            # Calculate compliance score
            total_rules = len(rules)
            compliance_score = rules_passed / total_rules if total_rules > 0 else 0.0
            
            # Determine overall status
            critical_violations = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
            if critical_violations:
                status = ComplianceStatus.NON_COMPLIANT
            elif violations:
                status = ComplianceStatus.REQUIRES_REVIEW
            else:
                status = ComplianceStatus.COMPLIANT
            
            # Save validation record
            validation = ComplianceValidation(
                id=validation_id,
                project_id=request.project_id,
                design_id=request.design_id,
                rule_id=rules[0].id,  # For simplicity, using first rule
                validation_data=request.validation_data,
                validation_result={
                    "rules_checked": total_rules,
                    "rules_passed": rules_passed,
                    "rules_failed": rules_failed,
                    "violations": [v.dict() for v in violations],
                    "recommendations": recommendations
                },
                status=status,
                compliance_score=compliance_score,
                violations=[v.dict() for v in violations],
                recommendations=recommendations,
                validated_at=datetime.utcnow()
            )
            
            self.db.add(validation)
            await self.db.commit()
            
            # Log audit event
            audit_logger.log_validation_completed(
                validation_id=validation_id,
                project_id=request.project_id,
                rule_id="multiple",
                status=status.value,
                compliance_score=compliance_score,
                violations_count=len(violations)
            )
            
            return ValidationResponse(
                validation_id=validation_id,
                project_id=request.project_id,
                design_id=request.design_id,
                status=status,
                compliance_score=compliance_score,
                rules_checked=total_rules,
                rules_passed=rules_passed,
                rules_failed=rules_failed,
                violations=violations,
                recommendations=recommendations,
                validated_at=datetime.utcnow()
            )
            
        except Exception as e:
            audit_logger.log_validation_failed(
                validation_id=validation_id,
                project_id=request.project_id,
                rule_id="multiple",
                error=str(e)
            )
            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
    
    async def _validate_against_rule(
        self,
        rule: ComplianceRule,
        validation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate data against a specific compliance rule."""
        # Mock validation logic - in production, this would implement
        # the actual rule validation based on rule.validation_logic
        
        violations = []
        recommendations = []
        passed = True
        
        # Example validation logic for different rule types
        if rule.rule_type == RuleType.BUILDING_CODE:
            # Check setback requirements
            if "setback_distances" in validation_data:
                setbacks = validation_data["setback_distances"]
                min_setback = rule.requirements.get("min_setback", 3.0)
                
                for side, distance in setbacks.items():
                    if distance < min_setback:
                        passed = False
                        violations.append(ViolationDetail(
                            rule_code=rule.rule_code,
                            rule_name=rule.rule_name,
                            severity=rule.severity,
                            description=f"Insufficient {side} setback distance",
                            current_value=distance,
                            required_value=min_setback,
                            recommendation=f"Increase {side} setback to at least {min_setback}m"
                        ))
        
        elif rule.rule_type == RuleType.ELECTRICAL_CODE:
            # Check electrical requirements
            if "electrical_config" in validation_data:
                electrical = validation_data["electrical_config"]
                max_voltage = rule.requirements.get("max_system_voltage", 600)
                
                if electrical.get("max_voltage", 0) > max_voltage:
                    passed = False
                    violations.append(ViolationDetail(
                        rule_code=rule.rule_code,
                        rule_name=rule.rule_name,
                        severity=rule.severity,
                        description="System voltage exceeds maximum allowed",
                        current_value=electrical.get("max_voltage"),
                        required_value=max_voltage,
                        recommendation=f"Reduce system voltage to {max_voltage}V or below"
                    ))
        
        # Add general recommendations
        if not violations:
            recommendations.append(f"Compliant with {rule.rule_name}")
        
        return {
            "passed": passed,
            "violations": violations,
            "recommendations": recommendations
        }


class ComplianceReportService:
    """Service for compliance report operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_report(
        self,
        request: ReportRequest
    ) -> ReportResponse:
        """Generate a compliance report for a project."""
        report_id = str(uuid.uuid4())
        
        try:
            # Get validation results for the project
            validations_query = select(ComplianceValidation).where(
                ComplianceValidation.project_id == request.project_id
            )
            
            result = await self.db.execute(validations_query)
            validations = result.scalars().all()
            
            if not validations:
                raise HTTPException(
                    status_code=404,
                    detail=f"No validation results found for project {request.project_id}"
                )
            
            # Calculate report metrics
            total_violations = sum(len(v.violations or []) for v in validations)
            critical_violations = 0
            warnings = 0
            
            for validation in validations:
                for violation in (validation.violations or []):
                    if violation.get("severity") == "critical":
                        critical_violations += 1
                    elif violation.get("severity") == "warning":
                        warnings += 1
            
            # Determine overall status and score
            scores = [v.compliance_score for v in validations if v.compliance_score is not None]
            overall_score = sum(scores) / len(scores) if scores else None
            
            if critical_violations > 0:
                overall_status = ComplianceStatus.NON_COMPLIANT
            elif total_violations > 0:
                overall_status = ComplianceStatus.REQUIRES_REVIEW
            else:
                overall_status = ComplianceStatus.COMPLIANT
            
            # Generate report summary
            summary = {
                "project_id": request.project_id,
                "region": request.region,
                "standards": request.standards,
                "validation_count": len(validations),
                "overall_score": overall_score,
                "total_violations": total_violations,
                "critical_violations": critical_violations,
                "warnings": warnings
            }
            
            # Generate detailed results
            detailed_results = {
                "validations": [
                    {
                        "validation_id": v.id,
                        "status": v.status.value,
                        "score": v.compliance_score,
                        "violations": v.violations,
                        "recommendations": v.recommendations,
                        "validated_at": v.validated_at.isoformat() if v.validated_at else None
                    }
                    for v in validations
                ]
            }
            
            # Create report record
            report = ComplianceReport(
                id=report_id,
                project_id=request.project_id,
                report_name=request.report_name,
                report_type=request.report_type,
                region=request.region,
                standards=request.standards,
                overall_status=overall_status,
                overall_score=overall_score,
                summary=summary,
                detailed_results=detailed_results,
                violations_count=total_violations,
                critical_violations_count=critical_violations,
                warnings_count=warnings,
                report_status=ReportStatus.DRAFT,
                generated_at=datetime.utcnow()
            )
            
            self.db.add(report)
            await self.db.commit()
            
            # Log audit event
            audit_logger.log_report_generated(
                report_id=report_id,
                project_id=request.project_id,
                report_type=request.report_type,
                overall_status=overall_status.value,
                overall_score=overall_score,
                violations_count=total_violations
            )
            
            return ReportResponse(
                report_id=report_id,
                project_id=request.project_id,
                report_name=request.report_name,
                report_type=request.report_type,
                overall_status=overall_status,
                overall_score=overall_score,
                violations_count=total_violations,
                critical_violations_count=critical_violations,
                warnings_count=warnings,
                report_status=ReportStatus.DRAFT,
                file_path=None,  # Will be set when PDF is generated
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# API Endpoints
@router.post("/validate", response_model=ValidationResponse)
async def validate_compliance(
    request: ValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Validate project compliance against regional standards.
    
    Performs comprehensive compliance validation for a solar project
    against specified regional building codes, electrical codes, and safety standards.
    """
    service = ComplianceValidationService(db)
    return await service.validate_compliance(request)


@router.get("/rules/{region}", response_model=List[RuleResponse])
async def get_compliance_rules(
    region: str,
    standard: Optional[str] = Query(None, description="Filter by specific standard"),
    rule_type: Optional[RuleType] = Query(None, description="Filter by rule type"),
    active_only: bool = Query(True, description="Return only active rules"),
    db: AsyncSession = Depends(get_db)
):
    """Get compliance rules for a specific region.
    
    Returns all applicable compliance rules for the specified region,
    optionally filtered by standard and rule type.
    """
    query = select(ComplianceRule).where(ComplianceRule.region == region)
    
    if standard:
        query = query.where(ComplianceRule.standard == standard)
    
    if rule_type:
        query = query.where(ComplianceRule.rule_type == rule_type)
    
    if active_only:
        query = query.where(ComplianceRule.is_active == True)
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return [
        RuleResponse(
            id=rule.id,
            rule_code=rule.rule_code,
            rule_name=rule.rule_name,
            rule_type=rule.rule_type,
            region=rule.region,
            standard=rule.standard,
            description=rule.description,
            severity=rule.severity,
            is_mandatory=rule.is_mandatory,
            is_active=rule.is_active,
            effective_date=rule.effective_date,
            expiry_date=rule.expiry_date
        )
        for rule in rules
    ]


@router.post("/report", response_model=ReportResponse)
async def generate_compliance_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Generate a comprehensive compliance report.
    
    Creates a detailed compliance report including validation results,
    violations, recommendations, and compliance scores.
    """
    service = ComplianceReportService(db)
    return await service.generate_report(request)


@router.get("/validation/{validation_id}", response_model=ValidationResponse)
async def get_validation_result(
    validation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed results for a specific compliance validation."""
    query = select(ComplianceValidation).where(ComplianceValidation.id == validation_id)
    result = await db.execute(query)
    validation = result.scalar_one_or_none()
    
    if not validation:
        raise HTTPException(status_code=404, detail="Validation not found")
    
    # Convert violations to ViolationDetail objects
    violations = [
        ViolationDetail(**violation) for violation in (validation.violations or [])
    ]
    
    return ValidationResponse(
        validation_id=validation.id,
        project_id=validation.project_id,
        design_id=validation.design_id,
        status=validation.status,
        compliance_score=validation.compliance_score,
        rules_checked=validation.validation_result.get("rules_checked", 0),
        rules_passed=validation.validation_result.get("rules_passed", 0),
        rules_failed=validation.validation_result.get("rules_failed", 0),
        violations=violations,
        recommendations=validation.recommendations or [],
        validated_at=validation.validated_at
    )


@router.get("/report/{report_id}", response_model=ReportResponse)
async def get_compliance_report(
    report_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get details for a specific compliance report."""
    query = select(ComplianceReport).where(ComplianceReport.id == report_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportResponse(
        report_id=report.id,
        project_id=report.project_id,
        report_name=report.report_name,
        report_type=report.report_type,
        overall_status=report.overall_status,
        overall_score=report.overall_score,
        violations_count=report.violations_count,
        critical_violations_count=report.critical_violations_count,
        warnings_count=report.warnings_count,
        report_status=report.report_status,
        file_path=report.file_path,
        generated_at=report.generated_at
    )


@router.get("/project/{project_id}/validations", response_model=List[ValidationResponse])
async def get_project_validations(
    project_id: str,
    status: Optional[ComplianceStatus] = Query(None, description="Filter by validation status"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db)
):
    """Get all compliance validations for a specific project."""
    query = select(ComplianceValidation).where(
        ComplianceValidation.project_id == project_id
    )
    
    if status:
        query = query.where(ComplianceValidation.status == status)
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    validations = result.scalars().all()
    
    return [
        ValidationResponse(
            validation_id=v.id,
            project_id=v.project_id,
            design_id=v.design_id,
            status=v.status,
            compliance_score=v.compliance_score,
            rules_checked=v.validation_result.get("rules_checked", 0),
            rules_passed=v.validation_result.get("rules_passed", 0),
            rules_failed=v.validation_result.get("rules_failed", 0),
            violations=[ViolationDetail(**violation) for violation in (v.violations or [])],
            recommendations=v.recommendations or [],
            validated_at=v.validated_at
        )
        for v in validations
    ]