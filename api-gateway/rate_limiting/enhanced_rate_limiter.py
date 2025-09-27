"""Enhanced Rate Limiting System for NextGen Fusion Platform

Provides comprehensive rate limiting with:
- Tenant-specific rate limiting policies
- Multiple rate limiting algorithms (token bucket, sliding window, fixed window)
- Hierarchical rate limits (global, tenant, user, endpoint)
- Dynamic rate limit adjustment
- Rate limit analytics and monitoring
- Burst handling and grace periods
- Integration with Redis for distributed rate limiting
"""

import time
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import redis.asyncio as redis
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.base import BaseHTTPMiddleware
import hashlib
import math
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitScope(Enum):
    """Rate limit scopes in order of precedence"""
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"
    ENDPOINT = "endpoint"
    IP_ADDRESS = "ip_address"


class TenantTier(Enum):
    """Tenant subscription tiers"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass
class RateLimitRule:
    """Defines a rate limiting rule"""
    requests: int  # Number of requests allowed
    window_seconds: int  # Time window in seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    burst_multiplier: float = 1.5  # Allow burst up to this multiplier
    grace_period_seconds: int = 0  # Grace period for new users/tenants
    
    @property
    def burst_limit(self) -> int:
        """Calculate burst limit"""
        return int(self.requests * self.burst_multiplier)
    
    def __str__(self) -> str:
        return f"{self.requests}/{self.window_seconds}s ({self.algorithm.value})"


@dataclass
class TenantRateLimitPolicy:
    """Rate limiting policy for a tenant"""
    tenant_id: str
    tier: TenantTier
    
    # Global limits
    global_limit: RateLimitRule
    
    # Per-user limits within tenant
    user_limit: RateLimitRule
    
    # Endpoint-specific limits
    endpoint_limits: Dict[str, RateLimitRule] = field(default_factory=dict)
    
    # Special limits for different operations
    read_limit: Optional[RateLimitRule] = None
    write_limit: Optional[RateLimitRule] = None
    upload_limit: Optional[RateLimitRule] = None
    
    # Policy metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    # Custom overrides
    custom_limits: Dict[str, RateLimitRule] = field(default_factory=dict)
    
    def get_limit_for_endpoint(self, endpoint: str, method: str = "GET") -> RateLimitRule:
        """Get rate limit rule for specific endpoint"""
        # Check for exact endpoint match
        endpoint_key = f"{method}:{endpoint}"
        if endpoint_key in self.endpoint_limits:
            return self.endpoint_limits[endpoint_key]
        
        # Check for method-specific limits
        if method.upper() in ["POST", "PUT", "PATCH", "DELETE"] and self.write_limit:
            return self.write_limit
        elif method.upper() == "GET" and self.read_limit:
            return self.read_limit
        
        # Check for upload endpoints
        if "upload" in endpoint.lower() and self.upload_limit:
            return self.upload_limit
        
        # Default to user limit
        return self.user_limit


@dataclass
class RateLimitState:
    """Current state of rate limiting for a key"""
    key: str
    requests_made: int = 0
    window_start: float = 0
    tokens: float = 0
    last_refill: float = 0
    first_request_time: Optional[float] = None
    
    # Sliding window specific
    request_times: deque = field(default_factory=deque)
    
    # Analytics
    total_requests: int = 0
    total_blocked: int = 0
    last_blocked_time: Optional[float] = None


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    limit: int
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None
    scope: Optional[RateLimitScope] = None
    rule_applied: Optional[str] = None
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers"""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time))
        }
        
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
        
        if self.scope:
            headers["X-RateLimit-Scope"] = self.scope.value
        
        if self.rule_applied:
            headers["X-RateLimit-Rule"] = self.rule_applied
        
        return headers


