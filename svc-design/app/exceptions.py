"""Custom exceptions for the application."""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception class for application-specific errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(AppException):
    """Raised when authorization fails."""
    pass


class ValidationError(AppException):
    """Raised when data validation fails."""
    pass


class NotFoundError(AppException):
    """Raised when a resource is not found."""
    pass


class ConflictError(AppException):
    """Raised when there's a conflict with existing data."""
    pass


class DatabaseError(AppException):
    """Raised when database operations fail."""
    pass


class ExternalServiceError(AppException):
    """Raised when external service calls fail."""
    pass


class RateLimitError(AppException):
    """Raised when rate limits are exceeded."""
    pass


class ConfigurationError(AppException):
    """Raised when configuration is invalid."""
    pass