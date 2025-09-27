import Redis from 'ioredis';
import { logger } from '../utils/logger';

export interface CacheConfig {
  host: string;
  port: number;
  password?: string;
  db?: number;
  keyPrefix?: string;
  retryDelayOnFailover?: number;
  maxRetriesPerRequest?: number;
}

export class CacheService {
  private redis: Redis;
  private isConnected: boolean = false;
  private readonly defaultTTL: number = 300; // 5 minutes

  constructor(config: CacheConfig) {
    this.redis = new Redis({
      host: config.host,
      port: config.port,
      password: config.password,
      db: config.db || 0,
      keyPrefix: config.keyPrefix || 'nf:',
      retryDelayOnFailover: config.retryDelayOnFailover || 100,
      maxRetriesPerRequest: config.maxRetriesPerRequest || 3,
      lazyConnect: true,
      reconnectOnError: (err) => {
        const targetError = 'READONLY';
        return err.message.includes(targetError);
      },
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.redis.on('connect', () => {
      this.isConnected = true;
      logger.info('Redis connected successfully');
    });

    this.redis.on('error', (err) => {
      this.isConnected = false;
      logger.error('Redis connection error:', err);
    });

    this.redis.on('close', () => {
      this.isConnected = false;
      logger.warn('Redis connection closed');
    });
  }

  async connect(): Promise<void> {
    try {
      await this.redis.connect();
      logger.info('Redis cache service initialized');
    } catch (error) {
      logger.error('Failed to connect to Redis:', error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    await this.redis.disconnect();
    this.isConnected = false;
  }

  // Cache-aside pattern: Get from cache, fallback to source
  async get<T>(key: string): Promise<T | null> {
    if (!this.isConnected) {
      logger.warn('Redis not connected, skipping cache get');
      return null;
    }

    try {
      const cached = await this.redis.get(key);
      if (cached) {
        return JSON.parse(cached) as T;
      }
      return null;
    } catch (error) {
      logger.error(`Cache get error for key ${key}:`, error);
      return null;
    }
  }

  // Set with TTL
  async set(key: string, value: any, ttl?: number): Promise<boolean> {
    if (!this.isConnected) {
      logger.warn('Redis not connected, skipping cache set');
      return false;
    }

    try {
      const serialized = JSON.stringify(value);
      const expiry = ttl || this.defaultTTL;
      await this.redis.setex(key, expiry, serialized);
      return true;
    } catch (error) {
      logger.error(`Cache set error for key ${key}:`, error);
      return false;
    }
  }

  // Delete from cache
  async del(key: string): Promise<boolean> {
    if (!this.isConnected) {
      return false;
    }

    try {
      const result = await this.redis.del(key);
      return result > 0;
    } catch (error) {
      logger.error(`Cache delete error for key ${key}:`, error);
      return false;
    }
  }

  // Pattern-based deletion (for cache invalidation)
  async delPattern(pattern: string): Promise<number> {
    if (!this.isConnected) {
      return 0;
    }

    try {
      const keys = await this.redis.keys(pattern);
      if (keys.length === 0) {
        return 0;
      }
      return await this.redis.del(...keys);
    } catch (error) {
      logger.error(`Cache pattern delete error for pattern ${pattern}:`, error);
      return 0;
    }
  }

  // Cache with automatic refresh
  async getOrSet<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    // Try to get from cache first
    const cached = await this.get<T>(key);
    if (cached !== null) {
      return cached;
    }

    // Fetch from source
    try {
      const data = await fetcher();
      // Cache the result
      await this.set(key, data, ttl);
      return data;
    } catch (error) {
      logger.error(`Error in getOrSet for key ${key}:`, error);
      throw error;
    }
  }

  // Multi-get for batch operations
  async mget<T>(keys: string[]): Promise<(T | null)[]> {
    if (!this.isConnected || keys.length === 0) {
      return keys.map(() => null);
    }

    try {
      const values = await this.redis.mget(...keys);
      return values.map(value => {
        if (value === null) return null;
        try {
          return JSON.parse(value) as T;
        } catch {
          return null;
        }
      });
    } catch (error) {
      logger.error('Cache mget error:', error);
      return keys.map(() => null);
    }
  }

  // Health check
  async ping(): Promise<boolean> {
    if (!this.isConnected) {
      return false;
    }

    try {
      const result = await this.redis.ping();
      return result === 'PONG';
    } catch {
      return false;
    }
  }

  // Get cache statistics
  async getStats(): Promise<any> {
    if (!this.isConnected) {
      return { connected: false };
    }

    try {
      const info = await this.redis.info('memory');
      const keyspace = await this.redis.info('keyspace');
      return {
        connected: true,
        memory: info,
        keyspace: keyspace,
        uptime: await this.redis.info('server')
      };
    } catch (error) {
      logger.error('Error getting cache stats:', error);
      return { connected: false, error: error.message };
    }
  }
}

// Singleton instance
let cacheService: CacheService | null = null;

export const initializeCache = (config: CacheConfig): CacheService => {
  if (!cacheService) {
    cacheService = new CacheService(config);
  }
  return cacheService;
};

export const getCache = (): CacheService | null => {
  return cacheService;
};

// Cache key generators for different services
export const CacheKeys = {
  // Design service keys
  design: {
    model: (id: string) => `design:model:${id}`,
    optimization: (projectId: string, params: string) => `design:opt:${projectId}:${params}`,
    shading: (modelId: string, timestamp: string) => `design:shade:${modelId}:${timestamp}`,
  },
  
  // Currency service keys
  currency: {
    rates: (base: string, target: string) => `currency:rate:${base}:${target}`,
    history: (pair: string, period: string) => `currency:hist:${pair}:${period}`,
    conversion: (amount: string, from: string, to: string) => `currency:conv:${amount}:${from}:${to}`,
  },
  
  // Project service keys
  project: {
    details: (id: string) => `project:${id}`,
    tasks: (projectId: string) => `project:tasks:${projectId}`,
    dependencies: (projectId: string) => `project:deps:${projectId}`,
    timeline: (projectId: string) => `project:timeline:${projectId}`,
  },
  
  // Compliance service keys
  compliance: {
    rules: (jurisdiction: string) => `compliance:rules:${jurisdiction}`,
    validation: (projectId: string, ruleSet: string) => `compliance:val:${projectId}:${ruleSet}`,
    report: (projectId: string) => `compliance:report:${projectId}`,
  },
  
  // User and session keys
  user: {
    profile: (id: string) => `user:profile:${id}`,
    permissions: (id: string) => `user:perms:${id}`,
    session: (sessionId: string) => `session:${sessionId}`,
  },
};