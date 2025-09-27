#!/usr/bin/env python3
"""
NextGen Fusion Commercial Solar Platform - Design Service
Handles solar system design, layout optimization, shading analysis, and BoM generation
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.core.database import get_engine, get_async_engine, get_db
from app.core.cache import initialize_design_cache, close_design_cache, check_design_cache_health
from app.core.auth import get_current_user
from app.api.v1 import design, layout, shading, bom
from app.models import Base

# Metrics
REQUEST_COUNT = Counter('design_service_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('design_service_request_duration_seconds', 'Request duration')


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    timestamp: str
    database: str
    cache: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Design Service...")
    
    # Initialize Redis caching
    try:
        await initialize_design_cache()
        logger.info("Redis caching initialized successfully")
    except Exception as e:
        logger.warning(f"Redis caching initialization failed: {e}")
    
    # Create database tables
    async_engine = get_async_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Design Service started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down Design Service...")
    
    # Close Redis connections
    try:
        await close_design_cache()
        logger.info("Redis caching closed successfully")
    except Exception as e:
        logger.warning(f"Redis caching shutdown failed: {e}")
    
    async_engine = get_async_engine()
    await async_engine.dispose()
    logger.info("Design Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="NextGen Fusion Design Service",
    description="Solar system design, layout optimization, and BoM generation service",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Collect metrics for all requests"""
    method = request.method
    endpoint = request.url.path
    
    with REQUEST_DURATION.time():
        response = await call_next(request)
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.ENVIRONMENT == "development" else "An unexpected error occurred"
        }
    )


@app.get("/health", response_model=HealthResponse)
@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check(db = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    
    # Test Redis cache connection
    cache_status = "healthy"
    try:
        cache_health = await check_design_cache_health()
        if not cache_health:
            cache_status = "unhealthy"
    except Exception as e:
        logger.warning(f"Cache health check failed: {e}")
        cache_status = "unavailable"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        service="design",
        timestamp=str(__import__('datetime').datetime.now()),
        database=db_status,
        cache=cache_status
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NextGen Fusion Design Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled"
    }


# Include API routers
app.include_router(design.router, prefix="/api/v1/design", tags=["design"])
app.include_router(layout.router, prefix="/api/v1/layout", tags=["layout"])
app.include_router(shading.router, prefix="/api/v1/shading", tags=["shading"])
app.include_router(bom.router, prefix="/api/v1/bom", tags=["bom"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8001)),
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )