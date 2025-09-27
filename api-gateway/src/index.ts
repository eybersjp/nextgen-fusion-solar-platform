/**
 * NextGen Fusion Commercial Solar Platform - API Gateway
 * Main entry point for the API Gateway service
 */

// Load environment variables FIRST
import dotenv from 'dotenv';
dotenv.config();

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { authMiddleware } from './middleware/auth.js';
import rateLimiterMiddleware from './middleware/rateLimiter.js';
import { errorHandler } from './middleware/error.js';
import { correlationMiddleware, performanceMiddleware, requestContextMiddleware } from './middleware/correlation.js';
import { tenantRateLimitMiddleware, burstProtectionMiddleware, rateLimitMonitoring, healthCheckBypass } from './middleware/rateLimiting.js';
import { versioningMiddleware, versionCompatibilityMiddleware } from './middleware/versioning.js';
import { cacheMiddleware, designCacheMiddleware, currencyCacheMiddleware, projectCacheMiddleware, complianceCacheMiddleware } from './middleware/cache.js';
import { initializeCache, CacheConfig } from './services/cache.js';
import { logger } from './utils/logger.js';
import { serviceRegistry } from './services/registry.js';
import healthRouter from './routes/health.js';
import authRouter from './routes/auth.js';
import pluginRouter from './routes/plugins.js';

const app = express();
const PORT = process.env['PORT'] || 3000;

// Initialize Redis cache
const cacheConfig: CacheConfig = {
  host: process.env['REDIS_HOST'] || 'localhost',
  port: parseInt(process.env['REDIS_PORT'] || '6379'),
  password: process.env['REDIS_PASSWORD'],
  db: parseInt(process.env['REDIS_DB'] || '0'),
  keyPrefix: process.env['REDIS_KEY_PREFIX'] || 'nf:',
};

const cache = initializeCache(cacheConfig);

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
      connectSrc: ["'self'"],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
    },
  },
  crossOriginEmbedderPolicy: false
}));

