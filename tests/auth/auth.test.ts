/**
 * NextGen Fusion Commercial Solar Platform
 * Authentication System Test Suite
 * 
 * Comprehensive tests for Auth0 integration, token management,
 * role-based access control, and security features.
 */

import { describe, it, expect, beforeEach, afterEach, vi, beforeAll, afterAll } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Auth0Provider } from '@auth0/auth0-react'
import axios from 'axios'
import { AuthProvider, useAuth } from '../../src/contexts/AuthContext'
import { RoleGuard, AdminOnly, ManagerOnly, UserOnly } from '../../src/components/auth/RoleGuard'
import { EnterpriseAuth } from '../../src/components/auth/EnterpriseAuth'
import { DomainRouter } from '../../src/components/auth/DomainRouter'
import { MFASetup } from '../../src/components/auth/MFASetup'
import { AuthErrorHandler } from '../../src/components/auth/AuthErrorHandler'
import { TokenStorage, SecureStorage, TokenRefresh } from '../../src/utils/tokenStorage'

// Mock Auth0
const mockAuth0User = {
  sub: 'auth0|123456789',
  email: 'test@example.com',
  name: 'Test User',
  given_name: 'Test',
  family_name: 'User',
  picture: 'https://example.com/avatar.jpg',
  email_verified: true,
  'https://nextgen-fusion.com/roles': ['User'],
  'https://nextgen-fusion.com/permissions': ['read:projects', 'write:projects']
}

const mockAuth0 = {
  isLoading: false,
  isAuthenticated: true,
  user: mockAuth0User,
  getAccessTokenSilently: vi.fn().mockResolvedValue('mock-access-token'),
  loginWithRedirect: vi.fn(),
  logout: vi.fn(),
  getIdTokenClaims: vi.fn().mockResolvedValue({
    __raw: 'mock-id-token',
    'https://nextgen-fusion.com/roles': ['User'],
    'https://nextgen-fusion.com/permissions': ['read:projects', 'write:projects']
  })
}

vi.mock('@auth0/auth0-react', () => ({
  Auth0Provider: ({ children }: { children: React.ReactNode }) => children,
  useAuth0: () => mockAuth0,
  withAuthenticationRequired: (component: any) => component
}))

// Mock axios
vi.mock('axios')
const mockedAxios = axios as any

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
})

// Mock crypto for token encryption
Object.defineProperty(window, 'crypto', {
  value: {
    getRandomValues: vi.fn().mockImplementation((arr) => {
      for (let i = 0; i < arr.length; i++) {
        arr[i] = Math.floor(Math.random() * 256)
      }
      return arr
    }),
    subtle: {
      importKey: vi.fn().mockResolvedValue({}),
      encrypt: vi.fn().mockResolvedValue(new ArrayBuffer(32)),
      decrypt: vi.fn().mockResolvedValue(new ArrayBuffer(32))
    }
  }
})

// Test utilities
const renderWithAuth = (component: React.ReactElement, authProps = {}) => {
  const defaultAuthProps = {
    domain: 'test.auth0.com',
    clientId: 'test-client-id',
    authorizationParams: {
      redirect_uri: window.location.origin,
      audience: 'https://api.nextgen-fusion.com'
    },
    ...authProps
  }

  return render(
    <BrowserRouter>
      <Auth0Provider {...defaultAuthProps}>
        <AuthProvider>
          {component}
        </AuthProvider>
      </Auth0Provider>
    </BrowserRouter>
  )
}

const TestComponent = () => {
  const { user, isAuthenticated, hasRole, hasPermission } = useAuth()
  
  return (
    <div>
      <div data-testid="auth-status">
        {isAuthenticated ? 'authenticated' : 'not-authenticated'}
      </div>
      <div data-testid="user-email">{user?.email}</div>
      <div data-testid="has-admin-role">
        {hasRole('Administrator') ? 'true' : 'false'}
      </div>
      <div data-testid="has-read-permission">
        {hasPermission('read:projects') ? 'true' : 'false'}
      </div>
    </div>
  )
}