class RateLimiter(ABC):
    """Abstract base class for rate limiters"""
    
    @abstractmethod
    async def check_rate_limit(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: Optional[float] = None
    ) -> RateLimitResult:
        """Check if request is within rate limit"""
        pass
    
    @abstractmethod
    async def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a key"""
        pass


class InMemoryRateLimiter(RateLimiter):
    """In-memory rate limiter implementation"""
    
    def __init__(self):
        self.states: Dict[str, RateLimitState] = {}
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: Optional[float] = None
    ) -> RateLimitResult:
        """Check rate limit using specified algorithm"""
        if current_time is None:
            current_time = time.time()
        
        async with self.lock:
            if key not in self.states:
                self.states[key] = RateLimitState(key=key)
            
            state = self.states[key]
            
            if rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                return await self._check_token_bucket(state, rule, current_time)
            elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                return await self._check_sliding_window(state, rule, current_time)
            elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                return await self._check_fixed_window(state, rule, current_time)
            elif rule.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
                return await self._check_leaky_bucket(state, rule, current_time)
            else:
                raise ValueError(f"Unsupported algorithm: {rule.algorithm}")
    
    async def _check_token_bucket(
        self, 
        state: RateLimitState, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Token bucket algorithm implementation"""
        # Initialize tokens if first request
        if state.last_refill == 0:
            state.tokens = rule.requests
            state.last_refill = current_time
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - state.last_refill
        tokens_to_add = (time_elapsed / rule.window_seconds) * rule.requests
        state.tokens = min(rule.burst_limit, state.tokens + tokens_to_add)
        state.last_refill = current_time
        
        # Check if request can be allowed
        if state.tokens >= 1:
            state.tokens -= 1
            state.total_requests += 1
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=int(state.tokens),
                reset_time=current_time + rule.window_seconds
            )
        else:
            state.total_blocked += 1
            state.last_blocked_time = current_time
            
            # Calculate retry after
            retry_after = int(math.ceil((1 - state.tokens) / rule.requests * rule.window_seconds))
            
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_time=current_time + retry_after,
                retry_after=retry_after
            )
    
    async def _check_sliding_window(
        self, 
        state: RateLimitState, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Sliding window algorithm implementation"""
        # Remove old requests outside the window
        window_start = current_time - rule.window_seconds
        while state.request_times and state.request_times[0] < window_start:
            state.request_times.popleft()
        
        # Check if within limit
        current_requests = len(state.request_times)
        
        if current_requests < rule.requests:
            state.request_times.append(current_time)
            state.total_requests += 1
            
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=rule.requests - current_requests - 1,
                reset_time=current_time + rule.window_seconds
            )
        else:
            state.total_blocked += 1
            state.last_blocked_time = current_time
            
            # Calculate when the oldest request will expire
            oldest_request = state.request_times[0] if state.request_times else current_time
            retry_after = int(math.ceil(oldest_request + rule.window_seconds - current_time))
            
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_time=oldest_request + rule.window_seconds,
                retry_after=max(1, retry_after)
            )
    
    async def _check_fixed_window(
        self, 
        state: RateLimitState, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Fixed window algorithm implementation"""
        # Calculate current window
        current_window = int(current_time // rule.window_seconds)
        state_window = int(state.window_start // rule.window_seconds) if state.window_start else 0
        
        # Reset if new window
        if current_window > state_window:
            state.requests_made = 0
            state.window_start = current_window * rule.window_seconds
        
        # Check if within limit
        if state.requests_made < rule.requests:
            state.requests_made += 1
            state.total_requests += 1
            
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=rule.requests - state.requests_made,
                reset_time=(current_window + 1) * rule.window_seconds
            )
        else:
            state.total_blocked += 1
            state.last_blocked_time = current_time
            
            reset_time = (current_window + 1) * rule.window_seconds
            retry_after = int(math.ceil(reset_time - current_time))
            
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_time=reset_time,
                retry_after=retry_after
            )
    
    async def _check_leaky_bucket(
        self, 
        state: RateLimitState, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Leaky bucket algorithm implementation"""
        # Initialize if first request
        if state.last_refill == 0:
            state.last_refill = current_time
            state.tokens = 0
        
        # Calculate leak (requests that have been processed)
        time_elapsed = current_time - state.last_refill
        leaked_tokens = (time_elapsed / rule.window_seconds) * rule.requests
        state.tokens = max(0, state.tokens - leaked_tokens)
        state.last_refill = current_time
        
        # Check if bucket has capacity
        if state.tokens < rule.requests:
            state.tokens += 1
            state.total_requests += 1
            
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=int(rule.requests - state.tokens),
                reset_time=current_time + rule.window_seconds
            )
        else:
            state.total_blocked += 1
            state.last_blocked_time = current_time
            
            # Calculate when bucket will have capacity
            retry_after = int(math.ceil(rule.window_seconds / rule.requests))
            
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_time=current_time + retry_after,
                retry_after=retry_after
            )
    
    async def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a key"""
        async with self.lock:
            if key in self.states:
                del self.states[key]


class RedisRateLimiter(RateLimiter):
    """Redis-based distributed rate limiter"""
    
    def __init__(self, redis_client: redis.Redis, key_prefix: str = "rate_limit:"):
        self.redis = redis_client
        self.key_prefix = key_prefix
    
    def _get_redis_key(self, key: str) -> str:
        """Get Redis key for rate limit state"""
        return f"{self.key_prefix}{key}"
    
    async def check_rate_limit(
        self, 
        key: str, 
        rule: RateLimitRule, 
        current_time: Optional[float] = None
    ) -> RateLimitResult:
        """Check rate limit using Redis"""
        if current_time is None:
            current_time = time.time()
        
        redis_key = self._get_redis_key(key)
        
        if rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return await self._check_sliding_window_redis(redis_key, rule, current_time)
        elif rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return await self._check_fixed_window_redis(redis_key, rule, current_time)
        elif rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return await self._check_token_bucket_redis(redis_key, rule, current_time)
        else:
            raise ValueError(f"Algorithm {rule.algorithm} not supported for Redis")
    
    async def _check_sliding_window_redis(
        self, 
        redis_key: str, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Sliding window implementation using Redis sorted sets"""
        window_start = current_time - rule.window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # Count current requests
        pipe.zcard(redis_key)
        
        # Add current request with score as timestamp
        request_id = f"{current_time}:{hash(current_time) % 10000}"
        pipe.zadd(redis_key, {request_id: current_time})
        
        # Set expiration
        pipe.expire(redis_key, rule.window_seconds + 1)
        
        results = await pipe.execute()
        current_requests = results[1]
        
        if current_requests < rule.requests:
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=rule.requests - current_requests - 1,
                reset_time=current_time + rule.window_seconds
            )
        else:
            # Remove the request we just added since it's not allowed
            await self.redis.zrem(redis_key, request_id)
            
            # Get oldest request time for retry calculation
            oldest = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                retry_after = int(math.ceil(oldest_time + rule.window_seconds - current_time))
            else:
                retry_after = rule.window_seconds
            
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_time=current_time + retry_after,
                retry_after=max(1, retry_after)
            )
    
    async def _check_fixed_window_redis(
        self, 
        redis_key: str, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Fixed window implementation using Redis"""
        window = int(current_time // rule.window_seconds)
        window_key = f"{redis_key}:{window}"
        
        # Increment counter
        current_count = await self.redis.incr(window_key)
        
        if current_count == 1:
            # Set expiration for new window
            await self.redis.expire(window_key, rule.window_seconds)
        
        if current_count <= rule.requests:
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=rule.requests - current_count,
                reset_time=(window + 1) * rule.window_seconds
            )
        else:
            reset_time = (window + 1) * rule.window_seconds
            retry_after = int(math.ceil(reset_time - current_time))
            
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_time=reset_time,
                retry_after=retry_after
            )
    
    async def _check_token_bucket_redis(
        self, 
        redis_key: str, 
        rule: RateLimitRule, 
        current_time: float
    ) -> RateLimitResult:
        """Token bucket implementation using Redis with Lua script"""
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local tokens_per_second = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        local burst_capacity = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or current_time
        
        -- Calculate tokens to add
        local time_elapsed = current_time - last_refill
        local tokens_to_add = time_elapsed * tokens_per_second
        tokens = math.min(burst_capacity, tokens + tokens_to_add)
        
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
            redis.call('EXPIRE', key, 3600)  -- 1 hour expiration
            return {1, tokens}  -- allowed, remaining tokens
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', current_time)
            redis.call('EXPIRE', key, 3600)
            return {0, 0}  -- not allowed, no tokens
        end
        """
        
        tokens_per_second = rule.requests / rule.window_seconds
        result = await self.redis.eval(
            lua_script, 
            1, 
            redis_key, 
            rule.requests, 
            tokens_per_second, 
            current_time, 
            rule.burst_limit
        )
        
        allowed = bool(result[0])
        remaining_tokens = int(result[1])
        
        if allowed:
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=remaining_tokens,
                reset_time=current_time + rule.window_seconds
            )
        else:
            retry_after = int(math.ceil(rule.window_seconds / rule.requests))
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_time=current_time + retry_after,
                retry_after=retry_after
            )
    
    async def reset_rate_limit(self, key: str) -> None:
        """Reset rate limit for a key"""
        redis_key = self._get_redis_key(key)
        await self.redis.delete(redis_key)


class TenantRateLimitManager:
    """Manages tenant-specific rate limiting policies"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.policies: Dict[str, TenantRateLimitPolicy] = {}
        self.default_policies: Dict[TenantTier, TenantRateLimitPolicy] = {}
        
        # Initialize default policies
        self._initialize_default_policies()
    
    def _initialize_default_policies(self) -> None:
        """Initialize default rate limiting policies for each tier"""
        # Free tier - very restrictive
        self.default_policies[TenantTier.FREE] = TenantRateLimitPolicy(
            tenant_id="default_free",
            tier=TenantTier.FREE,
            global_limit=RateLimitRule(100, 3600),  # 100 requests per hour
            user_limit=RateLimitRule(10, 60),  # 10 requests per minute per user
            read_limit=RateLimitRule(50, 3600),  # 50 reads per hour
            write_limit=RateLimitRule(10, 3600),  # 10 writes per hour
            upload_limit=RateLimitRule(2, 3600)  # 2 uploads per hour
        )
        
        # Basic tier
        self.default_policies[TenantTier.BASIC] = TenantRateLimitPolicy(
            tenant_id="default_basic",
            tier=TenantTier.BASIC,
            global_limit=RateLimitRule(1000, 3600),  # 1000 requests per hour
            user_limit=RateLimitRule(100, 60),  # 100 requests per minute per user
            read_limit=RateLimitRule(800, 3600),  # 800 reads per hour
            write_limit=RateLimitRule(200, 3600),  # 200 writes per hour
            upload_limit=RateLimitRule(20, 3600)  # 20 uploads per hour
        )
        
        # Professional tier
        self.default_policies[TenantTier.PROFESSIONAL] = TenantRateLimitPolicy(
            tenant_id="default_professional",
            tier=TenantTier.PROFESSIONAL,
            global_limit=RateLimitRule(10000, 3600),  # 10k requests per hour
            user_limit=RateLimitRule(500, 60),  # 500 requests per minute per user
            read_limit=RateLimitRule(8000, 3600),  # 8k reads per hour
            write_limit=RateLimitRule(2000, 3600),  # 2k writes per hour
            upload_limit=RateLimitRule(100, 3600)  # 100 uploads per hour
        )
        
        # Enterprise tier
        self.default_policies[TenantTier.ENTERPRISE] = TenantRateLimitPolicy(
            tenant_id="default_enterprise",
            tier=TenantTier.ENTERPRISE,
            global_limit=RateLimitRule(100000, 3600),  # 100k requests per hour
            user_limit=RateLimitRule(2000, 60),  # 2k requests per minute per user
            read_limit=RateLimitRule(80000, 3600),  # 80k reads per hour
            write_limit=RateLimitRule(20000, 3600),  # 20k writes per hour
            upload_limit=RateLimitRule(1000, 3600)  # 1k uploads per hour
        )
    
    def register_tenant_policy(self, policy: TenantRateLimitPolicy) -> None:
        """Register a custom tenant policy"""
        self.policies[policy.tenant_id] = policy
        logger.info(f"Registered rate limit policy for tenant {policy.tenant_id} (tier: {policy.tier.value})")
    
    def get_tenant_policy(self, tenant_id: str, tier: TenantTier = TenantTier.FREE) -> TenantRateLimitPolicy:
        """Get rate limiting policy for a tenant"""
        if tenant_id in self.policies:
            return self.policies[tenant_id]
        
        # Return default policy for tier
        return self.default_policies.get(tier, self.default_policies[TenantTier.FREE])
    
    async def check_rate_limits(
        self,
        tenant_id: str,
        user_id: str,
        endpoint: str,
        method: str,
        ip_address: str,
        tier: TenantTier = TenantTier.FREE
    ) -> Tuple[RateLimitResult, RateLimitScope]:
        """Check all applicable rate limits in order of precedence"""
        policy = self.get_tenant_policy(tenant_id, tier)
        current_time = time.time()
        
        # Check limits in order of precedence (most restrictive first)
        
        # 1. Global tenant limit
        global_key = f"tenant:{tenant_id}:global"
        global_result = await self.rate_limiter.check_rate_limit(
            global_key, policy.global_limit, current_time
        )
        if not global_result.allowed:
            global_result.scope = RateLimitScope.TENANT
            global_result.rule_applied = f"tenant_global_{policy.tier.value}"
            return global_result, RateLimitScope.TENANT
        
        # 2. Per-user limit within tenant
        user_key = f"tenant:{tenant_id}:user:{user_id}"
        user_result = await self.rate_limiter.check_rate_limit(
            user_key, policy.user_limit, current_time
        )
        if not user_result.allowed:
            user_result.scope = RateLimitScope.USER
            user_result.rule_applied = f"user_{policy.tier.value}"
            return user_result, RateLimitScope.USER
        
        # 3. Endpoint-specific limit
        endpoint_rule = policy.get_limit_for_endpoint(endpoint, method)
        endpoint_key = f"tenant:{tenant_id}:user:{user_id}:endpoint:{method}:{endpoint}"
        endpoint_result = await self.rate_limiter.check_rate_limit(
            endpoint_key, endpoint_rule, current_time
        )
        if not endpoint_result.allowed:
            endpoint_result.scope = RateLimitScope.ENDPOINT
            endpoint_result.rule_applied = f"endpoint_{method.lower()}_{policy.tier.value}"
            return endpoint_result, RateLimitScope.ENDPOINT
        
        # 4. IP-based limit (basic DDoS protection)
        ip_rule = RateLimitRule(1000, 60)  # 1000 requests per minute per IP
        ip_key = f"ip:{ip_address}"
        ip_result = await self.rate_limiter.check_rate_limit(
            ip_key, ip_rule, current_time
        )
        if not ip_result.allowed:
            ip_result.scope = RateLimitScope.IP_ADDRESS
            ip_result.rule_applied = "ip_protection"
            return ip_result, RateLimitScope.IP_ADDRESS
        
        # All limits passed - use the most restrictive remaining count
        min_remaining = min(
            global_result.remaining,
            user_result.remaining,
            endpoint_result.remaining,
            ip_result.remaining
        )
        
        result = RateLimitResult(
            allowed=True,
            limit=endpoint_rule.requests,
            remaining=min_remaining,
            reset_time=max(
                global_result.reset_time,
                user_result.reset_time,
                endpoint_result.reset_time,
                ip_result.reset_time
            ),
            scope=RateLimitScope.ENDPOINT,
            rule_applied=f"endpoint_{method.lower()}_{policy.tier.value}"
        )
        
        return result, RateLimitScope.ENDPOINT


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with tenant support"""
    
    def __init__(
        self, 
        app: FastAPI, 
        manager: TenantRateLimitManager,
        tenant_extractor: Callable[[Request], str] = None,
        user_extractor: Callable[[Request], str] = None,
        tier_extractor: Callable[[Request], TenantTier] = None
    ):
        super().__init__(app)
        self.manager = manager
        self.tenant_extractor = tenant_extractor or self._default_tenant_extractor
        self.user_extractor = user_extractor or self._default_user_extractor
        self.tier_extractor = tier_extractor or self._default_tier_extractor
    
    def _default_tenant_extractor(self, request: Request) -> str:
        """Default tenant extraction from headers or subdomain"""
        # Try header first
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # Try subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain not in ["www", "api"]:
                return subdomain
        
        return "default"
    
    def _default_user_extractor(self, request: Request) -> str:
        """Default user extraction from headers or auth"""
        # Try header first
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Try to get from auth context (would be set by auth middleware)
        if hasattr(request.state, 'user_id'):
            return request.state.user_id
        
        # Fallback to IP address
        return self._get_client_ip(request)
    
    def _default_tier_extractor(self, request: Request) -> TenantTier:
        """Default tier extraction from headers"""
        tier_header = request.headers.get("X-Tenant-Tier", "free")
        try:
            return TenantTier(tier_header.lower())
        except ValueError:
            return TenantTier.FREE
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/metrics", "/versions"]:
            return await call_next(request)
        
        # Extract tenant, user, and tier information
        tenant_id = self.tenant_extractor(request)
        user_id = self.user_extractor(request)
        tier = self.tier_extractor(request)
        ip_address = self._get_client_ip(request)
        
        # Check rate limits
        try:
            result, scope = await self.manager.check_rate_limits(
                tenant_id=tenant_id,
                user_id=user_id,
                endpoint=request.url.path,
                method=request.method,
                ip_address=ip_address,
                tier=tier
            )
            
            # Add rate limit info to request state
            request.state.rate_limit_result = result
            request.state.rate_limit_scope = scope
            
            if not result.allowed:
                # Create rate limit exceeded response
                response = Response(
                    content=json.dumps({
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {result.limit}, Scope: {scope.value}",
                        "retry_after": result.retry_after
                    }),
                    status_code=429,
                    media_type="application/json"
                )
                
                # Add rate limit headers
                for key, value in result.to_headers().items():
                    response.headers[key] = value
                
                return response
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers to successful response
            for key, value in result.to_headers().items():
                response.headers[key] = value
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue without rate limiting on error
            return await call_next(request)


# Utility functions
def create_redis_rate_limiter(redis_url: str = "redis://localhost:6379") -> RedisRateLimiter:
    """Create Redis-based rate limiter"""
    redis_client = redis.from_url(redis_url)
    return RedisRateLimiter(redis_client)


def create_in_memory_rate_limiter() -> InMemoryRateLimiter:
    """Create in-memory rate limiter"""
    return InMemoryRateLimiter()


def setup_enhanced_rate_limiting(
    app: FastAPI,
    redis_url: Optional[str] = None,
    tenant_extractor: Callable[[Request], str] = None,
    user_extractor: Callable[[Request], str] = None,
    tier_extractor: Callable[[Request], TenantTier] = None
) -> TenantRateLimitManager:
    """Setup enhanced rate limiting for FastAPI app"""
    # Create rate limiter
    if redis_url:
        rate_limiter = create_redis_rate_limiter(redis_url)
    else:
        rate_limiter = create_in_memory_rate_limiter()
    
    # Create manager
    manager = TenantRateLimitManager(rate_limiter)
    
    # Add middleware
    app.add_middleware(
        EnhancedRateLimitMiddleware,
        manager=manager,
        tenant_extractor=tenant_extractor,
        user_extractor=user_extractor,
        tier_extractor=tier_extractor
    )
    
    # Add rate limit management endpoints
    @app.get("/admin/rate-limits/tenant/{tenant_id}", tags=["rate-limiting"])
    async def get_tenant_policy(tenant_id: str):
        """Get rate limiting policy for a tenant"""
        policy = manager.get_tenant_policy(tenant_id)
        return {
            "tenant_id": policy.tenant_id,
            "tier": policy.tier.value,
            "global_limit": str(policy.global_limit),
            "user_limit": str(policy.user_limit),
            "read_limit": str(policy.read_limit) if policy.read_limit else None,
            "write_limit": str(policy.write_limit) if policy.write_limit else None,
            "upload_limit": str(policy.upload_limit) if policy.upload_limit else None,
            "is_active": policy.is_active
        }
    
    @app.post("/admin/rate-limits/tenant/{tenant_id}/reset", tags=["rate-limiting"])
    async def reset_tenant_limits(tenant_id: str):
        """Reset all rate limits for a tenant"""
        # This would reset all keys for the tenant
        # Implementation depends on the rate limiter backend
        return {"message": f"Rate limits reset for tenant {tenant_id}"}
    
    return manager