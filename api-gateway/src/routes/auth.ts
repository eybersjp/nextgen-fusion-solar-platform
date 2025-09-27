/**
 * Authentication routes for the API Gateway
 * Handles user authentication, registration, and token management
 */

import { Router, Request, Response } from 'express';
import { createClient } from '@supabase/supabase-js';
import { logger } from '../utils/logger.js';
import { authMiddleware, optionalAuth } from '../middleware/auth.js';

const router = Router();

// Initialize Supabase client
const supabaseUrl = process.env.SUPABASE_URL!;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY!;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase configuration. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.');
}

const supabase = createClient(supabaseUrl, supabaseAnonKey);

/**
 * User registration endpoint
 * Creates a new user account with email and password
 */
router.post('/register', async (req: Request, res: Response) => {
  try {
    const { email, password, firstName, lastName, organizationName } = req.body;

    if (!email || !password || !firstName || !lastName) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: email, password, firstName, lastName'
      });
    }

    // Register user with Supabase Auth
    const { data: authData, error: authError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          first_name: firstName,
          last_name: lastName,
          organization_name: organizationName
        }
      }
    });

    if (authError) {
      logger.error('Registration error:', authError);
      return res.status(400).json({
        success: false,
        error: authError.message
      });
    }

    if (!authData.user) {
      return res.status(400).json({
        success: false,
        error: 'Failed to create user account'
      });
    }

    logger.info(`User registered: ${email}`);

    res.status(201).json({
      success: true,
      data: {
        user: {
          id: authData.user.id,
          email: authData.user.email,
          emailConfirmed: authData.user.email_confirmed_at !== null
        },
        session: authData.session
      },
      message: 'User registered successfully. Please check your email for verification.'
    });

  } catch (error) {
    logger.error('Registration error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error during registration'
    });
  }
});

/**
 * User login endpoint
 * Authenticates user with email and password
 */
router.post('/login', async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        success: false,
        error: 'Email and password are required'
      });
    }

    // Authenticate with Supabase
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) {
      logger.warn(`Login failed for ${email}: ${error.message}`);
      return res.status(401).json({
        success: false,
        error: 'Invalid email or password'
      });
    }

    if (!data.user || !data.session) {
      return res.status(401).json({
        success: false,
        error: 'Authentication failed'
      });
    }

    logger.info(`User logged in: ${email}`);

    res.json({
      success: true,
      data: {
        user: {
          id: data.user.id,
          email: data.user.email,
          emailConfirmed: data.user.email_confirmed_at !== null
        },
        session: {
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
          expires_at: data.session.expires_at
        }
      },
      message: 'Login successful'
    });

  } catch (error) {
    logger.error('Login error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error during login'
    });
  }
});

/**
 * Token refresh endpoint
 * Refreshes an expired access token using refresh token
 */
router.post('/refresh', async (req: Request, res: Response) => {
  try {
    const { refresh_token } = req.body;

    if (!refresh_token) {
      return res.status(400).json({
        success: false,
        error: 'Refresh token is required'
      });
    }

    const { data, error } = await supabase.auth.refreshSession({
      refresh_token
    });

    if (error) {
      logger.warn('Token refresh failed:', error.message);
      return res.status(401).json({
        success: false,
        error: 'Invalid refresh token'
      });
    }

    if (!data.session) {
      return res.status(401).json({
        success: false,
        error: 'Failed to refresh session'
      });
    }

    res.json({
      success: true,
      data: {
        session: {
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
          expires_at: data.session.expires_at
        }
      },
      message: 'Token refreshed successfully'
    });

  } catch (error) {
    logger.error('Token refresh error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error during token refresh'
    });
  }
});

/**
 * Logout endpoint
 * Invalidates the current session
 */
router.post('/logout', authMiddleware, async (req: Request, res: Response) => {
  try {
    const authHeader = req.headers.authorization;
    const token = authHeader?.substring(7); // Remove 'Bearer ' prefix

    if (token) {
      const { error } = await supabase.auth.signOut();
      if (error) {
        logger.warn('Logout error:', error.message);
      }
    }

    logger.info(`User logged out: ${req.user?.email}`);

    res.json({
      success: true,
      message: 'Logged out successfully'
    });

  } catch (error) {
    logger.error('Logout error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error during logout'
    });
  }
});

/**
 * Get current user profile
 * Returns the authenticated user's profile information
 */
router.get('/me', authMiddleware, (req: Request, res: Response) => {
  res.json({
    success: true,
    data: {
      user: req.user
    }
  });
});

/**
 * Password reset request
 * Sends password reset email to user
 */
router.post('/forgot-password', async (req: Request, res: Response) => {
  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({
        success: false,
        error: 'Email is required'
      });
    }

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${process.env.FRONTEND_URL}/reset-password`
    });

    if (error) {
      logger.error('Password reset error:', error);
      return res.status(400).json({
        success: false,
        error: error.message
      });
    }

    logger.info(`Password reset requested for: ${email}`);

    res.json({
      success: true,
      message: 'Password reset email sent. Please check your inbox.'
    });

  } catch (error) {
    logger.error('Password reset error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error during password reset'
    });
  }
});

/**
 * Update password
 * Updates user password (requires authentication)
 */
router.put('/password', authMiddleware, async (req: Request, res: Response) => {
  try {
    const { currentPassword, newPassword } = req.body;

    if (!currentPassword || !newPassword) {
      return res.status(400).json({
        success: false,
        error: 'Current password and new password are required'
      });
    }

    // Verify current password by attempting to sign in
    const { error: verifyError } = await supabase.auth.signInWithPassword({
      email: req.user!.email,
      password: currentPassword
    });

    if (verifyError) {
      return res.status(400).json({
        success: false,
        error: 'Current password is incorrect'
      });
    }

    // Update password
    const { error } = await supabase.auth.updateUser({
      password: newPassword
    });

    if (error) {
      logger.error('Password update error:', error);
      return res.status(400).json({
        success: false,
        error: error.message
      });
    }

    logger.info(`Password updated for user: ${req.user!.email}`);

    res.json({
      success: true,
      message: 'Password updated successfully'
    });

  } catch (error) {
    logger.error('Password update error:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error during password update'
    });
  }
});

export default router;