export interface WebSocketMessage {
  type: 'opportunity' | 'trade_executed' | 'trade_failed' | 'gas_alert' | 'system_status' | 'predictions' | 'performance';
  profit?: string;
  reason?: string;
  gasPrice?: number;
  message?: string;
  status?: 'error' | 'success' | 'warning';
  timestamp: number;
}

export interface WebSocketContextType {
  connected: boolean;
  lastMessage: WebSocketMessage | null;
  lastUpdate: number;
  sendMessage: (message: any) => void;
}

export interface OpportunityMessage extends WebSocketMessage {
  type: 'opportunity';
  profit: string;
  tokenIn: string;
  tokenOut: string;
  route: string[];
  estimatedGas: number;
}

export interface TradeExecutedMessage extends WebSocketMessage {
  type: 'trade_executed';
  profit: string;
  txHash: string;
  gasUsed: number;
  actualProfit: string;
}

export interface TradeFailedMessage extends WebSocketMessage {
  type: 'trade_failed';
  reason: string;
  txHash?: string;
  gasUsed?: number;
}

export interface GasAlertMessage extends WebSocketMessage {
  type: 'gas_alert';
  gasPrice: number;
  threshold: number;
  network: string;
}

export interface SystemStatusMessage extends WebSocketMessage {
  type: 'system_status';
  status: 'error' | 'success' | 'warning';
  message: string;
  details?: any;
}

export interface PredictionData {
  gasPrice: number;
  confidence: number;
  timestamp: number;
  probability: number;
}

export interface PredictionsMessage extends WebSocketMessage {
  type: 'predictions';
  predictions: PredictionData[];
  timestamp: number;
}

export interface PerformanceData {
  profit: number;
  trades: number;
  successRate: number;
  gasUsed: number;
  timestamp: number;
}

export interface PerformanceMessage extends WebSocketMessage {
  type: 'performance';
  performance: PerformanceData[];
  timestamp: number;
}