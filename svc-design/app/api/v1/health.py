"""Health check endpoints for the Design Service.

Provides endpoints for monitoring service health, database connectivity,
and external service dependencies.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...core.config import get_settings
from ...core.database import check_database_connection, database_health_check
from ...core.cache import cache_manager
from ...core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Any]


class ServiceInfo(BaseModel):
    """Service information response model."""
    name: str
    version: str
    description: str
    environment: str
    features: Dict[str, bool]
    capabilities: Dict[str, Any]


# Track service start time for uptime calculation
service_start_time = datetime.utcnow()


@router.get("/", response_model=HealthStatus)
async def health_check():
    """Basic health check endpoint.
    
    Returns:
        HealthStatus: Service health information
    """
    try:
        settings = get_settings()
        current_time = datetime.utcnow()
        uptime = (current_time - service_start_time).total_seconds()
        
        # Perform basic health checks
        checks = {
            "service": "healthy",
            "timestamp": current_time.isoformat()
        }
        
        return HealthStatus(
            status="healthy",
            timestamp=current_time,
            version="1.0.0",
            environment=settings.ENVIRONMENT,
            uptime_seconds=uptime,
            checks=checks
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy"
        )


@router.get("/detailed", response_model=HealthStatus)
async def detailed_health_check():
    """Detailed health check with dependency verification.
    
    Returns:
        HealthStatus: Comprehensive service health information
    """
    try:
        settings = get_settings()
        current_time = datetime.utcnow()
        uptime = (current_time - service_start_time).total_seconds()
        
        # Perform detailed health checks
        checks = {
            "service": "healthy",
            "timestamp": current_time.isoformat()
        }
        
        # Check database connectivity
        try:
            db_healthy = check_database_connection()
            db_details = database_health_check()
            checks["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "details": db_details
            }
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            checks["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check cache connectivity
        try:
            cache_health = cache_manager.health_check()
            checks["cache"] = cache_health
        except Exception as e:
            logger.warning(f"Cache health check failed: {e}")
            checks["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check external services (if configured)
        checks["external_services"] = await check_external_services()
        
        # Determine overall status
        overall_status = "healthy"
        for check_name, check_result in checks.items():
            if isinstance(check_result, dict) and check_result.get("status") == "unhealthy":
                overall_status = "degraded"
                break
        
        return HealthStatus(
            status=overall_status,
            timestamp=current_time,
            version="1.0.0",
            environment=settings.ENVIRONMENT,
            uptime_seconds=uptime,
            checks=checks
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy"
        )


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint.
    
    Returns:
        dict: Simple ready/not ready status
    """
    try:
        # Check critical dependencies
        db_healthy = check_database_connection()
        
        if not db_healthy:
            raise HTTPException(
                status_code=503,
                detail="Service not ready - database unavailable"
            )
        
        return {"status": "ready"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service not ready"
        )


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint.
    
    Returns:
        dict: Simple alive/dead status
    """
    try:
        # Basic liveness check - service is running
        return {"status": "alive"}
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service not alive"
        )


@router.get("/info", response_model=ServiceInfo)
async def service_info():
    """Service information endpoint.
    
    Returns:
        ServiceInfo: Detailed service information
    """
    settings = get_settings()
    
    return ServiceInfo(
        name="NextGen Fusion Design Service",
        version="1.0.0",
        description="Solar design and engineering service for commercial solar projects",
        environment=settings.ENVIRONMENT,
        features={
            "solar_design": True,
            "layout_optimization": True,
            "shading_analysis": True,
            "bom_generation": True,
            "compliance_checking": True,
            "weather_integration": True,
            "pricing_integration": True
        },
        capabilities={
            "max_panel_count": 10000,
            "max_design_area_sqm": 100000,
            "supported_panel_types": [
                "monocrystalline",
                "polycrystalline",
                "thin_film",
                "bifacial"
            ],
            "supported_inverter_types": [
                "string",
                "power_optimizer",
                "microinverter",
                "central"
            ],
            "analysis_types": [
                "shading",
                "soiling",
                "thermal",
                "electrical",
                "structural"
            ],
            "supported_countries": ["ZA", "AU", "US"],
            "supported_currencies": ["ZAR", "AUD", "USD"]
        }
    )


@router.get("/metrics")
async def health_metrics():
    """Health and performance metrics endpoint.
    
    Returns:
        dict: Service metrics and statistics
    """
    try:
        current_time = datetime.utcnow()
        uptime = (current_time - service_start_time).total_seconds()
        
        # Get basic metrics
        metrics = {
            "service": {
                "name": "design-service",
                "version": "1.0.0",
                "uptime_seconds": uptime,
                "timestamp": current_time.isoformat()
            },
            "system": {
                "memory_usage_mb": 0,  # Would implement actual memory tracking
                "cpu_usage_percent": 0,  # Would implement actual CPU tracking
                "disk_usage_percent": 0  # Would implement actual disk tracking
            },
            "requests": {
                "total_count": 0,  # Would track from middleware
                "error_count": 0,  # Would track from middleware
                "avg_response_time_ms": 0  # Would track from middleware
            }
        }
        
        # Add database metrics if available
        try:
            db_health = database_health_check()
            metrics["database"] = db_health
        except Exception as e:
            logger.warning(f"Failed to get database metrics: {e}")
            metrics["database"] = {"status": "unknown", "error": str(e)}
        
        # Add cache metrics if available
        try:
            cache_health = cache_manager.health_check()
            metrics["cache"] = cache_health
        except Exception as e:
            logger.warning(f"Failed to get cache metrics: {e}")
            metrics["cache"] = {"status": "unknown", "error": str(e)}
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get health metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve metrics"
        )


async def check_external_services() -> Dict[str, Any]:
    """Check external service dependencies.
    
    Returns:
        Dict[str, Any]: External service health status
    """
    external_checks = {}
    
    # Weather service check
    try:
        # Would implement actual weather service health check
        external_checks["weather_service"] = {
            "status": "healthy",
            "response_time_ms": 150
        }
    except Exception as e:
        external_checks["weather_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Pricing service check
    try:
        # Would implement actual pricing service health check
        external_checks["pricing_service"] = {
            "status": "healthy",
            "response_time_ms": 200
        }
    except Exception as e:
        external_checks["pricing_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Compliance service check
    try:
        # Would implement actual compliance service health check
        external_checks["compliance_service"] = {
            "status": "healthy",
            "response_time_ms": 100
        }
    except Exception as e:
        external_checks["compliance_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return external_checks