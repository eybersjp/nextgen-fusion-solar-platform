#!/usr/bin/env python3
"""
Database configuration and models for the Compliance Service

This module defines SQLAlchemy models for compliance-related data
and provides database session management. Enhanced with multi-tenant
connection pooling and performance optimization.
"""

import uuid
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, AsyncGenerator
from decimal import Decimal
from enum import Enum
import logging

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .config import get_settings

# Add shared module to path for enhanced pooling
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

# Try to import enhanced pooling system
try:
    from database import (
        ServiceType, ServiceDatabaseManager, 
        get_service_db_manager, initialize_service_database
    )
    ENHANCED_POOLING_AVAILABLE = True
except ImportError:
    ENHANCED_POOLING_AVAILABLE = False

logger = logging.getLogger(__name__)
settings = get_settings()

# Global variables for database components
_engine = None
_session_factory = None
_service_manager = None


def init_database(tenant_id: Optional[str] = None) -> None:
    """Initialize database with enhanced pooling support.
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant isolation
    """
    global _engine, _session_factory, _service_manager
    
    if ENHANCED_POOLING_AVAILABLE:
        # Use enhanced pooling system
        _service_manager = initialize_service_database(
            service_type=ServiceType.COMPLIANCE,
            database_url=settings.DATABASE_URL,
            tenant_id=tenant_id
        )
        _engine = _service_manager.get_async_engine(tenant_id)
        _session_factory = _service_manager.get_async_session_factory(tenant_id)
    else:
        # Fallback to legacy pooling
        if "sqlite" in settings.DATABASE_URL:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO
            )
        else:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.DATABASE_ECHO,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW
            )
        
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False
        )


def get_engine() -> create_async_engine:
    """Get the database engine."""
    if _engine is None:
        init_database()
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Get the session factory."""
    if _session_factory is None:
        init_database()
    return _session_factory


# Legacy compatibility
engine = get_engine()
AsyncSessionLocal = get_session_factory()

# Create declarative base
Base = declarative_base()


# Enums
class ComplianceStatus(str, Enum):
    """Compliance validation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_REVIEW = "requires_review"
    EXPIRED = "expired"


class ViolationSeverity(str, Enum):
    """Compliance violation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RuleType(str, Enum):
    """Types of compliance rules."""
    BUILDING_CODE = "building_code"
    ELECTRICAL_CODE = "electrical_code"
    SAFETY_STANDARD = "safety_standard"
    ENVIRONMENTAL = "environmental"
    ZONING = "zoning"
    FIRE_SAFETY = "fire_safety"
    STRUCTURAL = "structural"
    ACCESSIBILITY = "accessibility"


class ReportStatus(str, Enum):
    """Compliance report status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# Database Models
class ComplianceRule(Base):
    """Compliance rules for different regions and standards."""
    __tablename__ = "compliance_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_code = Column(String(50), nullable=False, index=True)
    rule_name = Column(String(200), nullable=False)
    rule_type = Column(SQLEnum(RuleType), nullable=False, index=True)
    region = Column(String(10), nullable=False, index=True)
    standard = Column(String(50), nullable=False, index=True)
    
    description = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=False)  # Structured requirements
    validation_logic = Column(JSON, nullable=False)  # Validation rules
    
    severity = Column(SQLEnum(ViolationSeverity), nullable=False, default=ViolationSeverity.ERROR)
    is_mandatory = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    effective_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    
    # Relationships
    validations = relationship("ComplianceValidation", back_populates="rule")
    
    # Indexes
    __table_args__ = (
        Index("idx_compliance_rules_region_type", "region", "rule_type"),
        Index("idx_compliance_rules_standard_active", "standard", "is_active"),
        UniqueConstraint("rule_code", "region", "standard", name="uq_rule_code_region_standard"),
    )


class ComplianceValidation(Base):
    """Compliance validation records for projects/designs."""
    __tablename__ = "compliance_validations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(100), nullable=False, index=True)
    design_id = Column(String(100), nullable=True, index=True)
    rule_id = Column(String, ForeignKey("compliance_rules.id"), nullable=False)
    
    validation_data = Column(JSON, nullable=False)  # Input data for validation
    validation_result = Column(JSON, nullable=False)  # Detailed validation results
    
    status = Column(SQLEnum(ComplianceStatus), nullable=False, default=ComplianceStatus.PENDING)
    compliance_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    violations = Column(JSON, nullable=True)  # List of violations found
    recommendations = Column(JSON, nullable=True)  # Recommendations for compliance
    
    validated_at = Column(DateTime, nullable=True)
    validated_by = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rule = relationship("ComplianceRule", back_populates="validations")
    reports = relationship("ComplianceReport", secondary="compliance_report_validations", back_populates="validations")
    
    # Indexes
    __table_args__ = (
        Index("idx_compliance_validations_project", "project_id"),
        Index("idx_compliance_validations_design", "design_id"),
        Index("idx_compliance_validations_status", "status"),
        Index("idx_compliance_validations_score", "compliance_score"),
    )


