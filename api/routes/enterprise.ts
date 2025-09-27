import express from 'express'
import auth0Middleware from '../middleware/auth0.js'

const router = express.Router()

// Mock enterprise connections data
const enterpriseConnections = [
  {
    id: 'saml-acme-corp',
    name: 'ACME Corporation',
    domain: 'acme.com',
    strategy: 'saml',
    enabled: true,
    metadata: {
      ssoUrl: 'https://acme.com/sso/saml',
      certificate: '-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----',
      issuer: 'acme-corp',
      signInEndpoint: 'https://acme.com/sso/saml/login',
      signOutEndpoint: 'https://acme.com/sso/saml/logout'
    },
    settings: {
      mfaRequired: true,
      sessionTimeout: 60,
      passwordPolicy: 'strong',
      ssoOnly: true
    },
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-01-20T14:30:00Z'
  },
  {
    id: 'oidc-tech-solutions',
    name: 'Tech Solutions Inc',
    domain: 'techsolutions.com',
    strategy: 'oidc',
    enabled: true,
    metadata: {
      issuer: 'https://techsolutions.com/oidc',
      clientId: 'nextgen-fusion-client',
      authorizationEndpoint: 'https://techsolutions.com/oidc/auth',
      tokenEndpoint: 'https://techsolutions.com/oidc/token',
      userInfoEndpoint: 'https://techsolutions.com/oidc/userinfo'
    },
    settings: {
      mfaRequired: false,
      sessionTimeout: 120,
      passwordPolicy: 'standard',
      ssoOnly: false
    },
    createdAt: '2024-01-10T09:00:00Z',
    updatedAt: '2024-01-18T16:45:00Z'
  },
  {
    id: 'ad-global-enterprise',
    name: 'Global Enterprise',
    domain: 'global-enterprise.com',
    strategy: 'ad',
    enabled: true,
    metadata: {
      domain: 'global-enterprise.com',
      domainController: 'dc.global-enterprise.com',
      baseDN: 'DC=global-enterprise,DC=com',
      userSearchBase: 'OU=Users,DC=global-enterprise,DC=com'
    },
    settings: {
      mfaRequired: true,
      sessionTimeout: 480,
      passwordPolicy: 'strong',
      ssoOnly: true
    },
    createdAt: '2024-01-05T08:00:00Z',
    updatedAt: '2024-01-22T11:20:00Z'
  }
]

// Mock domain configurations
const domainConfigs = [
  { domain: 'acme.com', connectionId: 'saml-acme-corp', authType: 'enterprise' },
  { domain: 'techsolutions.com', connectionId: 'oidc-tech-solutions', authType: 'enterprise' },
  { domain: 'global-enterprise.com', connectionId: 'ad-global-enterprise', authType: 'enterprise' }
]

/**
 * GET /api/enterprise/connections
 * Get all enterprise connections
 * Requires: Admin role
 */
