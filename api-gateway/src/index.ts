/**
 * NextGen Fusion Commercial Solar Platform - API Gateway
 * Main entry point for the API Gateway service
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { createProxyMiddleware } from 'http-proxy-middleware';
import dotenv from 'dotenv';
import { authMiddleware } from './middleware/auth.js';
import { errorHandler } from './middleware/error.js';
import { logger } from './utils/logger.js';
import { serviceRegistry } from './services/registry.js';
import { healthRouter } from './routes/health.js';
import { authRouter } from './routes/auth.js';
import { pluginRouter } from './routes/plugins.js';

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

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
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:5173'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

// Compression and logging
app.use(compression());
app.use(morgan('combined', {
  stream: {
    write: (message: string) => logger.info(message.trim())
  }
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // limit each IP to 1000 requests per windowMs
  message: {
    error: 'Too many requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false
});
app.use(limiter);

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Health check and system routes (no auth required)
app.use('/health', healthRouter);
app.use('/auth', authRouter);

// Plugin management routes (admin auth required)
app.use('/api/plugins', authMiddleware, pluginRouter);

// Service proxy routes with authentication
const createServiceProxy = (serviceName: string, pathPrefix: string) => {
  return createProxyMiddleware({
    target: serviceRegistry.getServiceUrl(serviceName),
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
};

// Design service routes
app.use('/api/design', authMiddleware, createServiceProxy('svc-design', '/api/design'));

// Compliance service routes
app.use('/api/compliance', authMiddleware, createServiceProxy('svc-compliance', '/api/compliance'));

// Finance service routes
app.use('/api/finance', authMiddleware, createServiceProxy('svc-finance', '/api/finance'));

// Procurement service routes
app.use('/api/procure', authMiddleware, createServiceProxy('svc-procure', '/api/procure'));

// Operations service routes
app.use('/api/ops', authMiddleware, createServiceProxy('svc-ops', '/api/ops'));

// Support service routes
app.use('/api/support', authMiddleware, createServiceProxy('svc-support', '/api/support'));

// Projects API (direct implementation for core functionality)
app.use('/api/projects', authMiddleware, async (req, res, next) => {
  // This could be implemented directly in the gateway or proxied to a dedicated service
  // For now, we'll implement basic CRUD operations here
  try {
    const { method, path } = req;
    
    switch (method) {
      case 'GET':
        if (path === '/api/projects') {
          // List projects
          res.json({
            success: true,
            data: [],
            message: 'Projects endpoint - implementation pending'
          });
        } else {
          // Get specific project
          res.json({
            success: true,
            data: null,
            message: 'Project detail endpoint - implementation pending'
          });
        }
        break;
        
      case 'POST':
        // Create project
        res.json({
          success: true,
          data: null,
          message: 'Create project endpoint - implementation pending'
        });
        break;
        
      case 'PUT':
      case 'PATCH':
        // Update project
        res.json({
          success: true,
          data: null,
          message: 'Update project endpoint - implementation pending'
        });
        break;
        
      case 'DELETE':
        // Delete project
        res.json({
          success: true,
          message: 'Delete project endpoint - implementation pending'
        });
        break;
        
      default:
        res.status(405).json({
          success: false,
          error: 'Method not allowed'
        });
    }
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
app.listen(PORT, () => {
  logger.info(`API Gateway started on port ${PORT}`);
  logger.info('Service registry:', serviceRegistry.getAllServices());
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  process.exit(0);
});

export default app;