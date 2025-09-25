/**
 * Authentication middleware for the API Gateway
 * Handles JWT token validation and user context
 */

import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { createClient } from '@supabase/supabase-js';
import { logger } from '../utils/logger.js';

// Extend Express Request type to include user
declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        email: string;
        role: string;
        organization_id?: string;
      };
    }
  }
}

// Initialize Supabase client
const supabaseUrl = process.env.SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;

if (!supabaseUrl || !supabaseServiceKey) {
  throw new Error('Missing Supabase configuration. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.');
}

const supabase = createClient(supabaseUrl, supabaseServiceKey);

/**
 * Authentication middleware
 * Validates JWT tokens and loads user context
 */
export const authMiddleware = async (req: Request, res: Response, next: NextFunction) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({
        success: false,
        error: 'Missing or invalid authorization header'
      });
    }
    
    const token = authHeader.substring(7); // Remove 'Bearer ' prefix
    
    // Verify JWT token with Supabase
    const { data: { user }, error } = await supabase.auth.getUser(token);
    
    if (error || !user) {
      logger.warn('Invalid token:', error?.message);
      return res.status(401).json({
        success: false,
        error: 'Invalid or expired token'
      });
    }
    
    // Load user profile from database
    const { data: userProfile, error: profileError } = await supabase
      .from('users')
      .select('id, email, first_name, last_name, role, organization_id')
      .eq('id', user.id)
      .single();
    
    if (profileError || !userProfile) {
      logger.warn('User profile not found:', profileError?.message);
      return res.status(401).json({
        success: false,
        error: 'User profile not found'
      });
    }
    
    // Attach user context to request
    req.user = {
      id: userProfile.id,
      email: userProfile.email,
      role: userProfile.role,
      organization_id: userProfile.organization_id
    };
    
    logger.debug(`Authenticated user: ${userProfile.email} (${userProfile.role})`);
    next();
    
  } catch (error) {
    logger.error('Authentication error:', error);
    return res.status(500).json({
      success: false,
      error: 'Authentication service error'
    });
  }
};

/**
 * Role-based authorization middleware
 * Checks if user has required role
 */
export const requireRole = (requiredRoles: string | string[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        error: 'Authentication required'
      });
    }
    
    const roles = Array.isArray(requiredRoles) ? requiredRoles : [requiredRoles];
    
    if (!roles.includes(req.user.role)) {
      logger.warn(`Access denied for user ${req.user.email}. Required roles: ${roles.join(', ')}, user role: ${req.user.role}`);
      return res.status(403).json({
        success: false,
        error: 'Insufficient permissions'
      });
    }
    
    next();
  };
};

/**
 * Admin-only middleware
 */
export const requireAdmin = requireRole(['admin']);

/**
 * Manager or admin middleware
 */
export const requireManager = requireRole(['admin', 'manager']);

/**
 * Optional authentication middleware
 * Loads user context if token is present, but doesn't require it
 */
export const optionalAuth = async (req: Request, res: Response, next: NextFunction) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return next(); // No token provided, continue without user context
    }
    
    const token = authHeader.substring(7);
    
    // Verify JWT token with Supabase
    const { data: { user }, error } = await supabase.auth.getUser(token);
    
    if (error || !user) {
      return next(); // Invalid token, continue without user context
    }
    
    // Load user profile from database
    const { data: userProfile, error: profileError } = await supabase
      .from('users')
      .select('id, email, first_name, last_name, role, organization_id')
      .eq('id', user.id)
      .single();
    
    if (profileError || !userProfile) {
      return next(); // Profile not found, continue without user context
    }
    
    // Attach user context to request
    req.user = {
      id: userProfile.id,
      email: userProfile.email,
      role: userProfile.role,
      organization_id: userProfile.organization_id
    };
    
    next();
    
  } catch (error) {
    logger.error('Optional authentication error:', error);
    next(); // Continue without user context on error
  }
};

/**
 * API key authentication middleware
 * For service-to-service communication
 */
export const apiKeyAuth = (req: Request, res: Response, next: NextFunction) => {
  const apiKey = req.headers['x-api-key'] as string;
  const validApiKeys = process.env.VALID_API_KEYS?.split(',') || [];
  
  if (!apiKey || !validApiKeys.includes(apiKey)) {
    return res.status(401).json({
      success: false,
      error: 'Invalid API key'
    });
  }
  
  // Set service context
  req.user = {
    id: 'system',
    email: 'system@nextgenfusion.com',
    role: 'system',
    organization_id: undefined
  };
  
  next();
};