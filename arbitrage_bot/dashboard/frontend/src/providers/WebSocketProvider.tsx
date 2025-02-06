import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useAuth } from './AuthProvider';
import { useNotifications } from '../hooks/useNotifications';
import { AlertColor } from '@mui/material';
import {
  WebSocketContextType,
  WebSocketMessage,
  OpportunityMessage,
  TradeExecutedMessage,
  TradeFailedMessage,
  GasAlertMessage,
  SystemStatusMessage,
  PredictionsMessage,
  PerformanceMessage,
} from '../types/websocket';

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user } = useAuth();
  const { showNotification } = useNotifications();
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now());
  const ws = useRef<WebSocket | null>(null);

  const connect = () => {
    if (!user) return;

    const wsUrl = process.env.REACT_APP_WS_URL;
    if (!wsUrl) {
      showNotification('WebSocket URL not configured', 'error');
      return;
    }

    try {
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setConnected(true);
        showNotification('Connected to real-time updates', 'success');
        setLastUpdate(Date.now());
      };

      ws.current.onclose = () => {
        setConnected(false);
        showNotification('Disconnected from real-time updates', 'warning');
        setLastUpdate(Date.now());
        // Attempt to reconnect after 5 seconds
        setTimeout(connect, 5000);
      };

      ws.current.onerror = (error) => {
        showNotification('WebSocket error occurred', 'error');
        setLastUpdate(Date.now());
        console.error('WebSocket error:', error);
      };

      ws.current.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(data);
          setLastUpdate(Date.now());

          // Handle different message types
          switch (data.type) {
            case 'opportunity': {
              const msg = data as OpportunityMessage;
              showNotification(
                `New arbitrage opportunity: ${msg.profit}% profit`,
                'info'
              );
              break;
            }

            case 'trade_executed': {
              const msg = data as TradeExecutedMessage;
              showNotification(
                `Trade executed successfully: ${msg.profit} profit`,
                'success'
              );
              break;
            }

            case 'trade_failed': {
              const msg = data as TradeFailedMessage;
              showNotification(
                `Trade failed: ${msg.reason}`,
                'error'
              );
              break;
            }

            case 'gas_alert': {
              const msg = data as GasAlertMessage;
              showNotification(
                `High gas prices detected: ${msg.gasPrice} gwei`,
                'warning'
              );
              break;
            }

            case 'system_status': {
              const msg = data as SystemStatusMessage;
              if (msg.status === 'error') {
                showNotification(
                  `System error: ${msg.message}`,
                  'error'
                );
              }
              break;
            }

            case 'predictions': {
              const msg = data as PredictionsMessage;
              // Just update state, components will handle display
              break;
            }

            case 'performance': {
              const msg = data as PerformanceMessage;
              // Just update state, components will handle display
              break;
            }

            default:
              console.log('Received unknown message type:', data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          showNotification('Error processing real-time update', 'error');
        }
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      showNotification('Failed to connect to real-time updates', 'error');
    }
  };

  const disconnect = () => {
    if (ws.current) {
      ws.current.close();
      ws.current = null;
      setConnected(false);
      setLastUpdate(Date.now());
    }
  };

  const sendMessage = (message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
      setLastUpdate(Date.now());
    } else {
      showNotification('Not connected to server', 'error');
    }
  };

  useEffect(() => {
    if (user) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user]);

  return (
    <WebSocketContext.Provider
      value={{
        connected,
        lastMessage,
        lastUpdate,
        sendMessage,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};