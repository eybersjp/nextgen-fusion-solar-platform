#!/usr/bin/env python3
"""
Core module for the Compliance Service

This module provides shared utilities, configuration, and database access
for the compliance service.
"""

from .config import get_settings
from .database import (
    get_db,
    create_tables,
    drop_tables,
    ComplianceRule,
    ComplianceValidation,
    ComplianceReport,
    ComplianceReportValidation,
    ComplianceAuditLog,
    ComplianceCache,
    ComplianceStatus,
    ViolationSeverity,
    RuleType,
    ReportStatus
)
from .logging import get_logger, audit_logger, setup_logging

__all__ = [
    # Configuration
    "get_settings",
    
    # Database
    "get_db",
    "create_tables",
    "drop_tables",
    
    # Models
    "ComplianceRule",
    "ComplianceValidation",
    "ComplianceReport",
    "ComplianceReportValidation",
    "ComplianceAuditLog",
    "ComplianceCache",
    
    # Enums
    "ComplianceStatus",
    "ViolationSeverity",
    "RuleType",
    "ReportStatus",
    
    # Logging
    "get_logger",
    "audit_logger",
    "setup_logging",
]