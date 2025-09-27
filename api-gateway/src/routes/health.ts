/**
 * Health check routes for the API Gateway
 * Provides system status and service health monitoring
 */

import { Router, Request, Response } from 'express';
import { serviceRegistry } from '../services/registry.js';
import { logger } from '../utils/logger.js';

const router = Router();

/**
 * Basic health check endpoint
 * Returns 200 OK if the gateway is running
 */
router.get('/', (req: Request, res: Response) => {
  res.json({
    success: true,
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '1.0.0',
    uptime: process.uptime()
  });
});

/**
 * Detailed health check with service status
 * Returns health status of all registered services
 */
router.get('/detailed', async (req: Request, res: Response) => {
  try {
    const services = serviceRegistry.getAllServices();
    const serviceHealth = await Promise.allSettled(
      Object.entries(services).map(async ([name, url]) => {
        try {
          const response = await fetch(`${url}/health`, {
            method: 'GET',
            timeout: 5000
          });
          
          return {
            name,
            url,
            status: response.ok ? 'healthy' : 'unhealthy',
            responseTime: Date.now() - Date.now() // Simplified for now
          };
        } catch (error) {
          return {
            name,
            url,
            status: 'unreachable',
            error: error instanceof Error ? error.message : 'Unknown error'
          };
        }
      })
    );

    const healthResults = serviceHealth.map(result => 
      result.status === 'fulfilled' ? result.value : {
        name: 'unknown',
        status: 'error',
        error: result.reason
      }
    );

    const overallHealth = healthResults.every(service => service.status === 'healthy') 
      ? 'healthy' 
      : 'degraded';

    res.json({
      success: true,
      status: overallHealth,
      timestamp: new Date().toISOString(),
      gateway: {
        version: process.env.npm_package_version || '1.0.0',
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        nodeVersion: process.version
      },
      services: healthResults
    });

  } catch (error) {
    logger.error('Health check error:', error);
    res.status(500).json({
      success: false,
      status: 'error',
      error: 'Failed to check service health'
    });
  }
});

/**
 * Readiness probe for Kubernetes/container orchestration
 */
router.get('/ready', (req: Request, res: Response) => {
  // Check if all critical services are available
  const services = serviceRegistry.getAllServices();
  const hasRequiredServices = Object.keys(services).length > 0;
  
  if (hasRequiredServices) {
    res.json({
      success: true,
      status: 'ready',
      timestamp: new Date().toISOString()
    });
  } else {
    res.status(503).json({
      success: false,
      status: 'not ready',
      error: 'Required services not available'
    });
  }
});

/**
 * Liveness probe for Kubernetes/container orchestration
 */
router.get('/live', (req: Request, res: Response) => {
  res.json({
    success: true,
    status: 'alive',
    timestamp: new Date().toISOString()
  });
});

export default router;