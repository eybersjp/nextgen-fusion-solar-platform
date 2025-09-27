import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { Auth0Provider, useAuth0, User } from '@auth0/auth0-react'
import { TokenStorage, TokenRefresh } from '../utils/tokenStorage'
import { useAuthErrorHandler } from '../components/auth/AuthErrorHandler'

// Auth context types
interface AuthContextType {
  // Auth0 user and authentication state
  user: User | undefined
  isAuthenticated: boolean
  isLoading: boolean
  
  // Enhanced authentication methods
  login: (options?: LoginOptions) => Promise<void>
  logout: (options?: LogoutOptions) => Promise<void>
  loginWithRedirect: (options?: RedirectLoginOptions) => Promise<void>
  loginWithPopup: (options?: PopupLoginOptions) => Promise<void>
  
  // Token management
  getAccessTokenSilently: (options?: GetTokenSilentlyOptions) => Promise<string>
  getAccessTokenWithPopup: (options?: GetTokenWithPopupOptions) => Promise<string>
  
  // Role and permission management
  hasRole: (role: string) => boolean
  hasAnyRole: (roles: string[]) => boolean
  hasPermission: (permission: string) => boolean
  hasPermissions: (permissions: string[]) => boolean
  getUserRoles: () => string[]
  getUserPermissions: () => string[]
  
  // Session management
  refreshSession: () => Promise<void>
  clearSession: () => Promise<void>
  isSessionValid: () => Promise<boolean>
  
  // MFA management
  isMfaRequired: boolean
  mfaMethods: MfaMethod[]
  setupMfa: (method: string) => Promise<MfaSetupResult>
  verifyMfa: (code: string, method: string) => Promise<boolean>
  
  // Enterprise features
  isEnterpriseUser: boolean
  organizationId?: string
  organizationName?: string
  
  // Error handling
  authError: any
  clearAuthError: () => void
}

interface LoginOptions {
  redirectUri?: string
  appState?: any
  organization?: string
  invitation?: string
}

interface LogoutOptions {
  returnTo?: string
  federated?: boolean
}

interface RedirectLoginOptions extends LoginOptions {
  connection?: string
  prompt?: string
  screen_hint?: string
}

interface PopupLoginOptions {
  connection?: string
  prompt?: string
}

interface GetTokenSilentlyOptions {
  audience?: string
  scope?: string
  ignoreCache?: boolean
}

interface GetTokenWithPopupOptions {
  audience?: string
  scope?: string
}

interface MfaMethod {
  id: string
  type: 'sms' | 'email' | 'totp' | 'webauthn'
  name: string
  isEnabled: boolean
  isDefault: boolean
}

interface MfaSetupResult {
  qrCode?: string
  secret?: string
  backupCodes?: string[]
  challenge?: string
}

// Create the context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Auth0 configuration
const auth0Config = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN!,
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID!,
  authorizationParams: {
    redirect_uri: window.location.origin,
    audience: import.meta.env.VITE_AUTH0_AUDIENCE,
    scope: 'openid profile email read:users update:users read:roles read:permissions'
  },
  useRefreshTokens: true,
  cacheLocation: 'memory' as const,
  useRefreshTokensFallback: true
}