router.get('/connections', 
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  (req, res) => {
    try {
      const { domain, strategy, enabled } = req.query
      
      let filteredConnections = [...enterpriseConnections]
      
      // Filter by domain if provided
      if (domain) {
        filteredConnections = filteredConnections.filter(conn => 
          conn.domain.toLowerCase().includes((domain as string).toLowerCase())
        )
      }
      
      // Filter by strategy if provided
      if (strategy) {
        filteredConnections = filteredConnections.filter(conn => 
          conn.strategy === strategy
        )
      }
      
      // Filter by enabled status if provided
      if (enabled !== undefined) {
        const isEnabled = enabled === 'true'
        filteredConnections = filteredConnections.filter(conn => 
          conn.enabled === isEnabled
        )
      }
      
      res.json({
        connections: filteredConnections,
        total: filteredConnections.length,
        strategies: ['saml', 'oidc', 'ad']
      })
    } catch (error) {
      console.error('Error fetching enterprise connections:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * GET /api/enterprise/connections/:id
 * Get specific enterprise connection
 * Requires: Admin role
 */
router.get('/connections/:id',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  (req, res) => {
    try {
      const { id } = req.params
      const connection = enterpriseConnections.find(conn => conn.id === id)
      
      if (!connection) {
        return res.status(404).json({ error: 'Connection not found' })
      }
      
      res.json(connection)
    } catch (error) {
      console.error('Error fetching enterprise connection:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/enterprise/connections
 * Create new enterprise connection
 * Requires: Admin role
 */
router.post('/connections',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  (req, res) => {
    try {
      const { name, domain, strategy, metadata, settings } = req.body
      
      // Validate required fields
      if (!name || !domain || !strategy) {
        return res.status(400).json({ 
          error: 'Missing required fields: name, domain, strategy' 
        })
      }
      
      // Check if domain already exists
      const existingConnection = enterpriseConnections.find(conn => 
        conn.domain.toLowerCase() === domain.toLowerCase()
      )
      
      if (existingConnection) {
        return res.status(409).json({ 
          error: 'Connection with this domain already exists' 
        })
      }
      
      // Generate new connection ID
      const connectionId = `${strategy}-${domain.replace(/\./g, '-')}`
      
      const newConnection = {
        id: connectionId,
        name,
        domain: domain.toLowerCase(),
        strategy,
        enabled: true,
        metadata: metadata || {},
        settings: {
          mfaRequired: false,
          sessionTimeout: 60,
          passwordPolicy: 'standard',
          ssoOnly: false,
          ...settings
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      }
      
      enterpriseConnections.push(newConnection)
      
      // Add domain configuration
      domainConfigs.push({
        domain: domain.toLowerCase(),
        connectionId,
        authType: 'enterprise'
      })
      
      res.status(201).json(newConnection)
    } catch (error) {
      console.error('Error creating enterprise connection:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * PUT /api/enterprise/connections/:id
 * Update enterprise connection
 * Requires: Admin role
 */
router.put('/connections/:id',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  (req, res) => {
    try {
      const { id } = req.params
      const updates = req.body
      
      const connectionIndex = enterpriseConnections.findIndex(conn => conn.id === id)
      
      if (connectionIndex === -1) {
        return res.status(404).json({ error: 'Connection not found' })
      }
      
      // Update connection
      enterpriseConnections[connectionIndex] = {
        ...enterpriseConnections[connectionIndex],
        ...updates,
        id, // Prevent ID changes
        updatedAt: new Date().toISOString()
      }
      
      res.json(enterpriseConnections[connectionIndex])
    } catch (error) {
      console.error('Error updating enterprise connection:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * DELETE /api/enterprise/connections/:id
 * Delete enterprise connection
 * Requires: Admin role
 */
router.delete('/connections/:id',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  (req, res) => {
    try {
      const { id } = req.params
      
      const connectionIndex = enterpriseConnections.findIndex(conn => conn.id === id)
      
      if (connectionIndex === -1) {
        return res.status(404).json({ error: 'Connection not found' })
      }
      
      const connection = enterpriseConnections[connectionIndex]
      
      // Remove connection
      enterpriseConnections.splice(connectionIndex, 1)
      
      // Remove domain configuration
      const domainIndex = domainConfigs.findIndex(config => 
        config.connectionId === id
      )
      if (domainIndex !== -1) {
        domainConfigs.splice(domainIndex, 1)
      }
      
      res.json({ message: 'Connection deleted successfully', connection })
    } catch (error) {
      console.error('Error deleting enterprise connection:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/enterprise/connections/:id/test
 * Test enterprise connection
 * Requires: Admin role
 */
router.post('/connections/:id/test',
  auth0Middleware.authenticate,
  auth0Middleware.requireRole('admin'),
  (req, res) => {
    try {
      const { id } = req.params
      const connection = enterpriseConnections.find(conn => conn.id === id)
      
      if (!connection) {
        return res.status(404).json({ error: 'Connection not found' })
      }
      
      // Mock connection test
      const testResult = {
        success: connection.enabled,
        message: connection.enabled 
          ? 'Connection test successful'
          : 'Connection is disabled',
        details: {
          strategy: connection.strategy,
          domain: connection.domain,
          metadata: connection.metadata,
          timestamp: new Date().toISOString()
        }
      }
      
      res.json(testResult)
    } catch (error) {
      console.error('Error testing enterprise connection:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * GET /api/enterprise/domain-lookup
 * Look up authentication method for a domain
 * Public endpoint (no authentication required)
 */
router.get('/domain-lookup', (req, res) => {
  try {
    const { domain } = req.query
    
    if (!domain) {
      return res.status(400).json({ error: 'Domain parameter is required' })
    }
    
    const domainConfig = domainConfigs.find(config => 
      config.domain.toLowerCase() === (domain as string).toLowerCase()
    )
    
    if (!domainConfig) {
      return res.json({ 
        domain: domain as string,
        authType: 'social',
        connectionId: null
      })
    }
    
    const connection = enterpriseConnections.find(conn => 
      conn.id === domainConfig.connectionId
    )
    
    res.json({
      domain: domain as string,
      authType: domainConfig.authType,
      connectionId: domainConfig.connectionId,
      connectionName: connection?.name,
      strategy: connection?.strategy,
      enabled: connection?.enabled
    })
  } catch (error) {
    console.error('Error looking up domain:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
})

/**
 * GET /api/enterprise/onboarding/status
 * Get onboarding status for current user's organization
 * Requires: Authentication
 */
router.get('/onboarding/status',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const user = req.user
      const userDomain = user?.email?.split('@')[1]?.toLowerCase()
      
      if (!userDomain) {
        return res.status(400).json({ error: 'Unable to determine user domain' })
      }
      
      const connection = enterpriseConnections.find(conn => 
        conn.domain === userDomain
      )
      
      const onboardingStatus = {
        completed: !!connection,
        domain: userDomain,
        connectionId: connection?.id,
        organizationName: connection?.name,
        strategy: connection?.strategy,
        settings: connection?.settings,
        nextSteps: connection ? [] : [
          'Complete organization setup',
          'Configure security preferences',
          'Test SSO connection'
        ]
      }
      
      res.json(onboardingStatus)
    } catch (error) {
      console.error('Error fetching onboarding status:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/enterprise/onboarding/complete
 * Complete enterprise onboarding
 * Requires: Authentication
 */
router.post('/onboarding/complete',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const { organizationData, securityData } = req.body
      const user = req.user
      
      if (!organizationData || !securityData) {
        return res.status(400).json({ 
          error: 'Missing required onboarding data' 
        })
      }
      
      // Mock onboarding completion
      const onboardingResult = {
        success: true,
        message: 'Enterprise onboarding completed successfully',
        organization: {
          name: organizationData.name,
          domain: organizationData.domain,
          adminEmail: organizationData.adminEmail
        },
        security: securityData,
        nextSteps: [
          'IT administrator will receive setup instructions',
          'Users can now sign in with enterprise credentials',
          'Access admin panel to manage users and permissions'
        ]
      }
      
      res.status(201).json(onboardingResult)
    } catch (error) {
      console.error('Error completing enterprise onboarding:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

export default router