import { User } from '@auth0/auth0-react'

// Token storage interface
interface TokenData {
  accessToken: string
  refreshToken?: string
  idToken?: string
  expiresAt: number
  tokenType: string
  scope?: string
}

interface UserSession {
  user: User
  tokens: TokenData
  lastActivity: number
  sessionId: string
}

// Storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'auth0_access_token',
  REFRESH_TOKEN: 'auth0_refresh_token',
  ID_TOKEN: 'auth0_id_token',
  USER_DATA: 'auth0_user_data',
  SESSION_DATA: 'auth0_session_data',
  EXPIRES_AT: 'auth0_expires_at',
  TOKEN_TYPE: 'auth0_token_type',
  SCOPE: 'auth0_scope'
} as const

// Security configuration
const SECURITY_CONFIG = {
  // Session timeout in milliseconds (30 minutes)
  SESSION_TIMEOUT: 30 * 60 * 1000,
  // Token refresh threshold (5 minutes before expiry)
  REFRESH_THRESHOLD: 5 * 60 * 1000,
  // Maximum session duration (8 hours)
  MAX_SESSION_DURATION: 8 * 60 * 60 * 1000,
  // Storage encryption key (in production, this should be derived from user-specific data)
  ENCRYPTION_KEY: 'nextgen-fusion-auth-key',
  // Enable secure storage (localStorage with encryption)
  USE_SECURE_STORAGE: true
}

// Simple encryption/decryption utilities
class CryptoUtils {
  private static encoder = new TextEncoder()
  private static decoder = new TextDecoder()

  static async generateKey(password: string): Promise<CryptoKey> {
    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      this.encoder.encode(password),
      { name: 'PBKDF2' },
      false,
      ['deriveBits', 'deriveKey']
    )

    return crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: this.encoder.encode('nextgen-fusion-salt'),
        iterations: 100000,
        hash: 'SHA-256'
      },
      keyMaterial,
      { name: 'AES-GCM', length: 256 },
      false,
      ['encrypt', 'decrypt']
    )
  }

  static async encrypt(data: string, password: string): Promise<string> {
    try {
      const key = await this.generateKey(password)
      const iv = crypto.getRandomValues(new Uint8Array(12))
      const encodedData = this.encoder.encode(data)

      const encrypted = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv },
        key,
        encodedData
      )

      const encryptedArray = new Uint8Array(encrypted)
      const result = new Uint8Array(iv.length + encryptedArray.length)
      result.set(iv)
      result.set(encryptedArray, iv.length)

      return btoa(String.fromCharCode(...result))
    } catch (error) {
      console.error('Encryption failed:', error)
      return data // Fallback to unencrypted data
    }
  }

  static async decrypt(encryptedData: string, password: string): Promise<string> {
    try {
      const key = await this.generateKey(password)
      const data = new Uint8Array(
        atob(encryptedData)
          .split('')
          .map(char => char.charCodeAt(0))
      )

      const iv = data.slice(0, 12)
      const encrypted = data.slice(12)

      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv },
        key,
        encrypted
      )

      return this.decoder.decode(decrypted)
    } catch (error) {
      console.error('Decryption failed:', error)
      return encryptedData // Fallback to encrypted data
    }
  }
}

// Secure storage wrapper
class SecureStorage {
  private static isAvailable(): boolean {
    try {
      const test = '__storage_test__'
      localStorage.setItem(test, test)
      localStorage.removeItem(test)
      return true
    } catch {
      return false
    }
  }

  static async setItem(key: string, value: string): Promise<void> {
    if (!this.isAvailable()) {
      console.warn('localStorage not available, data will not persist')
      return
    }

    try {
      if (SECURITY_CONFIG.USE_SECURE_STORAGE && crypto.subtle) {
        const encrypted = await CryptoUtils.encrypt(value, SECURITY_CONFIG.ENCRYPTION_KEY)
        localStorage.setItem(key, encrypted)
      } else {
        localStorage.setItem(key, value)
      }
    } catch (error) {
      console.error('Failed to store data:', error)
    }
  }

  static async getItem(key: string): Promise<string | null> {
    if (!this.isAvailable()) {
      return null
    }

    try {
      const value = localStorage.getItem(key)
      if (!value) return null

      if (SECURITY_CONFIG.USE_SECURE_STORAGE && crypto.subtle) {
        return await CryptoUtils.decrypt(value, SECURITY_CONFIG.ENCRYPTION_KEY)
      }
      
      return value
    } catch (error) {
      console.error('Failed to retrieve data:', error)
      return null
    }
  }

  static removeItem(key: string): void {
    if (this.isAvailable()) {
      localStorage.removeItem(key)
    }
  }

