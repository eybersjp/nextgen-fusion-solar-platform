import { Request, Response, NextFunction } from 'express';
import { getCache } from '../services/cache';
import { logger } from '../utils/logger';
import { getCorrelationId } from './correlation';

export interface RateLimitConfig {
  windowMs: number; // Time window in milliseconds
  maxRequests: number; // Maximum requests per window
  keyGenerator?: (req: Request) => string;
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
  onLimitReached?: (req: Request, res: Response) => void;
  message?: string;
  headers?: boolean;
}

export interface TenantRateLimitConfig extends RateLimitConfig {
  tenantId: string;
  tier: 'free' | 'basic' | 'premium' | 'enterprise';
  customLimits?: {
    [endpoint: string]: Partial<RateLimitConfig>;
  };
}

// Default rate limit configurations by tier
const DEFAULT_TIER_LIMITS: Record<string, RateLimitConfig> = {
  free: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    maxRequests: 100,
    message: 'Too many requests from this IP, please try again later.'
  },
  basic: {
    windowMs: 15 * 60 * 1000,
    maxRequests: 500,
    message: 'Rate limit exceeded for basic tier.'
  },
  premium: {
    windowMs: 15 * 60 * 1000,
    maxRequests: 2000,
    message: 'Rate limit exceeded for premium tier.'
  },
  enterprise: {
    windowMs: 15 * 60 * 1000,
    maxRequests: 10000,
    message: 'Rate limit exceeded for enterprise tier.'
  }
};

// Endpoint-specific rate limits
const ENDPOINT_LIMITS: Record<string, Partial<RateLimitConfig>> = {
  '/api/v1/auth/login': {
    windowMs: 15 * 60 * 1000,
    maxRequests: 5, // Strict limit for login attempts
    message: 'Too many login attempts, please try again later.'
  },
  '/api/v1/auth/register': {
    windowMs: 60 * 60 * 1000, // 1 hour
    maxRequests: 3,
    message: 'Too many registration attempts, please try again later.'
  },
  '/api/v1/design/optimize': {
    windowMs: 5 * 60 * 1000, // 5 minutes
    maxRequests: 10, // Expensive operation
    message: 'Too many optimization requests, please try again later.'
  },
  '/api/v1/compliance/validate': {
    windowMs: 10 * 60 * 1000, // 10 minutes
    maxRequests: 50,
    message: 'Too many validation requests, please try again later.'
  }
};

// Rate limit store using Redis
class RateLimitStore {
  private cache = getCache();
  
  async increment(key: string, windowMs: number): Promise<{ count: number; resetTime: number }> {
    if (!this.cache) {
      throw new Error('Cache service not available for rate limiting');
    }
    
    const now = Date.now();
    const windowStart = Math.floor(now / windowMs) * windowMs;
    const resetTime = windowStart + windowMs;
    const cacheKey = `ratelimit:${key}:${windowStart}`;
    
    try {
      // Use Redis INCR for atomic increment
      const count = await this.cache.redis.incr(cacheKey);
      
      // Set expiration on first increment
      if (count === 1) {
        await this.cache.redis.expire(cacheKey, Math.ceil(windowMs / 1000));
      }
      
      return { count, resetTime };
    } catch (error) {
      logger.error('Rate limit store error:', error);
      throw error;
    }
  }
  
  async get(key: string, windowMs: number): Promise<{ count: number; resetTime: number }> {
    if (!this.cache) {
      return { count: 0, resetTime: Date.now() + windowMs };
    }
    
    const now = Date.now();
    const windowStart = Math.floor(now / windowMs) * windowMs;
    const resetTime = windowStart + windowMs;
    const cacheKey = `ratelimit:${key}:${windowStart}`;
    
    try {
      const count = await this.cache.redis.get(cacheKey);
      return { count: parseInt(count || '0', 10), resetTime };
    } catch (error) {
      logger.error('Rate limit get error:', error);
      return { count: 0, resetTime };
    }
  }
  
  async reset(key: string): Promise<void> {
    if (!this.cache) {
      return;
    }
    
    try {
      const pattern = `ratelimit:${key}:*`;
      await this.cache.delPattern(pattern);
    } catch (error) {
      logger.error('Rate limit reset error:', error);
    }
  }
}

