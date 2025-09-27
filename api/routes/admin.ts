/**
 * Admin routes with role-based access control
 * Demonstrates RBAC implementation with Auth0
 */
import { Router, type Response } from 'express'
import auth0Middleware, { type AuthenticatedRequest } from '../middleware/auth0.js'

const router = Router()

/**
 * Get all users (Admin only)
 * GET /api/admin/users
 * Requires: admin role
 */
router.get('/users', 
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    try {
      // Mock user data - replace with actual database query
      const users = [
        {
          id: '1',
          email: 'admin@example.com',
          name: 'System Administrator',
          roles: ['admin'],
          permissions: ['read:*', 'write:*', 'delete:*'],
          lastLogin: '2024-01-15T10:30:00Z',
          emailVerified: true,
          status: 'active'
        },
        {
          id: '2',
          email: 'manager@example.com',
          name: 'Project Manager',
          roles: ['manager'],
          permissions: ['read:projects', 'write:projects', 'manage:projects'],
          lastLogin: '2024-01-14T15:45:00Z',
          emailVerified: true,
          status: 'active'
        },
        {
          id: '3',
          email: 'user@example.com',
          name: 'Regular User',
          roles: ['user'],
          permissions: ['read:projects', 'read:profile', 'write:profile'],
          lastLogin: '2024-01-13T09:15:00Z',
          emailVerified: true,
          status: 'active'
        }
      ]

      res.json({
        success: true,
        data: {
          users,
          total: users.length
        }
      })
    } catch (error) {
      console.error('Error fetching users:', error)
      res.status(500).json({
        success: false,
        error: 'Internal server error'
      })
    }
  }
)

/**
 * Update user roles (Admin only)
 * PUT /api/admin/users/:userId/roles
 * Requires: admin role
 */
router.put('/users/:userId/roles',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    try {
      const { userId } = req.params
      const { roles } = req.body

      if (!Array.isArray(roles)) {
        res.status(400).json({
          success: false,
          error: 'Roles must be an array'
        })
        return
      }

      // Validate roles
      const validRoles = ['admin', 'manager', 'user', 'viewer']
      const invalidRoles = roles.filter(role => !validRoles.includes(role))
      
      if (invalidRoles.length > 0) {
        res.status(400).json({
          success: false,
          error: `Invalid roles: ${invalidRoles.join(', ')}`
        })
        return
      }

      // TODO: Update user roles in Auth0 Management API
      // This would typically involve calling Auth0 Management API
      // to update the user's app_metadata with new roles

      res.json({
        success: true,
        data: {
          userId,
          roles,
          message: 'User roles updated successfully'
        }
      })
    } catch (error) {
      console.error('Error updating user roles:', error)
      res.status(500).json({
        success: false,
        error: 'Internal server error'
      })
    }
  }
)

/**
 * Get system analytics (Admin/Manager)
 * GET /api/admin/analytics
 * Requires: admin or manager role
 */
router.get('/analytics',
  auth0Middleware.authenticate,
  auth0Middleware.requireAnyRole(['admin', 'manager']),
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    try {
      // Mock analytics data
      const analytics = {
        totalUsers: 150,
        activeUsers: 120,
        newUsersThisMonth: 25,
        totalProjects: 45,
        activeProjects: 32,
        completedProjects: 13,
        systemHealth: {
          uptime: '99.9%',
          responseTime: '120ms',
          errorRate: '0.1%'
        },
        usersByRole: {
          admin: 5,
          manager: 15,
          user: 100,
          viewer: 30
        }
      }

      res.json({
        success: true,
        data: analytics
      })
    } catch (error) {
      console.error('Error fetching analytics:', error)
      res.status(500).json({
        success: false,
        error: 'Internal server error'
      })
    }
  }
)

/**
 * Delete user (Admin only)
 * DELETE /api/admin/users/:userId
 * Requires: admin role and delete:users permission
 */
router.delete('/users/:userId',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  auth0Middleware.requirePermission('delete:users'),
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    try {
      const { userId } = req.params

      // Prevent self-deletion
      if (userId === req.user?.sub) {
        res.status(400).json({
          success: false,
          error: 'Cannot delete your own account'
        })
        return
      }

      // TODO: Delete user from Auth0 and database
      // This would involve calling Auth0 Management API

      res.json({
        success: true,
        data: {
          userId,
          message: 'User deleted successfully'
        }
      })
    } catch (error) {
      console.error('Error deleting user:', error)
      res.status(500).json({
        success: false,
        error: 'Internal server error'
      })
    }
  }
)

/**
 * Get audit logs (Admin only)
 * GET /api/admin/audit-logs
 * Requires: admin role and read:audit-logs permission
 */
router.get('/audit-logs',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  auth0Middleware.requirePermission('read:audit-logs'),
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    try {
      const { page = 1, limit = 50 } = req.query

      // Mock audit logs
      const auditLogs = [
        {
          id: '1',
          timestamp: '2024-01-15T10:30:00Z',
          userId: req.user?.sub,
          action: 'user.login',
          resource: 'authentication',
          details: { ip: '192.168.1.1', userAgent: 'Mozilla/5.0...' }
        },
        {
          id: '2',
          timestamp: '2024-01-15T10:25:00Z',
          userId: 'user123',
          action: 'user.role.updated',
          resource: 'user_management',
          details: { oldRoles: ['user'], newRoles: ['user', 'manager'] }
        },
        {
          id: '3',
          timestamp: '2024-01-15T10:20:00Z',
          userId: 'admin456',
          action: 'project.created',
          resource: 'projects',
          details: { projectId: 'proj789', projectName: 'Solar Installation Alpha' }
        }
      ]

      res.json({
        success: true,
        data: {
          logs: auditLogs,
          pagination: {
            page: Number(page),
            limit: Number(limit),
            total: auditLogs.length,
            totalPages: Math.ceil(auditLogs.length / Number(limit))
          }
        }
      })
    } catch (error) {
      console.error('Error fetching audit logs:', error)
      res.status(500).json({
        success: false,
        error: 'Internal server error'
      })
    }
  }
)

/**
 * Update system settings (Admin only)
 * PUT /api/admin/settings
 * Requires: admin role and write:settings permission
 */
router.put('/settings',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  auth0Middleware.requirePermission('write:settings'),
  async (req: AuthenticatedRequest, res: Response): Promise<void> => {
    try {
      const { settings } = req.body

      if (!settings || typeof settings !== 'object') {
        res.status(400).json({
          success: false,
          error: 'Settings object is required'
        })
        return
      }

      // TODO: Validate and save settings to database
      // This would involve validating the settings schema
      // and saving to your configuration store

      res.json({
        success: true,
        data: {
          settings,
          message: 'Settings updated successfully',
          updatedBy: req.user?.email,
          updatedAt: new Date().toISOString()
        }
      })
    } catch (error) {
      console.error('Error updating settings:', error)
      res.status(500).json({
        success: false,
        error: 'Internal server error'
      })
    }
  }
)

export default router