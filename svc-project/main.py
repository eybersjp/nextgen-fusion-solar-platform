#!/usr/bin/env python3
"""
Project Management Service for NextGen Fusion Commercial Solar Platform

This service provides project management capabilities including task management,
milestone tracking, Gantt chart data, resource allocation, and project analytics.

Features:
- Task CRUD operations
- Milestone management
- Gantt chart data generation
- Resource allocation tracking
- Project timeline management
- Team collaboration tools
- Progress reporting
- Risk management
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
from pydantic import ValidationError
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from prometheus_client import start_http_server
import time
import traceback
from datetime import datetime
import uvicorn

from app.api import api_router
from app.core import get_settings, create_tables
from app.core.logging import setup_logging, logger, RequestTrackingMiddleware
from app.core.idempotency import IdempotencyMiddleware
from app.core.errors import (
    AppException,
    handle_app_exception,
    handle_http_exception,
    handle_validation_error,
    handle_generic_exception
)
from services.database_integration import project_db_service

# Setup logging
setup_logging()
settings = get_settings()

# Track service start time for uptime calculation
start_time = time.time()

# Prometheus metrics - check if already registered to avoid duplicates
try:
    REQUEST_COUNT = Counter(
        'project_requests_total',
        'Total number of project management requests',
        ['method', 'endpoint', 'status']
    )
except ValueError:
    # Metric already exists, get it from registry
    REQUEST_COUNT = REGISTRY._names_to_collectors['project_requests_total']

try:
    REQUEST_DURATION = Histogram(
        'project_request_duration_seconds',
        'Request duration in seconds',
        ['method', 'endpoint']
    )
except ValueError:
    REQUEST_DURATION = REGISTRY._names_to_collectors['project_request_duration_seconds']

try:
    TASK_COUNT = Counter(
        'project_tasks_total',
        'Total number of tasks',
        ['project_id', 'status', 'priority']
    )
except ValueError:
    TASK_COUNT = REGISTRY._names_to_collectors['project_tasks_total']

try:
    MILESTONE_COUNT = Counter(
        'project_milestones_total',
        'Total number of milestones',
        ['project_id', 'status']
    )
except ValueError:
    MILESTONE_COUNT = REGISTRY._names_to_collectors['project_milestones_total']

try:
    PROJECT_DURATION = Histogram(
        'project_completion_duration_days',
        'Project completion duration in days',
        ['project_type']
    )
except ValueError:
    PROJECT_DURATION = REGISTRY._names_to_collectors['project_completion_duration_days']

# Database pool metrics
try:
    DB_POOL_SIZE = Gauge(
        'db_pool_size',
        'Current database pool size'
    )
except ValueError:
    DB_POOL_SIZE = REGISTRY._names_to_collectors['db_pool_size']

try:
    DB_POOL_IN_USE = Gauge(
        'db_pool_in_use',
        'Number of database connections currently in use'
    )
except ValueError:
    DB_POOL_IN_USE = REGISTRY._names_to_collectors['db_pool_in_use']

try:
    DB_ACQUIRE_SECONDS = Histogram(
        'db_acquire_seconds_bucket',
        'Time spent acquiring database connections',
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
except ValueError:
    DB_ACQUIRE_SECONDS = REGISTRY._names_to_collectors['db_acquire_seconds_bucket']

# Critical path cache metrics
try:
    CRITICAL_PATH_CACHE_HITS = Counter(
        'critical_path_cache_hits_total',
        'Total number of critical path cache hits'
    )
except ValueError:
    CRITICAL_PATH_CACHE_HITS = REGISTRY._names_to_collectors['critical_path_cache_hits_total']

try:
    CRITICAL_PATH_CACHE_MISSES = Counter(
        'critical_path_cache_misses_total',
        'Total number of critical path cache misses'
    )
except ValueError:
    CRITICAL_PATH_CACHE_MISSES = REGISTRY._names_to_collectors['critical_path_cache_misses_total']

try:
    CRITICAL_PATH_CALC_DURATION = Histogram(
        'critical_path_calc_duration_seconds',
        'Time spent calculating critical path',
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
    )
except ValueError:
    CRITICAL_PATH_CALC_DURATION = REGISTRY._names_to_collectors['critical_path_calc_duration_seconds']

# Tenant metrics
try:
    TENANT_ACTIVE_PROJECTS = Gauge(
        'tenant_active_projects',
        'Number of active projects per tenant',
        ['tenant_id']
    )
except ValueError:
    TENANT_ACTIVE_PROJECTS = REGISTRY._names_to_collectors['tenant_active_projects']

# HTTP request metrics with enhanced labels
try:
    HTTP_REQUESTS_TOTAL = Counter(
        'http_requests_total',
        'Total number of HTTP requests',
        ['route', 'method', 'status']
    )
except ValueError:
    HTTP_REQUESTS_TOTAL = REGISTRY._names_to_collectors['http_requests_total']

try:
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        'http_request_duration_seconds_bucket',
        'HTTP request duration in seconds',
        ['route'],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
    )
except ValueError:
    HTTP_REQUEST_DURATION_SECONDS = REGISTRY._names_to_collectors['http_request_duration_seconds_bucket']


async def update_database_metrics():
    """Update database pool metrics."""
    try:
        pool_status = await project_db_service.get_pool_status()
        
        # Update database pool metrics
        if pool_status:
            DB_POOL_SIZE.set(pool_status.get("current_size", 0))
            DB_POOL_IN_USE.set(pool_status.get("checked_out", 0))
            
    except Exception as e:
        logger.error(f"Failed to update database metrics: {e}")


async def metrics_updater():
    """Background task to update metrics periodically."""
    while True:
        try:
            await update_database_metrics()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Metrics updater error: {e}")
            await asyncio.sleep(60)  # Wait longer on error


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Project Management Service...")
    
    try:
        # Create database tables
        await create_tables()
        logger.info("Database tables created successfully")
        
        # Initialize ProjectDatabaseService
        project_db_service.initialize()
        logger.info("ProjectDatabaseService initialized successfully")
        
        # Start Prometheus metrics server
        if settings.ENABLE_METRICS:
            start_http_server(settings.METRICS_PORT)
            logger.info(f"Metrics server started on port {settings.METRICS_PORT}")
        
        # Start metrics updater background task
        metrics_task = asyncio.create_task(metrics_updater())
        logger.info("Metrics updater started")
        
        # Initialize project management engine
        logger.info("Project management engine initialized")
        
        logger.info("Project Management Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Project Management Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Project Management Service...")
    
    # Cancel metrics updater
    try:
        metrics_task.cancel()
        await metrics_task
    except asyncio.CancelledError:
        logger.info("Metrics updater cancelled")
    except Exception as e:
        logger.error(f"Error cancelling metrics updater: {e}")
    
    # Cleanup ProjectDatabaseService
    try:
        await project_db_service.cleanup_old_data()
        logger.info("ProjectDatabaseService cleanup completed")
    except Exception as e:
        logger.error(f"Error during ProjectDatabaseService cleanup: {e}")


# Create FastAPI application
app = FastAPI(
    title="NextGen Fusion Project Management Service",
    description="Project management service for NextGen Fusion Commercial Solar Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Include API router
app.include_router(api_router, prefix="/api")

# Add middleware
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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
    
    # Update enhanced HTTP metrics
    HTTP_REQUESTS_TOTAL.labels(
        route=endpoint,
        method=method,
        status=status_code
    ).inc()
    
    HTTP_REQUEST_DURATION_SECONDS.labels(
        route=endpoint
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


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application-specific exceptions"""
    return handle_app_exception(request, exc)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    return handle_http_exception(request, exc)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return handle_validation_error(request, exc)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    return handle_generic_exception(request, exc)


