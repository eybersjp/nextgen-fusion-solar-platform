"""Pluggable Rules Engine Models for NextGen Fusion Platform

Provides flexible compliance rule management:
- Dynamic rule definition and execution
- Multi-jurisdiction support
- Rule versioning and audit trails
- Performance optimization with caching
- Extensible rule types and conditions
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, Boolean, Numeric, Integer, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class RuleType(str, Enum):
    """Types of compliance rules"""
    SAFETY = "safety"
    ELECTRICAL = "electrical"
    STRUCTURAL = "structural"
    ENVIRONMENTAL = "environmental"
    ZONING = "zoning"
    BUILDING_CODE = "building_code"
    FIRE_SAFETY = "fire_safety"
    ACCESSIBILITY = "accessibility"
    ENERGY_EFFICIENCY = "energy_efficiency"
    GRID_CONNECTION = "grid_connection"
    CUSTOM = "custom"


class RuleStatus(str, Enum):
    """Rule lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    TESTING = "testing"


class ConditionOperator(str, Enum):
    """Operators for rule conditions"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    REGEX_MATCH = "regex_match"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class RuleSeverity(str, Enum):
    """Severity levels for rule violations"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    BLOCKING = "blocking"


class ExecutionResult(str, Enum):
    """Rule execution results"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class ComplianceJurisdiction(Base):
    """Compliance jurisdictions (countries, states, cities)"""
    __tablename__ = "compliance_jurisdictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    jurisdiction_type = Column(String(50), nullable=False)  # country, state, city, utility
    parent_jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("compliance_jurisdictions.id"))
    
    # Metadata
    description = Column(Text)
    official_website = Column(String(500))
    contact_info = Column(JSONB)
    timezone = Column(String(50))
    currency_code = Column(String(3))
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent_jurisdiction = relationship("ComplianceJurisdiction", remote_side=[id])
    child_jurisdictions = relationship("ComplianceJurisdiction", back_populates="parent_jurisdiction")
    rules = relationship("ComplianceRule", back_populates="jurisdiction")
    
    __table_args__ = (
        Index("idx_jurisdiction_code_active", "code", "is_active"),
        Index("idx_jurisdiction_type", "jurisdiction_type"),
        Index("idx_jurisdiction_parent", "parent_jurisdiction_id"),
    )
    
    def __repr__(self):
        return f"<ComplianceJurisdiction(code='{self.code}', name='{self.name}')>"


class ComplianceRule(Base):
    """Core compliance rule definition"""
    __tablename__ = "compliance_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code = Column(String(100), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text)
    
    # Classification
    rule_type = Column(String(50), nullable=False, index=True)
    category = Column(String(100), index=True)
    subcategory = Column(String(100))
    
    # Jurisdiction and versioning
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("compliance_jurisdictions.id"), nullable=False)
    version = Column(String(20), nullable=False, default="1.0")
    parent_rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id"))
    
    # Rule logic
    rule_expression = Column(Text, nullable=False)  # JSON or expression language
    conditions = Column(JSONB)  # Structured conditions
    parameters = Column(JSONB)  # Rule parameters and thresholds
    
    # Execution settings
    severity = Column(String(20), nullable=False, default=RuleSeverity.WARNING)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    execution_order = Column(Integer, default=100)
    timeout_seconds = Column(Integer, default=30)
    
    # Lifecycle
    status = Column(String(20), nullable=False, default=RuleStatus.DRAFT)
    effective_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True))
    
    # Documentation
    documentation_url = Column(String(500))
    legal_reference = Column(Text)
    implementation_notes = Column(Text)
    
    # Metadata
    tags = Column(JSONB)  # For categorization and search
    created_by_user_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    jurisdiction = relationship("ComplianceJurisdiction", back_populates="rules")
    parent_rule = relationship("ComplianceRule", remote_side=[id])
    child_rules = relationship("ComplianceRule", back_populates="parent_rule")
    conditions_rel = relationship("RuleCondition", back_populates="rule", cascade="all, delete-orphan")
    actions = relationship("RuleAction", back_populates="rule", cascade="all, delete-orphan")
    executions = relationship("RuleExecution", back_populates="rule")
    
    __table_args__ = (
        Index("idx_rule_code_jurisdiction", "rule_code", "jurisdiction_id"),
        Index("idx_rule_type_status", "rule_type", "status"),
        Index("idx_rule_effective_date", "effective_date"),
        Index("idx_rule_execution_order", "execution_order"),
        Index("idx_rule_mandatory", "is_mandatory"),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        if status not in [s.value for s in RuleStatus]:
            raise ValueError(f"Invalid rule status: {status}")
        return status
    
    @validates('severity')
    def validate_severity(self, key, severity):
        if severity not in [s.value for s in RuleSeverity]:
            raise ValueError(f"Invalid rule severity: {severity}")
        return severity
    
    def is_active(self) -> bool:
        """Check if rule is currently active"""
        now = datetime.utcnow()
        return (
            self.status == RuleStatus.ACTIVE and
            (self.effective_date is None or self.effective_date <= now) and
            (self.expiry_date is None or self.expiry_date > now)
        )
    
    def __repr__(self):
        return f"<ComplianceRule(code='{self.rule_code}', name='{self.name}')>"


class RuleCondition(Base):
    """Individual conditions within a rule"""
    __tablename__ = "rule_conditions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False)
    
    # Condition definition
    field_path = Column(String(200), nullable=False)  # JSONPath or dot notation
    operator = Column(String(50), nullable=False)
    expected_value = Column(JSONB)  # Can be any JSON type
    
    # Logical grouping
    condition_group = Column(String(50), default="default")
    logical_operator = Column(String(10), default="AND")  # AND, OR
    
    # Metadata
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rule = relationship("ComplianceRule", back_populates="conditions_rel")
    
    __table_args__ = (
        Index("idx_condition_rule_active", "rule_id", "is_active"),
        Index("idx_condition_group", "condition_group"),
    )
    
    @validates('operator')
    def validate_operator(self, key, operator):
        if operator not in [op.value for op in ConditionOperator]:
            raise ValueError(f"Invalid condition operator: {operator}")
        return operator
    
    def __repr__(self):
        return f"<RuleCondition(field='{self.field_path}', operator='{self.operator}')>"


class RuleAction(Base):
    """Actions to take when rule conditions are met"""
    __tablename__ = "rule_actions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False)
    
    # Action definition
    action_type = Column(String(50), nullable=False)  # validate, transform, notify, block
    action_config = Column(JSONB, nullable=False)  # Action-specific configuration
    
    # Execution settings
    execution_order = Column(Integer, default=100)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rule = relationship("ComplianceRule", back_populates="actions")
    
    __table_args__ = (
        Index("idx_action_rule_active", "rule_id", "is_active"),
        Index("idx_action_type", "action_type"),
        Index("idx_action_execution_order", "execution_order"),
    )
    
    def __repr__(self):
        return f"<RuleAction(type='{self.action_type}', rule_id='{self.rule_id}')>"


class RuleExecution(Base):
    """Record of rule execution attempts"""
    __tablename__ = "rule_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False)
    
    # Execution context
    execution_context = Column(String(100), nullable=False)  # design_validation, project_review, etc.
    target_entity_type = Column(String(50), nullable=False)  # solar_design, project, component
    target_entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Execution details
    started_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    completed_at = Column(DateTime(timezone=True))
    execution_time_ms = Column(Integer)
    
    # Results
    result = Column(String(20), nullable=False)
    passed_conditions = Column(Integer, default=0)
    failed_conditions = Column(Integer, default=0)
    
    # Data
    input_data = Column(JSONB)  # Input data for the rule
    output_data = Column(JSONB)  # Results and computed values
    error_details = Column(JSONB)  # Error information if execution failed
    
    # Metadata
    executed_by_user_id = Column(UUID(as_uuid=True))
    execution_version = Column(String(20))  # Rule version at time of execution
    
    # Relationships
    rule = relationship("ComplianceRule", back_populates="executions")
    violations = relationship("RuleViolation", back_populates="execution", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_execution_rule_context", "rule_id", "execution_context"),
        Index("idx_execution_target", "target_entity_type", "target_entity_id"),
        Index("idx_execution_started_at", "started_at"),
        Index("idx_execution_result", "result"),
    )
    
    @validates('result')
    def validate_result(self, key, result):
        if result not in [r.value for r in ExecutionResult]:
            raise ValueError(f"Invalid execution result: {result}")
        return result
    
    def __repr__(self):
        return f"<RuleExecution(rule_id='{self.rule_id}', result='{self.result}')>"


class RuleViolation(Base):
    """Specific violations found during rule execution"""
    __tablename__ = "rule_violations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("rule_executions.id"), nullable=False)
    
    # Violation details
    violation_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    field_path = Column(String(200))  # Field that caused the violation
    
    # Values
    expected_value = Column(JSONB)
    actual_value = Column(JSONB)
    suggested_fix = Column(Text)
    
    # Resolution
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by_user_id = Column(UUID(as_uuid=True))
    resolution_notes = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    execution = relationship("RuleExecution", back_populates="violations")
    
    __table_args__ = (
        Index("idx_violation_execution", "execution_id"),
        Index("idx_violation_severity", "severity"),
        Index("idx_violation_resolved", "is_resolved"),
        Index("idx_violation_type", "violation_type"),
    )
    
    @validates('severity')
    def validate_severity(self, key, severity):
        if severity not in [s.value for s in RuleSeverity]:
            raise ValueError(f"Invalid violation severity: {severity}")
        return severity
    
    def __repr__(self):
        return f"<RuleViolation(type='{self.violation_type}', severity='{self.severity}')>"


class RuleSet(Base):
    """Collections of related rules"""
    __tablename__ = "rule_sets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Classification
    category = Column(String(100), index=True)
    jurisdiction_id = Column(UUID(as_uuid=True), ForeignKey("compliance_jurisdictions.id"))
    
    # Configuration
    execution_strategy = Column(String(50), default="sequential")  # sequential, parallel, conditional
    stop_on_first_failure = Column(Boolean, default=False)
    
    # Lifecycle
    version = Column(String(20), nullable=False, default="1.0")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    jurisdiction = relationship("ComplianceJurisdiction")
    rule_memberships = relationship("RuleSetMembership", back_populates="rule_set", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_ruleset_category_active", "category", "is_active"),
        Index("idx_ruleset_jurisdiction", "jurisdiction_id"),
    )
    
    def __repr__(self):
        return f"<RuleSet(name='{self.name}', version='{self.version}')>"


class RuleSetMembership(Base):
    """Many-to-many relationship between rule sets and rules"""
    __tablename__ = "rule_set_memberships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_set_id = Column(UUID(as_uuid=True), ForeignKey("rule_sets.id"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False)
    
    # Membership configuration
    execution_order = Column(Integer, default=100)
    is_active = Column(Boolean, default=True, nullable=False)
    conditions = Column(JSONB)  # Conditions for when this rule applies in the set
    
    # Metadata
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    added_by_user_id = Column(UUID(as_uuid=True))
    
    # Relationships
    rule_set = relationship("RuleSet", back_populates="rule_memberships")
    rule = relationship("ComplianceRule")
    
    __table_args__ = (
        Index("idx_membership_ruleset_active", "rule_set_id", "is_active"),
        Index("idx_membership_execution_order", "execution_order"),
    )
    
    def __repr__(self):
        return f"<RuleSetMembership(rule_set_id='{self.rule_set_id}', rule_id='{self.rule_id}')>"


class RuleTemplate(Base):
    """Templates for creating common rule patterns"""
    __tablename__ = "rule_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Template definition
    rule_type = Column(String(50), nullable=False)
    template_schema = Column(JSONB, nullable=False)  # JSON schema for parameters
    rule_expression_template = Column(Text, nullable=False)  # Template with placeholders
    default_parameters = Column(JSONB)  # Default parameter values
    
    # Metadata
    category = Column(String(100), index=True)
    tags = Column(JSONB)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_template_type_active", "rule_type", "is_active"),
        Index("idx_template_category", "category"),
    )
    
    def __repr__(self):
        return f"<RuleTemplate(name='{self.name}', type='{self.rule_type}')>"


class RulePerformanceMetrics(Base):
    """Performance metrics for rule execution"""
    __tablename__ = "rule_performance_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Execution statistics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    
    # Performance metrics
    avg_execution_time_ms = Column(Numeric(10, 2))
    min_execution_time_ms = Column(Integer)
    max_execution_time_ms = Column(Integer)
    p95_execution_time_ms = Column(Integer)
    
    # Results distribution
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rule = relationship("ComplianceRule")
    
    __table_args__ = (
        Index("idx_metrics_rule_period", "rule_id", "period_start", "period_end"),
        Index("idx_metrics_period", "period_start", "period_end"),
    )
    
    def __repr__(self):
        return f"<RulePerformanceMetrics(rule_id='{self.rule_id}', executions={self.total_executions})>"