class ComplianceReport(Base):
    """Compliance reports for projects."""
    __tablename__ = "compliance_reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(100), nullable=False, index=True)
    report_name = Column(String(200), nullable=False)
    report_type = Column(String(50), nullable=False)  # e.g., "full", "summary", "custom"
    
    region = Column(String(10), nullable=False)
    standards = Column(JSON, nullable=False)  # List of standards covered
    
    overall_status = Column(SQLEnum(ComplianceStatus), nullable=False)
    overall_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    summary = Column(JSON, nullable=False)  # Report summary data
    detailed_results = Column(JSON, nullable=False)  # Detailed compliance results
    
    violations_count = Column(Integer, nullable=False, default=0)
    critical_violations_count = Column(Integer, nullable=False, default=0)
    warnings_count = Column(Integer, nullable=False, default=0)
    
    report_status = Column(SQLEnum(ReportStatus), nullable=False, default=ReportStatus.DRAFT)
    
    file_path = Column(String(500), nullable=True)  # Path to generated report file
    file_size = Column(Integer, nullable=True)  # File size in bytes
    
    generated_at = Column(DateTime, nullable=True)
    generated_by = Column(String(100), nullable=True)
    
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    validations = relationship("ComplianceValidation", secondary="compliance_report_validations", back_populates="reports")
    
    # Indexes
    __table_args__ = (
        Index("idx_compliance_reports_project", "project_id"),
        Index("idx_compliance_reports_status", "report_status"),
        Index("idx_compliance_reports_region", "region"),
        Index("idx_compliance_reports_score", "overall_score"),
    )


class ComplianceReportValidation(Base):
    """Association table for compliance reports and validations."""
    __tablename__ = "compliance_report_validations"
    
    report_id = Column(String, ForeignKey("compliance_reports.id"), primary_key=True)
    validation_id = Column(String, ForeignKey("compliance_validations.id"), primary_key=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ComplianceAuditLog(Base):
    """Audit log for compliance-related activities."""
    __tablename__ = "compliance_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)  # e.g., "validation", "report", "rule"
    resource_id = Column(String(100), nullable=False, index=True)
    
    user_id = Column(String(100), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    
    details = Column(JSON, nullable=True)  # Additional action details
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_compliance_audit_logs_action", "action"),
        Index("idx_compliance_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_compliance_audit_logs_user", "user_id"),
        Index("idx_compliance_audit_logs_timestamp", "timestamp"),
    )


class ComplianceCache(Base):
    """Cache for compliance validation results."""
    __tablename__ = "compliance_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    cache_key = Column(String(255), nullable=False, unique=True, index=True)
    cache_data = Column(JSON, nullable=False)
    
    expires_at = Column(DateTime, nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_compliance_cache_key", "cache_key"),
        Index("idx_compliance_cache_expires", "expires_at"),
    )


# Database session management
async def get_db(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """Get database session with optional tenant isolation.
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant sessions
        
    Yields:
        AsyncSession: Database session
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager and tenant_id:
        # Use enhanced pooling with tenant isolation
        async with _service_manager.get_async_session(tenant_id) as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
    else:
        # Use standard session factory
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


async def get_db_session(tenant_id: Optional[str] = None) -> AsyncSession:
    """Get a single database session (not a generator).
    
    Args:
        tenant_id: Optional tenant identifier for multi-tenant sessions
        
    Returns:
        AsyncSession: Database session
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager and tenant_id:
        return _service_manager.get_async_session(tenant_id)
    else:
        session_factory = get_session_factory()
        return session_factory()


async def check_database_health(tenant_id: Optional[str] = None) -> dict:
    """Check database health with optional tenant context.
    
    Args:
        tenant_id: Optional tenant identifier
        
    Returns:
        dict: Health check results
    """
    if ENHANCED_POOLING_AVAILABLE and _service_manager:
        return await _service_manager.health_check(tenant_id)
    else:
        # Basic health check
        try:
            async with get_db_session(tenant_id) as session:
                await session.execute("SELECT 1")
            return {"status": "healthy", "tenant_id": tenant_id}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "tenant_id": tenant_id}


async def create_tables(tenant_id: Optional[str] = None):
    """Create all database tables.
    
    Args:
        tenant_id: Optional tenant identifier
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def drop_tables(tenant_id: Optional[str] = None):
    """Drop all database tables.
    
    Args:
        tenant_id: Optional tenant identifier
        
    Warning: This will delete all data!
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


async def close_database_connections():
    """Close all database connections and dispose engines."""
    global _engine, _session_factory, _service_manager
    
    try:
        if ENHANCED_POOLING_AVAILABLE and _service_manager:
            await _service_manager.close_all_connections()
        elif _engine:
            await _engine.dispose()
        
        # Reset global variables
        _engine = None
        _session_factory = None
        _service_manager = None
        
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")