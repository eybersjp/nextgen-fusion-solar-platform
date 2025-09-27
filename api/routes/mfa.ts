import express from 'express'
import auth0Middleware from '../middleware/auth0.js'

const router = express.Router()

// Mock MFA methods data
interface MFAMethod {
  id: string
  userId: string
  type: 'sms' | 'email' | 'totp' | 'webauthn'
  enabled: boolean
  primary: boolean
  phoneNumber?: string
  email?: string
  secret?: string
  createdAt: string
  lastUsed?: string
}

interface BackupCode {
  id: string
  userId: string
  code: string
  used: boolean
  usedAt?: string
  createdAt: string
}

// Mock data storage
const userMFAMethods: MFAMethod[] = [
  {
    id: 'mfa-1',
    userId: 'user-123',
    type: 'totp',
    enabled: true,
    primary: true,
    secret: 'JBSWY3DPEHPK3PXP',
    createdAt: '2024-01-15T10:00:00Z',
    lastUsed: '2024-01-20T14:30:00Z'
  },
  {
    id: 'mfa-2',
    userId: 'user-456',
    type: 'sms',
    enabled: true,
    primary: true,
    phoneNumber: '+1234567890',
    createdAt: '2024-01-10T09:00:00Z',
    lastUsed: '2024-01-18T16:45:00Z'
  }
]

const userBackupCodes: BackupCode[] = [
  {
    id: 'backup-1',
    userId: 'user-123',
    code: 'ABC123DEF',
    used: false,
    createdAt: '2024-01-15T10:00:00Z'
  },
  {
    id: 'backup-2',
    userId: 'user-123',
    code: 'GHI456JKL',
    used: false,
    createdAt: '2024-01-15T10:00:00Z'
  }
]

// Mock pending MFA setups
const pendingMFASetups = new Map<string, any>()

/**
 * GET /api/mfa/methods
 * Get user's MFA methods
 * Requires: Authentication
 */
