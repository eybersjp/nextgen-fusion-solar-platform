#!/usr/bin/env python3
"""
Core module for the Currency Service.

Provides shared utilities, configuration, and database access.
"""

from .config import get_settings
from .database import get_db, create_tables, drop_tables
from .logging import get_logger, audit_logger, setup_logging

__all__ = [
    "get_settings",
    "get_db",
    "create_tables",
    "drop_tables",
    "get_logger",
    "audit_logger",
    "setup_logging"
]