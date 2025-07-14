import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, AuthState, LoginResponse } from '../types';
import { ApiClient } from '../lib/api';

interface AuthContextType extends AuthState {
  login: (token: string) => Promise<void>;
  logout: () => void;
  hasRole: (role: User['role']) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  const api = new ApiClient();

  const login = async (token: string) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      // Send token to backend for verification and session creation
      // Backend should set HttpOnly cookie and return user data
      const response = await api.post<LoginResponse>('/auth/login', { token });
      
      if (response.error) {
        throw new Error(response.error);
      }

      // Don't store token in localStorage - backend sets HttpOnly cookie
      setState({
        user: response.data.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Login failed',
      });
    }
  };

  const logout = async () => {
    try {
      // Call backend to clear session cookie
      await api.post('/auth/logout', {});
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  };

  const hasRole = (role: User['role']): boolean => {
    if (!state.user) return false;
    return state.user.role === role;
  };

  const refreshUser = async () => {
    try {
      // Check if we have a valid session cookie
      const response = await api.get<LoginResponse>('/auth/me');
      if (response.error) {
        throw new Error(response.error);
      }

      setState({
        user: response.data.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to refresh user data',
      });
    }
  };

  // Check for existing session on mount
  useEffect(() => {
    // Always try to refresh user data (will use session cookie if available)
    refreshUser();
  }, []);

  const value = {
    ...state,
    login,
    logout,
    hasRole,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 