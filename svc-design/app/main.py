"""Main application module for the Design Service.

Initializes FastAPI application with middleware, routes,
and configuration for the solar design service.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from .core.config import get_settings
from .core.logging import setup_logging, get_logger
from .core.database import (
    init_database, 
    close_database_connections, 
    close_async_database_connections,
    check_database_connection
)
from .core.cache import cache_manager
from .core.middleware import setup_middleware
from .core.exceptions import DesignServiceException
from .api import api_router


# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Design Service...")
    
    try:
        # Initialize database
        init_database()
        logger.info("Database initialized")
        
        # Check database connection
        if not check_database_connection():
            logger.error("Database connection failed")
            raise Exception("Database connection failed")
        
        # Test cache connection
        cache_health = cache_manager.health_check()
        if cache_health.get('status') == 'healthy':
            logger.info("Cache connection established")
        else:
            logger.warning(f"Cache connection issues: {cache_health}")
        
        logger.info("Design Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Design Service: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Design Service...")
        
        try:
            # Close database connections
            close_database_connections()
            await close_async_database_connections()
            
            # Close cache connections
            cache_manager.close()
            
            logger.info("Design Service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="NextGen Fusion Design Service",
        description="Solar design and engineering service for commercial solar projects",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan
    )
    
    # Set up middleware
    setup_middleware(app)
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Add custom exception handlers
    setup_exception_handlers(app)
    
    # Add custom routes
    setup_custom_routes(app)
    
    return app


def setup_exception_handlers(app: FastAPI):
    """Set up custom exception handlers."""
    
    @app.exception_handler(DesignServiceException)
    async def design_service_exception_handler(
        request: Request, 
        exc: DesignServiceException
    ):
        """Handle custom design service exceptions."""
        logger.warning(
            f"Design service exception: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            f"HTTP exception: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "url": str(request.url)
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            f"Unexpected exception: {str(exc)}",
            extra={
                "url": str(request.url),
                "method": request.method
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": getattr(request.state, "request_id", None)
            }
        )


def setup_custom_routes(app: FastAPI):
    """Set up custom application routes."""
    
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint."""
        return {
            "service": "NextGen Fusion Design Service",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/api/v1/health"
        }
    
    @app.get("/info", tags=["Info"])
    async def service_info():
        """Service information endpoint."""
        settings = get_settings()
        
        return {
            "service": "design-service",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "features": {
                "solar_design": True,
                "layout_optimization": True,
                "shading_analysis": True,
                "bom_generation": True,
                "compliance_checking": True
            },
            "capabilities": {
                "max_panel_count": 10000,
                "supported_panel_types": ["monocrystalline", "polycrystalline", "thin_film"],
                "supported_inverter_types": ["string", "power_optimizer", "microinverter"],
                "analysis_types": ["shading", "soiling", "thermal", "electrical"]
            }
        }
    
    @app.get("/metrics", tags=["Monitoring"])
    async def metrics(request: Request):
        """Application metrics endpoint."""
        try:
            # Get metrics from middleware
            metrics_data = {}
            if hasattr(app.state, "metrics_middleware"):
                metrics_data = app.state.metrics_middleware.get_metrics()
            
            # Add database health
            from .core.database import database_health_check
            db_health = database_health_check()
            
            # Add cache health
            cache_health = cache_manager.health_check()
            
            return {
                "service": "design-service",
                "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
                "metrics": metrics_data,
                "health": {
                    "database": db_health.get("status", "unknown"),
                    "cache": cache_health.get("status", "unknown")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {
                "service": "design-service",
                "error": "Failed to collect metrics"
            }
    
    @app.get("/openapi-custom.json", include_in_schema=False)
    async def custom_openapi():
        """Custom OpenAPI schema with additional metadata."""
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="NextGen Fusion Design Service API",
            version="1.0.0",
            description="""
            # NextGen Fusion Design Service API
            
            This service provides comprehensive solar design and engineering capabilities
            for commercial solar projects, including:
            
            ## Features
            
            - **Solar System Design**: Create and manage solar panel layouts
            - **Shading Analysis**: Perform detailed shading calculations
            - **Bill of Materials**: Generate accurate component lists and pricing
            - **Layout Optimization**: Optimize panel placement for maximum efficiency
            - **Compliance Checking**: Validate designs against local regulations
            
            ## Authentication
            
            All endpoints require JWT authentication via the `Authorization` header:
            ```
            Authorization: Bearer <your-jwt-token>
            ```
            
            ## Rate Limiting
            
            API requests are rate limited to 60 requests per minute per user.
            
            ## Error Handling
            
            The API uses standard HTTP status codes and returns detailed error messages
            in JSON format with the following structure:
            ```json
            {
                "error": "Error description",
                "error_code": "SPECIFIC_ERROR_CODE",
                "details": {},
                "request_id": "unique-request-id"
            }
            ```
            """,
            routes=app.routes,
        )
        
        # Add custom metadata
        openapi_schema["info"]["contact"] = {
            "name": "NextGen Fusion Support",
            "email": "support@nextgenfusion.com",
            "url": "https://nextgenfusion.com/support"
        }
        
        openapi_schema["info"]["license"] = {
            "name": "Proprietary",
            "url": "https://nextgenfusion.com/license"
        }
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
        
        # Add global security requirement
        openapi_schema["security"] = [{"BearerAuth": []}]
        
        # Add tags
        openapi_schema["tags"] = [
            {
                "name": "Health",
                "description": "Service health and monitoring endpoints"
            },
            {
                "name": "Designs",
                "description": "Solar design project management"
            },
            {
                "name": "Layouts",
                "description": "Solar panel layout and configuration"
            },
            {
                "name": "Shading",
                "description": "Shading analysis and calculations"
            },
            {
                "name": "BOM",
                "description": "Bill of Materials and component management"
            }
        ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema


# Create the application instance
app = create_application()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
        access_log=True,
        server_header=False,
        date_header=False
    )