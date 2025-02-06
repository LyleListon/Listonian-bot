import React from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { SnackbarProvider } from 'notistack';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';

import Layout from './components/Layout';
import Login from './pages/Login';
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
        <SnackbarProvider
          maxSnack={3}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'right',
          }}
        >
          <Router>
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
                  />

                  {/* Catch all route */}
                  <Route
                    path="*"
                    element={<Navigate to="/" replace />}
                  />
                </Routes>
              </WebSocketProvider>
            </AuthProvider>
          </Router>
        </SnackbarProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;