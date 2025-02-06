import React, { createContext, useContext, useEffect, useState } from 'react';
import { useSnackbar } from 'notistack';
import { WebSocketContextType, WebSocketUpdate } from '../types';

// Create WebSocket context
const WebSocketContext = createContext<WebSocketContextType>({
  lastUpdate: null,
  connected: false,
  error: null,
});

// WebSocket configuration
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 2000;

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<WebSocketUpdate | null>(null);
  const { enqueueSnackbar } = useSnackbar();

  // Initialize WebSocket connection
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
          setConnected(true);
          setError(null);
          enqueueSnackbar('Connected to server', { variant: 'success' });
        };

        ws.onclose = () => {
          setConnected(false);
          enqueueSnackbar('Connection lost. Reconnecting...', { variant: 'warning' });
          // Attempt to reconnect
          setTimeout(connect, RECONNECT_DELAY);
        };

        ws.onerror = (event) => {
          setError('WebSocket error');
          enqueueSnackbar('Connection error', { variant: 'error' });
        };

        ws.onmessage = (event) => {
          try {
            const data: WebSocketUpdate = JSON.parse(event.data);
            setLastUpdate(data);

            // Check for critical alerts
            checkAlerts(data);
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        setSocket(ws);

        // Cleanup on unmount
        return () => {
          ws.close();
        };
      } catch (e) {
        setError('Failed to connect');
        enqueueSnackbar('Failed to connect to server', { variant: 'error' });
        // Attempt to reconnect
        setTimeout(connect, RECONNECT_DELAY);
      }
    };

    connect();
  }, [enqueueSnackbar]);

  // Check for critical conditions that need alerts
  const checkAlerts = (data: WebSocketUpdate) => {
    // Check risk metrics
    if (data.detector.risk_metrics.drawdown > 0.1) {
      enqueueSnackbar(`High drawdown alert: ${(data.detector.risk_metrics.drawdown * 100).toFixed(2)}%`, {
        variant: 'error',
        persist: true,
      });
    }

    // Check gas predictions
    if (data.predictions.gas.uncertainty > 0.3) {
      enqueueSnackbar(`High gas price uncertainty: ${(data.predictions.gas.uncertainty * 100).toFixed(2)}%`, {
        variant: 'warning',
      });
    }

    // Check liquidity predictions
    if (data.predictions.liquidity.uncertainty > 0.3) {
      enqueueSnackbar(`High liquidity uncertainty: ${(data.predictions.liquidity.uncertainty * 100).toFixed(2)}%`, {
        variant: 'warning',
      });
    }

    // Check performance
    if (data.performance.trades.win_rate < 0.5) {
      enqueueSnackbar(`Low win rate alert: ${(data.performance.trades.win_rate * 100).toFixed(2)}%`, {
        variant: 'warning',
      });
    }
  };

  // Provide real-time data to children
  return (
    <WebSocketContext.Provider
      value={{
        lastUpdate,
        connected,
        error,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

// Custom hook for using WebSocket context
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export default WebSocketProvider;