#!/usr/bin/env python3
"""
Idempotency middleware and utilities for NextGen Fusion Platform

Provides idempotency key handling for POST endpoints to prevent duplicate operations.
"""

import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis import Redis
from redis.exceptions import RedisError

from .config import settings
from .logging import logger, get_request_id


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle idempotency keys for POST requests"""
    
    def __init__(self, app, redis_client: Optional[Redis] = None):
        super().__init__(app)
        self.redis_client = redis_client
        self.ttl_seconds = 3600  # 1 hour TTL for idempotency keys
        
    async def dispatch(self, request: Request, call_next):
        # Only process POST requests
        if request.method != "POST":
            return await call_next(request)
            
        # Check for idempotency key header
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            # No idempotency key provided - proceed normally
            return await call_next(request)
            
        # Validate idempotency key format
        if not self._is_valid_idempotency_key(idempotency_key):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "code": "INVALID_IDEMPOTENCY_KEY",
                    "message": "Idempotency key must be a valid UUID or alphanumeric string (8-64 characters)",
                    "traceId": get_request_id()
                }
            )
            
        # Generate cache key
        cache_key = await self._generate_cache_key(request, idempotency_key)
        
        # Check if we have a cached response
        if self.redis_client:
            try:
                cached_response = await self._get_cached_response(cache_key)
                if cached_response:
                    logger.info(
                        "Idempotency key hit - returning cached response",
                        idempotency_key=idempotency_key,
                        cache_key=cache_key
                    )
                    return JSONResponse(
                        status_code=cached_response["status_code"],
                        content=cached_response["content"],
                        headers=cached_response.get("headers", {})
                    )
            except RedisError as e:
                logger.warning(
                    "Redis error during idempotency check",
                    error=str(e),
                    idempotency_key=idempotency_key
                )
                # Continue without caching if Redis is unavailable
                
        # Process the request
        response = await call_next(request)
        
        # Cache successful responses (2xx status codes)
        if 200 <= response.status_code < 300 and self.redis_client:
            try:
                await self._cache_response(cache_key, response, idempotency_key)
            except RedisError as e:
                logger.warning(
                    "Redis error during response caching",
                    error=str(e),
                    idempotency_key=idempotency_key
                )
                
        return response
        
    def _is_valid_idempotency_key(self, key: str) -> bool:
        """Validate idempotency key format"""
        if not key or len(key) < 8 or len(key) > 64:
            return False
        # Allow alphanumeric, hyphens, and underscores
        return key.replace("-", "").replace("_", "").isalnum()
        
    async def _generate_cache_key(self, request: Request, idempotency_key: str) -> str:
        """Generate cache key from request details and idempotency key"""
        # Include method, path, and body hash for uniqueness
        path = str(request.url.path)
        
        # Read and hash request body
        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()[:16]
        
        # Include tenant ID if available
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        
        cache_key = f"idempotency:{tenant_id}:{path}:{idempotency_key}:{body_hash}"
        return cache_key
        
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response from Redis"""
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning("Error retrieving cached response", error=str(e), cache_key=cache_key)
        return None
        
    async def _cache_response(self, cache_key: str, response: Response, idempotency_key: str):
        """Cache response in Redis"""
        try:
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
                
            # Parse response content
            try:
                content = json.loads(response_body.decode())
            except json.JSONDecodeError:
                content = response_body.decode()
                
            # Prepare cache data
            cache_data = {
                "status_code": response.status_code,
                "content": content,
                "headers": dict(response.headers),
                "cached_at": datetime.utcnow().isoformat()
            }
            
            # Store in Redis with TTL
            self.redis_client.setex(
                cache_key,
                self.ttl_seconds,
                json.dumps(cache_data, default=str)
            )
            
            logger.info(
                "Response cached for idempotency",
                idempotency_key=idempotency_key,
                cache_key=cache_key,
                status_code=response.status_code
            )
            
            # Recreate response body iterator
            response.body_iterator = iter([response_body])
            
        except Exception as e:
            logger.error(
                "Error caching response",
                error=str(e),
                idempotency_key=idempotency_key,
                cache_key=cache_key
            )


def get_redis_client() -> Optional[Redis]:
    """Get Redis client for idempotency caching"""
    try:
        if settings.REDIS_URL:
            return Redis.from_url(settings.REDIS_URL, decode_responses=False)
    except Exception as e:
        logger.warning("Failed to connect to Redis for idempotency", error=str(e))
    return None


# Utility functions for manual idempotency checking
async def check_idempotency_key(
    idempotency_key: str,
    operation_id: str,
    redis_client: Optional[Redis] = None
) -> Optional[Dict[str, Any]]:
    """Check if an idempotency key has been used for a specific operation"""
    if not redis_client:
        return None
        
    cache_key = f"idempotency:manual:{operation_id}:{idempotency_key}"
    
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except (RedisError, json.JSONDecodeError) as e:
        logger.warning("Error checking manual idempotency key", error=str(e))
        
    return None


async def store_idempotency_result(
    idempotency_key: str,
    operation_id: str,
    result: Dict[str, Any],
    redis_client: Optional[Redis] = None,
    ttl_seconds: int = 3600
):
    """Store result for manual idempotency checking"""
    if not redis_client:
        return
        
    cache_key = f"idempotency:manual:{operation_id}:{idempotency_key}"
    
    try:
        cache_data = {
            "result": result,
            "stored_at": datetime.utcnow().isoformat()
        }
        
        redis_client.setex(
            cache_key,
            ttl_seconds,
            json.dumps(cache_data, default=str)
        )
        
        logger.info(
            "Idempotency result stored",
            idempotency_key=idempotency_key,
            operation_id=operation_id
        )
        
    except Exception as e:
        logger.error(
            "Error storing idempotency result",
            error=str(e),
            idempotency_key=idempotency_key,
            operation_id=operation_id
        )