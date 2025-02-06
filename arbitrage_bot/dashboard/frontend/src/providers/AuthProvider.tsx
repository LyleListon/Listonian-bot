import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';

interface User {
  id: string;
  email: string;
  name?: string;
  picture?: string;
  provider: 'google' | 'github';
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (provider: 'google' | 'github') => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (!token) {
          setLoading(false);
          return;
        }

        const response = await fetch('/api/auth/user', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          localStorage.removeItem('auth_token');
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        setError('Failed to verify authentication');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Handle OAuth popup window
  const handleOAuthPopup = (provider: string) => {
    const width = 500;
    const height = 600;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      `/api/auth/login/${provider}`,
      `Login with ${provider}`,
      `width=${width},height=${height},left=${left},top=${top}`
    );

    if (popup) {
      const checkPopup = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkPopup);
          // Check if authentication was successful
          const token = localStorage.getItem('auth_token');
          if (token) {
            window.location.reload();
          }
        }
      }, 500);
    }
  };

  const login = (provider: 'google' | 'github') => {
    setError(null);
    handleOAuthPopup(provider);
  };

  const logout = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) return;

      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        localStorage.removeItem('auth_token');
        setUser(null);
        navigate('/login');
        enqueueSnackbar('Successfully logged out', { variant: 'success' });
      } else {
        throw new Error('Logout failed');
      }
    } catch (err) {
      console.error('Logout failed:', err);
      enqueueSnackbar('Failed to logout', { variant: 'error' });
    }
  };

  // Listen for auth messages from popup
  useEffect(() => {
    const handleMessage = async (event: MessageEvent) => {
      if (event.data?.type === 'AUTH_SUCCESS') {
        const { token } = event.data;
        localStorage.setItem('auth_token', token);

        try {
          const response = await fetch('/api/auth/user', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
            navigate('/');
            enqueueSnackbar('Successfully logged in', { variant: 'success' });
          }
        } catch (err) {
          console.error('Failed to get user data:', err);
          setError('Failed to get user data');
          enqueueSnackbar('Failed to get user data', { variant: 'error' });
        }
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [navigate, enqueueSnackbar]);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        login,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};