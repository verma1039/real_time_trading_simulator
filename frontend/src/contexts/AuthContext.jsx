import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { client, setAccessToken } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const refreshSession = useCallback(async () => {
    setIsLoading(true);
    try {
      // Attempt to refresh the session via the HTTP-only cookie
      const { data } = await client.post('/auth/refresh');
      setAccessToken(data.access_token);
      
      // Fetch the current user's profile
      const userRes = await client.get('/auth/me');
      setUser(userRes.data);
      setIsAuthenticated(true);
    } catch (err) {
      // If refresh fails (e.g., no cookie or expired), clear session state
      setAccessToken(null);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize the auth state on first mount
  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  const login = async (email, password) => {
    try {
      const { data } = await client.post('/auth/login', { email, password });
      setAccessToken(data.access_token);
      
      const userRes = await client.get('/auth/me');
      setUser(userRes.data);
      setIsAuthenticated(true);
      return true;
    } catch (err) {
      throw err;
    }
  };

  const logout = async () => {
    try {
      await client.post('/auth/logout');
    } catch (err) {
      console.error('Logout API failed, forcing local cleanup', err);
    } finally {
      setAccessToken(null);
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refreshSession
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
