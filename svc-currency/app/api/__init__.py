#!/usr/bin/env python3
"""
API package initialization for Currency Service

This module provides the main API router that includes all API versions.
"""

from fastapi import APIRouter

from .v1 import api_router as v1_router

# Create main API router
api_router = APIRouter()

# Include v1 API routes
api_router.include_router(
    v1_router,
    prefix="/v1"
)