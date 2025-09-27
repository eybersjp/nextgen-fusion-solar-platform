#!/usr/bin/env python3
"""
Main API router for the Project Management Service

This module initializes the main API router that includes all API versions.
"""

from fastapi import APIRouter

from .v1 import v1_router

# Create the main API router
api_router = APIRouter()

# Include version routers
api_router.include_router(
    v1_router,
    prefix="/v1"
)

__all__ = ["api_router"]