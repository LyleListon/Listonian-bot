import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useAuth } from '../providers/AuthProvider';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = true,
}) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  // Handle authentication requirements
  if (requireAuth) {
    // Redirect to login if not authenticated
    if (!user) {
      return <Navigate to="/login" state={{ from: location }} replace />;
    }
  } else {
    // Redirect to dashboard if already authenticated (for login page)
    if (user) {
      return <Navigate to="/" replace />;
    }
  }

  // Render protected content
  return <>{children}</>;
};

export default ProtectedRoute;