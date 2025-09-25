"""Logging configuration for the Design Service.

Provides structured logging with JSON format,
request tracing, and observability features.
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import uuid4

from pythonjsonlogger import jsonlogger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings


# Context variables for request tracing
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
organization_id_var: ContextVar[Optional[str]] = ContextVar('organization_id', default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = time.time()
        log_record['iso_timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime())
        
        # Add service information
        log_record['service'] = 'design-service'
        log_record['version'] = get_settings().APP_VERSION
        log_record['environment'] = get_settings().ENVIRONMENT
        
        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_record['request_id'] = request_id
        
        user_id = user_id_var.get()
        if user_id:
            log_record['user_id'] = user_id
        
        organization_id = organization_id_var.get()
        if organization_id:
            log_record['organization_id'] = organization_id
        
        # Add log level as string
        log_record['level'] = record.levelname
        
        # Add module and function information
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add thread and process information
        log_record['thread_id'] = record.thread
        log_record['process_id'] = record.process


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid4())
        request_id_var.set(request_id)
        
        # Extract user information from request if available
        user_id = getattr(request.state, 'user_id', None)
        organization_id = getattr(request.state, 'organization_id', None)
        
        if user_id:
            user_id_var.set(user_id)
        if organization_id:
            organization_id_var.set(organization_id)
        
        # Log request start
        start_time = time.time()
        logger = logging.getLogger(__name__)
        
        logger.info(
            "Request started",
            extra={
                "event": "request_started",
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length"),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    "event": "request_completed",
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "response_headers": dict(response.headers),
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "event": "request_failed",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise
        
        finally:
            # Clear context variables
            request_id_var.set(None)
            user_id_var.set(None)
            organization_id_var.set(None)


def setup_logging() -> None:
    """Configure logging for the application."""
    settings = get_settings()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Configure formatter based on log format
    if settings.LOG_FORMAT.lower() == "json":
        formatter = CustomJsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_logger_levels()
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "event": "logging_configured",
            "log_level": settings.LOG_LEVEL,
            "log_format": settings.LOG_FORMAT,
            "log_file": settings.LOG_FILE,
        }
    )


def configure_logger_levels() -> None:
    """Configure log levels for specific loggers."""
    settings = get_settings()
    
    # Set levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Set debug level for our application in development
    if settings.DEBUG:
        logging.getLogger("app").setLevel(logging.DEBUG)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        logging.getLogger("app").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(f"app.{name}")


def log_function_call(func_name: str, args: Dict[str, Any] = None, **kwargs) -> None:
    """Log function call with parameters."""
    logger = get_logger("function_calls")
    
    extra_data = {
        "event": "function_called",
        "function": func_name,
    }
    
    if args:
        extra_data["args"] = args
    
    if kwargs:
        extra_data.update(kwargs)
    
    logger.debug(f"Function {func_name} called", extra=extra_data)


def log_database_operation(operation: str, table: str, **kwargs) -> None:
    """Log database operation."""
    logger = get_logger("database")
    
    extra_data = {
        "event": "database_operation",
        "operation": operation,
        "table": table,
    }
    
    if kwargs:
        extra_data.update(kwargs)
    
    logger.debug(f"Database {operation} on {table}", extra=extra_data)


def log_external_service_call(service: str, endpoint: str, method: str = "GET", **kwargs) -> None:
    """Log external service call."""
    logger = get_logger("external_services")
    
    extra_data = {
        "event": "external_service_call",
        "service": service,
        "endpoint": endpoint,
        "method": method,
    }
    
    if kwargs:
        extra_data.update(kwargs)
    
    logger.info(f"Calling {service} {method} {endpoint}", extra=extra_data)


def log_calculation_start(calculation_type: str, **kwargs) -> None:
    """Log calculation start."""
    logger = get_logger("calculations")
    
    extra_data = {
        "event": "calculation_started",
        "calculation_type": calculation_type,
        "start_time": time.time(),
    }
    
    if kwargs:
        extra_data.update(kwargs)
    
    logger.info(f"Starting {calculation_type} calculation", extra=extra_data)


def log_calculation_end(calculation_type: str, duration: float, success: bool = True, **kwargs) -> None:
    """Log calculation end."""
    logger = get_logger("calculations")
    
    extra_data = {
        "event": "calculation_completed" if success else "calculation_failed",
        "calculation_type": calculation_type,
        "duration_ms": round(duration * 1000, 2),
        "success": success,
    }
    
    if kwargs:
        extra_data.update(kwargs)
    
    if success:
        logger.info(f"Completed {calculation_type} calculation", extra=extra_data)
    else:
        logger.error(f"Failed {calculation_type} calculation", extra=extra_data)


def log_business_event(event_type: str, entity_type: str, entity_id: str, **kwargs) -> None:
    """Log business event."""
    logger = get_logger("business_events")
    
    extra_data = {
        "event": "business_event",
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
    }
    
    if kwargs:
        extra_data.update(kwargs)
    
    logger.info(f"{event_type} {entity_type} {entity_id}", extra=extra_data)


def log_security_event(event_type: str, user_id: str = None, **kwargs) -> None:
    """Log security event."""
    logger = get_logger("security")
    
    extra_data = {
        "event": "security_event",
        "event_type": event_type,
    }
    
    if user_id:
        extra_data["user_id"] = user_id
    
    if kwargs:
        extra_data.update(kwargs)
    
    logger.warning(f"Security event: {event_type}", extra=extra_data)


def log_performance_metric(metric_name: str, value: float, unit: str = "ms", **kwargs) -> None:
    """Log performance metric."""
    logger = get_logger("performance")
    
    extra_data = {
        "event": "performance_metric",
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
    }
    
    if kwargs:
        extra_data.update(kwargs)
    
    logger.info(f"Performance metric: {metric_name} = {value} {unit}", extra=extra_data)


class LoggingContext:
    """Context manager for adding extra logging context."""
    
    def __init__(self, **context):
        self.context = context
        self.original_values = {}
    
    def __enter__(self):
        # Store original values
        for key, value in self.context.items():
            if key == 'request_id':
                self.original_values[key] = request_id_var.get()
                request_id_var.set(value)
            elif key == 'user_id':
                self.original_values[key] = user_id_var.get()
                user_id_var.set(value)
            elif key == 'organization_id':
                self.original_values[key] = organization_id_var.get()
                organization_id_var.set(value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original values
        for key, value in self.original_values.items():
            if key == 'request_id':
                request_id_var.set(value)
            elif key == 'user_id':
                user_id_var.set(value)
            elif key == 'organization_id':
                organization_id_var.set(value)


def with_logging_context(**context):
    """Decorator for adding logging context to functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with LoggingContext(**context):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def set_request_id(request_id: str) -> None:
    """Set the request ID in the current context."""
    request_id_var.set(request_id)


def set_user_id(user_id: str) -> None:
    """Set the user ID in the current context."""
    user_id_var.set(user_id)


def set_organization_id(organization_id: str) -> None:
    """Set the organization ID in the current context."""
    organization_id_var.set(organization_id)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


def get_user_id() -> Optional[str]:
    """Get the current user ID from context."""
    return user_id_var.get()


def get_organization_id() -> Optional[str]:
    """Get the current organization ID from context."""
    return organization_id_var.get()