  static clear(): void {
    if (this.isAvailable()) {
      // Only clear auth-related items
      Object.values(STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key)
      })
    }
  }
}

// Token storage manager
export class TokenStorage {
  private static sessionId: string = this.generateSessionId()

  private static generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // Store tokens securely
  static async storeTokens(tokens: TokenData, user?: User): Promise<void> {
    try {
      await SecureStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, tokens.accessToken)
      await SecureStorage.setItem(STORAGE_KEYS.EXPIRES_AT, tokens.expiresAt.toString())
      await SecureStorage.setItem(STORAGE_KEYS.TOKEN_TYPE, tokens.tokenType)

      if (tokens.refreshToken) {
        await SecureStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, tokens.refreshToken)
      }

      if (tokens.idToken) {
        await SecureStorage.setItem(STORAGE_KEYS.ID_TOKEN, tokens.idToken)
      }

      if (tokens.scope) {
        await SecureStorage.setItem(STORAGE_KEYS.SCOPE, tokens.scope)
      }

      if (user) {
        await SecureStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user))
      }

      // Store session data
      const sessionData: UserSession = {
        user: user || {} as User,
        tokens,
        lastActivity: Date.now(),
        sessionId: this.sessionId
      }
      
      await SecureStorage.setItem(STORAGE_KEYS.SESSION_DATA, JSON.stringify(sessionData))
      
      console.log('Tokens stored securely')
    } catch (error) {
      console.error('Failed to store tokens:', error)
      throw new Error('Token storage failed')
    }
  }

  // Retrieve tokens
  static async getTokens(): Promise<TokenData | null> {
    try {
      const accessToken = await SecureStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
      const expiresAtStr = await SecureStorage.getItem(STORAGE_KEYS.EXPIRES_AT)
      const tokenType = await SecureStorage.getItem(STORAGE_KEYS.TOKEN_TYPE)

      if (!accessToken || !expiresAtStr || !tokenType) {
        return null
      }

      const refreshToken = await SecureStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
      const idToken = await SecureStorage.getItem(STORAGE_KEYS.ID_TOKEN)
      const scope = await SecureStorage.getItem(STORAGE_KEYS.SCOPE)

      return {
        accessToken,
        refreshToken: refreshToken || undefined,
        idToken: idToken || undefined,
        expiresAt: parseInt(expiresAtStr, 10),
        tokenType,
        scope: scope || undefined
      }
    } catch (error) {
      console.error('Failed to retrieve tokens:', error)
      return null
    }
  }

  // Get user data
  static async getUser(): Promise<User | null> {
    try {
      const userData = await SecureStorage.getItem(STORAGE_KEYS.USER_DATA)
      return userData ? JSON.parse(userData) : null
    } catch (error) {
      console.error('Failed to retrieve user data:', error)
      return null
    }
  }

  // Get session data
  static async getSession(): Promise<UserSession | null> {
    try {
      const sessionData = await SecureStorage.getItem(STORAGE_KEYS.SESSION_DATA)
      return sessionData ? JSON.parse(sessionData) : null
    } catch (error) {
      console.error('Failed to retrieve session data:', error)
      return null
    }
  }

  // Check if tokens are valid and not expired
  static async isTokenValid(): Promise<boolean> {
    try {
      const tokens = await this.getTokens()
      if (!tokens) return false

      const now = Date.now()
      const isExpired = now >= tokens.expiresAt
      
      if (isExpired) {
        console.log('Token has expired')
        return false
      }

      // Check session timeout
      const session = await this.getSession()
      if (session) {
        const sessionAge = now - session.lastActivity
        const maxSessionAge = now - (session.lastActivity - SECURITY_CONFIG.MAX_SESSION_DURATION)
        
        if (sessionAge > SECURITY_CONFIG.SESSION_TIMEOUT || maxSessionAge > SECURITY_CONFIG.MAX_SESSION_DURATION) {
          console.log('Session has timed out')
          await this.clearTokens()
          return false
        }
      }

      return true
    } catch (error) {
      console.error('Failed to validate token:', error)
      return false
    }
  }

  // Check if token needs refresh
  static async shouldRefreshToken(): Promise<boolean> {
    try {
      const tokens = await this.getTokens()
      if (!tokens || !tokens.refreshToken) return false

      const now = Date.now()
      const timeUntilExpiry = tokens.expiresAt - now
      
      return timeUntilExpiry <= SECURITY_CONFIG.REFRESH_THRESHOLD
    } catch (error) {
      console.error('Failed to check refresh requirement:', error)
      return false
    }
  }

  // Update last activity timestamp
  static async updateActivity(): Promise<void> {
    try {
      const session = await this.getSession()
      if (session) {
        session.lastActivity = Date.now()
        await SecureStorage.setItem(STORAGE_KEYS.SESSION_DATA, JSON.stringify(session))
      }
    } catch (error) {
      console.error('Failed to update activity:', error)
    }
  }

  // Clear all stored tokens and session data
  static async clearTokens(): Promise<void> {
    try {
      SecureStorage.clear()
      console.log('Tokens cleared')
    } catch (error) {
      console.error('Failed to clear tokens:', error)
    }
  }

  // Get access token for API calls
  static async getAccessToken(): Promise<string | null> {
    try {
      const isValid = await this.isTokenValid()
      if (!isValid) {
        return null
      }

      await this.updateActivity()
      const tokens = await this.getTokens()
      return tokens?.accessToken || null
    } catch (error) {
      console.error('Failed to get access token:', error)
      return null
    }
  }

  // Rotate refresh token (called after successful token refresh)
  static async rotateRefreshToken(newTokens: TokenData): Promise<void> {
    try {
      console.log('Rotating refresh token')
      const user = await this.getUser()
      await this.storeTokens(newTokens, user || undefined)
    } catch (error) {
      console.error('Failed to rotate refresh token:', error)
      throw error
    }
  }

  // Export session data for debugging (development only)
  static async exportSessionData(): Promise<any> {
    if (import.meta.env.MODE !== 'development') {
      console.warn('Session export is only available in development mode')
      return null
    }

    try {
      const tokens = await this.getTokens()
      const user = await this.getUser()
      const session = await this.getSession()
      
      return {
        tokens: tokens ? { ...tokens, accessToken: '***', refreshToken: '***' } : null,
        user,
        session: session ? { ...session, tokens: { ...session.tokens, accessToken: '***', refreshToken: '***' } } : null,
        isValid: await this.isTokenValid(),
        shouldRefresh: await this.shouldRefreshToken()
      }
    } catch (error) {
      console.error('Failed to export session data:', error)
      return null
    }
  }
}

