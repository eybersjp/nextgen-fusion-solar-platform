#!/usr/bin/env python3
"""
Core module for the Project Management Service

This module provides shared utilities, configuration, and database access
for the project management service.
"""

from .config import get_settings
from .database import (
    get_db, create_tables, drop_tables,
    Project, Task, Milestone, ProjectTeamMember, ProjectResource,
    TaskComment, TaskTimeLog, TaskDependency,
    ProjectStatus, TaskStatus, TaskPriority, MilestoneStatus,
    ResourceType, TeamRole
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
    "Project",
    "Task",
    "Milestone",
    "ProjectTeamMember",
    "ProjectResource",
    "TaskComment",
    "TaskTimeLog",
    "TaskDependency",
    
    # Enums
    "ProjectStatus",
    "TaskStatus",
    "TaskPriority",
    "MilestoneStatus",
    "ResourceType",
    "TeamRole",
    
    # Logging
    "get_logger",
    "audit_logger",
    "setup_logging",
]