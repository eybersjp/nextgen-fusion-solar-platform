"""Middleware for the Design Service.

Provides request/response processing, CORS, authentication,
rate limiting, logging, and other cross-cutting concerns.
"""

import time
import uuid
from datetime import datetime
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from .config import get_settings
from .logging import get_logger, set_request_id, set_user_id, set_organization_id
from .auth import AuthService
from ..exceptions import AuthenticationError
from .security import check_rate_limit, validate_json_input
from .cache import cache_manager
from .exceptions import (
    DesignServiceException, 
    AuthenticationError, 
    RateLimitError,
    ValidationError
)


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_id": request_id
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                extra={
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4),
                    "request_id": request_id
                }
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            logger.error(
                "Request failed",
                extra={
                    "error": str(e),
                    "process_time": round(process_time, 4),
                    "request_id": request_id
                },
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": request_id
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": str(round(process_time, 4))
                }
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication."""
    
    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/",
            "/health",
            "/health/live",
            "/health/ready",
            "/health/metrics",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Missing or invalid authorization header"}
            )
        
        token = auth_header.split(" ")[1]
        
        try:
            # Get database session
            from .database import get_db
            db = next(get_db())
            
            # Verify token and get user
            auth_service = AuthService()
            user = await auth_service.get_current_user(token, db)
            
            # Add user to request state
            request.state.user = user
            request.state.token = token
            
            # Set logging context
            set_user_id(user.id)
            if user.organizations:
                set_organization_id(user.organizations[0])  # Use first org
            
            return await call_next(request)
            
        except AuthenticationError as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Authentication service error"}
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(
        self, 
        app: ASGIApp, 
        requests_per_minute: int = 60,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.exclude_paths = exclude_paths or ["/health"]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        try:
            # Check rate limit
            allowed = check_rate_limit(
                key=f"rate_limit:{client_id}",
                limit=self.requests_per_minute,
                window=60  # 1 minute
            )
            
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "limit": self.requests_per_minute,
                        "window": "1 minute"
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Window": "60",
                        "Retry-After": "60"
                    }
                )
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Continue processing if rate limiting fails
            return await call_next(request)
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use user ID if authenticated
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Fall back to IP address
        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            return f"ip:{client_ip.split(',')[0].strip()}"
        
        if hasattr(request.client, "host"):
            return f"ip:{request.client.host}"
        
        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation."""
    
    def __init__(self, app: ASGIApp, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "Request too large",
                    "max_size": self.max_request_size
                }
            )
        
        # Validate JSON for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        validate_json_input(body.decode('utf-8'))
                except ValidationError as e:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": str(e)}
                    )
                except Exception as e:
                    logger.error(f"Request validation error: {e}")
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": "Invalid request format"}
                    )
        
        return await call_next(request)


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for HTTP caching."""
    
    def __init__(self, app: ASGIApp, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cacheable_methods = ["GET"]
        self.cacheable_paths = [
            "/api/v1/designs",
            "/api/v1/layouts",
            "/api/v1/components",
            "/api/v1/suppliers"
        ]
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Only cache GET requests for specific paths
        if (
            request.method not in self.cacheable_methods or
            not any(request.url.path.startswith(path) for path in self.cacheable_paths)
        ):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        cached_response = cache_manager.get(cache_key, "http_cache")
        if cached_response:
            logger.debug(f"Cache hit for {cache_key}")
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers={
                    **cached_response["headers"],
                    "X-Cache": "HIT"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if 200 <= response.status_code < 300:
            try:
                # Read response content
                content = b""
                async for chunk in response.body_iterator:
                    content += chunk
                
                # Cache the response
                cache_data = {
                    "content": content.decode('utf-8'),
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                
                cache_manager.set(cache_key, cache_data, self.cache_ttl, "http_cache")
                
                # Create new response with cached content
                response = Response(
                    content=content,
                    status_code=response.status_code,
                    headers={
                        **dict(response.headers),
                        "X-Cache": "MISS",
                        "Cache-Control": f"max-age={self.cache_ttl}"
                    }
                )
                
            except Exception as e:
                logger.error(f"Cache middleware error: {e}")
                # Return original response if caching fails
                response.headers["X-Cache"] = "ERROR"
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        key_parts = [
            request.method,
            str(request.url.path),
            str(request.url.query)
        ]
        
        # Include user context for personalized responses
        if hasattr(request.state, "user") and request.state.user:
            key_parts.append(f"user:{request.state.user.id}")
        
        return ":".join(key_parts)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling."""
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await call_next(request)
            
        except DesignServiceException as e:
            # Handle custom application exceptions
            logger.warning(f"Application error: {e}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.message,
                    "error_code": e.error_code,
                    "details": e.details
                }
            )
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            return JSONResponse(
                status_code=e.status_code,
                content={"error": e.detail}
            )
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.request_duration_sum = 0.0
        self.error_count = 0
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Update metrics
            duration = time.time() - start_time
            self.request_count += 1
            self.request_duration_sum += duration
            
            if response.status_code >= 400:
                self.error_count += 1
            
            # Add metrics headers
            response.headers["X-Request-Count"] = str(self.request_count)
            response.headers["X-Avg-Response-Time"] = str(
                round(self.request_duration_sum / self.request_count, 4)
            )
            response.headers["X-Error-Rate"] = str(
                round(self.error_count / self.request_count, 4)
            )
            
            return response
            
        except Exception as e:
            self.error_count += 1
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "avg_response_time": self.request_duration_sum / max(self.request_count, 1)
        }


def setup_middleware(app):
    """Set up all middleware for the application."""
    settings = get_settings()
    
    # Error handling (should be first)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Metrics collection
    metrics_middleware = MetricsMiddleware(app)
    app.add_middleware(MetricsMiddleware)
    
    # Request validation
    app.add_middleware(
        RequestValidationMiddleware,
        max_request_size=settings.MAX_REQUEST_SIZE
    )
    
    # Rate limiting
    if settings.ENABLE_RATE_LIMITING:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        )
    
    # HTTP caching
    if settings.ENABLE_HTTP_CACHE:
        app.add_middleware(
            CacheMiddleware,
            cache_ttl=settings.HTTP_CACHE_TTL
        )
    
    # Authentication (should be after logging but before business logic)
    app.add_middleware(AuthenticationMiddleware)
    
    # CORS
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
    
    # Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Trusted hosts
    if settings.ALLOWED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # Store metrics middleware reference for access
    app.state.metrics_middleware = metrics_middleware
    
    logger.info("Middleware setup completed")