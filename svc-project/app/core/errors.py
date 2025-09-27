#!/usr/bin/env python3
"""
Uniform error handling for NextGen Fusion Platform

Provides consistent error responses with proper error envelopes and trace IDs.
"""

from typing import Optional, Dict, Any, List
from enum import Enum

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .logging import logger, get_request_id


class ErrorCode(str, Enum):
    """Standard error codes for the application"""
    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    
    # Business logic errors
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    MILESTONE_NOT_FOUND = "MILESTONE_NOT_FOUND"
    TEAM_MEMBER_NOT_FOUND = "TEAM_MEMBER_NOT_FOUND"
    INVALID_PROJECT_STATE = "INVALID_PROJECT_STATE"
    INVALID_TASK_DEPENDENCY = "INVALID_TASK_DEPENDENCY"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    
    # Cache errors
    CACHE_UNAVAILABLE = "CACHE_UNAVAILABLE"
    CACHE_TIMEOUT = "CACHE_TIMEOUT"
    
    # Idempotency errors
    INVALID_IDEMPOTENCY_KEY = "INVALID_IDEMPOTENCY_KEY"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    
    # External service errors
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"


class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response envelope"""
    code: str = Field(..., description="Error code identifying the type of error")
    message: str = Field(..., description="Human-readable error message")
    traceId: str = Field(..., description="Unique trace ID for request tracking")
    details: Optional[List[ErrorDetail]] = Field(None, description="Additional error details")
    timestamp: Optional[str] = Field(None, description="ISO timestamp when error occurred")
    path: Optional[str] = Field(None, description="API path where error occurred")


class AppException(Exception):
    """Base application exception with error code and details"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        status_code: int = 500
    ):
        self.code = code
        self.message = message
        self.details = details or []
        self.status_code = status_code
        super().__init__(message)


class ValidationException(AppException):
    """Exception for validation errors"""
    
    def __init__(self, message: str, details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
            status_code=400
        )


class NotFoundException(AppException):
    """Exception for resource not found errors"""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} with identifier '{identifier}' not found",
            status_code=404
        )


class ConflictException(AppException):
    """Exception for resource conflict errors"""
    
    def __init__(self, message: str, details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=message,
            details=details,
            status_code=409
        )


class DatabaseException(AppException):
    """Exception for database-related errors"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        # Determine specific error code based on the original error
        code = ErrorCode.DATABASE_CONNECTION_ERROR
        if original_error:
            error_str = str(original_error).lower()
            if "timeout" in error_str:
                code = ErrorCode.DATABASE_TIMEOUT
            elif "constraint" in error_str or "violation" in error_str:
                code = ErrorCode.CONSTRAINT_VIOLATION
                
        super().__init__(
            code=code,
            message=message,
            status_code=500
        )
        self.original_error = original_error


class CacheException(AppException):
    """Exception for cache-related errors"""
    
    def __init__(self, message: str, is_timeout: bool = False):
        code = ErrorCode.CACHE_TIMEOUT if is_timeout else ErrorCode.CACHE_UNAVAILABLE
        super().__init__(
            code=code,
            message=message,
            status_code=503
        )


class ExternalServiceException(AppException):
    """Exception for external service errors"""
    
    def __init__(self, service_name: str, message: str, is_timeout: bool = False):
        code = ErrorCode.EXTERNAL_SERVICE_TIMEOUT if is_timeout else ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE
        super().__init__(
            code=code,
            message=f"{service_name}: {message}",
            status_code=503
        )


def create_error_response(
    code: ErrorCode,
    message: str,
    status_code: int = 500,
    details: Optional[List[ErrorDetail]] = None,
    request: Optional[Request] = None
) -> JSONResponse:
    """Create a standardized error response"""
    from datetime import datetime
    
    trace_id = get_request_id() or "unknown"
    
    error_response = ErrorResponse(
        code=code.value,
        message=message,
        traceId=trace_id,
        details=details,
        timestamp=datetime.utcnow().isoformat() + "Z",
        path=str(request.url.path) if request else None
    )
    
    # Log the error
    logger.error(
        "API error response",
        error_code=code.value,
        message=message,
        status_code=status_code,
        trace_id=trace_id,
        path=error_response.path
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict(exclude_none=True)
    )


def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions"""
    return create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request=request
    )


def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    # Map HTTP status codes to error codes
    status_to_code = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        429: ErrorCode.TOO_MANY_REQUESTS,
        500: ErrorCode.INTERNAL_SERVER_ERROR
    }
    
    error_code = status_to_code.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)
    
    return create_error_response(
        code=error_code,
        message=exc.detail,
        status_code=exc.status_code,
        request=request
    )


def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors"""
    details = []
    
    # Extract validation error details if it's a Pydantic ValidationError
    if hasattr(exc, 'errors'):
        for error in exc.errors():
            field_path = '.'.join(str(loc) for loc in error.get('loc', []))
            details.append(ErrorDetail(
                field=field_path if field_path else None,
                message=error.get('msg', 'Validation error'),
                code=error.get('type')
            ))
    
    return create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="Validation failed",
        status_code=422,
        details=details if details else None,
        request=request
    )


def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    trace_id = get_request_id() or "unknown"
    
    # Log the full exception for debugging
    logger.exception(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        trace_id=trace_id,
        path=str(request.url.path)
    )
    
    return create_error_response(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        status_code=500,
        request=request
    )


# Utility functions for common error scenarios
def project_not_found(project_id: int) -> NotFoundException:
    """Create project not found exception"""
    return NotFoundException("Project", str(project_id))


def task_not_found(task_id: int) -> NotFoundException:
    """Create task not found exception"""
    return NotFoundException("Task", str(task_id))


def milestone_not_found(milestone_id: int) -> NotFoundException:
    """Create milestone not found exception"""
    return NotFoundException("Milestone", str(milestone_id))


def invalid_dependency(message: str) -> ValidationException:
    """Create invalid dependency exception"""
    return ValidationException(
        message=message,
        details=[ErrorDetail(message=message, code="INVALID_DEPENDENCY")]
    )


def circular_dependency_error(task_ids: List[int]) -> ConflictException:
    """Create circular dependency exception"""
    return ConflictException(
        message=f"Circular dependency detected involving tasks: {', '.join(map(str, task_ids))}",
        details=[ErrorDetail(
            message="Tasks cannot depend on themselves directly or indirectly",
            code="CIRCULAR_DEPENDENCY"
        )]
    )