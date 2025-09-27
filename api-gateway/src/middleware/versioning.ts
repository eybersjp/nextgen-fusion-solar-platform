import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';
import { getCorrelationId } from './correlation';

export interface VersionConfig {
  supportedVersions: string[];
  defaultVersion: string;
  deprecatedVersions?: {
    version: string;
    deprecationDate: string;
    sunsetDate: string;
    message?: string;
  }[];
  versionHeader?: string;
  versionParam?: string;
  versionPath?: boolean;
}

export interface VersionedEndpoint {
  path: string;
  versions: {
    [version: string]: {
      handler?: (req: Request, res: Response, next: NextFunction) => void;
      proxy?: {
        target: string;
        pathRewrite?: { [key: string]: string };
      };
      deprecated?: boolean;
      changes?: string[];
    };
  };
}

// Default version configuration
const DEFAULT_VERSION_CONFIG: VersionConfig = {
  supportedVersions: ['v1', 'v2'],
  defaultVersion: 'v1',
  deprecatedVersions: [],
  versionHeader: 'api-version',
  versionParam: 'version',
  versionPath: true
};

// Version extraction strategies
class VersionExtractor {
  static fromPath(req: Request): string | null {
    const pathMatch = req.path.match(/^\/api\/(v\d+)\//i);
    return pathMatch ? pathMatch[1].toLowerCase() : null;
  }
  
  static fromHeader(req: Request, headerName: string): string | null {
    const header = req.headers[headerName.toLowerCase()] as string;
    return header ? header.toLowerCase() : null;
  }
  
  static fromQuery(req: Request, paramName: string): string | null {
    const param = req.query[paramName] as string;
    return param ? param.toLowerCase() : null;
  }
  
  static fromAcceptHeader(req: Request): string | null {
    const accept = req.headers.accept;
    if (!accept) return null;
    
    // Look for version in Accept header like: application/vnd.api+json;version=v2
    const versionMatch = accept.match(/version=([^;,\s]+)/i);
    return versionMatch ? versionMatch[1].toLowerCase() : null;
  }
}

// Version validation and normalization
class VersionValidator {
  static isSupported(version: string, supportedVersions: string[]): boolean {
    return supportedVersions.includes(version);
  }
  
  static normalize(version: string): string {
    // Ensure version starts with 'v'
    if (version && !version.startsWith('v')) {
      return `v${version}`;
    }
    return version;
  }
  
  static isDeprecated(version: string, deprecatedVersions: VersionConfig['deprecatedVersions']): boolean {
    if (!deprecatedVersions) return false;
    return deprecatedVersions.some(dep => dep.version === version);
  }
  
