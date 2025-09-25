"""API package for the Design Service.

Provides RESTful API endpoints for solar design, layout optimization,
shading analysis, and bill of materials management.
"""

from fastapi import APIRouter

from .v1 import api_router as v1_router


# Main API router
api_router = APIRouter()

# Include versioned API routes
api_router.include_router(v1_router, prefix="/v1")


__all__ = ["api_router"]