router.get('/methods',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      const methods = userMFAMethods.filter(method => method.userId === userId)
      
      // Remove sensitive data
      const safeMethods = methods.map(method => ({
        id: method.id,
        type: method.type,
        enabled: method.enabled,
        primary: method.primary,
        phoneNumber: method.phoneNumber ? method.phoneNumber.replace(/.(?=.{4})/g, '*') : undefined,
        email: method.email,
        createdAt: method.createdAt,
        lastUsed: method.lastUsed
      }))
      
      res.json(safeMethods)
    } catch (error) {
      console.error('Error fetching MFA methods:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/mfa/setup
 * Setup a new MFA method
 * Requires: Authentication
 */
router.post('/setup',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      const { type, phoneNumber, email } = req.body
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      if (!type || !['sms', 'email', 'totp', 'webauthn'].includes(type)) {
        return res.status(400).json({ error: 'Invalid MFA type' })
      }
      
      // Check if user already has this type of MFA
      const existingMethod = userMFAMethods.find(method => 
        method.userId === userId && method.type === type
      )
      
      if (existingMethod) {
        return res.status(409).json({ error: 'MFA method already exists' })
      }
      
      let setupData: any = {
        userId,
        type,
        setupId: `setup-${Date.now()}`
      }
      
      switch (type) {
        case 'sms':
          if (!phoneNumber) {
            return res.status(400).json({ error: 'Phone number required for SMS MFA' })
          }
          setupData.phoneNumber = phoneNumber
          setupData.verificationCode = Math.floor(100000 + Math.random() * 900000).toString()
          break
          
        case 'email':
          setupData.email = email || req.user?.email
          setupData.verificationCode = Math.floor(100000 + Math.random() * 900000).toString()
          break
          
        case 'totp':
          setupData.secret = 'JBSWY3DPEHPK3PXP' // Mock secret
          setupData.qrCodeUrl = `otpauth://totp/NextGen%20Fusion:${req.user?.email}?secret=${setupData.secret}&issuer=NextGen%20Fusion`
          break
          
        case 'webauthn':
          setupData.challenge = 'mock-webauthn-challenge'
          break
      }
      
      // Store pending setup
      pendingMFASetups.set(setupData.setupId, setupData)
      
      // Remove sensitive data from response
      const responseData = { ...setupData }
      delete responseData.verificationCode
      
      res.json({
        setupId: setupData.setupId,
        type: setupData.type,
        qrCodeUrl: setupData.qrCodeUrl,
        secret: setupData.secret,
        challenge: setupData.challenge,
        message: type === 'sms' ? 'Verification code sent to your phone' :
                type === 'email' ? 'Verification code sent to your email' :
                'Setup initiated'
      })
    } catch (error) {
      console.error('Error setting up MFA:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/mfa/verify
 * Verify MFA setup
 * Requires: Authentication
 */
router.post('/verify',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      const { setupId, code, type } = req.body
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      if (!code) {
        return res.status(400).json({ error: 'Verification code required' })
      }
      
      // Get pending setup
      const setupData = setupId ? pendingMFASetups.get(setupId) : null
      
      if (setupId && !setupData) {
        return res.status(404).json({ error: 'Setup session not found' })
      }
      
      // Verify code based on type
      let isValid = false
      const mfaType = type || setupData?.type
      
      switch (mfaType) {
        case 'sms':
        case 'email':
          isValid = setupData?.verificationCode === code
          break
          
        case 'totp':
          // Mock TOTP verification - in real implementation, use a TOTP library
          isValid = code.length === 6 && /^\d{6}$/.test(code)
          break
          
        case 'webauthn':
          // Mock WebAuthn verification
          isValid = code === 'webauthn-success'
          break
          
        default:
          return res.status(400).json({ error: 'Invalid MFA type' })
      }
      
      if (!isValid) {
        return res.status(400).json({ error: 'Invalid verification code' })
      }
      
      // Create MFA method
      const newMethod: MFAMethod = {
        id: `mfa-${Date.now()}`,
        userId,
        type: mfaType,
        enabled: true,
        primary: userMFAMethods.filter(m => m.userId === userId).length === 0,
        phoneNumber: setupData?.phoneNumber,
        email: setupData?.email || req.user?.email,
        secret: setupData?.secret,
        createdAt: new Date().toISOString()
      }
      
      userMFAMethods.push(newMethod)
      
      // Generate backup codes
      const backupCodes = []
      for (let i = 0; i < 8; i++) {
        const code = Math.random().toString(36).substring(2, 11).toUpperCase()
        backupCodes.push(code)
        
        userBackupCodes.push({
          id: `backup-${Date.now()}-${i}`,
          userId,
          code,
          used: false,
          createdAt: new Date().toISOString()
        })
      }
      
      // Clean up pending setup
      if (setupId) {
        pendingMFASetups.delete(setupId)
      }
      
      res.json({
        success: true,
        method: {
          id: newMethod.id,
          type: newMethod.type,
          enabled: newMethod.enabled,
          primary: newMethod.primary,
          createdAt: newMethod.createdAt
        },
        backupCodes
      })
    } catch (error) {
      console.error('Error verifying MFA:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/mfa/challenge
 * Create MFA challenge for login
 * Requires: Authentication
 */
router.post('/challenge',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      const { type } = req.body
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      const method = userMFAMethods.find(m => 
        m.userId === userId && m.type === type && m.enabled
      )
      
      if (!method) {
        return res.status(404).json({ error: 'MFA method not found' })
      }
      
      const challengeId = `challenge-${Date.now()}`
      let challengeData: any = {
        challengeId,
        userId,
        type,
        createdAt: new Date().toISOString(),
        expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString() // 5 minutes
      }
      
      switch (type) {
        case 'sms':
          challengeData.verificationCode = Math.floor(100000 + Math.random() * 900000).toString()
          challengeData.phoneNumber = method.phoneNumber
          break
          
        case 'email':
          challengeData.verificationCode = Math.floor(100000 + Math.random() * 900000).toString()
          challengeData.email = method.email
          break
          
        case 'totp':
          // No additional data needed for TOTP
          break
          
        case 'webauthn':
          challengeData.challenge = 'mock-webauthn-challenge'
          break
      }
      
      // Store challenge (in real implementation, use Redis or similar)
      pendingMFASetups.set(challengeId, challengeData)
      
      res.json({
        challengeId,
        type,
        message: type === 'sms' ? 'Verification code sent to your phone' :
                type === 'email' ? 'Verification code sent to your email' :
                type === 'totp' ? 'Enter code from your authenticator app' :
                'Complete WebAuthn challenge',
        expiresAt: challengeData.expiresAt
      })
    } catch (error) {
      console.error('Error creating MFA challenge:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/mfa/validate
 * Validate MFA challenge
 * Requires: Authentication
 */
router.post('/validate',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      const { challengeId, code } = req.body
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      if (!challengeId || !code) {
        return res.status(400).json({ error: 'Challenge ID and code required' })
      }
      
      const challengeData = pendingMFASetups.get(challengeId)
      
      if (!challengeData) {
        return res.status(404).json({ error: 'Challenge not found or expired' })
      }
      
      if (challengeData.userId !== userId) {
        return res.status(403).json({ error: 'Invalid challenge' })
      }
      
      // Check expiration
      if (new Date() > new Date(challengeData.expiresAt)) {
        pendingMFASetups.delete(challengeId)
        return res.status(400).json({ error: 'Challenge expired' })
      }
      
      // Validate code
      let isValid = false
      
      switch (challengeData.type) {
        case 'sms':
        case 'email':
          isValid = challengeData.verificationCode === code
          break
          
        case 'totp':
          // Mock TOTP validation
          isValid = code.length === 6 && /^\d{6}$/.test(code)
          break
          
        case 'webauthn':
          isValid = code === 'webauthn-success'
          break
          
        default:
          // Check if it's a backup code
          const backupCode = userBackupCodes.find(bc => 
            bc.userId === userId && bc.code === code && !bc.used
          )
          if (backupCode) {
            backupCode.used = true
            backupCode.usedAt = new Date().toISOString()
            isValid = true
          }
      }
      
      if (!isValid) {
        return res.status(400).json({ error: 'Invalid verification code' })
      }
      
      // Update last used timestamp
      const method = userMFAMethods.find(m => 
        m.userId === userId && m.type === challengeData.type
      )
      if (method) {
        method.lastUsed = new Date().toISOString()
      }
      
      // Clean up challenge
      pendingMFASetups.delete(challengeId)
      
      res.json({
        success: true,
        message: 'MFA validation successful',
        validatedAt: new Date().toISOString()
      })
    } catch (error) {
      console.error('Error validating MFA:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * DELETE /api/mfa/methods/:id
 * Remove MFA method
 * Requires: Authentication
 */
router.delete('/methods/:id',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      const { id } = req.params
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      const methodIndex = userMFAMethods.findIndex(method => 
        method.id === id && method.userId === userId
      )
      
      if (methodIndex === -1) {
        return res.status(404).json({ error: 'MFA method not found' })
      }
      
      const method = userMFAMethods[methodIndex]
      
      // Check if this is the only MFA method
      const userMethods = userMFAMethods.filter(m => m.userId === userId && m.enabled)
      if (userMethods.length === 1) {
        return res.status(400).json({ 
          error: 'Cannot remove the only MFA method. Add another method first.' 
        })
      }
      
      // Remove method
      userMFAMethods.splice(methodIndex, 1)
      
      // If this was the primary method, make another method primary
      if (method.primary) {
        const remainingMethods = userMFAMethods.filter(m => m.userId === userId && m.enabled)
        if (remainingMethods.length > 0) {
          remainingMethods[0].primary = true
        }
      }
      
      res.json({
        success: true,
        message: 'MFA method removed successfully',
        removedMethod: {
          id: method.id,
          type: method.type
        }
      })
    } catch (error) {
      console.error('Error removing MFA method:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * GET /api/mfa/backup-codes
 * Get user's backup codes
 * Requires: Authentication
 */
router.get('/backup-codes',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      const codes = userBackupCodes.filter(code => 
        code.userId === userId && !code.used
      )
      
      res.json({
        codes: codes.map(code => ({
          id: code.id,
          code: code.code,
          createdAt: code.createdAt
        })),
        total: codes.length
      })
    } catch (error) {
      console.error('Error fetching backup codes:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

/**
 * POST /api/mfa/backup-codes/regenerate
 * Regenerate backup codes
 * Requires: Authentication
 */
router.post('/backup-codes/regenerate',
  auth0Middleware.authenticate,
  (req, res) => {
    try {
      const userId = req.user?.sub
      
      if (!userId) {
        return res.status(400).json({ error: 'User ID not found' })
      }
      
      // Remove existing unused backup codes
      const existingCodesIndices = []
      for (let i = userBackupCodes.length - 1; i >= 0; i--) {
        if (userBackupCodes[i].userId === userId && !userBackupCodes[i].used) {
          existingCodesIndices.push(i)
        }
      }
      
      existingCodesIndices.forEach(index => {
        userBackupCodes.splice(index, 1)
      })
      
      // Generate new backup codes
      const newCodes = []
      for (let i = 0; i < 8; i++) {
        const code = Math.random().toString(36).substring(2, 11).toUpperCase()
        newCodes.push(code)
        
        userBackupCodes.push({
          id: `backup-${Date.now()}-${i}`,
          userId,
          code,
          used: false,
          createdAt: new Date().toISOString()
        })
      }
      
      res.json({
        success: true,
        codes: newCodes,
        message: 'Backup codes regenerated successfully'
      })
    } catch (error) {
      console.error('Error regenerating backup codes:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  }
)

export default router