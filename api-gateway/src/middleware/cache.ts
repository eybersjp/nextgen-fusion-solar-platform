import { Request, Response, NextFunction } from 'express';
import { getCache, CacheKeys } from '../services/cache';
import { logger } from '../utils/logger';
import crypto from 'crypto';

export interface CacheOptions {
  ttl?: number; // Time to live in seconds
  keyGenerator?: (req: Request) => string;
  condition?: (req: Request, res: Response) => boolean;
  skipCache?: (req: Request) => boolean;
  varyBy?: string[]; // Headers to vary cache by
}

// Default cache key generator
const defaultKeyGenerator = (req: Request): string => {
  const { method, originalUrl, query, headers } = req;
  const userId = req.user?.id || 'anonymous';
  const tenant = headers['x-tenant-id'] || 'default';
  
  // Create a hash of query parameters for consistent keys
  const queryHash = crypto
    .createHash('md5')
    .update(JSON.stringify(query))
    .digest('hex');
  
  return `api:${method}:${originalUrl}:${userId}:${tenant}:${queryHash}`;
};

// Cache middleware factory
export const cacheMiddleware = (options: CacheOptions = {}) => {
  const {
    ttl = 300, // 5 minutes default
    keyGenerator = defaultKeyGenerator,
    condition = () => true,
    skipCache = () => false,
    varyBy = ['authorization', 'x-tenant-id']
  } = options;

  return async (req: Request, res: Response, next: NextFunction) => {
    // Skip caching for non-GET requests or when condition not met
    if (req.method !== 'GET' || skipCache(req)) {
      return next();
    }

    const cache = getCache();
    if (!cache) {
      logger.warn('Cache service not available, skipping cache middleware');
      return next();
    }

    try {
      const cacheKey = keyGenerator(req);
      
      // Try to get from cache
      const cachedResponse = await cache.get<{
        statusCode: number;
        headers: Record<string, string>;
        body: any;
        timestamp: number;
      }>(cacheKey);

      if (cachedResponse) {
        logger.debug(`Cache hit for key: ${cacheKey}`);
        
        // Set cached headers
        Object.entries(cachedResponse.headers).forEach(([key, value]) => {
          res.setHeader(key, value);
        });
        
        // Add cache headers
        res.setHeader('X-Cache', 'HIT');
        res.setHeader('X-Cache-Key', cacheKey);
        res.setHeader('X-Cache-Timestamp', cachedResponse.timestamp.toString());
        
        return res.status(cachedResponse.statusCode).json(cachedResponse.body);
      }

      // Cache miss - intercept response
      logger.debug(`Cache miss for key: ${cacheKey}`);
      
      const originalSend = res.json;
      const originalStatus = res.status;
      let statusCode = 200;
      
      // Override status method to capture status code
      res.status = function(code: number) {
        statusCode = code;
        return originalStatus.call(this, code);
      };
      
      // Override json method to cache response
      res.json = function(body: any) {
        // Only cache successful responses
        if (statusCode >= 200 && statusCode < 300 && condition(req, res)) {
          const responseToCache = {
            statusCode,
            headers: extractCacheableHeaders(res, varyBy),
            body,
            timestamp: Date.now()
          };
          
          // Cache asynchronously (don't wait)
          cache.set(cacheKey, responseToCache, ttl).catch(error => {
            logger.error(`Failed to cache response for key ${cacheKey}:`, error);
          });
          
          // Add cache headers
          res.setHeader('X-Cache', 'MISS');
          res.setHeader('X-Cache-Key', cacheKey);
        }
        
        return originalSend.call(this, body);
      };
      
      next();
    } catch (error) {
      logger.error('Cache middleware error:', error);
      next(); // Continue without caching on error
    }
  };
};

// Extract headers that should be cached
const extractCacheableHeaders = (res: Response, varyBy: string[]): Record<string, string> => {
  const headers: Record<string, string> = {};
  
  // Standard cacheable headers
  const cacheableHeaders = [
    'content-type',
    'content-encoding',
    'content-language',
    'etag',
    'last-modified',
    ...varyBy
  ];
  
  cacheableHeaders.forEach(header => {
    const value = res.getHeader(header);
    if (value && typeof value === 'string') {
      headers[header] = value;
    }
  });
  
  return headers;
};

// Service-specific cache middleware
export const designCacheMiddleware = cacheMiddleware({
  ttl: 600, // 10 minutes for design data
  keyGenerator: (req) => {
    const { params, query } = req;
    const userId = req.user?.id || 'anonymous';
    return CacheKeys.design.model(`${params.id || 'list'}:${userId}:${JSON.stringify(query)}`);
  },
  condition: (req, res) => {
    // Cache successful GET requests for design data
    return req.method === 'GET' && res.statusCode < 300;
  }
});

export const currencyCacheMiddleware = cacheMiddleware({
  ttl: 300, // 5 minutes for currency rates
  keyGenerator: (req) => {
    const { query } = req;
    const base = query.base as string || 'USD';
    const target = query.target as string || 'ZAR';
    return CacheKeys.currency.rates(base, target);
  },
  condition: (req, res) => {
    return req.method === 'GET' && res.statusCode < 300;
  }
});

export const projectCacheMiddleware = cacheMiddleware({
  ttl: 180, // 3 minutes for project data (more dynamic)
  keyGenerator: (req) => {
    const { params, query } = req;
    const userId = req.user?.id || 'anonymous';
    return CacheKeys.project.details(`${params.id || 'list'}:${userId}:${JSON.stringify(query)}`);
  },
  skipCache: (req) => {
    // Skip cache for write operations
    return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method);
  }
});

export const complianceCacheMiddleware = cacheMiddleware({
  ttl: 1800, // 30 minutes for compliance rules (relatively static)
  keyGenerator: (req) => {
    const { params, query } = req;
    const jurisdiction = query.jurisdiction as string || params.jurisdiction || 'default';
    return CacheKeys.compliance.rules(jurisdiction);
  },
  condition: (req, res) => {
    return req.method === 'GET' && res.statusCode < 300;
  }
});

// Cache invalidation middleware
export const cacheInvalidationMiddleware = (patterns: string[]) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    const cache = getCache();
    if (!cache) {
      return next();
    }

    // Store original end function
    const originalEnd = res.end;
    
    res.end = function(chunk?: any, encoding?: any) {
      // Only invalidate on successful write operations
      if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method) && res.statusCode < 400) {
        // Invalidate cache patterns asynchronously
        Promise.all(
          patterns.map(pattern => cache.delPattern(pattern))
        ).catch(error => {
          logger.error('Cache invalidation error:', error);
        });
      }
      
      return originalEnd.call(this, chunk, encoding);
    };
    
    next();
  };
};

// Cache warming utility
export const warmCache = async (keys: { key: string; fetcher: () => Promise<any>; ttl?: number }[]) => {
  const cache = getCache();
  if (!cache) {
    logger.warn('Cache service not available for warming');
    return;
  }

  logger.info(`Warming cache with ${keys.length} keys`);
  
  const results = await Promise.allSettled(
    keys.map(async ({ key, fetcher, ttl }) => {
      try {
        const data = await fetcher();
        await cache.set(key, data, ttl);
        return { key, success: true };
      } catch (error) {
        logger.error(`Failed to warm cache for key ${key}:`, error);
        return { key, success: false, error };
      }
    })
  );
  
  const successful = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
  logger.info(`Cache warming completed: ${successful}/${keys.length} keys warmed successfully`);
};