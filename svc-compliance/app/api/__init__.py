#!/usr/bin/env python3
"""
API router initialization for the Compliance Service

This module sets up the main FastAPI router for the compliance service.
"""

from fastapi import APIRouter

from .v1 import api_router as v1_router

# Create the main API router
api_router = APIRouter()

# Include version routers
api_router.include_router(
    v1_router,
    prefix="/api/v1",
    tags=["compliance"]
)