// CORS configuration
app.use(cors({
  origin: process.env['ALLOWED_ORIGINS']?.split(',') || ['http://localhost:5173'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

// Compression and logging
app.use(compression());

// Correlation ID and request tracking (must be early in middleware chain)
app.use(correlationMiddleware({
  headerName: 'x-correlation-id',
  setResponseHeader: true,
  logRequests: true,
  includeUserAgent: true,
  includeIP: true
}));

// Performance monitoring
app.use(performanceMiddleware());

// Request context storage
app.use(requestContextMiddleware());

// Enhanced logging with correlation ID
app.use(morgan('combined', {
  stream: {
    write: (message: string) => logger.info(message.trim())
  }
}));

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// API versioning (before rate limiting to allow version-specific limits)
app.use(versioningMiddleware({
  supportedVersions: ['v1', 'v2'],
  defaultVersion: 'v1',
  deprecatedVersions: [
    {
      version: 'v1',
      deprecationDate: '2024-06-01',
      sunsetDate: '2024-12-31',
      message: 'API v1 is deprecated. Please migrate to v2.'
    }
  ],
  versionHeader: 'api-version',
  versionParam: 'version',
  versionPath: true
}));

// Version compatibility transformations
app.use(versionCompatibilityMiddleware());

// Rate limiting with health check bypass
app.use(healthCheckBypass);
app.use(rateLimitMonitoring());
app.use(tenantRateLimitMiddleware());
app.use(burstProtectionMiddleware({
  burstLimit: 20,
  burstWindowMs: 60 * 1000, // 1 minute
  sustainedLimit: 100,
  sustainedWindowMs: 15 * 60 * 1000 // 15 minutes
}));
app.use(rateLimiterMiddleware);

// Health check and system routes (no auth required)
app.use('/health', healthRouter);
app.use('/auth', authRouter);

// Plugin management routes (admin auth required)
app.use('/api/plugins', authMiddleware, pluginRouter);

// Service-specific caching middleware
app.use('/api/*/design', designCacheMiddleware);
app.use('/api/*/currency', currencyCacheMiddleware);
app.use('/api/*/project', projectCacheMiddleware);
app.use('/api/*/compliance', complianceCacheMiddleware);

// Service proxy routes with authentication
const createServiceProxy = (serviceName: string, pathPrefix: string) => {
  try {
    const targetUrl = serviceRegistry.getServiceUrl(serviceName);
    logger.info(`Creating proxy for ${serviceName} with target: ${targetUrl}`);
    
    return createProxyMiddleware({
      target: targetUrl,
      changeOrigin: true,
      pathRewrite: {
        [`^${pathPrefix}`]: ''
      },
      onProxyReq: (proxyReq, req, res) => {
        // Forward user context to services
        if (req.user) {
          proxyReq.setHeader('X-User-ID', req.user.id);
          proxyReq.setHeader('X-User-Role', req.user.role);
          proxyReq.setHeader('X-Organization-ID', req.user.organization_id || '');
        }
        
        // Log the proxied request
        logger.info(`Proxying ${req.method} ${req.path} to ${serviceName}`);
      },
      onError: (err, req, res) => {
        logger.error(`Proxy error for ${serviceName}:`, err);
        res.status(502).json({
          success: false,
          error: 'Service temporarily unavailable'
        });
      }
    });
  } catch (error) {
    logger.error(`Error creating proxy for ${serviceName}:`, error);
    throw error;
  }
};

// Dynamic service proxy setup - only create proxies for registered services
// Move this inside route handlers to avoid initialization issues

// Design service routes (FastAPI backend) - MUST BE BEFORE /api/projects
// Simple test route for debugging
app.get('/api/test', (req, res) => {
  console.log('=== /api/test route hit ===');
  console.log('req.path:', req.path);
  console.log('req.url:', req.url);
  
  try {
    const services = serviceRegistry.getAllServices();
    console.log('Services from registry:', services);
    
    res.json({ 
      success: true, 
      message: 'Test route working', 
      path: req.path,
      services: services
    });
  } catch (error) {
    console.log('Error in test route:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Debug route to test middleware chain
app.get('/api/debug/middleware', (req, res) => {
  console.log('=== Debug middleware route hit ===');
  console.log('req.path:', req.path);
  console.log('req.url:', req.url);
  console.log('req.originalUrl:', req.originalUrl);
  res.json({
    success: true,
    message: 'Middleware debug route working',
    path: req.path,
    url: req.url,
    originalUrl: req.originalUrl
  });
});

// Debug route to test design service connection
app.get('/api/design/debug', async (req, res) => {
  try {
    const response = await fetch('http://localhost:8001/health');
    const data = await response.json();
    res.json({ success: true, message: 'Direct connection to design service', data });
  } catch (error) {
    res.json({ success: false, error: error.message });
  }
});

// IMPORTANT: Specific routes MUST come before general routes
// Health check route without auth for testing
app.get('/api/design/health', async (req, res) => {
  console.log('=== /api/design/health route hit ===');
  try {
    const response = await fetch('http://localhost:8001/health');
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.log('Direct fetch error:', error.message);
    res.status(502).json({
      success: false,
      error: 'Design service temporarily unavailable'
    });
  }
});

// Test route without auth for debugging
app.get('/api/design/test', async (req, res) => {
  console.log('=== /api/design/test route hit ===');
  try {
    const response = await fetch('http://localhost:8001/api/v1/design/test');
    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.log('Direct fetch error:', error.message);
    res.status(502).json({
      success: false,
      error: 'Design service temporarily unavailable'
    });
  }
});

// All other design routes require authentication - MUST be last
// Temporarily removing authMiddleware to debug
app.use('/api/design', createProxyMiddleware({
  target: 'http://localhost:8001',
  changeOrigin: true,
  pathRewrite: {
    '^/api/design': '/api/v1'
  },
  onProxyReq: (proxyReq, req, res) => {
    // Forward user context to services
    if (req.user) {
      proxyReq.setHeader('X-User-ID', req.user.id);
      proxyReq.setHeader('X-User-Role', req.user.role);
      proxyReq.setHeader('X-Organization-ID', req.user.organization_id || '');
    }
    
    // Log the proxied request
    logger.info(`Proxying ${req.method} ${req.path} to svc-design`);
  },
  onError: (err, req, res) => {
    logger.error(`Proxy error for svc-design:`, err);
    res.status(502).json({
      success: false,
      error: 'Design service temporarily unavailable'
    });
  }
}));

// Placeholder routes for services not yet implemented
const createPlaceholderRoute = (path: string, serviceName: string) => {
  app.use(path, authMiddleware, (req, res) => {
    res.status(503).json({
      success: false,
      error: `${serviceName} service is not yet implemented`,
      message: 'This service will be available in a future release'
    });
  });
};

// Get registered services dynamically
const getRegisteredServices = () => {
  try {
    return serviceRegistry.getAllServices();
  } catch (error) {
    logger.error('Error getting registered services:', error);
    return {};
  }
};

// Currency service routes - lazy proxy creation
app.use('/api/currency', authMiddleware, (req, res, next) => {
  try {
    const currencyServices = getRegisteredServices()['svc-currency'];
    if (currencyServices && currencyServices.length > 0) {
      const proxy = createServiceProxy('svc-currency', '/api/currency');
      proxy(req, res, next);
    } else {
      res.status(503).json({
        success: false,
        error: 'Currency service is not available',
        message: 'Service is starting up or temporarily unavailable'
      });
    }
  } catch (error) {
    logger.error('Currency service proxy error:', error);
    res.status(503).json({
      success: false,
      error: 'Currency service temporarily unavailable'
    });
  }
});

// Compliance service routes - lazy proxy creation
app.use('/api/compliance', authMiddleware, (req, res, next) => {
  try {
    const complianceServices = getRegisteredServices()['svc-compliance'];
    if (complianceServices && complianceServices.length > 0) {
      const proxy = createServiceProxy('svc-compliance', '/api/compliance');
      proxy(req, res, next);
    } else {
      res.status(503).json({
        success: false,
        error: 'Compliance service is not available',
        message: 'Service is starting up or temporarily unavailable'
      });
    }
  } catch (error) {
    logger.error('Compliance service proxy error:', error);
    res.status(503).json({
      success: false,
      error: 'Compliance service temporarily unavailable'
    });
  }
});

// Project service routes - lazy proxy creation
app.use('/api/project', authMiddleware, (req, res, next) => {
  try {
    const projectServices = getRegisteredServices()['svc-project'];
    if (projectServices && projectServices.length > 0) {
      const proxy = createServiceProxy('svc-project', '/api/project');
      proxy(req, res, next);
    } else {
      res.status(503).json({
        success: false,
        error: 'Project service is not available',
        message: 'Service is starting up or temporarily unavailable'
      });
    }
  } catch (error) {
    logger.error('Project service proxy error:', error);
    res.status(503).json({
      success: false,
      error: 'Project service temporarily unavailable'
    });
  }
});

// Create placeholder routes for unimplemented services
const allServices = getRegisteredServices();
if (!allServices['svc-finance']) {
  createPlaceholderRoute('/api/finance', 'Finance');
}
if (!allServices['svc-procure']) {
  createPlaceholderRoute('/api/procure', 'Procurement');
}
if (!allServices['svc-ops']) {
  createPlaceholderRoute('/api/ops', 'Operations');
}
if (!allServices['svc-support']) {
  createPlaceholderRoute('/api/support', 'Support');
}

// Projects API (direct implementation for core functionality)
// Handle exact /api/projects path
app.get('/api/projects', authMiddleware, async (req, res, next) => {
  try {
    res.json({
      success: true,
      data: [],
      message: 'Projects endpoint - implementation pending'
    });
  } catch (error) {
    next(error);
  }
});

// Handle /api/projects/metrics
app.get('/api/projects/metrics', authMiddleware, async (req, res, next) => {
  try {
    res.json({
      success: true,
      metrics: {
        total_projects: 0,
        active_projects: 0,
        completed_projects: 0,
        total_capacity_kw: 0,
        total_investment: 0,
        average_progress: 0
      }
    });
  } catch (error) {
    next(error);
  }
});

// Handle specific project by ID
app.get('/api/projects/:id', authMiddleware, async (req, res, next) => {
  try {
    res.json({
      success: true,
      data: null,
      message: 'Project detail endpoint - implementation pending'
    });
  } catch (error) {
    next(error);
  }
});

// Create project
app.post('/api/projects', authMiddleware, async (req, res, next) => {
  try {
    res.json({
      success: true,
      data: null,
      message: 'Create project endpoint - implementation pending'
    });
  } catch (error) {
    next(error);
  }
});

// Update project
app.put('/api/projects/:id', authMiddleware, async (req, res, next) => {
  try {
    res.json({
      success: true,
      data: null,
      message: 'Update project endpoint - implementation pending'
    });
  } catch (error) {
    next(error);
  }
});

// Delete project
app.delete('/api/projects/:id', authMiddleware, async (req, res, next) => {
  try {
    res.json({
      success: true,
      message: 'Delete project endpoint - implementation pending'
    });
  } catch (error) {
    next(error);
  }
});

// Catch-all for undefined routes
app.use('*', (req, res) => {
  res.status(404).json({
    success: false,
    error: 'API endpoint not found',
    path: req.originalUrl
  });
});

// Error handling middleware
app.use(errorHandler);

// Start server
app.listen(PORT, async () => {
  logger.info(`API Gateway started on port ${PORT}`);
  
  // Initialize Redis cache
  try {
    await cache.connect();
    logger.info('Redis cache connected successfully');
  } catch (error) {
    logger.error('Failed to connect to Redis cache:', error);
    logger.warn('API Gateway will continue without caching');
  }
  
  logger.info('Service registry:', serviceRegistry.getAllServices());
  
  // Log configuration
  logger.info('API Gateway configuration:', {
    port: PORT,
    environment: process.env['NODE_ENV'] || 'development',
    redisHost: process.env['REDIS_HOST'] || 'localhost',
    redisPort: process.env['REDIS_PORT'] || '6379',
    corsOrigin: process.env['ALLOWED_ORIGINS'] || 'http://localhost:5173',
    supportedVersions: ['v1', 'v2'],
    defaultVersion: 'v1'
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  
  try {
    await cache.disconnect();
    logger.info('Redis cache disconnected');
  } catch (error) {
    logger.error('Error disconnecting Redis cache:', error);
  }
  
  process.exit(0);
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully');
  
  try {
    await cache.disconnect();
    logger.info('Redis cache disconnected');
  } catch (error) {
    logger.error('Error disconnecting Redis cache:', error);
  }
  
  process.exit(0);
});

export default app;