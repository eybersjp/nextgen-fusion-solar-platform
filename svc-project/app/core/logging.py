#!/usr/bin/env python3
"""
Logging configuration for the Project Management Service

This module sets up structured logging with JSON format for production
and human-readable format for development.
"""

import logging
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from functools import lru_cache
from contextvars import ContextVar

import structlog
from structlog.stdlib import LoggerFactory
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

from .config import get_settings

settings = get_settings()

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
tenant_id_var: ContextVar[str] = ContextVar('tenant_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')


def add_request_context(logger, method_name, event_dict):
    """Add request context to log entries."""
    request_id = request_id_var.get()
    tenant_id = tenant_id_var.get()
    user_id = user_id_var.get()
    
    if request_id:
        event_dict['request_id'] = request_id
    if tenant_id:
        event_dict['tenant_id'] = tenant_id
    if user_id:
        event_dict['user_id'] = user_id
    
    return event_dict


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track requests and add context for logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Extract tenant ID from headers or path
        tenant_id = request.headers.get('X-Tenant-ID', '')
        if not tenant_id and hasattr(request.state, 'tenant_id'):
            tenant_id = request.state.tenant_id
        tenant_id_var.set(tenant_id)
        
        # Extract user ID from headers or auth context
        user_id = request.headers.get('X-User-ID', '')
        if not user_id and hasattr(request.state, 'user_id'):
            user_id = request.state.user_id
        user_id_var.set(user_id)
        
        # Add request ID to response headers
        start_time = time.time()
        
        try:
            response = await call_next(request)
            response.headers['X-Request-ID'] = request_id
            
            # Log request completion
            duration_ms = (time.time() - start_time) * 1000
            logger = get_logger('request')
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                user_agent=request.headers.get('User-Agent', ''),
                client_ip=request.client.host if request.client else ''
            )
            
            return response
            
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger = get_logger('request')
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                error_type=type(exc).__name__,
                user_agent=request.headers.get('User-Agent', ''),
                client_ip=request.client.host if request.client else ''
            )
            raise


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    if settings.LOG_FORMAT == "json":
        # JSON logging for production
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                add_request_context,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # Human-readable logging for development
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                add_request_context,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer(colors=True)
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
    
    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


@lru_cache()
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


