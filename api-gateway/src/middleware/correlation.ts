import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger';

// Extend Express Request interface to include correlation ID
declare global {
  namespace Express {
    interface Request {
      correlationId?: string;
      requestStartTime?: number;
    }
  }
}

export interface CorrelationOptions {
  headerName?: string;
  generateId?: () => string;
  setResponseHeader?: boolean;
  logRequests?: boolean;
  includeUserAgent?: boolean;
  includeIP?: boolean;
}

// Default correlation ID generator
const defaultIdGenerator = (): string => {
  return uuidv4();
};

// Correlation ID middleware
export const correlationMiddleware = (options: CorrelationOptions = {}) => {
  const {
    headerName = 'x-correlation-id',
    generateId = defaultIdGenerator,
    setResponseHeader = true,
    logRequests = true,
    includeUserAgent = true,
    includeIP = true
  } = options;

  return (req: Request, res: Response, next: NextFunction) => {
    // Get correlation ID from header or generate new one
    const correlationId = req.headers[headerName] as string || generateId();
    
    // Store correlation ID in request
    req.correlationId = correlationId;
    req.requestStartTime = Date.now();
    
    // Set response header if enabled
    if (setResponseHeader) {
      res.setHeader(headerName, correlationId);
    }
    
    // Add correlation ID to response locals for templates
    res.locals.correlationId = correlationId;
    
    // Log request start if enabled
    if (logRequests) {
      const logData: any = {
        correlationId,
        method: req.method,
        url: req.originalUrl,
        timestamp: new Date().toISOString(),
        userAgent: includeUserAgent ? req.headers['user-agent'] : undefined,
        ip: includeIP ? getClientIP(req) : undefined,
        userId: req.user?.id,
        tenantId: req.headers['x-tenant-id']
      };
      
      // Remove undefined values
      Object.keys(logData).forEach(key => {
        if (logData[key] === undefined) {
          delete logData[key];
        }
      });
      
      logger.info('Request started', logData);
    }
    
    // Override res.end to log request completion
    if (logRequests) {
      const originalEnd = res.end;
      
      res.end = function(chunk?: any, encoding?: any) {
        const duration = req.requestStartTime ? Date.now() - req.requestStartTime : 0;
        
        const logData: any = {
          correlationId,
          method: req.method,
          url: req.originalUrl,
          statusCode: res.statusCode,
          duration,
          timestamp: new Date().toISOString(),
          userId: req.user?.id,
          tenantId: req.headers['x-tenant-id']
        };
        
        // Remove undefined values
        Object.keys(logData).forEach(key => {
          if (logData[key] === undefined) {
            delete logData[key];
          }
        });
        
        // Log with appropriate level based on status code
        if (res.statusCode >= 500) {
          logger.error('Request completed with server error', logData);
        } else if (res.statusCode >= 400) {
          logger.warn('Request completed with client error', logData);
        } else {
          logger.info('Request completed successfully', logData);
        }
        
        return originalEnd.call(this, chunk, encoding);
      };
    }
    
    next();
  };
};

// Get client IP address
const getClientIP = (req: Request): string => {
  return (
    req.headers['x-forwarded-for'] as string ||
    req.headers['x-real-ip'] as string ||
    req.connection.remoteAddress ||
    req.socket.remoteAddress ||
    'unknown'
  ).split(',')[0].trim();
};

// Enhanced logger that includes correlation ID
export const createCorrelatedLogger = (baseLogger: any) => {
  return {
    info: (message: string, meta?: any, req?: Request) => {
      const correlationId = req?.correlationId;
      baseLogger.info(message, { ...meta, correlationId });
    },
    
    warn: (message: string, meta?: any, req?: Request) => {
      const correlationId = req?.correlationId;
      baseLogger.warn(message, { ...meta, correlationId });
    },
    
    error: (message: string, meta?: any, req?: Request) => {
      const correlationId = req?.correlationId;
      baseLogger.error(message, { ...meta, correlationId });
    },
    
    debug: (message: string, meta?: any, req?: Request) => {
      const correlationId = req?.correlationId;
      baseLogger.debug(message, { ...meta, correlationId });
    }
  };
};

// Middleware to add correlation ID to outgoing service requests
export const addCorrelationToServiceRequests = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    // Store original request headers for service calls
    req.serviceHeaders = {
      'x-correlation-id': req.correlationId || '',
      'x-user-id': req.user?.id || '',
      'x-tenant-id': req.headers['x-tenant-id'] as string || '',
      'x-request-timestamp': req.requestStartTime?.toString() || Date.now().toString()
    };
    
    next();
  };
};

// Utility to get correlation ID from request
export const getCorrelationId = (req: Request): string => {
  return req.correlationId || 'unknown';
};

// Utility to create child logger with correlation context
export const getCorrelatedLogger = (req: Request) => {
  return {
    info: (message: string, meta?: any) => {
      logger.info(message, { ...meta, correlationId: req.correlationId });
    },
    
    warn: (message: string, meta?: any) => {
      logger.warn(message, { ...meta, correlationId: req.correlationId });
    },
    
    error: (message: string, meta?: any) => {
      logger.error(message, { ...meta, correlationId: req.correlationId });
    },
    
    debug: (message: string, meta?: any) => {
      logger.debug(message, { ...meta, correlationId: req.correlationId });
    }
  };
};

// Performance monitoring middleware
export const performanceMiddleware = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    const startTime = process.hrtime.bigint();
    
    const originalEnd = res.end;
    
    res.end = function(chunk?: any, encoding?: any) {
      const endTime = process.hrtime.bigint();
      const duration = Number(endTime - startTime) / 1000000; // Convert to milliseconds
      
      // Add performance headers
      res.setHeader('X-Response-Time', `${duration.toFixed(2)}ms`);
      
      // Log slow requests (> 1 second)
      if (duration > 1000) {
        logger.warn('Slow request detected', {
          correlationId: req.correlationId,
          method: req.method,
          url: req.originalUrl,
          duration: `${duration.toFixed(2)}ms`,
          statusCode: res.statusCode
        });
      }
      
      // Log performance metrics
      logger.debug('Request performance', {
        correlationId: req.correlationId,
        method: req.method,
        url: req.originalUrl,
        duration: `${duration.toFixed(2)}ms`,
        statusCode: res.statusCode,
        userAgent: req.headers['user-agent'],
        contentLength: res.getHeader('content-length')
      });
      
      return originalEnd.call(this, chunk, encoding);
    };
    
    next();
  };
};

// Request context storage for async operations
class RequestContext {
  private static contexts = new Map<string, any>();
  
  static set(correlationId: string, context: any): void {
    this.contexts.set(correlationId, context);
  }
  
  static get(correlationId: string): any {
    return this.contexts.get(correlationId);
  }
  
  static delete(correlationId: string): void {
    this.contexts.delete(correlationId);
  }
  
  static clear(): void {
    this.contexts.clear();
  }
}

// Middleware to store request context
export const requestContextMiddleware = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    if (req.correlationId) {
      RequestContext.set(req.correlationId, {
        userId: req.user?.id,
        tenantId: req.headers['x-tenant-id'],
        userAgent: req.headers['user-agent'],
        ip: getClientIP(req),
        timestamp: Date.now()
      });
      
      // Clean up context after response
      const originalEnd = res.end;
      res.end = function(chunk?: any, encoding?: any) {
        if (req.correlationId) {
          RequestContext.delete(req.correlationId);
        }
        return originalEnd.call(this, chunk, encoding);
      };
    }
    
    next();
  };
};

export { RequestContext };