const rateLimitStore = new RateLimitStore();

// Default key generator
const defaultKeyGenerator = (req: Request): string => {
  const ip = req.ip || req.connection.remoteAddress || 'unknown';
  const userId = req.user?.id;
  const tenantId = req.headers['x-tenant-id'] as string;
  
  // Use user ID if authenticated, otherwise IP
  if (userId) {
    return `user:${userId}:${tenantId || 'default'}`;
  }
  
  return `ip:${ip}:${tenantId || 'default'}`;
};

// Basic rate limiting middleware
export const rateLimitMiddleware = (config: RateLimitConfig) => {
  const {
    windowMs,
    maxRequests,
    keyGenerator = defaultKeyGenerator,
    skipSuccessfulRequests = false,
    skipFailedRequests = false,
    onLimitReached,
    message = 'Too many requests, please try again later.',
    headers = true
  } = config;
  
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      const key = keyGenerator(req);
      const correlationId = getCorrelationId(req);
      
      // Get current count
      const { count, resetTime } = await rateLimitStore.get(key, windowMs);
      
      // Set rate limit headers
      if (headers) {
        res.setHeader('X-RateLimit-Limit', maxRequests.toString());
        res.setHeader('X-RateLimit-Remaining', Math.max(0, maxRequests - count).toString());
        res.setHeader('X-RateLimit-Reset', Math.ceil(resetTime / 1000).toString());
        res.setHeader('X-RateLimit-Window', windowMs.toString());
      }
      
      // Check if limit exceeded
      if (count >= maxRequests) {
        logger.warn('Rate limit exceeded', {
          correlationId,
          key,
          count,
          limit: maxRequests,
          resetTime: new Date(resetTime).toISOString(),
          ip: req.ip,
          userAgent: req.headers['user-agent'],
          endpoint: req.originalUrl
        });
        
        if (onLimitReached) {
          onLimitReached(req, res);
        }
        
        return res.status(429).json({
          error: 'Rate limit exceeded',
          message,
          retryAfter: Math.ceil((resetTime - Date.now()) / 1000),
          correlationId
        });
      }
      
      // Increment counter after successful check
      const originalEnd = res.end;
      res.end = function(chunk?: any, encoding?: any) {
        const shouldCount = (
          (!skipSuccessfulRequests || res.statusCode >= 400) &&
          (!skipFailedRequests || res.statusCode < 400)
        );
        
        if (shouldCount) {
          rateLimitStore.increment(key, windowMs).catch(error => {
            logger.error('Failed to increment rate limit counter:', error);
          });
        }
        
        return originalEnd.call(this, chunk, encoding);
      };
      
      next();
    } catch (error) {
      logger.error('Rate limiting middleware error:', error);
      // Continue without rate limiting on error
      next();
    }
  };
};

// Tenant-aware rate limiting
export const tenantRateLimitMiddleware = () => {
  return async (req: Request, res: Response, next: NextFunction) => {
    const tenantId = req.headers['x-tenant-id'] as string || 'default';
    const endpoint = req.route?.path || req.path;
    
    try {
      // Get tenant configuration (in real app, this would come from database)
      const tenantConfig = await getTenantRateLimitConfig(tenantId);
      
      // Check for endpoint-specific limits
      const endpointConfig = tenantConfig.customLimits?.[endpoint] || ENDPOINT_LIMITS[endpoint];
      
      // Merge configurations
      const finalConfig: RateLimitConfig = {
        ...DEFAULT_TIER_LIMITS[tenantConfig.tier],
        ...endpointConfig,
        keyGenerator: (req: Request) => `tenant:${tenantId}:${endpoint}:${req.user?.id || req.ip}`
      };
      
      // Apply rate limiting
      const rateLimitHandler = rateLimitMiddleware(finalConfig);
      await rateLimitHandler(req, res, next);
      
    } catch (error) {
      logger.error('Tenant rate limiting error:', error);
      // Fallback to default rate limiting
      const defaultHandler = rateLimitMiddleware(DEFAULT_TIER_LIMITS.free);
      await defaultHandler(req, res, next);
    }
  };
};

