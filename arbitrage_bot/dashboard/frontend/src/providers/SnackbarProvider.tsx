import React from 'react';
import { SnackbarProvider as NotistackProvider } from 'notistack';

interface SnackbarProviderProps {
  children: React.ReactNode;
}

export const SnackbarProvider: React.FC<SnackbarProviderProps> = ({ children }) => {
  return (
    <NotistackProvider
      maxSnack={3}
      anchorOrigin={{
        vertical: 'bottom',
        horizontal: 'right',
      }}
      autoHideDuration={3000}
    >
      {children}
    </NotistackProvider>
  );
};

export default SnackbarProvider;