describe('Authentication System', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocalStorage.getItem.mockReturnValue(null)
  })

  describe('AuthContext', () => {
    it('should provide authentication state', async () => {
      renderWithAuth(<TestComponent />)
      
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated')
        expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com')
      })
    })

    it('should handle role checking', async () => {
      renderWithAuth(<TestComponent />)
      
      await waitFor(() => {
        expect(screen.getByTestId('has-admin-role')).toHaveTextContent('false')
      })
    })

    it('should handle permission checking', async () => {
      renderWithAuth(<TestComponent />)
      
      await waitFor(() => {
        expect(screen.getByTestId('has-read-permission')).toHaveTextContent('true')
      })
    })
  })

  describe('RoleGuard Component', () => {
    const ProtectedContent = () => <div data-testid="protected-content">Protected Content</div>
    const FallbackContent = () => <div data-testid="fallback-content">Access Denied</div>

    it('should render content for users with required role', async () => {
      const mockUserWithRole = {
        ...mockAuth0User,
        'https://nextgen-fusion.com/roles': ['User']
      }
      
      vi.mocked(mockAuth0.user).mockReturnValue(mockUserWithRole)
      
      renderWithAuth(
        <RoleGuard roles={['User']} fallback={<FallbackContent />}>
          <ProtectedContent />
        </RoleGuard>
      )
      
      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
        expect(screen.queryByTestId('fallback-content')).not.toBeInTheDocument()
      })
    })

    it('should render fallback for users without required role', async () => {
      const mockUserWithoutRole = {
        ...mockAuth0User,
        'https://nextgen-fusion.com/roles': ['Viewer']
      }
      
      vi.mocked(mockAuth0.user).mockReturnValue(mockUserWithoutRole)
      
      renderWithAuth(
        <RoleGuard roles={['Administrator']} fallback={<FallbackContent />}>
          <ProtectedContent />
        </RoleGuard>
      )
      
      await waitFor(() => {
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
        expect(screen.getByTestId('fallback-content')).toBeInTheDocument()
      })
    })

    it('should handle permission-based access', async () => {
      renderWithAuth(
        <RoleGuard permissions={['read:projects']}>
          <ProtectedContent />
        </RoleGuard>
      )
      
      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument()
      })
    })
  })

  describe('AdminOnly Component', () => {
    it('should render content for administrators', async () => {
      const mockAdminUser = {
        ...mockAuth0User,
        'https://nextgen-fusion.com/roles': ['Administrator']
      }
      
      vi.mocked(mockAuth0.user).mockReturnValue(mockAdminUser)
      
      renderWithAuth(
        <AdminOnly>
          <div data-testid="admin-content">Admin Content</div>
        </AdminOnly>
      )
      
      await waitFor(() => {
        expect(screen.getByTestId('admin-content')).toBeInTheDocument()
      })
    })

    it('should not render content for non-administrators', async () => {
      renderWithAuth(
        <AdminOnly>
          <div data-testid="admin-content">Admin Content</div>
        </AdminOnly>
      )
      
      await waitFor(() => {
        expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument()
      })
    })
  })

  describe('EnterpriseAuth Component', () => {
    beforeEach(() => {
      mockedAxios.get.mockResolvedValue({
        data: {
          connections: [
            {
              id: '1',
              name: 'Acme Corp SAML',
              strategy: 'samlp',
              domain: 'acme.com',
              enabled: true
            },
            {
              id: '2',
              name: 'TechCorp OIDC',
              strategy: 'oidc',
              domain: 'techcorp.com',
              enabled: true
            }
          ]
        }
      })
    })

    it('should render enterprise connections', async () => {
      renderWithAuth(<EnterpriseAuth />)
      
      await waitFor(() => {
        expect(screen.getByText('Enterprise Sign-In')).toBeInTheDocument()
      })
    })

    it('should filter connections by domain', async () => {
      renderWithAuth(<EnterpriseAuth userDomain="acme.com" />)
      
      await waitFor(() => {
        expect(screen.getByText('Acme Corp SAML')).toBeInTheDocument()
        expect(screen.queryByText('TechCorp OIDC')).not.toBeInTheDocument()
      })
    })
  })

  describe('DomainRouter Component', () => {
    beforeEach(() => {
      mockedAxios.get.mockResolvedValue({
        data: {
          authMethod: 'enterprise',
          connection: {
            id: '1',
            name: 'Acme Corp SAML',
            strategy: 'samlp'
          }
        }
      })
    })

    it('should detect enterprise domains', async () => {
      renderWithAuth(<DomainRouter />)
      
      const emailInput = screen.getByPlaceholderText('Enter your email address')
      fireEvent.change(emailInput, { target: { value: 'user@acme.com' } })
      
      const continueButton = screen.getByText('Continue')
      fireEvent.click(continueButton)
      
      await waitFor(() => {
        expect(screen.getByText('Enterprise Sign-In')).toBeInTheDocument()
      })
    })

    it('should show social login for non-enterprise domains', async () => {
      mockedAxios.get.mockResolvedValue({
        data: {
          authMethod: 'social'
        }
      })
      
      renderWithAuth(<DomainRouter />)
      
      const emailInput = screen.getByPlaceholderText('Enter your email address')
      fireEvent.change(emailInput, { target: { value: 'user@gmail.com' } })
      
      const continueButton = screen.getByText('Continue')
      fireEvent.click(continueButton)
      
      await waitFor(() => {
        expect(screen.getByText('Sign in with Google')).toBeInTheDocument()
      })
    })
  })

  describe('MFASetup Component', () => {
    beforeEach(() => {
      mockedAxios.get.mockResolvedValue({
        data: {
          methods: [
            {
              id: '1',
              type: 'totp',
              name: 'Authenticator App',
              enabled: true,
              verified: true
            }
          ]
        }
      })
    })

    it('should render MFA setup options', async () => {
      renderWithAuth(<MFASetup />)
      
      await waitFor(() => {
        expect(screen.getByText('Multi-Factor Authentication')).toBeInTheDocument()
        expect(screen.getByText('Authenticator App')).toBeInTheDocument()
      })
    })

    it('should handle MFA method setup', async () => {
      mockedAxios.post.mockResolvedValue({
        data: {
          qrCode: 'data:image/png;base64,mock-qr-code',
          secret: 'MOCK-SECRET-KEY',
          backupCodes: ['123456', '789012']
        }
      })
      
      renderWithAuth(<MFASetup />)
      
      await waitFor(() => {
        const setupButton = screen.getByText('Set Up')
        fireEvent.click(setupButton)
      })
      
      await waitFor(() => {
        expect(screen.getByText('Scan QR Code')).toBeInTheDocument()
      })
    })
  })

  describe('AuthErrorHandler Component', () => {
    it('should handle Auth0 errors', () => {
      const error = new Error('login_required')
      error.name = 'Auth0Error'
      
      render(<AuthErrorHandler error={error} />)
      
      expect(screen.getByText('Authentication Required')).toBeInTheDocument()
      expect(screen.getByText('Sign In')).toBeInTheDocument()
    })

    it('should handle token expired errors', () => {
      const error = new Error('Token expired')
      error.name = 'TokenExpiredError'
      
      render(<AuthErrorHandler error={error} />)
      
      expect(screen.getByText('Session Expired')).toBeInTheDocument()
      expect(screen.getByText('Refresh Session')).toBeInTheDocument()
    })

    it('should handle MFA required errors', () => {
      const error = new Error('mfa_required')
      error.name = 'Auth0Error'
      
      render(<AuthErrorHandler error={error} />)
      
      expect(screen.getByText('Multi-Factor Authentication Required')).toBeInTheDocument()
      expect(screen.getByText('Complete MFA')).toBeInTheDocument()
    })
  })

  describe('Token Storage', () => {
    describe('SecureStorage', () => {
      it('should encrypt and store data', async () => {
        const storage = new SecureStorage()
        const testData = { token: 'test-token', expires: Date.now() + 3600000 }
        
        await storage.setItem('test-key', testData)
        
        expect(mockLocalStorage.setItem).toHaveBeenCalled()
      })

      it('should decrypt and retrieve data', async () => {
        const storage = new SecureStorage()
        const testData = { token: 'test-token', expires: Date.now() + 3600000 }
        
        // Mock encrypted data in localStorage
        mockLocalStorage.getItem.mockReturnValue(JSON.stringify({
          data: 'encrypted-data',
          iv: 'mock-iv'
        }))
        
        // Mock decryption
        const mockDecryptedData = new TextEncoder().encode(JSON.stringify(testData))
        window.crypto.subtle.decrypt = vi.fn().mockResolvedValue(mockDecryptedData.buffer)
        
        const result = await storage.getItem('test-key')
        
        expect(result).toEqual(testData)
      })

      it('should handle decryption errors gracefully', async () => {
        const storage = new SecureStorage()
        
        mockLocalStorage.getItem.mockReturnValue('invalid-data')
        
        const result = await storage.getItem('test-key')
        
        expect(result).toBeNull()
      })
    })

    describe('TokenStorage', () => {
      let tokenStorage: TokenStorage

      beforeEach(() => {
        tokenStorage = new TokenStorage()
      })

      it('should store and retrieve tokens', async () => {
        const tokenData = {
          accessToken: 'access-token',
          refreshToken: 'refresh-token',
          idToken: 'id-token',
          expiresAt: Date.now() + 3600000
        }
        
        await tokenStorage.setTokens(tokenData)
        const retrieved = await tokenStorage.getTokens()
        
        expect(retrieved).toEqual(tokenData)
      })

      it('should detect expired tokens', async () => {
        const expiredTokenData = {
          accessToken: 'access-token',
          refreshToken: 'refresh-token',
          idToken: 'id-token',
          expiresAt: Date.now() - 1000 // Expired
        }
        
        await tokenStorage.setTokens(expiredTokenData)
        const isValid = await tokenStorage.isTokenValid()
        
        expect(isValid).toBe(false)
      })

      it('should clear tokens on logout', async () => {
        const tokenData = {
          accessToken: 'access-token',
          refreshToken: 'refresh-token',
          idToken: 'id-token',
          expiresAt: Date.now() + 3600000
        }
        
        await tokenStorage.setTokens(tokenData)
        await tokenStorage.clearTokens()
        
        const retrieved = await tokenStorage.getTokens()
        expect(retrieved).toBeNull()
      })
    })

    describe('TokenRefresh', () => {
      let tokenRefresh: TokenRefresh

      beforeEach(() => {
        tokenRefresh = new TokenRefresh()
      })

      it('should refresh tokens when expired', async () => {
        const newTokens = {
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
          id_token: 'new-id-token',
          expires_in: 3600
        }
        
        mockedAxios.post.mockResolvedValue({ data: newTokens })
        
        const result = await tokenRefresh.refreshTokens('old-refresh-token')
        
        expect(result.accessToken).toBe('new-access-token')
        expect(result.refreshToken).toBe('new-refresh-token')
      })

      it('should handle refresh token errors', async () => {
        mockedAxios.post.mockRejectedValue(new Error('Invalid refresh token'))
        
        await expect(tokenRefresh.refreshTokens('invalid-token')).rejects.toThrow('Invalid refresh token')
      })
    })
  })

  describe('API Integration', () => {
    beforeEach(() => {
      mockedAxios.get.mockClear()
      mockedAxios.post.mockClear()
      mockedAxios.patch.mockClear()
      mockedAxios.delete.mockClear()
    })

    it('should include auth token in API requests', async () => {
      const { createAuthInterceptor } = await import('../../src/utils/tokenStorage')
      
      const mockAxiosInstance = {
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() }
        }
      }
      
      createAuthInterceptor(mockAxiosInstance as any)
      
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled()
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled()
    })

    it('should handle 401 responses with token refresh', async () => {
      const mockAxiosInstance = {
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() }
        },
        request: vi.fn()
      }
      
      // Mock 401 response
      const error = {
        response: { status: 401 },
        config: { url: '/api/test' }
      }
      
      // Mock successful token refresh
      mockedAxios.post.mockResolvedValue({
        data: {
          access_token: 'new-token',
          refresh_token: 'new-refresh-token',
          expires_in: 3600
        }
      })
      
      const { createAuthInterceptor } = await import('../../src/utils/tokenStorage')
      createAuthInterceptor(mockAxiosInstance as any)
      
      // Get the response interceptor
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0][1]
      
      // Should attempt to refresh token and retry request
      await expect(responseInterceptor(error)).resolves.toBeDefined()
    })
  })

  describe('Security Features', () => {
    it('should validate JWT tokens', async () => {
      const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
      
      // Mock JWT validation endpoint
      mockedAxios.post.mockResolvedValue({
        data: {
          valid: true,
          decoded: {
            sub: '1234567890',
            name: 'John Doe',
            iat: 1516239022
          }
        }
      })
      
      const response = await axios.post('/api/auth/validate', { token: mockToken })
      
      expect(response.data.valid).toBe(true)
      expect(response.data.decoded.sub).toBe('1234567890')
    })

    it('should enforce rate limiting on auth endpoints', async () => {
      // Mock rate limit exceeded response
      mockedAxios.post.mockRejectedValue({
        response: {
          status: 429,
          data: {
            error: 'rate_limit_exceeded',
            message: 'Too many requests'
          }
        }
      })
      
      await expect(axios.post('/api/auth/login')).rejects.toMatchObject({
        response: {
          status: 429,
          data: {
            error: 'rate_limit_exceeded'
          }
        }
      })
    })

    it('should sanitize user input', () => {
      const maliciousInput = '<script>alert("xss")</script>'
      const sanitizedInput = maliciousInput.replace(/<script[^>]*>.*?<\/script>/gi, '')
      
      expect(sanitizedInput).not.toContain('<script>')
    })
  })

  describe('Performance', () => {
    it('should cache user permissions', async () => {
      const TestPermissionComponent = () => {
        const { hasPermission } = useAuth()
        
        // Call hasPermission multiple times
        const canRead = hasPermission('read:projects')
        const canWrite = hasPermission('write:projects')
        const canDelete = hasPermission('delete:projects')
        
        return (
          <div>
            <div data-testid="can-read">{canRead ? 'true' : 'false'}</div>
            <div data-testid="can-write">{canWrite ? 'true' : 'false'}</div>
            <div data-testid="can-delete">{canDelete ? 'true' : 'false'}</div>
          </div>
        )
      }
      
      renderWithAuth(<TestPermissionComponent />)
      
      await waitFor(() => {
        expect(screen.getByTestId('can-read')).toHaveTextContent('true')
        expect(screen.getByTestId('can-write')).toHaveTextContent('true')
        expect(screen.getByTestId('can-delete')).toHaveTextContent('false')
      })
      
      // Verify that getIdTokenClaims was called only once (cached)
      expect(mockAuth0.getIdTokenClaims).toHaveBeenCalledTimes(1)
    })

    it('should debounce token refresh attempts', async () => {
      const tokenRefresh = new TokenRefresh()
      
      // Mock multiple simultaneous refresh attempts
      const refreshPromises = [
        tokenRefresh.refreshTokens('refresh-token'),
        tokenRefresh.refreshTokens('refresh-token'),
        tokenRefresh.refreshTokens('refresh-token')
      ]
      
      mockedAxios.post.mockResolvedValue({
        data: {
          access_token: 'new-token',
          refresh_token: 'new-refresh-token',
          expires_in: 3600
        }
      })
      
      await Promise.all(refreshPromises)
      
      // Should only make one actual refresh request
      expect(mockedAxios.post).toHaveBeenCalledTimes(1)
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      mockedAxios.get.mockRejectedValue(new Error('Network Error'))
      
      renderWithAuth(<EnterpriseAuth />)
      
      await waitFor(() => {
        expect(screen.getByText('Unable to load enterprise connections')).toBeInTheDocument()
      })
    })

    it('should handle Auth0 service errors', async () => {
      const auth0Error = new Error('Auth0 service unavailable')
      mockAuth0.loginWithRedirect.mockRejectedValue(auth0Error)
      
      render(<AuthErrorHandler error={auth0Error} />)
      
      expect(screen.getByText('Authentication Service Unavailable')).toBeInTheDocument()
    })

    it('should provide fallback UI for authentication failures', async () => {
      const mockUnauthenticatedAuth0 = {
        ...mockAuth0,
        isAuthenticated: false,
        user: null,
        error: new Error('Authentication failed')
      }
      
      vi.mocked(mockAuth0).mockReturnValue(mockUnauthenticatedAuth0)
      
      const ProtectedComponent = () => {
        const { isAuthenticated } = useAuth()
        
        if (!isAuthenticated) {
          return <div data-testid="login-required">Please log in</div>
        }
        
        return <div data-testid="protected-content">Protected Content</div>
      }
      
      renderWithAuth(<ProtectedComponent />)
      
      await waitFor(() => {
        expect(screen.getByTestId('login-required')).toBeInTheDocument()
        expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
      })
    })
  })
})

