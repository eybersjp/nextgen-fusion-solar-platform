import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';
import { promisify } from 'util';

interface Auth0User {
  sub: string;
  email?: string;
  email_verified?: boolean;
  name?: string;
  picture?: string;
  roles?: string[];
  permissions?: string[];
  auth_provider: 'auth0';
  aud?: string | string[];
  iss?: string;
  iat?: number;
  exp?: number;
}

interface AuthenticatedRequest extends Request {
  user?: Auth0User;
}

class Auth0Middleware {
  private domain?: string;
  private audience?: string;
  private issuer?: string;
  private client?: jwksClient.JwksClient;
  private initialized = false;

  private initialize() {
    if (this.initialized) return;
    
    this.domain = process.env.AUTH0_DOMAIN!;
    this.audience = process.env.AUTH0_API_AUDIENCE!;
    this.issuer = process.env.AUTH0_ISSUER || `https://${this.domain}/`;

    if (!this.domain || !this.audience) {
      throw new Error('AUTH0_DOMAIN and AUTH0_API_AUDIENCE must be set');
    }

    this.client = jwksClient({
      jwksUri: `https://${this.domain}/.well-known/jwks.json`,
      cache: true,
      cacheMaxEntries: 5,
      cacheMaxAge: 600000, // 10 minutes
    });
    
    this.initialized = true;
  }

  private getKey = (header: jwt.JwtHeader, callback: jwt.SigningKeyCallback): void => {
    this.initialize();
    this.client!.getSigningKey(header.kid!, (err, key) => {
      if (err) {
        return callback(err);
      }
      const signingKey = key?.getPublicKey();
      callback(null, signingKey);
    });
  };

  private verifyToken = promisify(jwt.verify);

  public authenticate = async (
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    try {
      this.initialize();
      
      const authHeader = req.headers.authorization;

      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        res.status(401).json({
          success: false,
          error: 'Authorization header required',
        });
        return;
      }

      const token = authHeader.substring(7); // Remove 'Bearer ' prefix

      // Verify token
      const decoded = await this.verifyToken(token, this.getKey, {
        audience: this.audience!,
        issuer: this.issuer!,
        algorithms: ['RS256'],
      }) as jwt.JwtPayload;

      // Extract user information
      const user: Auth0User = {
        sub: decoded.sub!,
        email: decoded.email,
        email_verified: decoded.email_verified || false,
        name: decoded.name,
        picture: decoded.picture,
        roles: decoded['https://nextgen-solar.com/roles'] || [],
        permissions: decoded['https://nextgen-solar.com/permissions'] || [],
        auth_provider: 'auth0',
        aud: decoded.aud,
        iss: decoded.iss,
        iat: decoded.iat,
        exp: decoded.exp,
      };

      req.user = user;
      next();
    } catch (error) {
      console.error('Auth0 token verification failed:', error);
      
      if (error instanceof jwt.TokenExpiredError) {
        res.status(401).json({
          success: false,
          error: 'Token has expired',
        });
      } else if (error instanceof jwt.JsonWebTokenError) {
        res.status(401).json({
          success: false,
          error: 'Invalid token',
        });
      } else {
        res.status(401).json({
          success: false,
          error: 'Token verification failed',
        });
      }
    }
  };

  public optionalAuthenticate = async (
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    try {
      const authHeader = req.headers.authorization;

      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        // No token provided, continue without authentication
        next();
        return;
      }

      // Try to authenticate, but don't fail if token is invalid
      await this.authenticate(req, res, next);
    } catch (error) {
      // Continue without authentication if token is invalid
      next();
    }
  };

  public requireRole = (role: string) => {
    return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
      if (!req.user) {
        res.status(401).json({
          success: false,
          error: 'Authentication required',
        });
        return;
      }

      const userRoles = req.user.roles || [];
      if (!userRoles.includes(role)) {
        res.status(403).json({
          success: false,
          error: `Access denied. Required role: ${role}`,
        });
        return;
      }

      next();
    };
  };

  public requireAnyRole = (...roles: string[]) => {
    return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
      if (!req.user) {
        res.status(401).json({
          success: false,
          error: 'Authentication required',
        });
        return;
      }

      const userRoles = req.user.roles || [];
      const hasRequiredRole = roles.some(role => userRoles.includes(role));
      
      if (!hasRequiredRole) {
        res.status(403).json({
          success: false,
          error: `Access denied. Required roles: ${roles.join(', ')}`,
        });
        return;
      }

      next();
    };
  };

  public requirePermission = (permission: string) => {
    return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
      if (!req.user) {
        res.status(401).json({
          success: false,
          error: 'Authentication required',
        });
        return;
      }

      const userPermissions = req.user.permissions || [];
      if (!userPermissions.includes(permission)) {
        res.status(403).json({
          success: false,
          error: `Access denied. Required permission: ${permission}`,
        });
        return;
      }

      next();
    };
  };

  public requirePermissions = (...permissions: string[]) => {
    return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
      if (!req.user) {
        res.status(401).json({
          success: false,
          error: 'Authentication required',
        });
        return;
      }

      const userPermissions = req.user.permissions || [];
      const missingPermissions = permissions.filter(perm => !userPermissions.includes(perm));
      
      if (missingPermissions.length > 0) {
        res.status(403).json({
          success: false,
          error: `Access denied. Missing permissions: ${missingPermissions.join(', ')}`,
        });
        return;
      }

      next();
    };
  };
}

// Export singleton instance
const auth0Middleware = new Auth0Middleware();

export default auth0Middleware;
export { AuthenticatedRequest, Auth0User };