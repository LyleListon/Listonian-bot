"""
Metrics processor for analyzing and aggregating collected metrics.
Provides trend analysis and performance insights.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import defaultdict

class MetricsProcessor:
    """
    Processes and analyzes collected metrics to provide insights.
    Handles trend detection, anomaly detection, and metric aggregation.
    """

    def __init__(self):
        self.trend_window = 60  # 60 data points for trend analysis
        self.anomaly_threshold = 2.0  # Standard deviations for anomaly detection

    def analyze_system_metrics(self, metrics: List[Dict]) -> Dict:
        """Analyze system performance metrics."""
        if not metrics:
            return {}

        cpu_values = [m['cpu_percent'] for m in metrics]
        memory_values = [m['memory_percent'] for m in metrics]
        disk_values = [m['disk_percent'] for m in metrics]

        return {
            'cpu': {
                'current': cpu_values[-1],
                'average': np.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'trend': self._calculate_trend(cpu_values),
                'anomalies': self._detect_anomalies(cpu_values)
            },
            'memory': {
                'current': memory_values[-1],
                'average': np.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'trend': self._calculate_trend(memory_values),
                'anomalies': self._detect_anomalies(memory_values)
            },
            'disk': {
                'current': disk_values[-1],
                'average': np.mean(disk_values),
                'max': max(disk_values),
                'min': min(disk_values),
                'trend': self._calculate_trend(disk_values),
                'anomalies': self._detect_anomalies(disk_values)
            }
        }

    def analyze_trading_metrics(self, metrics: List[Dict]) -> Dict:
        """Analyze trading performance metrics."""
        if not metrics:
            return {}

        profits = [m.get('profit', 0) for m in metrics]
        gas_costs = [m.get('gas_cost', 0) for m in metrics]
        execution_times = [m.get('execution_time', 0) for m in metrics]

        return {
            'profit': {
                'total': sum(profits),
                'average': np.mean(profits) if profits else 0,
                'trend': self._calculate_trend(profits),
                'volatility': np.std(profits) if len(profits) > 1 else 0
            },
            'gas': {
                'total': sum(gas_costs),
                'average': np.mean(gas_costs) if gas_costs else 0,
                'trend': self._calculate_trend(gas_costs)
            },
            'execution': {
                'average_time': np.mean(execution_times) if execution_times else 0,
                'max_time': max(execution_times) if execution_times else 0,
                'min_time': min(execution_times) if execution_times else 0
            }
        }

    def analyze_blockchain_metrics(self, metrics: List[Dict]) -> Dict:
        """Analyze blockchain-related metrics."""
        if not metrics:
            return {}

        gas_prices = [m.get('gas_price', 0) for m in metrics]
        block_times = [m.get('block_time', 0) for m in metrics]
        
        return {
            'gas_price': {
                'current': gas_prices[-1] if gas_prices else 0,
                'average': np.mean(gas_prices) if gas_prices else 0,
                'trend': self._calculate_trend(gas_prices),
                'volatility': np.std(gas_prices) if len(gas_prices) > 1 else 0
            },
            'block_time': {
                'average': np.mean(block_times) if block_times else 0,
                'trend': self._calculate_trend(block_times)
            }
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction and strength."""
        if len(values) < 2:
            return "stable"

        # Use last trend_window points or all if less
        window = min(self.trend_window, len(values))
        recent_values = values[-window:]
        
        # Calculate linear regression
        x = np.arange(len(recent_values))
        y = np.array(recent_values)
        slope, _ = np.polyfit(x, y, 1)
        
        # Determine trend direction and strength
        if abs(slope) < 0.01:
            return "stable"
        elif slope > 0:
            return "increasing" if slope > 0.05 else "slightly_increasing"
        else:
            return "decreasing" if slope < -0.05 else "slightly_decreasing"

    def _detect_anomalies(self, values: List[float]) -> List[int]:
        """Detect anomalies using standard deviation method."""
        if len(values) < 2:
            return []

        mean = np.mean(values)
        std = np.std(values)
        threshold = std * self.anomaly_threshold
        
        anomalies = []
        for i, value in enumerate(values):
            if abs(value - mean) > threshold:
                anomalies.append(i)
        
        return anomalies

    def calculate_performance_score(self, metrics: Dict) -> float:
        """Calculate overall performance score (0-100)."""
        score = 100.0
        
        # System metrics impact
        if 'system' in metrics:
            sys_metrics = metrics['system']
            # CPU penalty
            if sys_metrics.get('cpu', {}).get('current', 0) > 80:
                score -= 10
            elif sys_metrics.get('cpu', {}).get('current', 0) > 60:
                score -= 5
                
            # Memory penalty
            if sys_metrics.get('memory', {}).get('current', 0) > 90:
                score -= 15
            elif sys_metrics.get('memory', {}).get('current', 0) > 70:
                score -= 7
        
        # Trading metrics impact
        if 'trading' in metrics:
            trade_metrics = metrics['trading']
            # Profit trend impact
            if trade_metrics.get('profit', {}).get('trend') == 'increasing':
                score += 5
            elif trade_metrics.get('profit', {}).get('trend') == 'decreasing':
                score -= 5
                
            # Execution time impact
            avg_time = trade_metrics.get('execution', {}).get('average_time', 0)
            if avg_time > 5:  # More than 5 seconds
                score -= 10
        
        return max(0, min(100, score))

    def get_health_status(self, metrics: Dict) -> Tuple[str, List[str]]:
        """Get system health status and warnings."""
        status = "healthy"
        warnings = []
        
        # Check system metrics
        if 'system' in metrics:
            sys_metrics = metrics['system']
            
            if sys_metrics.get('cpu', {}).get('current', 0) > 80:
                status = "degraded"
                warnings.append("High CPU usage")
                
            if sys_metrics.get('memory', {}).get('current', 0) > 90:
                status = "critical"
                warnings.append("Critical memory usage")
        
        # Check trading metrics
        if 'trading' in metrics:
            trade_metrics = metrics['trading']
            
            if trade_metrics.get('profit', {}).get('trend') == 'decreasing':
                warnings.append("Declining profit trend")
                
            if trade_metrics.get('execution', {}).get('average_time', 0) > 5:
                warnings.append("Slow execution times")
        
        return status, warnings

# Global metrics processor instance
metrics_processor = MetricsProcessor()