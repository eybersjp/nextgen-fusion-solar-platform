import React from 'react';
import { Auth0Provider as Auth0ProviderBase } from '@auth0/auth0-react';
import { useNavigate } from 'react-router-dom';

interface Auth0ProviderProps {
  children: React.ReactNode;
}

const Auth0Provider: React.FC<Auth0ProviderProps> = ({ children }) => {
  const navigate = useNavigate();

  const domain = import.meta.env.VITE_AUTH0_DOMAIN!;
  const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID!;
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE!;
  const redirectUri = import.meta.env.VITE_AUTH0_REDIRECT_URI || window.location.origin;
  const isDevelopment = import.meta.env.VITE_ENV === 'development';

  const onRedirectCallback = (appState?: any) => {
    navigate(appState?.returnTo || window.location.pathname);
  };

  // Check for proper Auth0 configuration
  const isValidAuth0Config = domain && 
    clientId && 
    domain !== 'your-auth0-domain' && 
    clientId !== 'your-auth0-client-id' &&
    !domain.includes('demo') &&
    domain.includes('.auth0.com');

  if (!domain || !clientId || !isValidAuth0Config) {
    console.warn('Auth0 configuration incomplete or using placeholder values.');
    
    if (isDevelopment) {
      // In development, show a mock auth state instead of crashing
      return (
        <div className="flex items-center justify-center min-h-screen bg-gray-50">
          <div className="text-center p-8 bg-white rounded-lg shadow-md max-w-md">
            <div className="mb-4">
              <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">Development Mode</h2>
              <p className="text-gray-600 mb-4">Auth0 not configured. Using development mode.</p>
              <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded">
                <p className="font-medium mb-1">To set up Auth0:</p>
                <ol className="text-left list-decimal list-inside space-y-1">
                  <li>Create an Auth0 tenant</li>
                  <li>Update VITE_AUTH0_DOMAIN in .env</li>
                  <li>Update VITE_AUTH0_CLIENT_ID in .env</li>
                  <li>Restart the development server</li>
                </ol>
              </div>
            </div>
            <button 
              onClick={() => window.location.reload()} 
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }
    
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">Authentication Configuration Error</h2>
          <p className="text-gray-600">Please configure Auth0 environment variables.</p>
        </div>
      </div>
    );
  }

  return (
    <Auth0ProviderBase
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: redirectUri,
        audience: audience,
        scope: 'openid profile email read:users read:projects write:projects admin:system'
      }}
      onRedirectCallback={onRedirectCallback}
      useRefreshTokens={true}
      cacheLocation="localstorage"
    >
      {children}
    </Auth0ProviderBase>
  );
};

export default Auth0Provider;