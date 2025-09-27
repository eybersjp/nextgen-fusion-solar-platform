#!/usr/bin/env python3
"""
API v1 router initialization for the Compliance Service

This module sets up the FastAPI router for version 1 of the compliance API.
"""

from fastapi import APIRouter

from .compliance import router as compliance_router

# Create the main v1 API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    compliance_router,
    prefix="/compliance",
    tags=["Compliance"]
)