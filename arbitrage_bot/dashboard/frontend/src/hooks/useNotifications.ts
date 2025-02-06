import { useState, useCallback } from 'react';
import { AlertColor } from '@mui/material';

export interface Notification {
  id: string;
  message: string;
  type: AlertColor;
  autoHideDuration?: number;
}

export interface UseNotificationsReturn {
  notifications: Notification[];
  showNotification: (message: string, type?: AlertColor) => void;
  closeNotification: (id: string) => void;
}

const DEFAULT_AUTO_HIDE_DURATION = 6000;

export const useNotifications = (): UseNotificationsReturn => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const showNotification = useCallback((
    message: string,
    type: AlertColor = 'info'
  ) => {
    const id = Math.random().toString(36).substring(7);
    const notification: Notification = {
      id,
      message,
      type,
      autoHideDuration: DEFAULT_AUTO_HIDE_DURATION,
    };

    setNotifications((prev) => [...prev, notification]);

    // Auto remove notification after duration
    setTimeout(() => {
      closeNotification(id);
    }, notification.autoHideDuration);
  }, []);

  const closeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((notification) => notification.id !== id));
  }, []);

  return {
    notifications,
    showNotification,
    closeNotification,
  };
};

export default useNotifications;