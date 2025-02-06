// API Response Types
export interface DetectorStatus {
  opportunities: Opportunity[];
  active_trades: number;
  performance: PerformanceStats;
  risk_metrics: RiskMetrics;
}

export interface Opportunity {
  path: string[];
  expected_profit: number;
  confidence: number;
  gas_cost: number;
  position_size: number;
  risk_score: number;
  timestamp: string;
}

export interface PerformanceStats {
  trades_executed: number;
  successful_trades: number;
  total_profit: number;
  total_loss: number;
  average_execution_time: number;
}

export interface RiskMetrics {
  volatility: number;
  drawdown: number;
  exposure: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
  recovery_factor: number;
  win_rate: number;
}

export interface Predictions {
  gas: GasPrediction;
  liquidity: LiquidityPrediction;
}

export interface GasPrediction {
  price: number;
  uncertainty: number;
  confidence: number;
}

export interface LiquidityPrediction {
  total: number;
  volume: number;
  impact: number;
  uncertainty: number;
  confidence: number;
}

export interface PerformanceMetrics {
  trades: {
    total: number;
    successful: number;
    win_rate: number;
    average_profit: number;
  };
  profit_loss: {
    total_profit: number;
    total_loss: number;
    net_profit: number;
  };
  risk: {
    drawdown: number;
    exposure: number;
    sharpe_ratio: number;
    volatility: number;
  };
}

export interface HistoricalData {
  timestamps: string[];
  values: number[];
}

export interface SystemHealth {
  detector: boolean;
  model_manager: boolean;
  data_coordinator: boolean;
  websocket_connections: number;
  timestamp: string;
}

// WebSocket Update Type
export interface WebSocketUpdate {
  timestamp: string;
  detector: DetectorStatus;
  predictions: Predictions;
  performance: PerformanceMetrics;
}

// Theme Types
export interface ThemeConfig {
  mode: 'light' | 'dark';
  primary: string;
  secondary: string;
  background: {
    default: string;
    paper: string;
  };
}

// Chart Types
export interface ChartConfig {
  type: 'line' | 'bar' | 'pie';
  data: any;
  options: any;
}

// Component Props Types
export interface CardProps {
  title: string;
  value: string | number;
  change?: number;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
}

export interface ChartProps {
  data: any;
  title: string;
  height?: number;
  loading?: boolean;
}

export interface TableProps {
  data: any[];
  columns: {
    field: string;
    headerName: string;
    width?: number;
    renderCell?: (params: any) => React.ReactNode;
  }[];
  loading?: boolean;
}

// Context Types
export interface WebSocketContextType {
  lastUpdate: WebSocketUpdate | null;
  connected: boolean;
  error: string | null;
}