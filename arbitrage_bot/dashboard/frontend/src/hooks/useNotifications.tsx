import React from 'react';
import MuiAlert, { AlertProps } from '@mui/material/Alert';
import MuiSnackbar, { SnackbarProps } from '@mui/material/Snackbar';

type NotificationVariant = 'error' | 'warning' | 'info' | 'success';

interface NotificationOptions {
  variant?: NotificationVariant;
  duration?: number;
}

interface NotificationState {
  open: boolean;
  message: string;
  variant: NotificationVariant;
  duration: number;
}

const initialState: NotificationState = {
  open: false,
  message: '',
  variant: 'info',
  duration: 3000,
};

interface NotificationHookReturn {
  showNotification: (message: string, options?: NotificationOptions) => void;
  closeNotification: () => void;
  NotificationComponent: React.FC;
}

export const useNotifications = (): NotificationHookReturn => {
  const [state, setState] = React.useState<NotificationState>(initialState);

  const showNotification = React.useCallback(
    (message: string, options: NotificationOptions = {}) => {
      const { variant = 'info', duration = 3000 } = options;
      setState({
        open: true,
        message,
        variant,
        duration,
      });
    },
    []
  );

  const closeNotification = React.useCallback(() => {
    setState((prev: NotificationState) => ({ ...prev, open: false }));
  }, []);

  const handleClose = React.useCallback(
    (event?: React.SyntheticEvent | Event, reason?: string) => {
      if (reason === 'clickaway') {
        return;
      }
      closeNotification();
    },
    [closeNotification]
  );

  const NotificationComponent: React.FC = React.memo(() => (
    <MuiSnackbar
      open={state.open}
      autoHideDuration={state.duration}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
    >
      <MuiAlert
        elevation={6}
        variant="filled"
        onClose={handleClose}
        severity={state.variant}
      >
        {state.message}
      </MuiAlert>
    </MuiSnackbar>
  ));

  NotificationComponent.displayName = 'NotificationComponent';

  return {
    showNotification,
    closeNotification,
    NotificationComponent,
  };
};

export type { NotificationVariant, NotificationOptions };