import { useAuth0 } from '@auth0/auth0-react';
import { useCallback, useEffect, useMemo } from 'react';
import { useAuthStore } from '../stores/authStore';

export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  roles: string[];
  permissions: string[];
  emailVerified: boolean;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  token: string | null;
}

export interface AuthActions {
  login: (options?: { returnTo?: string }) => Promise<void>;
  logout: (options?: { returnTo?: string }) => void;
  getAccessToken: () => Promise<string | undefined>;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  clearError: () => void;
}

export const useAuth = (): AuthState & AuthActions => {
  const {
    user: auth0User,
    isAuthenticated: auth0IsAuthenticated,
    isLoading: auth0IsLoading,
    error: auth0Error,
    loginWithRedirect,
    logout: auth0Logout,
    getAccessTokenSilently
  } = useAuth0();

  const {
    user: storeUser,
    token,
    isLoading: storeIsLoading,
    error: storeError,
    setUser,
    setToken,
    clearError: storeClearError,
    logout: storeLogout
  } = useAuthStore();

  // Transform Auth0 user to our User interface
  const transformedUser = useMemo((): User | null => {
    if (!auth0User || !auth0IsAuthenticated) return null;

    return {
      id: auth0User.sub || '',
      email: auth0User.email || '',
      name: auth0User.name || auth0User.email || '',
      picture: auth0User.picture,
      roles: auth0User['https://nextgen-fusion.com/roles'] || [],
      permissions: auth0User['https://nextgen-fusion.com/permissions'] || [],
      emailVerified: auth0User.email_verified || false
    };
  }, [auth0User, auth0IsAuthenticated]);

  // Update store when Auth0 state changes
  useEffect(() => {
    if (transformedUser) {
      setUser(transformedUser);
    }
  }, [transformedUser, setUser]);

  // Get and store access token
  useEffect(() => {
    const getToken = async () => {
      if (auth0IsAuthenticated && !auth0IsLoading) {
        try {
          const accessToken = await getAccessTokenSilently();
          setToken(accessToken);
        } catch (error) {
          console.error('Failed to get access token:', error);
        }
      }
    };

    getToken();
  }, [auth0IsAuthenticated, auth0IsLoading, getAccessTokenSilently, setToken]);

  const login = useCallback(async (options?: { returnTo?: string }) => {
    await loginWithRedirect({
      appState: {
        returnTo: options?.returnTo || window.location.pathname
      }
    });
  }, [loginWithRedirect]);

  const logout = useCallback((options?: { returnTo?: string }) => {
    storeLogout();
    auth0Logout({
      logoutParams: {
        returnTo: options?.returnTo || window.location.origin
      }
    });
  }, [auth0Logout, storeLogout]);

  const getAccessToken = useCallback(async (): Promise<string | undefined> => {
    if (!auth0IsAuthenticated) return undefined;
    
    try {
      return await getAccessTokenSilently();
    } catch (error) {
      console.error('Failed to get access token:', error);
      return undefined;
    }
  }, [auth0IsAuthenticated, getAccessTokenSilently]);

  const hasPermission = useCallback((permission: string): boolean => {
    return transformedUser?.permissions.includes(permission) || false;
  }, [transformedUser]);

  const hasRole = useCallback((role: string): boolean => {
    return transformedUser?.roles.includes(role) || false;
  }, [transformedUser]);

  const clearError = useCallback(() => {
    storeClearError();
  }, [storeClearError]);

  return {
    user: transformedUser,
    isAuthenticated: auth0IsAuthenticated,
    isLoading: auth0IsLoading || storeIsLoading,
    error: auth0Error?.message || storeError,
    token,
    login,
    logout,
    getAccessToken,
    hasPermission,
    hasRole,
    clearError
  };
};