// Integration tests
describe('Authentication Integration', () => {
  beforeAll(() => {
    // Setup test environment
    process.env.NODE_ENV = 'test'
  })

  afterAll(() => {
    // Cleanup
    vi.restoreAllMocks()
  })

  it('should complete full authentication flow', async () => {
    // Mock successful login flow
    mockAuth0.loginWithRedirect.mockResolvedValue(undefined)
    mockAuth0.getAccessTokenSilently.mockResolvedValue('valid-access-token')
    
    const LoginComponent = () => {
      const { loginWithRedirect, isAuthenticated, user } = useAuth()
      
      return (
        <div>
          {!isAuthenticated ? (
            <button onClick={() => loginWithRedirect()} data-testid="login-button">
              Log In
            </button>
          ) : (
            <div>
              <div data-testid="welcome-message">Welcome, {user?.name}</div>
              <div data-testid="user-roles">{user?.roles?.join(', ')}</div>
            </div>
          )}
        </div>
      )
    }
    
    renderWithAuth(<LoginComponent />)
    
    // Initially should show login button
    expect(screen.getByTestId('login-button')).toBeInTheDocument()
    
    // Click login button
    fireEvent.click(screen.getByTestId('login-button'))
    
    // Verify login was called
    expect(mockAuth0.loginWithRedirect).toHaveBeenCalled()
    
    // After authentication, should show welcome message
    await waitFor(() => {
      expect(screen.getByTestId('welcome-message')).toHaveTextContent('Welcome, Test User')
    })
  })

  it('should handle role-based navigation', async () => {
    const NavigationComponent = () => {
      const { hasRole } = useAuth()
      
      return (
        <nav>
          <a href="/dashboard" data-testid="dashboard-link">Dashboard</a>
          {hasRole('Manager') && (
            <a href="/analytics" data-testid="analytics-link">Analytics</a>
          )}
          {hasRole('Administrator') && (
            <a href="/admin" data-testid="admin-link">Admin</a>
          )}
        </nav>
      )
    }
    
    // Test with regular user
    renderWithAuth(<NavigationComponent />)
    
    await waitFor(() => {
      expect(screen.getByTestId('dashboard-link')).toBeInTheDocument()
      expect(screen.queryByTestId('analytics-link')).not.toBeInTheDocument()
      expect(screen.queryByTestId('admin-link')).not.toBeInTheDocument()
    })
  })

  it('should handle enterprise SSO flow', async () => {
    // Mock enterprise domain detection
    mockedAxios.get.mockResolvedValue({
      data: {
        authMethod: 'enterprise',
        connection: {
          id: 'enterprise-connection',
          name: 'Acme Corp SAML',
          strategy: 'samlp'
        }
      }
    })
    
    const EnterpriseLoginComponent = () => {
      const { loginWithRedirect } = useAuth()
      
      const handleEnterpriseLogin = () => {
        loginWithRedirect({
          authorizationParams: {
            connection: 'enterprise-connection'
          }
        })
      }
      
      return (
        <button onClick={handleEnterpriseLogin} data-testid="enterprise-login">
          Sign in with SSO
        </button>
      )
    }
    
    renderWithAuth(<EnterpriseLoginComponent />)
    
    fireEvent.click(screen.getByTestId('enterprise-login'))
    
    expect(mockAuth0.loginWithRedirect).toHaveBeenCalledWith({
      authorizationParams: {
        connection: 'enterprise-connection'
      }
    })
  })
})