#!/usr/bin/env python3
"""
API v1 router initialization for Currency Service

This module sets up the main API router and includes all endpoint routers.
"""

from fastapi import APIRouter

from .currency import router as currency_router

# Create main API router
api_router = APIRouter()

# Include currency endpoints
api_router.include_router(
    currency_router,
    prefix="/currency",
    tags=["Currency"]
)