  static getDeprecationInfo(version: string, deprecatedVersions: VersionConfig['deprecatedVersions']) {
    if (!deprecatedVersions) return null;
    return deprecatedVersions.find(dep => dep.version === version);
  }
}

// Main versioning middleware
export const versioningMiddleware = (config: Partial<VersionConfig> = {}) => {
  const finalConfig = { ...DEFAULT_VERSION_CONFIG, ...config };
  
  return (req: Request, res: Response, next: NextFunction) => {
    const correlationId = getCorrelationId(req);
    
    try {
      let version: string | null = null;
      
      // Try different extraction strategies in order of preference
      if (finalConfig.versionPath) {
        version = VersionExtractor.fromPath(req);
      }
      
      if (!version && finalConfig.versionHeader) {
        version = VersionExtractor.fromHeader(req, finalConfig.versionHeader);
      }
      
      if (!version && finalConfig.versionParam) {
        version = VersionExtractor.fromQuery(req, finalConfig.versionParam);
      }
      
      if (!version) {
        version = VersionExtractor.fromAcceptHeader(req);
      }
      
      // Use default version if none specified
      if (!version) {
        version = finalConfig.defaultVersion;
        logger.debug('Using default API version', {
          correlationId,
          version,
          path: req.path
        });
      }
      
      // Normalize version
      version = VersionValidator.normalize(version);
      
      // Validate version
      if (!VersionValidator.isSupported(version, finalConfig.supportedVersions)) {
        logger.warn('Unsupported API version requested', {
          correlationId,
          requestedVersion: version,
          supportedVersions: finalConfig.supportedVersions,
          path: req.path
        });
        
        return res.status(400).json({
          error: 'Unsupported API version',
          requestedVersion: version,
          supportedVersions: finalConfig.supportedVersions,
          message: `API version '${version}' is not supported. Please use one of: ${finalConfig.supportedVersions.join(', ')}`,
          correlationId
        });
      }
      
      // Check for deprecation
      if (VersionValidator.isDeprecated(version, finalConfig.deprecatedVersions)) {
        const deprecationInfo = VersionValidator.getDeprecationInfo(version, finalConfig.deprecatedVersions);
        
        logger.warn('Deprecated API version used', {
          correlationId,
          version,
          deprecationInfo,
          path: req.path,
          userAgent: req.headers['user-agent']
        });
        
        // Add deprecation headers
        res.setHeader('Deprecation', deprecationInfo?.deprecationDate || 'true');
        res.setHeader('Sunset', deprecationInfo?.sunsetDate || '');
        res.setHeader('Link', `</api/${finalConfig.supportedVersions[finalConfig.supportedVersions.length - 1]}>; rel="successor-version"`);
        
        if (deprecationInfo?.message) {
          res.setHeader('Warning', `299 - "${deprecationInfo.message}"`);
        }
      }
      
      // Store version in request for downstream use
      req.apiVersion = version;
      
      // Add version headers to response
      res.setHeader('API-Version', version);
      res.setHeader('API-Supported-Versions', finalConfig.supportedVersions.join(', '));
      
      // Rewrite path to include version if not already present
      if (finalConfig.versionPath && !req.path.includes(`/${version}/`)) {
        req.url = req.url.replace(/^\/api\//, `/api/${version}/`);
        req.path = req.path.replace(/^\/api\//, `/api/${version}/`);
      }
      
      logger.debug('API version resolved', {
        correlationId,
        version,
        originalPath: req.originalUrl,
        rewrittenPath: req.path
      });
      
      next();
    } catch (error) {
      logger.error('Version middleware error:', error);
      res.status(500).json({
        error: 'Internal server error in version handling',
        correlationId
      });
    }
  };
};

// Versioned endpoint handler
export const versionedEndpoint = (endpoints: VersionedEndpoint[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const version = req.apiVersion || 'v1';
    const correlationId = getCorrelationId(req);
    
    // Find matching endpoint
    const endpoint = endpoints.find(ep => {
      const pattern = new RegExp(ep.path.replace(/:[^/]+/g, '[^/]+'));
      return pattern.test(req.path);
    });
    
    if (!endpoint) {
      return next(); // No versioned endpoint found, continue
    }
    
    const versionConfig = endpoint.versions[version];
    if (!versionConfig) {
      logger.warn('Version not implemented for endpoint', {
        correlationId,
        version,
        path: req.path,
        availableVersions: Object.keys(endpoint.versions)
      });
      
      return res.status(404).json({
        error: 'Version not implemented',
        version,
        path: req.path,
        availableVersions: Object.keys(endpoint.versions),
        correlationId
      });
    }
    
    // Log version usage
    logger.info('Versioned endpoint accessed', {
      correlationId,
      version,
      path: req.path,
      deprecated: versionConfig.deprecated,
      changes: versionConfig.changes
    });
    
    // Handle deprecated endpoint
    if (versionConfig.deprecated) {
      res.setHeader('Warning', '299 - "This endpoint version is deprecated"');
    }
    
    // Execute version-specific handler or proxy
    if (versionConfig.handler) {
      return versionConfig.handler(req, res, next);
    } else if (versionConfig.proxy) {
      // Set up proxy configuration
      req.proxyConfig = versionConfig.proxy;
      return next();
    }
    
    next();
  };
};

// Version compatibility middleware
export const versionCompatibilityMiddleware = () => {
  return (req: Request, res: Response, next: NextFunction) => {
    const version = req.apiVersion;
    const correlationId = getCorrelationId(req);
    
    // Apply version-specific transformations
    switch (version) {
      case 'v1':
        // V1 compatibility transformations
        applyV1Compatibility(req, res);
        break;
      case 'v2':
        // V2 enhancements
        applyV2Enhancements(req, res);
        break;
      default:
        logger.debug('No specific compatibility rules for version', {
          correlationId,
          version
        });
    }
    
    next();
  };
};

// V1 compatibility transformations
function applyV1Compatibility(req: Request, res: Response): void {
  // Transform request for V1 compatibility
  if (req.body) {
    // Example: Convert new field names to old ones
    if (req.body.projectData) {
      req.body.project_data = req.body.projectData;
      delete req.body.projectData;
    }
  }
  
  // Override response transformation
  const originalJson = res.json;
  res.json = function(body: any) {
    // Transform response for V1 compatibility
    if (body && typeof body === 'object') {
      // Example: Convert snake_case to camelCase for V1
      body = transformResponseForV1(body);
    }
    return originalJson.call(this, body);
  };
}

// V2 enhancements
function applyV2Enhancements(req: Request, res: Response): void {
  // Add V2-specific headers
  res.setHeader('API-Features', 'enhanced-validation,bulk-operations,async-processing');
  
  // Override response to add V2 metadata
  const originalJson = res.json;
  res.json = function(body: any) {
    if (body && typeof body === 'object' && !body.meta) {
      body.meta = {
        version: 'v2',
        timestamp: new Date().toISOString(),
        correlationId: req.correlationId
      };
    }
    return originalJson.call(this, body);
  };
}

// Response transformation utilities
function transformResponseForV1(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(transformResponseForV1);
  }
  
  if (obj && typeof obj === 'object') {
    const transformed: any = {};
    for (const [key, value] of Object.entries(obj)) {
      // Convert camelCase to snake_case for V1
      const v1Key = key.replace(/([A-Z])/g, '_$1').toLowerCase();
      transformed[v1Key] = transformResponseForV1(value);
    }
    return transformed;
  }
  
  return obj;
}

// Version migration helper
export const versionMigrationMiddleware = (migrations: {
  [fromVersion: string]: {
    [toVersion: string]: (data: any) => any;
  };
}) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const requestedVersion = req.apiVersion;
    const targetVersion = 'v2'; // Always migrate to latest
    
    if (requestedVersion !== targetVersion && migrations[requestedVersion]?.[targetVersion]) {
      const migrator = migrations[requestedVersion][targetVersion];
      
      // Migrate request body
      if (req.body) {
        req.body = migrator(req.body);
      }
      
      // Migrate query parameters
      if (req.query) {
        req.query = migrator(req.query);
      }
    }
    
    next();
  };
};

// Extend Express Request interface
declare global {
  namespace Express {
    interface Request {
      apiVersion?: string;
      proxyConfig?: {
        target: string;
        pathRewrite?: { [key: string]: string };
      };
    }
  }
}

export { VersionExtractor, VersionValidator };