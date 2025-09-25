/**
 * Service registry for managing microservice endpoints
 * Handles service discovery, health checks, and load balancing
 */

import { logger } from '../utils/logger.js';

interface ServiceEndpoint {
  id: string;
  name: string;
  url: string;
  health: string;
  version: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  lastCheck: Date;
  metadata?: Record<string, any>;
}

interface ServiceConfig {
  name: string;
  urls: string[];
  healthPath: string;
  timeout: number;
  retries: number;
}

class ServiceRegistry {
  private services: Map<string, ServiceEndpoint[]> = new Map();
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private readonly HEALTH_CHECK_INTERVAL = 30000; // 30 seconds

  constructor() {
    this.initializeServices();
    this.startHealthChecks();
  }

  /**
   * Initialize services from environment variables
   */
  private initializeServices() {
    const serviceConfigs: ServiceConfig[] = [
      {
        name: 'svc-design',
        urls: [process.env.SVC_DESIGN_URL || 'http://localhost:8001'],
        healthPath: '/health',
        timeout: 5000,
        retries: 3
      },
      {
        name: 'svc-compliance',
        urls: [process.env.SVC_COMPLIANCE_URL || 'http://localhost:8002'],
        healthPath: '/health',
        timeout: 5000,
        retries: 3
      },
      {
        name: 'svc-finance',
        urls: [process.env.SVC_FINANCE_URL || 'http://localhost:8003'],
        healthPath: '/health',
        timeout: 5000,
        retries: 3
      },
      {
        name: 'svc-procure',
        urls: [process.env.SVC_PROCURE_URL || 'http://localhost:8004'],
        healthPath: '/health',
        timeout: 5000,
        retries: 3
      },
      {
        name: 'svc-ops',
        urls: [process.env.SVC_OPS_URL || 'http://localhost:8005'],
        healthPath: '/health',
        timeout: 5000,
        retries: 3
      },
      {
        name: 'svc-support',
        urls: [process.env.SVC_SUPPORT_URL || 'http://localhost:8006'],
        healthPath: '/health',
        timeout: 5000,
        retries: 3
      }
    ];

    serviceConfigs.forEach(config => {
      const endpoints: ServiceEndpoint[] = config.urls.map((url, index) => ({
        id: `${config.name}-${index}`,
        name: config.name,
        url,
        health: `${url}${config.healthPath}`,
        version: '1.0.0',
        status: 'unknown',
        lastCheck: new Date(),
        metadata: {
          timeout: config.timeout,
          retries: config.retries
        }
      }));

      this.services.set(config.name, endpoints);
    });

    logger.info(`Initialized ${this.services.size} services in registry`);
  }

  /**
   * Get a healthy endpoint for a service
   */
  getServiceEndpoint(serviceName: string): ServiceEndpoint | null {
    const endpoints = this.services.get(serviceName);
    if (!endpoints || endpoints.length === 0) {
      logger.warn(`Service ${serviceName} not found in registry`);
      return null;
    }

    // Find healthy endpoints
    const healthyEndpoints = endpoints.filter(ep => ep.status === 'healthy');
    
    if (healthyEndpoints.length === 0) {
      logger.warn(`No healthy endpoints found for service ${serviceName}`);
      // Return first endpoint as fallback
      return endpoints[0];
    }

    // Simple round-robin load balancing
    const randomIndex = Math.floor(Math.random() * healthyEndpoints.length);
    return healthyEndpoints[randomIndex];
  }

  /**
   * Get all services and their status
   */
  getAllServices(): Record<string, ServiceEndpoint[]> {
    const result: Record<string, ServiceEndpoint[]> = {};
    this.services.forEach((endpoints, serviceName) => {
      result[serviceName] = endpoints;
    });
    return result;
  }

  /**
   * Register a new service endpoint
   */
  registerService(endpoint: Omit<ServiceEndpoint, 'lastCheck' | 'status'>): void {
    const fullEndpoint: ServiceEndpoint = {
      ...endpoint,
      status: 'unknown',
      lastCheck: new Date()
    };

    const existing = this.services.get(endpoint.name) || [];
    existing.push(fullEndpoint);
    this.services.set(endpoint.name, existing);

    logger.info(`Registered new endpoint for service ${endpoint.name}: ${endpoint.url}`);
  }

  /**
   * Unregister a service endpoint
   */
  unregisterService(serviceName: string, endpointId: string): void {
    const endpoints = this.services.get(serviceName);
    if (!endpoints) return;

    const filtered = endpoints.filter(ep => ep.id !== endpointId);
    this.services.set(serviceName, filtered);

    logger.info(`Unregistered endpoint ${endpointId} from service ${serviceName}`);
  }

  /**
   * Start periodic health checks
   */
  private startHealthChecks(): void {
    this.healthCheckInterval = setInterval(() => {
      this.performHealthChecks();
    }, this.HEALTH_CHECK_INTERVAL);

    logger.info('Started health check monitoring');
  }

  /**
   * Stop health checks
   */
  stopHealthChecks(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
      logger.info('Stopped health check monitoring');
    }
  }

  /**
   * Perform health checks on all registered services
   */
  private async performHealthChecks(): Promise<void> {
    const promises: Promise<void>[] = [];

    this.services.forEach((endpoints, serviceName) => {
      endpoints.forEach(endpoint => {
        promises.push(this.checkEndpointHealth(endpoint));
      });
    });

    await Promise.allSettled(promises);
  }

  /**
   * Check health of a specific endpoint
   */
  private async checkEndpointHealth(endpoint: ServiceEndpoint): Promise<void> {
    try {
      const controller = new AbortController();
      const timeout = endpoint.metadata?.timeout || 5000;
      
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      const response = await fetch(endpoint.health, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json'
        }
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        endpoint.status = 'healthy';
        endpoint.lastCheck = new Date();
      } else {
        endpoint.status = 'unhealthy';
        endpoint.lastCheck = new Date();
        logger.warn(`Health check failed for ${endpoint.name} (${endpoint.url}): ${response.status}`);
      }
    } catch (error) {
      endpoint.status = 'unhealthy';
      endpoint.lastCheck = new Date();
      logger.warn(`Health check error for ${endpoint.name} (${endpoint.url}):`, error);
    }
  }

  /**
   * Get service statistics
   */
  getStats(): Record<string, any> {
    const stats: Record<string, any> = {};
    
    this.services.forEach((endpoints, serviceName) => {
      const healthy = endpoints.filter(ep => ep.status === 'healthy').length;
      const total = endpoints.length;
      
      stats[serviceName] = {
        total,
        healthy,
        unhealthy: total - healthy,
        healthRatio: total > 0 ? (healthy / total) * 100 : 0
      };
    });

    return stats;
  }
}

// Export singleton instance
export const serviceRegistry = new ServiceRegistry();