class ProjectAuditLogger:
    """Specialized logger for project management audit trails."""
    
    def __init__(self):
        self.logger = get_logger("project_audit")
    
    def log_project_created(self, project_id: int, project_name: str, created_by: str, **kwargs):
        """Log project creation event."""
        self.logger.info(
            "Project created",
            event_type="project_created",
            project_id=project_id,
            project_name=project_name,
            created_by=created_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_project_updated(self, project_id: int, updated_by: str, changes: Dict[str, Any], **kwargs):
        """Log project update event."""
        self.logger.info(
            "Project updated",
            event_type="project_updated",
            project_id=project_id,
            updated_by=updated_by,
            changes=changes,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_project_deleted(self, project_id: int, deleted_by: str, **kwargs):
        """Log project deletion event."""
        self.logger.warning(
            "Project deleted",
            event_type="project_deleted",
            project_id=project_id,
            deleted_by=deleted_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_task_created(self, task_id: int, project_id: int, task_title: str, created_by: str, **kwargs):
        """Log task creation event."""
        self.logger.info(
            "Task created",
            event_type="task_created",
            task_id=task_id,
            project_id=project_id,
            task_title=task_title,
            created_by=created_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_task_updated(self, task_id: int, project_id: int, updated_by: str, changes: Dict[str, Any], **kwargs):
        """Log task update event."""
        self.logger.info(
            "Task updated",
            event_type="task_updated",
            task_id=task_id,
            project_id=project_id,
            updated_by=updated_by,
            changes=changes,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_task_assigned(self, task_id: int, project_id: int, assigned_to: str, assigned_by: str, **kwargs):
        """Log task assignment event."""
        self.logger.info(
            "Task assigned",
            event_type="task_assigned",
            task_id=task_id,
            project_id=project_id,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_task_completed(self, task_id: int, project_id: int, completed_by: str, **kwargs):
        """Log task completion event."""
        self.logger.info(
            "Task completed",
            event_type="task_completed",
            task_id=task_id,
            project_id=project_id,
            completed_by=completed_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_milestone_created(self, milestone_id: int, project_id: int, milestone_name: str, created_by: str, **kwargs):
        """Log milestone creation event."""
        self.logger.info(
            "Milestone created",
            event_type="milestone_created",
            milestone_id=milestone_id,
            project_id=project_id,
            milestone_name=milestone_name,
            created_by=created_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_milestone_completed(self, milestone_id: int, project_id: int, completed_by: str, **kwargs):
        """Log milestone completion event."""
        self.logger.info(
            "Milestone completed",
            event_type="milestone_completed",
            milestone_id=milestone_id,
            project_id=project_id,
            completed_by=completed_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_team_member_added(self, project_id: int, user_id: str, role: str, added_by: str, **kwargs):
        """Log team member addition event."""
        self.logger.info(
            "Team member added",
            event_type="team_member_added",
            project_id=project_id,
            user_id=user_id,
            role=role,
            added_by=added_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_team_member_removed(self, project_id: int, user_id: str, removed_by: str, **kwargs):
        """Log team member removal event."""
        self.logger.info(
            "Team member removed",
            event_type="team_member_removed",
            project_id=project_id,
            user_id=user_id,
            removed_by=removed_by,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_resource_allocated(self, resource_id: int, project_id: int, allocated_by: str, allocation_details: Dict[str, Any], **kwargs):
        """Log resource allocation event."""
        self.logger.info(
            "Resource allocated",
            event_type="resource_allocated",
            resource_id=resource_id,
            project_id=project_id,
            allocated_by=allocated_by,
            allocation_details=allocation_details,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_time_logged(self, task_id: int, project_id: int, user_id: str, hours: float, **kwargs):
        """Log time tracking event."""
        self.logger.info(
            "Time logged",
            event_type="time_logged",
            task_id=task_id,
            project_id=project_id,
            user_id=user_id,
            hours=hours,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_security_event(self, event_type: str, user_id: Optional[str], details: Dict[str, Any], **kwargs):
        """Log security-related events."""
        self.logger.warning(
            f"Security event: {event_type}",
            event_type=f"security_{event_type}",
            user_id=user_id,
            details=details,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_data_access(self, user_id: str, resource_type: str, resource_id: int, action: str, **kwargs):
        """Log data access events for compliance."""
        self.logger.info(
            "Data access",
            event_type="data_access",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )


# Global audit logger instance
audit_logger = ProjectAuditLogger()


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


def get_tenant_id() -> str:
    """Get the current tenant ID from context."""
    return tenant_id_var.get()


def get_user_id() -> str:
    """Get the current user ID from context."""
    return user_id_var.get()


def log_database_operation(operation: str, table: str, record_id: Optional[int] = None, 
                          duration_ms: Optional[float] = None, error: Optional[str] = None):
    """Log database operations with context."""
    logger = get_logger('database')
    
    log_data = {
        'operation': operation,
        'table': table,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if record_id is not None:
        log_data['record_id'] = record_id
    if duration_ms is not None:
        log_data['duration_ms'] = round(duration_ms, 2)
    if error:
        log_data['error'] = error
        logger.error(f"Database operation failed: {operation} on {table}", **log_data)
    else:
        logger.info(f"Database operation: {operation} on {table}", **log_data)


def log_cache_operation(operation: str, cache_key: str, hit: bool = False, 
                       duration_ms: Optional[float] = None):
    """Log cache operations."""
    logger = get_logger('cache')
    
    log_data = {
        'operation': operation,
        'cache_key': cache_key,
        'cache_hit': hit,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if duration_ms is not None:
        log_data['duration_ms'] = round(duration_ms, 2)
    
    logger.info(f"Cache operation: {operation}", **log_data)


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = 'warning'):
    """Log security events with proper context."""
    logger = get_logger('security')
    
    log_data = {
        'event_type': event_type,
        'severity': severity,
        'details': details,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if severity == 'critical':
        logger.critical(f"Security event: {event_type}", **log_data)
    elif severity == 'error':
        logger.error(f"Security event: {event_type}", **log_data)
    else:
        logger.warning(f"Security event: {event_type}", **log_data)