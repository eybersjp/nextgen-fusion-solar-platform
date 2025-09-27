"""Design Service API Module

Provides REST API endpoints for the NextGen Fusion design service:
- Solar panel layout optimization
- 3D design visualization
- Performance analysis
- Compliance checking
"""

from fastapi import APIRouter
from .layout_optimization import router as layout_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(layout_router)

# Health check for the entire service
@api_router.get("/health")
async def service_health():
    """Overall service health check"""
    return {
        "service": "svc-design",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": [
            "/layout-optimization"
        ]
    }

__all__ = ["api_router