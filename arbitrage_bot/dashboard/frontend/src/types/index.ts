export interface WebSocketUpdate {
  timestamp: string;
  detector: {
    risk_metrics: {
      drawdown: number;
    };
    risk: {
      level: number;
      factors: string[];
      current: number;
      historical: number[];
    };
  };
  predictions: {
    gas: {
      uncertainty: number;
      price: number;
      confidence: number;
    };
    liquidity: {
      uncertainty: number;
      total: number;
      confidence: number;
    };
  };
  performance: {
    trades: {
      win_rate: number;
      successful: number;
      total: number;
    };
    profit_loss: {
      total: number;
      net_profit: number;
      total_profit: number;
      daily: number[];
      weekly: number[];
    };
    risk: {
      current: number;
      historical: number[];
      factors: string[];
      drawdown: number;
      exposure: number;
      volatility: number;
      metrics: {
        sharpe_ratio: number;
        sortino_ratio: number;
        max_drawdown: number;
      };
    };
  };
}

export interface WebSocketContextType {
  lastUpdate: WebSocketUpdate | null;
  connected: boolean;
  error: string | null;
}

export interface SnackbarMessage {
  message: string;
  variant: 'success' | 'error' | 'warning' | 'info';
  persist?: boolean;
}

// Chart data types
export interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    borderColor?: string;
    backgroundColor?: string;
    fill?: boolean;
  }[];
}

export interface ChartOptions {
  responsive: boolean;
  plugins: {
    legend: {
      position: 'top' | 'bottom' | 'left' | 'right';
    };
    title: {
      display: boolean;
      text: string;
    };
  };
  scales?: {
    y: {
      beginAtZero?: boolean;
      title?: {
        display: boolean;
        text: string;
      };
    };
  };
}

// Chart colors
export const CHART_COLORS = {
  primary: '#00ff9f',
  secondary: '#7b1fa2',
  success: '#4caf50',
  warning: '#ff9800',
  error: '#f44336',
  info: '#2196f3',
  background: 'rgba(19, 47, 76, 0.9)',
};