#!/usr/bin/env python3
"""
Logging configuration for the Compliance Service

This module sets up structured logging with JSON format for production
and human-readable format for development.
"""

import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import uuid

import structlog
from structlog.stdlib import LoggerFactory

from .config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT == "production" 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper())
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DATABASE_ECHO else logging.WARNING
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


class ComplianceAuditLogger:
    """Specialized logger for compliance audit trails."""
    
    def __init__(self):
        self.logger = get_logger("compliance.audit")
    
    def log_validation_started(
        self,
        validation_id: str,
        project_id: str,
        rule_id: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log compliance validation start."""
        self.logger.info(
            "Compliance validation started",
            validation_id=validation_id,
            project_id=project_id,
            rule_id=rule_id,
            user_id=user_id,
            action="validation_started",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_validation_completed(
        self,
        validation_id: str,
        project_id: str,
        rule_id: str,
        status: str,
        compliance_score: Optional[float] = None,
        violations_count: int = 0,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log compliance validation completion."""
        self.logger.info(
            "Compliance validation completed",
            validation_id=validation_id,
            project_id=project_id,
            rule_id=rule_id,
            status=status,
            compliance_score=compliance_score,
            violations_count=violations_count,
            user_id=user_id,
            action="validation_completed",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_validation_failed(
        self,
        validation_id: str,
        project_id: str,
        rule_id: str,
        error: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log compliance validation failure."""
        self.logger.error(
            "Compliance validation failed",
            validation_id=validation_id,
            project_id=project_id,
            rule_id=rule_id,
            error=error,
            user_id=user_id,
            action="validation_failed",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_report_generated(
        self,
        report_id: str,
        project_id: str,
        report_type: str,
        overall_status: str,
        overall_score: Optional[float] = None,
        violations_count: int = 0,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log compliance report generation."""
        self.logger.info(
            "Compliance report generated",
            report_id=report_id,
            project_id=project_id,
            report_type=report_type,
            overall_status=overall_status,
            overall_score=overall_score,
            violations_count=violations_count,
            user_id=user_id,
            action="report_generated",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_report_approved(
        self,
        report_id: str,
        project_id: str,
        approved_by: str,
        **kwargs
    ) -> None:
        """Log compliance report approval."""
        self.logger.info(
            "Compliance report approved",
            report_id=report_id,
            project_id=project_id,
            approved_by=approved_by,
            action="report_approved",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_rule_created(
        self,
        rule_id: str,
        rule_code: str,
        rule_type: str,
        region: str,
        standard: str,
        created_by: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log compliance rule creation."""
        self.logger.info(
            "Compliance rule created",
            rule_id=rule_id,
            rule_code=rule_code,
            rule_type=rule_type,
            region=region,
            standard=standard,
            created_by=created_by,
            action="rule_created",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_rule_updated(
        self,
        rule_id: str,
        rule_code: str,
        changes: Dict[str, Any],
        updated_by: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log compliance rule update."""
        self.logger.info(
            "Compliance rule updated",
            rule_id=rule_id,
            rule_code=rule_code,
            changes=changes,
            updated_by=updated_by,
            action="rule_updated",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_rule_deactivated(
        self,
        rule_id: str,
        rule_code: str,
        reason: str,
        deactivated_by: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log compliance rule deactivation."""
        self.logger.warning(
            "Compliance rule deactivated",
            rule_id=rule_id,
            rule_code=rule_code,
            reason=reason,
            deactivated_by=deactivated_by,
            action="rule_deactivated",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log security-related events."""
        self.logger.warning(
            "Security event detected",
            event_type=event_type,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action="security_event",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_data_access(
        self,
        resource_type: str,
        resource_id: str,
        access_type: str,  # "read", "write", "delete"
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log data access for compliance tracking."""
        self.logger.info(
            "Data access logged",
            resource_type=resource_type,
            resource_id=resource_id,
            access_type=access_type,
            user_id=user_id,
            action="data_access",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        success: bool,
        **kwargs
    ) -> None:
        """Log performance metrics for compliance operations."""
        self.logger.info(
            "Performance metric recorded",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            action="performance_metric",
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )


# Global audit logger instance
audit_logger = ComplianceAuditLogger()