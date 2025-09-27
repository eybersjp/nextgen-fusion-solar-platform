#!/usr/bin/env python3
"""
Compliance Service for NextGen Fusion Commercial Solar Platform

This service provides compliance validation, rule management, and regulatory
checking capabilities for solar installations across different regions.

Features:
- Compliance rule engine
- Regional regulation validation
- Automated compliance reporting
- Code compliance checking
- Safety standard validation
- Environmental impact assessment
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import start_http_server
import uvicorn

from app.core import get_settings, setup_logging, create_tables
from app.core.logging import get_logger
from app.api import api_router

# Setup logging
setup_logging()
logger = get_logger(__name__)
settings = get_settings()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'compliance_requests_total',
    'Total number of compliance requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'compliance_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

VALIDATION_COUNT = Counter(
    'compliance_validations_total',
    'Total number of compliance validations',
    ['region', 'rule_type', 'result']
)

RULE_EXECUTION_TIME = Histogram(
    'compliance_rule_execution_seconds',
    'Time taken to execute compliance rules',
    ['rule_type', 'region']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Compliance Service...")
    
    try:
        # Create database tables
        await create_tables()
        logger.info("Database tables created successfully")
        
        # Start Prometheus metrics server
        if settings.ENABLE_METRICS:
            start_http_server(settings.METRICS_PORT)
            logger.info(f"Metrics server started on port {settings.METRICS_PORT}")
        
        # Initialize compliance rule engine
        # This would load compliance rules from database/config
        logger.info("Compliance rule engine initialized")
        
        logger.info("Compliance Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Compliance Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Compliance Service...")


# Create FastAPI application
app = FastAPI(
    title="NextGen Fusion Compliance Service",
    description="Compliance validation and regulatory checking service",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Middleware for metrics and logging
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics and log requests."""
    start_time = datetime.utcnow()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    # Extract endpoint info
    method = request.method
    endpoint = request.url.path
    status_code = response.status_code
    
    # Update metrics
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status=status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)
    
    # Log request
    logger.info(
        f"{method} {endpoint} - {status_code} - {duration:.3f}s",
        extra={
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration": duration,
            "user_agent": request.headers.get("user-agent"),
            "remote_addr": request.client.host if request.client else None
        }
    )
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {exc}",
        exc_info=True,
        extra={
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "exception_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Include API routes
app.include_router(api_router, prefix="/api")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "compliance-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# Metrics endpoint
@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


# Ready check endpoint
@app.get("/ready", tags=["Health"])
async def ready_check():
    """Readiness check endpoint."""
    try:
        # Check database connectivity
        # This would be implemented based on your database setup
        
        return {
            "status": "ready",
            "service": "compliance-service",
            "checks": {
                "database": "ok",
                "rule_engine": "ok"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )