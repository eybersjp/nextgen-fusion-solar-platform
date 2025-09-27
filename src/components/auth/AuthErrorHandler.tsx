import React from 'react'
import { AlertCircle, RefreshCw, Shield, Wifi, Clock, Key } from 'lucide-react'
import { useAuth } from '@auth0/auth0-react'

interface AuthError {
  error: string
  error_description?: string
  state?: string
}

interface AuthErrorHandlerProps {
  error?: AuthError | Error | null
  onRetry?: () => void
  onDismiss?: () => void
  className?: string
}

const AuthErrorHandler: React.FC<AuthErrorHandlerProps> = ({ 
  error, 
  onRetry, 
  onDismiss, 
  className = '' 
}) => {
  const { loginWithRedirect } = useAuth()

  if (!error) return null

  const getErrorInfo = (error: AuthError | Error) => {
    // Handle Auth0 specific errors
    if ('error' in error) {
      const auth0Error = error as AuthError
      
      switch (auth0Error.error) {
        case 'access_denied':
          return {
            title: 'Access Denied',
            message: 'You do not have permission to access this application. Please contact your administrator.',
            icon: Shield,
            color: 'red',
            actions: [
              { label: 'Contact Support', action: () => window.open('mailto:support@nextgenfusion.com') },
              { label: 'Try Again', action: () => loginWithRedirect() }
            ]
          }
          
        case 'unauthorized':
          return {
            title: 'Authentication Required',
            message: 'Please sign in to access this resource.',
            icon: Key,
            color: 'blue',
            actions: [
              { label: 'Sign In', action: () => loginWithRedirect() }
            ]
          }
          
        case 'login_required':
          return {
            title: 'Login Required',
            message: 'Your session has expired. Please sign in again.',
            icon: Clock,
            color: 'yellow',
            actions: [
              { label: 'Sign In', action: () => loginWithRedirect() }
            ]
          }
          
        case 'consent_required':
          return {
            title: 'Consent Required',
            message: 'Additional permissions are required to access this resource.',
            icon: Shield,
            color: 'blue',
            actions: [
              { label: 'Grant Permissions', action: () => loginWithRedirect() }
            ]
          }
          
        case 'interaction_required':
          return {
            title: 'Interaction Required',
            message: 'Additional authentication steps are required.',
            icon: Shield,
            color: 'blue',
            actions: [
              { label: 'Continue', action: () => loginWithRedirect() }
            ]
          }
          
        case 'mfa_required':
          return {
            title: 'Multi-Factor Authentication Required',
            message: 'Please complete multi-factor authentication to continue.',
            icon: Shield,
            color: 'blue',
            actions: [
              { label: 'Complete MFA', action: () => loginWithRedirect() }
            ]
          }
          
        case 'invalid_request':
          return {
            title: 'Invalid Request',
            message: 'The authentication request was invalid. Please try again.',
            icon: AlertCircle,
            color: 'red',
            actions: [
              { label: 'Try Again', action: onRetry || (() => window.location.reload()) }
            ]
          }
          
        case 'server_error':
          return {
            title: 'Server Error',
            message: 'A server error occurred during authentication. Please try again later.',
            icon: AlertCircle,
            color: 'red',
            actions: [
              { label: 'Retry', action: onRetry || (() => window.location.reload()) },
              { label: 'Contact Support', action: () => window.open('mailto:support@nextgenfusion.com') }
            ]
          }
          
        case 'temporarily_unavailable':
          return {
            title: 'Service Temporarily Unavailable',
            message: 'The authentication service is temporarily unavailable. Please try again in a few minutes.',
            icon: Wifi,
            color: 'yellow',
            actions: [
              { label: 'Retry', action: onRetry || (() => window.location.reload()) }
            ]
          }
          
        case 'invalid_scope':
          return {
            title: 'Invalid Permissions',
            message: 'The requested permissions are invalid or not available.',
            icon: Shield,
            color: 'red',
            actions: [
              { label: 'Contact Support', action: () => window.open('mailto:support@nextgenfusion.com') }
            ]
          }
          
        case 'invalid_client':
          return {
            title: 'Configuration Error',
            message: 'There is a configuration issue with the application. Please contact support.',
            icon: AlertCircle,
            color: 'red',
            actions: [
              { label: 'Contact Support', action: () => window.open('mailto:support@nextgenfusion.com') }
            ]
          }
          
        default:
          return {
            title: 'Authentication Error',
            message: auth0Error.error_description || auth0Error.error || 'An unknown authentication error occurred.',
            icon: AlertCircle,
            color: 'red',
            actions: [
              { label: 'Try Again', action: onRetry || (() => loginWithRedirect()) },
              { label: 'Contact Support', action: () => window.open('mailto:support@nextgenfusion.com') }
            ]
          }
      }
    }
    
    // Handle generic JavaScript errors
    const genericError = error as Error
    
    // Network errors
    if (genericError.message.includes('fetch') || genericError.message.includes('network')) {
      return {
        title: 'Network Error',
        message: 'Unable to connect to the authentication service. Please check your internet connection.',
        icon: Wifi,
        color: 'red',
        actions: [
          { label: 'Retry', action: onRetry || (() => window.location.reload()) }
        ]
      }
    }
    
    // Timeout errors
    if (genericError.message.includes('timeout')) {
      return {
        title: 'Request Timeout',
        message: 'The authentication request timed out. Please try again.',
        icon: Clock,
        color: 'yellow',
        actions: [
          { label: 'Retry', action: onRetry || (() => window.location.reload()) }
        ]
      }
    }
    
    // Default error
    return {
      title: 'Authentication Error',
      message: genericError.message || 'An unexpected error occurred during authentication.',
      icon: AlertCircle,
      color: 'red',
      actions: [
        { label: 'Try Again', action: onRetry || (() => window.location.reload()) },
        { label: 'Contact Support', action: () => window.open('mailto:support@nextgenfusion.com') }
      ]
    }
  }

  const errorInfo = getErrorInfo(error)
  const IconComponent = errorInfo.icon

  const colorClasses = {
    red: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: 'text-red-600',
      title: 'text-red-900',
      message: 'text-red-800',
      button: 'bg-red-600 hover:bg-red-700 text-white',
      buttonSecondary: 'border-red-300 text-red-700 hover:bg-red-50'
    },
    yellow: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      icon: 'text-yellow-600',
      title: 'text-yellow-900',
      message: 'text-yellow-800',
      button: 'bg-yellow-600 hover:bg-yellow-700 text-white',
      buttonSecondary: 'border-yellow-300 text-yellow-700 hover:bg-yellow-50'
    },
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-600',
      title: 'text-blue-900',
      message: 'text-blue-800',
      button: 'bg-blue-600 hover:bg-blue-700 text-white',
      buttonSecondary: 'border-blue-300 text-blue-700 hover:bg-blue-50'
    }
  }

  const colors = colorClasses[errorInfo.color as keyof typeof colorClasses]

  return (
    <div className={`rounded-lg p-6 ${colors.bg} ${colors.border} border ${className}`}>
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          <IconComponent className={`h-6 w-6 ${colors.icon}`} />
        </div>
        
        <div className="flex-1">
          <h3 className={`text-lg font-semibold ${colors.title} mb-2`}>
            {errorInfo.title}
          </h3>
          
          <p className={`text-sm ${colors.message} mb-4`}>
            {errorInfo.message}
          </p>
          
          {errorInfo.actions.length > 0 && (
            <div className="flex flex-wrap gap-3">
              {errorInfo.actions.map((action, index) => (
                <button
                  key={index}
                  onClick={action.action}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    index === 0 
                      ? colors.button
                      : `border ${colors.buttonSecondary}`
                  }`}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
          
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="mt-3 text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
      
      {/* Technical details for debugging (only in development) */}
      {import.meta.env.MODE === 'development' && (
        <details className="mt-4 text-xs">
          <summary className={`cursor-pointer ${colors.message} font-medium`}>
            Technical Details
          </summary>
          <pre className={`mt-2 p-3 bg-gray-100 rounded text-gray-700 overflow-auto`}>
            {JSON.stringify(error, null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}

// Hook for handling authentication errors globally
export const useAuthErrorHandler = () => {
  const [authError, setAuthError] = React.useState<AuthError | Error | null>(null)
  
  const handleAuthError = React.useCallback((error: AuthError | Error) => {
    console.error('Authentication error:', error)
    setAuthError(error)
  }, [])
  
  const clearAuthError = React.useCallback(() => {
    setAuthError(null)
  }, [])
  
  const retryAuth = React.useCallback(() => {
    setAuthError(null)
    // Additional retry logic can be added here
  }, [])
  
  return {
    authError,
    handleAuthError,
    clearAuthError,
    retryAuth
  }
}

// Error boundary for authentication errors
export class AuthErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ComponentType<{ error: Error }> },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ComponentType<{ error: Error }> }) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Auth error boundary caught an error:', error, errorInfo)
  }
  
  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback
        return <FallbackComponent error={this.state.error} />
      }
      
      return (
        <AuthErrorHandler 
          error={this.state.error}
          onRetry={() => this.setState({ hasError: false, error: null })}
        />
      )
    }
    
    return this.props.children
  }
}

export default AuthErrorHandler