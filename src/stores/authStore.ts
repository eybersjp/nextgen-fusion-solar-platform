import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Updated User interface to support both legacy and Auth0 users
export interface User {
  id: string;
  email: string;
  name: string; // Unified name field
  full_name?: string; // Legacy field for backward compatibility
  picture?: string; // Auth0 profile picture
  avatar_url?: string; // Legacy avatar field
  roles: string[]; // Auth0 roles array
  permissions: string[]; // Auth0 permissions array
  role?: string; // Legacy single role for backward compatibility
  emailVerified: boolean; // Auth0 email verification status
  created_at?: string; // Legacy field
  updated_at?: string; // Legacy field
  // Auth0 specific fields
  sub?: string; // Auth0 subject identifier
  auth_provider?: 'auth0' | 'legacy'; // Track authentication provider
}

export interface AuthState {
  // State
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  authProvider: 'auth0' | 'legacy' | null; // Track which auth system is being used

  // Actions
  login: (email: string, password: string) => Promise<void>; // Legacy login
  register: (email: string, password: string, fullName: string) => Promise<void>; // Legacy register
  logout: () => void;
  refreshToken: () => Promise<void>; // Legacy token refresh
  clearError: () => void;
  setUser: (user: User) => void;
  setToken: (token: string) => void;
  setAuthProvider: (provider: 'auth0' | 'legacy') => void;
  // Auth0 specific actions
  setAuth0User: (user: any) => void; // Transform Auth0 user to our User interface
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      authProvider: null,

      // Actions
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Login failed');
          }

          const data = await response.json();
          
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Login failed',
          });
          throw error;
        }
      },

      register: async (email: string, password: string, fullName: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
              email, 
              password, 
              full_name: fullName 
            }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Registration failed');
          }

          const data = await response.json();
          
          set({
            user: data.user,
            token: data.access_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Registration failed',
          });
          throw error;
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshToken: async () => {
        const { token } = get();
        if (!token) return;

        try {
          const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          });

          if (!response.ok) {
            throw new Error('Token refresh failed');
          }

          const data = await response.json();
          
          set({
            token: data.access_token,
            user: data.user,
          });
        } catch (error) {
          // If refresh fails, logout the user
          get().logout();
          throw error;
        }
      },

      clearError: () => set({ error: null }),
      
      setUser: (user: User) => set({ user }),
      
      setToken: (token: string) => set({ token, isAuthenticated: true }),
      
      setAuthProvider: (provider: 'auth0' | 'legacy') => set({ authProvider: provider }),
      
      // Transform Auth0 user to our User interface
      setAuth0User: (auth0User: any) => {
        if (!auth0User) {
          set({ user: null, authProvider: null });
          return;
        }
        
        const transformedUser: User = {
          id: auth0User.sub || '',
          email: auth0User.email || '',
          name: auth0User.name || auth0User.email || '',
          picture: auth0User.picture,
          roles: auth0User['https://nextgen-fusion.com/roles'] || [],
          permissions: auth0User['https://nextgen-fusion.com/permissions'] || [],
          emailVerified: auth0User.email_verified || false,
          sub: auth0User.sub,
          auth_provider: 'auth0'
        };
        
        set({ 
          user: transformedUser, 
          authProvider: 'auth0',
          isAuthenticated: true 
        });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
        authProvider: state.authProvider,
      }),
    }
  )
);