/**
 * Advanced rate limiting middleware with per-user and global limits
 * Implements sliding window rate limiting for better user experience
 */

import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger.js';

interface RateLimitStore {
  [key: string]: {
    requests: number[];
    lastReset: number;
  };
}

class AdvancedRateLimiter {
  private userStore: RateLimitStore = {};
  private globalStore: RateLimitStore = { global: { requests: [], lastReset: Date.now() } };
  private readonly userLimit: number;
  private readonly globalLimit: number;
  private readonly windowMs: number;

  constructor(userLimit: number = 100, globalLimit: number = 1000, windowMs: number = 60 * 1000) {
    this.userLimit = userLimit;
    this.globalLimit = globalLimit;
    this.windowMs = windowMs;

    // Clean up old entries every 5 minutes
    setInterval(() => this.cleanup(), 5 * 60 * 1000);
  }

  private cleanup(): void {
    const now = Date.now();
    const cutoff = now - this.windowMs;

    // Clean user store
    Object.keys(this.userStore).forEach(userId => {
      this.userStore[userId].requests = this.userStore[userId].requests.filter(timestamp => timestamp > cutoff);
      if (this.userStore[userId].requests.length === 0) {
        delete this.userStore[userId];
      }
    });

    // Clean global store
    this.globalStore.global.requests = this.globalStore.global.requests.filter(timestamp => timestamp > cutoff);
  }

  private getRequestCount(store: RateLimitStore, key: string): number {
    if (!store[key]) {
      store[key] = { requests: [], lastReset: Date.now() };
    }

    const now = Date.now();
    const cutoff = now - this.windowMs;

    // Remove old requests
    store[key].requests = store[key].requests.filter(timestamp => timestamp > cutoff);
    
    return store[key].requests.length;
  }

  private addRequest(store: RateLimitStore, key: string): void {
    if (!store[key]) {
      store[key] = { requests: [], lastReset: Date.now() };
    }
    store[key].requests.push(Date.now());
  }

  public middleware() {
    return (req: Request, res: Response, next: NextFunction): void => {
      try {
        // Check global rate limit first
        const globalCount = this.getRequestCount(this.globalStore, 'global');
        if (globalCount >= this.globalLimit) {
          logger.warn(`Global rate limit exceeded: ${globalCount}/${this.globalLimit}`);
          res.status(429).json({
            success: false,
            error: 'Global rate limit exceeded. Please try again later.',
            retryAfter: Math.ceil(this.windowMs / 1000)
          });
          return;
        }

        // Check user-specific rate limit if user is authenticated
        if (req.user?.id) {
          const userId = req.user.id;
          const userCount = this.getRequestCount(this.userStore, userId);
          
          if (userCount >= this.userLimit) {
            logger.warn(`User rate limit exceeded for ${userId}: ${userCount}/${this.userLimit}`);
            res.status(429).json({
              success: false,
              error: 'User rate limit exceeded. Please try again later.',
              retryAfter: Math.ceil(this.windowMs / 1000),
              limit: this.userLimit,
              remaining: 0,
              reset: new Date(Date.now() + this.windowMs).toISOString()
            });
            return;
          }

          // Add request to user store
          this.addRequest(this.userStore, userId);
          
          // Add rate limit headers for authenticated users
          res.set({
            'X-RateLimit-Limit': this.userLimit.toString(),
            'X-RateLimit-Remaining': (this.userLimit - userCount - 1).toString(),
            'X-RateLimit-Reset': new Date(Date.now() + this.windowMs).toISOString()
          });
        }

        // Add request to global store
        this.addRequest(this.globalStore, 'global');
        
        // Add global rate limit headers
        res.set({
          'X-RateLimit-Global-Limit': this.globalLimit.toString(),
          'X-RateLimit-Global-Remaining': (this.globalLimit - globalCount - 1).toString()
        });

        next();
      } catch (error) {
        logger.error('Rate limiter error:', error);
        // Don't block requests on rate limiter errors
        next();
      }
    };
  }

  public getStats(): { userCount: number; globalCount: number; activeUsers: number } {
    const globalCount = this.getRequestCount(this.globalStore, 'global');
    const activeUsers = Object.keys(this.userStore).length;
    const userCount = Object.values(this.userStore).reduce((total, user) => total + user.requests.length, 0);
    
    return {
      userCount,
      globalCount,
      activeUsers
    };
  }
}

// Create singleton instance
const rateLimiter = new AdvancedRateLimiter(
  parseInt(process.env.USER_RATE_LIMIT || '100'),
  parseInt(process.env.GLOBAL_RATE_LIMIT || '1000'),
  parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000')
);

export { rateLimiter };
export default rateLimiter.middleware();