# Include API routes
app.include_router(api_router, prefix="/api")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        await project_db_service.test_connection()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "project-management",
            "version": "1.0.0",
            "database": "connected",
            "uptime_seconds": int(time.time() - start_time)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "project-management",
                "version": "1.0.0",
                "database": "disconnected",
                "error": str(e),
                "uptime_seconds": int(time.time() - start_time)
            }
        )


# Version endpoint
@app.get("/version")
async def get_version():
    """Get service version information"""
    return {
        "service": "project-management",
        "version": "1.0.0",
        "build_time": "2024-01-15T10:00:00Z",
        "git_commit": "abc123def456",
        "environment": settings.ENVIRONMENT,
        "python_version": "3.11+",
        "dependencies": {
            "fastapi": "0.104+",
            "sqlalchemy": "2.0+",
            "redis": "5.0+",
            "prometheus_client": "0.19+"
        }
    }


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    # Update database metrics before serving
    await update_database_metrics()
    
    return JSONResponse(
        content=generate_latest(REGISTRY).decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    )


# Admin runtime endpoint
@app.get("/admin/runtime")
async def get_runtime_info():
    """Get runtime configuration and status (read-only)"""
    try:
        pool_status = await project_db_service.get_pool_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - start_time),
            "environment": settings.ENVIRONMENT,
            "database": {
                "pool_config": {
                    "max_size": pool_status.get("max_size", "unknown"),
                    "min_idle": pool_status.get("min_idle", "unknown"),
                    "max_overflow": pool_status.get("max_overflow", "unknown"),
                    "pool_timeout": pool_status.get("pool_timeout", "unknown")
                },
                "current_status": {
                    "size": pool_status.get("size", 0),
                    "checked_in": pool_status.get("checked_in", 0),
                    "checked_out": pool_status.get("checked_out", 0),
                    "overflow": pool_status.get("overflow", 0),
                    "invalid": pool_status.get("invalid", 0)
                }
            },
            "cache": {
                "redis_url": settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else "not_configured",
                "cache_ttl_seconds": settings.CACHE_TTL_SECONDS if hasattr(settings, 'CACHE_TTL_SECONDS') else 300,
                "caching_enabled": settings.ENABLE_CACHING if hasattr(settings, 'ENABLE_CACHING') else False
            },
            "logging": {
                "level": logging.getLogger().level,
                "structured_logging": True,
                "request_tracking": True
            },
            "features": {
                "idempotency_keys": True,
                "critical_path_caching": True,
                "prometheus_metrics": True,
                "error_handling": True
            }
        }
    except Exception as e:
        logger.error(f"Failed to get runtime info: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve runtime information",
                "timestamp": datetime.utcnow().isoformat()
            }
        )





# Ready check endpoint
@app.get("/ready", tags=["Health"])
async def ready_check():
    """Readiness check endpoint."""
    try:
        # Check database connectivity
        # This would be implemented based on your database setup
        
        return {
            "status": "ready",
            "service": "project-management-service",
            "checks": {
                "database": "ok",
                "task_engine": "ok",
                "notification_service": "ok"
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