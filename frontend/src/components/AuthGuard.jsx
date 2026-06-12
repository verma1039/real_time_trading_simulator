import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AuthGuard = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="d-flex items-center justify-center h-screen bg-base">
        <div className="d-flex flex-col items-center gap-4">
          <div className="skeleton skeleton-circle" style={{ width: '48px', height: '48px' }}></div>
          <span className="text-sm font-medium text-muted">Restoring session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export default AuthGuard;