// Token refresh utility
export class TokenRefresh {
  private static refreshPromise: Promise<TokenData | null> | null = null

  // Refresh access token using refresh token
  static async refreshAccessToken(): Promise<TokenData | null> {
    // Prevent multiple simultaneous refresh attempts
    if (this.refreshPromise) {
      return this.refreshPromise
    }

    this.refreshPromise = this.performRefresh()
    
    try {
      const result = await this.refreshPromise
      return result
    } finally {
      this.refreshPromise = null
    }
  }

  private static async performRefresh(): Promise<TokenData | null> {
    try {
      const tokens = await TokenStorage.getTokens()
      if (!tokens?.refreshToken) {
        console.log('No refresh token available')
        return null
      }

      console.log('Refreshing access token')
      
      // In a real implementation, this would call Auth0's token endpoint
      // For now, we'll simulate the refresh
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          refresh_token: tokens.refreshToken
        })
      })

      if (!response.ok) {
        throw new Error(`Token refresh failed: ${response.status}`)
      }

      const newTokens = await response.json()
      
      // Store the new tokens
      await TokenStorage.rotateRefreshToken(newTokens)
      
      console.log('Access token refreshed successfully')
      return newTokens
    } catch (error) {
      console.error('Token refresh failed:', error)
      // Clear invalid tokens
      await TokenStorage.clearTokens()
      return null
    }
  }
}

// Auto-refresh interceptor for API calls
export const createAuthInterceptor = () => {
  return async (url: string, options: RequestInit = {}): Promise<Response> => {
    // Check if token needs refresh before making the request
    const shouldRefresh = await TokenStorage.shouldRefreshToken()
    if (shouldRefresh) {
      await TokenRefresh.refreshAccessToken()
    }

    // Get current access token
    const accessToken = await TokenStorage.getAccessToken()
    
    if (accessToken) {
      options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${accessToken}`
      }
    }

    // Make the request
    const response = await fetch(url, options)
    
    // Handle 401 responses by attempting token refresh
    if (response.status === 401 && accessToken) {
      console.log('Received 401, attempting token refresh')
      
      const refreshedTokens = await TokenRefresh.refreshAccessToken()
      if (refreshedTokens) {
        // Retry the request with new token
        options.headers = {
          ...options.headers,
          'Authorization': `Bearer ${refreshedTokens.accessToken}`
        }
        
        return fetch(url, options)
      } else {
        // Refresh failed, redirect to login
        window.location.href = '/login'
      }
    }
    
    return response
  }
}

export default TokenStorage