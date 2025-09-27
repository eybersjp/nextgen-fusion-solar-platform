"""API v1 package for the Design Service.

Version 1 of the RESTful API endpoints for solar design services.
"""

from fastapi import APIRouter

from .health import router as health_router
from .auth import router as auth_router
from .projects import router as projects_router
from .solar import router as solar_router
from .designs import router as designs_router
from .design_3d import router as design_3d_router
from .layouts import router as layouts_router
from .shading import router as shading_router
from .bom import router as bom_router


# API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects_router, prefix="/projects", tags=["Projects"])
api_router.include_router(solar_router, prefix="/solar", tags=["Solar Design"])
api_router.include_router(designs_router, prefix="/designs", tags=["Designs"])
api_router.include_router(design_3d_router, prefix="/design", tags=["3D Design"])
api_router.include_router(layouts_router, prefix="/layouts", tags=["Layouts"])
api_router.include_router(shading_router, prefix="/shading", tags=["Shading"])
api_router.include_router(bom_router, prefix="/bom", tags=["BOM"])


__all__ = ["api_router"]