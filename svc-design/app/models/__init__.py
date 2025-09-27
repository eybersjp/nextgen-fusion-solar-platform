"""Models package for the Design Service.

This package contains all SQLAlchemy models for the application.
"""

from .base import BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin
from .user import User, UserSession
from .project import Project
from .solar import SolarDesign, SolarComponent, DesignCalculation

# Alias for backward compatibility
Base = BaseModel

__all__ = [
    "BaseModel",
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "User",
    "UserSession",
    "Project",
    "SolarDesign",
    "SolarComponent",
    "DesignCalculation",
]