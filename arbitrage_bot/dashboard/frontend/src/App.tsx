import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@mui/material/styles';
import { createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import type { RouteProps } from 'react-router';
import { BrowserRouter } from 'react-router-dom/dist/index.js';
import { Routes } from 'react-router-dom/dist/index.js';
import { Route } from 'react-router-dom/dist/index.js';
import { Navigate } from 'react-router-dom/dist/index.js';
import { Outlet } from 'react-router-dom/dist/index.js';

import Layout from './components/Layout';
import Login from './pages/Login';
import DashboardContent from './components/DashboardContent';
import UserManagement from './pages/UserManagement';
import ProtectedRoute from './components/ProtectedRoute';
import { WebSocketProvider } from './providers/WebSocketProvider';
import { AuthProvider } from './providers/AuthProvider';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 1000, // Refetch every second
      staleTime: 500,
    },
  },
});

// Create dark theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00ff9f',
    },
    secondary: {
      main: '#7b1fa2',
    },
    background: {
      default: '#0a1929',
      paper: '#132f4c',
    },
  },
  typography: {
    fontFamily: '"Roboto Mono", monospace',
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(19, 47, 76, 0.9)',
          backdropFilter: 'blur(4px)',
        },
      },
    },
  },
});

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <AuthProvider>
            <WebSocketProvider>
              <Routes>
                {/* Public route */}
                <Route
                  path="/login"
                  element={
                    <ProtectedRoute requireAuth={false}>
                      <Login />
                    </ProtectedRoute>
                  }
                />

                {/* Protected routes */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<DashboardContent />} />
                  <Route path="users" element={<UserManagement />} />
                  <Route path="opportunities" element={<div>Opportunities</div>} />
                  <Route path="performance" element={<div>Performance</div>} />
                  <Route path="settings" element={<div>Settings</div>} />
                </Route>

                {/* Catch all route */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </WebSocketProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;