// Get tenant rate limit configuration
async function getTenantRateLimitConfig(tenantId: string): Promise<TenantRateLimitConfig> {
  // In a real application, this would fetch from database
  // For now, return default configuration based on tenant ID pattern
  
  const cache = getCache();
  const cacheKey = `tenant:config:${tenantId}`;
  
  if (cache) {
    const cached = await cache.get<TenantRateLimitConfig>(cacheKey);
    if (cached) {
      return cached;
    }
  }
  
  // Default configuration logic
  let tier: 'free' | 'basic' | 'premium' | 'enterprise' = 'free';
  
  if (tenantId.includes('enterprise')) {
    tier = 'enterprise';
  } else if (tenantId.includes('premium')) {
    tier = 'premium';
  } else if (tenantId.includes('basic')) {
    tier = 'basic';
  }
  
  const config: TenantRateLimitConfig = {
    tenantId,
    tier,
    ...DEFAULT_TIER_LIMITS[tier],
    customLimits: {}
  };
  
  // Cache the configuration
  if (cache) {
    await cache.set(cacheKey, config, 3600); // Cache for 1 hour
  }
  
  return config;
}

// Burst protection middleware
export const burstProtectionMiddleware = (config: {
  burstLimit: number;
  burstWindowMs: number;
  sustainedLimit: number;
  sustainedWindowMs: number;
}) => {
  const { burstLimit, burstWindowMs, sustainedLimit, sustainedWindowMs } = config;
  
  return async (req: Request, res: Response, next: NextFunction) => {
    const key = defaultKeyGenerator(req);
    
    try {
      // Check burst limit (short window)
      const burstResult = await rateLimitStore.get(`burst:${key}`, burstWindowMs);
      if (burstResult.count >= burstLimit) {
        return res.status(429).json({
          error: 'Burst limit exceeded',
          message: 'Too many requests in a short time period',
          retryAfter: Math.ceil((burstResult.resetTime - Date.now()) / 1000)
        });
      }
      
      // Check sustained limit (longer window)
      const sustainedResult = await rateLimitStore.get(`sustained:${key}`, sustainedWindowMs);
      if (sustainedResult.count >= sustainedLimit) {
        return res.status(429).json({
          error: 'Sustained limit exceeded',
          message: 'Too many requests over time',
          retryAfter: Math.ceil((sustainedResult.resetTime - Date.now()) / 1000)
        });
      }
      
      // Increment both counters
      const originalEnd = res.end;
      res.end = function(chunk?: any, encoding?: any) {
        Promise.all([
          rateLimitStore.increment(`burst:${key}`, burstWindowMs),
          rateLimitStore.increment(`sustained:${key}`, sustainedWindowMs)
        ]).catch(error => {
          logger.error('Failed to increment burst protection counters:', error);
        });
        
        return originalEnd.call(this, chunk, encoding);
      };
      
      next();
    } catch (error) {
      logger.error('Burst protection middleware error:', error);
      next();
    }
  };
};

// Rate limit bypass for specific conditions
export const rateLimitBypass = (condition: (req: Request) => boolean) => {
  return (req: Request, res: Response, next: NextFunction) => {
    if (condition(req)) {
      // Skip rate limiting
      res.setHeader('X-RateLimit-Bypassed', 'true');
      return next();
    }
    
    next();
  };
};

// Admin endpoints bypass
export const adminBypass = rateLimitBypass((req: Request) => {
  return req.user?.role === 'admin' || req.user?.permissions?.includes('bypass_rate_limit');
});

// Health check bypass
export const healthCheckBypass = rateLimitBypass((req: Request) => {
  return req.path === '/health' || req.path === '/api/health';
});

// Rate limit monitoring and alerting
export const rateLimitMonitoring = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    const originalEnd = res.end;
    
    res.end = function(chunk?: any, encoding?: any) {
      if (res.statusCode === 429) {
        // Log rate limit hit for monitoring
        logger.warn('Rate limit triggered', {
          correlationId: getCorrelationId(req),
          ip: req.ip,
          userAgent: req.headers['user-agent'],
          endpoint: req.originalUrl,
          method: req.method,
          userId: req.user?.id,
          tenantId: req.headers['x-tenant-id'],
          timestamp: new Date().toISOString()
        });
        
        // Could trigger alerts here for high rate limit violations
      }
      
      return originalEnd.call(this, chunk, encoding);
    };
    
    next();
  };
};

export { rateLimitStore };