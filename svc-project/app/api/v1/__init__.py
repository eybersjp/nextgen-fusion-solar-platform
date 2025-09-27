#!/usr/bin/env python3
"""
API v1 router for the Project Management Service

This module initializes the API router for version 1 of the project management service.
"""

from fastapi import APIRouter

from .project import router as project_router

# Create the main v1 router
v1_router = APIRouter()

# Include sub-routers
v1_router.include_router(
    project_router,
    prefix="/project",
    tags=["Project Management"]
)

__all__ = ["v1_router"]