// Enhanced Auth Provider Component
const EnhancedAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const {
    user,
    isAuthenticated,
    isLoading,
    loginWithRedirect: auth0LoginWithRedirect,
    loginWithPopup: auth0LoginWithPopup,
    logout: auth0Logout,
    getAccessTokenSilently: auth0GetAccessTokenSilently,
    getAccessTokenWithPopup: auth0GetAccessTokenWithPopup,
    error
  } = useAuth0()
  
  const { authError, handleAuthError, clearAuthError } = useAuthErrorHandler()
  const [isMfaRequired, setIsMfaRequired] = useState(false)
  const [mfaMethods, setMfaMethods] = useState<MfaMethod[]>([])
  const [isEnterpriseUser, setIsEnterpriseUser] = useState(false)
  const [organizationId, setOrganizationId] = useState<string | undefined>()
  const [organizationName, setOrganizationName] = useState<string | undefined>()
  
  // Handle Auth0 errors
  useEffect(() => {
    if (error) {
      handleAuthError(error)
    }
  }, [error, handleAuthError])
  
  // Initialize user session data
  useEffect(() => {
    if (isAuthenticated && user) {
      initializeUserSession()
    }
  }, [isAuthenticated, user])
  
  const initializeUserSession = useCallback(async () => {
    if (!user) return
    
    try {
      // Store user data and tokens
      const accessToken = await auth0GetAccessTokenSilently()
      const tokenData = {
        accessToken,
        expiresAt: Date.now() + (60 * 60 * 1000), // 1 hour
        tokenType: 'Bearer'
      }
      
      await TokenStorage.storeTokens(tokenData, user)
      
      // Check for enterprise features
      const isEnterprise = user.email?.includes('@') && 
        !['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'].some(domain => 
          user.email?.endsWith(domain)
        )
      
      setIsEnterpriseUser(isEnterprise)
      
      // Extract organization info from user metadata
      const orgId = user['https://nextgenfusion.com/organization_id']
      const orgName = user['https://nextgenfusion.com/organization_name']
      
      if (orgId) setOrganizationId(orgId)
      if (orgName) setOrganizationName(orgName)
      
      // Check MFA status
      await checkMfaStatus()
      
    } catch (error) {
      console.error('Failed to initialize user session:', error)
      handleAuthError(error as Error)
    }
  }, [user, auth0GetAccessTokenSilently, handleAuthError])
  
  const checkMfaStatus = useCallback(async () => {
    try {
      const accessToken = await TokenStorage.getAccessToken()
      if (!accessToken) return
      
      const response = await fetch('/api/mfa/methods', {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      })
      
      if (response.ok) {
        const methods = await response.json()
        setMfaMethods(methods)
        setIsMfaRequired(methods.length === 0) // Require MFA if no methods set up
      }
    } catch (error) {
      console.error('Failed to check MFA status:', error)
    }
  }, [])
  
  // Enhanced login methods
  const login = useCallback(async (options: LoginOptions = {}) => {
    try {
      await auth0LoginWithRedirect({
        authorizationParams: {
          redirect_uri: options.redirectUri || window.location.origin,
          organization: options.organization,
          invitation: options.invitation
        },
        appState: options.appState
      })
    } catch (error) {
      handleAuthError(error as Error)
    }
  }, [auth0LoginWithRedirect, handleAuthError])
  
  const loginWithRedirect = useCallback(async (options: RedirectLoginOptions = {}) => {
    try {
      await auth0LoginWithRedirect({
        authorizationParams: {
          redirect_uri: options.redirectUri || window.location.origin,
          connection: options.connection,
          prompt: options.prompt,
          screen_hint: options.screen_hint,
          organization: options.organization,
          invitation: options.invitation
        },
        appState: options.appState
      })
    } catch (error) {
      handleAuthError(error as Error)
    }
  }, [auth0LoginWithRedirect, handleAuthError])
  
  const loginWithPopup = useCallback(async (options: PopupLoginOptions = {}) => {
    try {
      await auth0LoginWithPopup({
        authorizationParams: {
          connection: options.connection,
          prompt: options.prompt
        }
      })
    } catch (error) {
      handleAuthError(error as Error)
    }
  }, [auth0LoginWithPopup, handleAuthError])
  
  const logout = useCallback(async (options: LogoutOptions = {}) => {
    try {
      await TokenStorage.clearTokens()
      await auth0Logout({
        logoutParams: {
          returnTo: options.returnTo || window.location.origin,
          federated: options.federated
        }
      })
    } catch (error) {
      handleAuthError(error as Error)
    }
  }, [auth0Logout, handleAuthError])
  
  // Enhanced token methods
  const getAccessTokenSilently = useCallback(async (options: GetTokenSilentlyOptions = {}) => {
    try {
      // Check if we should refresh the token
      const shouldRefresh = await TokenStorage.shouldRefreshToken()
      if (shouldRefresh) {
        await TokenRefresh.refreshAccessToken()
      }
      
      const token = await auth0GetAccessTokenSilently({
        authorizationParams: {
          audience: options.audience,
          scope: options.scope
        },
        cacheMode: options.ignoreCache ? 'off' : 'on'
      })
      
      // Update stored token
      const tokenData = {
        accessToken: token,
        expiresAt: Date.now() + (60 * 60 * 1000), // 1 hour
        tokenType: 'Bearer',
        scope: options.scope
      }
      
      await TokenStorage.storeTokens(tokenData, user)
      
      return token
    } catch (error) {
      handleAuthError(error as Error)
      throw error
    }
  }, [auth0GetAccessTokenSilently, user, handleAuthError])
  
  const getAccessTokenWithPopup = useCallback(async (options: GetTokenWithPopupOptions = {}) => {
    try {
      const token = await auth0GetAccessTokenWithPopup({
        authorizationParams: {
          audience: options.audience,
          scope: options.scope
        }
      })
      
      // Update stored token
      const tokenData = {
        accessToken: token,
        expiresAt: Date.now() + (60 * 60 * 1000), // 1 hour
        tokenType: 'Bearer',
        scope: options.scope
      }
      
      await TokenStorage.storeTokens(tokenData, user)
      
      return token
    } catch (error) {
      handleAuthError(error as Error)
      throw error
    }
  }, [auth0GetAccessTokenWithPopup, user, handleAuthError])
  
  // Role and permission methods
  const getUserRoles = useCallback((): string[] => {
    if (!user) return []
    return user['https://nextgenfusion.com/roles'] || []
  }, [user])
  
  const getUserPermissions = useCallback((): string[] => {
    if (!user) return []
    return user['https://nextgenfusion.com/permissions'] || []
  }, [user])
  
  const hasRole = useCallback((role: string): boolean => {
    const roles = getUserRoles()
    return roles.includes(role)
  }, [getUserRoles])
  
  const hasAnyRole = useCallback((roles: string[]): boolean => {
    const userRoles = getUserRoles()
    return roles.some(role => userRoles.includes(role))
  }, [getUserRoles])
  
  const hasPermission = useCallback((permission: string): boolean => {
    const permissions = getUserPermissions()
    return permissions.includes(permission)
  }, [getUserPermissions])
  
  const hasPermissions = useCallback((permissions: string[]): boolean => {
    const userPermissions = getUserPermissions()
    return permissions.every(permission => userPermissions.includes(permission))
  }, [getUserPermissions])
  
  // Session management
  const refreshSession = useCallback(async () => {
    try {
      await TokenRefresh.refreshAccessToken()
      await initializeUserSession()
    } catch (error) {
      handleAuthError(error as Error)
    }
  }, [initializeUserSession, handleAuthError])
  
  const clearSession = useCallback(async () => {
    try {
      await TokenStorage.clearTokens()
      setIsMfaRequired(false)
      setMfaMethods([])
      setIsEnterpriseUser(false)
      setOrganizationId(undefined)
      setOrganizationName(undefined)
    } catch (error) {
      console.error('Failed to clear session:', error)
    }
  }, [])
  
  const isSessionValid = useCallback(async (): Promise<boolean> => {
    return await TokenStorage.isTokenValid()
  }, [])
  
  // MFA methods
  const setupMfa = useCallback(async (method: string): Promise<MfaSetupResult> => {
    try {
      const accessToken = await TokenStorage.getAccessToken()
      if (!accessToken) throw new Error('No access token available')
      
      const response = await fetch('/api/mfa/setup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ method })
      })
      
      if (!response.ok) {
        throw new Error('MFA setup failed')
      }
      
      const result = await response.json()
      await checkMfaStatus() // Refresh MFA status
      
      return result
    } catch (error) {
      handleAuthError(error as Error)
      throw error
    }
  }, [checkMfaStatus, handleAuthError])
  
  const verifyMfa = useCallback(async (code: string, method: string): Promise<boolean> => {
    try {
      const accessToken = await TokenStorage.getAccessToken()
      if (!accessToken) throw new Error('No access token available')
      
      const response = await fetch('/api/mfa/verify', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code, method })
      })
      
      if (!response.ok) {
        throw new Error('MFA verification failed')
      }
      
      const result = await response.json()
      if (result.success) {
        await checkMfaStatus() // Refresh MFA status
        setIsMfaRequired(false)
      }
      
      return result.success
    } catch (error) {
      handleAuthError(error as Error)
      return false
    }
  }, [checkMfaStatus, handleAuthError])
  
  const contextValue: AuthContextType = {
    // Auth0 state
    user,
    isAuthenticated,
    isLoading,
    
    // Authentication methods
    login,
    logout,
    loginWithRedirect,
    loginWithPopup,
    
    // Token management
    getAccessTokenSilently,
    getAccessTokenWithPopup,
    
    // Role and permission management
    hasRole,
    hasAnyRole,
    hasPermission,
    hasPermissions,
    getUserRoles,
    getUserPermissions,
    
    // Session management
    refreshSession,
    clearSession,
    isSessionValid,
    
    // MFA management
    isMfaRequired,
    mfaMethods,
    setupMfa,
    verifyMfa,
    
    // Enterprise features
    isEnterpriseUser,
    organizationId,
    organizationName,
    
    // Error handling
    authError: authError || error,
    clearAuthError
  }
  
  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}

// Main Auth Provider with Auth0
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <Auth0Provider {...auth0Config}>
      <EnhancedAuthProvider>
        {children}
      </EnhancedAuthProvider>
    </Auth0Provider>
  )
}

// Custom hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Higher-order component for protected routes
export const withAuth = <P extends object>(
  Component: React.ComponentType<P>
): React.FC<P> => {
  return (props: P) => {
    const { isAuthenticated, isLoading } = useAuth()
    
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
        </div>
      )
    }
    
    if (!isAuthenticated) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Authentication Required</h1>
            <p className="text-gray-600 mb-6">Please sign in to access this page.</p>
            <button
              onClick={() => window.location.href = '/login'}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
              Sign In
            </button>
          </div>
        </div>
      )
    }
    
    return <Component {...props} />
  }
}

export default AuthProvider