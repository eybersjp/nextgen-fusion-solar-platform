"""Core module for the Design Service.

This module contains core functionality including database configuration,
security, logging, and other shared utilities.
"""

from .database import get_db
from .auth import get_current_user, AuthenticationError
from ..models.user import User
from .config import settings

# Placeholder imports for missing dependencies
# These will need to be implemented later
class RequireDesignRead:
    """Placeholder for design read permission dependency"""
    pass

class RequireDesignWrite:
    """Placeholder for design write permission dependency"""
    pass

class RequireDesignDelete:
    """Placeholder for design delete permission dependency"""
    pass

class RequireDesignApprove:
    """Placeholder for design approve permission dependency"""
    pass

class RequireLayoutRead:
    """Placeholder for layout read permission dependency"""
    pass

class RequireLayoutWrite:
    """Placeholder for layout write permission dependency"""
    pass

class RequireLayoutDelete:
    """Placeholder for layout delete permission dependency"""
    pass

class RequireLayoutApprove:
    """Placeholder for layout approve permission dependency"""
    pass

class RequireLayoutOptimize:
    """Placeholder for layout optimize permission dependency"""
    pass

class RequireShadingRead:
    """Placeholder for shading read permission dependency"""
    pass

class RequireShadingWrite:
    """Placeholder for shading write permission dependency"""
    pass

class RequireShadingDelete:
    """Placeholder for shading delete permission dependency"""
    pass

class RequireBOMRead:
    """Placeholder for BOM read permission dependency"""
    pass

class RequireBOMWrite:
    """Placeholder for BOM write permission dependency"""
    pass

class RequireBOMDelete:
    """Placeholder for BOM delete permission dependency"""
    pass

def get_logger(name: str):
    """Get logger instance"""
    from loguru import logger
    return logger

class DesignError(Exception):
    """Base design error"""
    pass

class DesignNotFoundError(DesignError):
    """Design not found error"""
    pass

class DesignValidationError(DesignError):
    """Design validation error"""
    pass

class DesignPermissionError(DesignError):
    """Design permission error"""
    pass

class LayoutError(Exception):
    """Base exception for layout operations"""
    pass

class LayoutNotFoundError(Exception):
    """Raised when layout is not found"""
    pass

class LayoutValidationError(Exception):
    """Raised when layout validation fails"""
    pass

class LayoutOptimizationError(Exception):
    """Raised when layout optimization fails"""
    pass

__all__ = [
    "get_db",
    "get_current_user", 
    "User",
    "AuthenticationError",
    "settings",
    "RequireDesignRead",
    "RequireDesignWrite",
    "RequireDesignDelete",
    "RequireDesignApprove",
    "RequireLayoutRead",
    "RequireLayoutWrite",
    "RequireLayoutDelete",
    "RequireLayoutApprove",
    "RequireLayoutOptimize",
    "RequireShadingRead",
    "RequireShadingWrite",
    "RequireShadingDelete",
    "RequireBOMRead",
    "RequireBOMWrite",
    "RequireBOMDelete",
    "get_logger",
    "DesignError",
    "DesignNotFoundError",
    "DesignValidationError",
    "DesignPermissionError",
    "LayoutError",
    "LayoutNotFoundError",
    "LayoutValidationError",
    "LayoutOptimizationError"
]