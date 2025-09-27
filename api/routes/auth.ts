/**
 * Auth0 authentication API routes
 * Handle user information, token validation, and Auth0 integration
 */
import { Router, type Request, type Response } from 'express'
import auth0Middleware, { type AuthenticatedRequest } from '../middleware/auth0.js'

const router = Router()

/**
 * Get current user information
 * GET /api/auth/me
 * Requires: Valid Auth0 token
 */
router.get('/me', auth0Middleware.authenticate, async (req: AuthenticatedRequest, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: 'User not authenticated'
      })
      return
    }

    res.json({
      success: true,
      data: {
        user: req.user
      }
    })
  } catch (error) {
    console.error('Error fetching user info:', error)
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    })
  }
})

/**
 * Validate Auth0 token
 * POST /api/auth/validate
 * Requires: Valid Auth0 token
 */
router.post('/validate', auth0Middleware.authenticate, async (req: AuthenticatedRequest, res: Response): Promise<void> => {
  try {
    res.json({
      success: true,
      data: {
        valid: true,
        user: req.user
      }
    })
  } catch (error) {
    console.error('Error validating token:', error)
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    })
  }
})

/**
 * Get user permissions
 * GET /api/auth/permissions
 * Requires: Valid Auth0 token
 */
router.get('/permissions', auth0Middleware.authenticate, async (req: AuthenticatedRequest, res: Response): Promise<void> => {
  try {
    if (!req.user) {
      res.status(401).json({
        success: false,
        error: 'User not authenticated'
      })
      return
    }

    res.json({
      success: true,
      data: {
        roles: req.user.roles || [],
        permissions: req.user.permissions || []
      }
    })
  } catch (error) {
    console.error('Error fetching permissions:', error)
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    })
  }
})

/**
 * Health check for Auth0 configuration
 * GET /api/auth/health
 */
router.get('/health', async (req: Request, res: Response): Promise<void> => {
  try {
    const auth0Config = {
      domain: process.env.AUTH0_DOMAIN ? 'configured' : 'missing',
      audience: process.env.AUTH0_API_AUDIENCE ? 'configured' : 'missing',
      issuer: process.env.AUTH0_ISSUER ? 'configured' : 'missing'
    }

    const isHealthy = auth0Config.domain === 'configured' && auth0Config.audience === 'configured'

    res.status(isHealthy ? 200 : 503).json({
      success: isHealthy,
      data: {
        auth0: auth0Config,
        status: isHealthy ? 'healthy' : 'misconfigured'
      }
    })
  } catch (error) {
    console.error('Error checking auth health:', error)
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    })
  }
})

export default router
