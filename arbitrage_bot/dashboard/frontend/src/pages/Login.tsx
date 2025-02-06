import React from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Typography,
  useTheme,
  Divider,
} from '@mui/material';
import {
  GitHub as GitHubIcon,
  Google as GoogleIcon,
} from '@mui/icons-material';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../providers/AuthProvider';

const Login: React.FC = () => {
  const theme = useTheme();
  const { user, loading, login } = useAuth();

  // Redirect if already authenticated
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
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        background: `linear-gradient(45deg, ${theme.palette.primary.dark} 0%, ${theme.palette.secondary.dark} 100%)`,
      }}
    >
      <Container maxWidth="sm">
        <Card
          sx={{
            backdropFilter: 'blur(4px)',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            boxShadow: theme.shadows[20],
          }}
        >
          <CardContent>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Typography variant="h4" component="h1" gutterBottom>
                Arbitrage Dashboard
              </Typography>
              <Typography variant="subtitle1" color="textSecondary">
                Sign in to access the dashboard
              </Typography>
            </Box>

            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
                maxWidth: 300,
                mx: 'auto',
              }}
            >
              <Button
                variant="contained"
                size="large"
                startIcon={<GoogleIcon />}
                onClick={() => login('google')}
                sx={{
                  backgroundColor: '#4285F4',
                  color: 'white',
                  '&:hover': {
                    backgroundColor: '#3367D6',
                  },
                }}
              >
                Sign in with Google
              </Button>

              <Button
                variant="contained"
                size="large"
                startIcon={<GitHubIcon />}
                onClick={() => login('github')}
                sx={{
                  backgroundColor: '#24292E',
                  color: 'white',
                  '&:hover': {
                    backgroundColor: '#1B1F23',
                  },
                }}
              >
                Sign in with GitHub
              </Button>

              <Box sx={{ my: 2 }}>
                <Divider>
                  <Typography
                    variant="body2"
                    color="textSecondary"
                    sx={{ px: 1 }}
                  >
                    Secure Authentication
                  </Typography>
                </Divider>
              </Box>

              <Typography
                variant="body2"
                color="textSecondary"
                align="center"
                sx={{ mt: 2 }}
              >
                By signing in, you agree to our Terms of Service and Privacy Policy
              </Typography>
            </Box>
          </CardContent>
        </Card>

        {/* Security badges */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            gap: 2,
            mt: 3,
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: 'rgba(255, 255, 255, 0.7)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            🔒 Secure OAuth2
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: 'rgba(255, 255, 255, 0.7)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            🛡️ End-to-end encryption
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default Login;