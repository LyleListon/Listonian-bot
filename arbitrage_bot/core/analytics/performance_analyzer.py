"""
Performance Analyzer Module

Provides advanced performance analysis for the arbitrage system.
"""

import logging
import asyncio
import math
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import json
import os
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """
    Analyzes trading performance with advanced metrics.
    
    Features:
    - Performance benchmarking against market indices
    - Drawdown analysis
    - Volatility calculation
    - Risk-adjusted performance metrics (Sharpe, Sortino, Calmar ratios)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the performance analyzer.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()
        
        # Storage for performance data
        self._performance_history = []
        self._benchmark_data = {}
        self._drawdown_history = {}
        
        # Storage paths
        self.storage_dir = self.config.get('storage_dir', 'analytics')
        self.performance_file = os.path.join(self.storage_dir, 'performance_history.json')
        self.benchmark_file = os.path.join(self.storage_dir, 'benchmark_data.json')
        
        # Risk-free rate for Sharpe ratio calculation (default: 2%)
        self.risk_free_rate = float(self.config.get('risk_free_rate', 0.02))
        
        # Cache settings
        self.cache_ttl = int(self.config.get('cache_ttl', 300))  # 5 minutes
        self._last_cache_update = 0
        
    async def initialize(self) -> bool:
        """
        Initialize the performance analyzer.
        
        Returns:
            True if initialization successful
        """
        try:
            # Create storage directory if it doesn't exist
            os.makedirs(self.storage_dir, exist_ok=True)
            
            # Load historical data if available
            await self._load_historical_data()
            
            self.initialized = True
            logger.info("Performance analyzer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize performance analyzer: {e}")
            return False
    
    async def _load_historical_data(self) -> None:
        """Load historical performance data from storage."""
        try:
            # Load performance history
            if os.path.exists(self.performance_file):
                async with self.lock:
                    with open(self.performance_file, 'r') as f:
                        data = json.load(f)
                        
                    # Convert string timestamps back to datetime objects
                    for entry in data:
                        if 'timestamp' in entry:
                            entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                    
                    self._performance_history = data
                    logger.info(f"Loaded {len(data)} historical performance entries")
            else:
                logger.info("No historical performance data found")
                
            # Load benchmark data
            if os.path.exists(self.benchmark_file):
                async with self.lock:
                    with open(self.benchmark_file, 'r') as f:
                        self._benchmark_data = json.load(f)
                    logger.info(f"Loaded benchmark data for {len(self._benchmark_data)} indices")
            else:
                logger.info("No benchmark data found")
                
        except Exception as e:
            logger.error(f"Error loading historical performance data: {e}")
    
    async def _save_historical_data(self) -> None:
        """Save historical performance data to storage."""
        try:
            # Save performance history
            async with self.lock:
                # Convert datetime objects to ISO format strings for JSON serialization
                data_to_save = []
                for entry in self._performance_history:
                    entry_copy = entry.copy()
                    if isinstance(entry_copy.get('timestamp'), datetime):
                        entry_copy['timestamp'] = entry_copy['timestamp'].isoformat()
                    data_to_save.append(entry_copy)
                
                with open(self.performance_file, 'w') as f:
                    json.dump(data_to_save, f, indent=2)
                
                logger.info(f"Saved {len(data_to_save)} performance entries to {self.performance_file}")
                
            # Save benchmark data
            async with self.lock:
                with open(self.benchmark_file, 'w') as f:
                    json.dump(self._benchmark_data, f, indent=2)
                logger.info(f"Saved benchmark data to {self.benchmark_file}")
                
        except Exception as e:
            logger.error(f"Error saving historical performance data: {e}")
    
    async def track_performance(self, performance_data: Dict[str, Any]) -> None:
        """
        Track a new performance entry.
        
        Args:
            performance_data: Dictionary containing performance data with at least:
                - portfolio_value: Current portfolio value
                - profit_loss: Profit/loss since last entry
                - timestamp: Entry timestamp (optional, defaults to now)
                - trade_count: Number of trades in this period
                - gas_cost: Gas cost in native currency
        """
        if not self.initialized:
            raise RuntimeError("Performance analyzer not initialized")
        
        # Ensure required fields are present
        required_fields = ['portfolio_value', 'profit_loss']
        for field in required_fields:
            if field not in performance_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Add timestamp if not present
        if 'timestamp' not in performance_data:
            performance_data['timestamp'] = datetime.utcnow()
        
        async with self.lock:
            # Add to performance history
            self._performance_history.append(performance_data)
            
            # Update drawdown history
            await self._update_drawdown_history()
            
            # Save to storage
            await self._save_historical_data()
    
    async def _update_drawdown_history(self) -> None:
        """Update drawdown history based on performance data."""
        if not self._performance_history:
            return
        
        try:
            # Sort by timestamp
            sorted_history = sorted(self._performance_history, key=lambda x: x.get('timestamp', datetime.min))
            
            # Calculate running maximum and drawdowns
            running_max = float(sorted_history[0].get('portfolio_value', 0))
            drawdowns = []
            
            for entry in sorted_history:
                value = float(entry.get('portfolio_value', 0))
                timestamp = entry.get('timestamp', datetime.min)
                
                # Update running maximum
                running_max = max(running_max, value)
                
                # Calculate drawdown
                drawdown = (running_max - value) / running_max if running_max > 0 else 0
                
                drawdowns.append({
                    'timestamp': timestamp,
                    'portfolio_value': value,
                    'peak_value': running_max,
                    'drawdown': drawdown
                })
            
            self._drawdown_history = {
                'drawdowns': drawdowns,
                'max_drawdown': max(d.get('drawdown', 0) for d in drawdowns) if drawdowns else 0
            }
            
        except Exception as e:
            logger.error(f"Error updating drawdown history: {e}")
    
    async def add_benchmark_data(self, benchmark_id: str, data: Dict[str, Any]) -> None:
        """
        Add or update benchmark data for comparison.
        
        Args:
            benchmark_id: Identifier for the benchmark (e.g., "ETH", "BTC", "S&P500")
            data: Dictionary with benchmark data:
                - values: List of values over time
                - timestamps: List of corresponding timestamps
                - metadata: Optional metadata about the benchmark
        """
        if not self.initialized:
            raise RuntimeError("Performance analyzer not initialized")
        
        # Validate data
        if 'values' not in data or 'timestamps' not in data:
            raise ValueError("Benchmark data must include 'values' and 'timestamps'")
        
        if len(data['values']) != len(data['timestamps']):
            raise ValueError("Values and timestamps must have the same length")
        
        async with self.lock:
            # Convert timestamps to ISO format if they're datetime objects
            timestamps = []
            for ts in data['timestamps']:
                if isinstance(ts, datetime):
                    timestamps.append(ts.isoformat())
                else:
                    timestamps.append(ts)
            
            # Store benchmark data
            self._benchmark_data[benchmark_id] = {
                'values': data['values'],
                'timestamps': timestamps,
                'metadata': data.get('metadata', {})
            }
            
            # Save to storage
            await self._save_historical_data()
    
    async def get_performance_metrics(self, timeframe: str = "all") -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Args:
            timeframe: Time frame for metrics ("1d", "7d", "30d", "90d", "1y", "all")
            
        Returns:
            Dictionary with performance metrics
        """
        if not self.initialized:
            raise RuntimeError("Performance analyzer not initialized")
        
        if not self._performance_history:
            return {
                'timeframe': timeframe,
                'total_return': 0,
                'annualized_return': 0,
                'volatility': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'calmar_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'recovery_factor': 0
            }
        
        async with self.lock:
            # Filter data by timeframe
            filtered_data = await self._filter_by_timeframe(self._performance_history, timeframe)
            
            if not filtered_data:
                return {
                    'timeframe': timeframe,
                    'total_return': 0,
                    'annualized_return': 0,
                    'volatility': 0,
                    'sharpe_ratio': 0,
                    'sortino_ratio': 0,
                    'calmar_ratio': 0,
                    'max_drawdown': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'recovery_factor': 0
                }
            
            # Calculate basic metrics
            total_return = await self._calculate_total_return(filtered_data)
            annualized_return = await self._calculate_annualized_return(filtered_data)
            volatility = await self._calculate_volatility(filtered_data)
            
            # Calculate drawdown metrics
            drawdown_data = await self._filter_by_timeframe(self._drawdown_history.get('drawdowns', []), timeframe)
            max_drawdown = max(d.get('drawdown', 0) for d in drawdown_data) if drawdown_data else 0
            
            # Calculate risk-adjusted metrics
            sharpe_ratio = await self._calculate_sharpe_ratio(filtered_data, annualized_return, volatility)
            sortino_ratio = await self._calculate_sortino_ratio(filtered_data, annualized_return)
            calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
            
            # Calculate trading metrics
            win_rate = await self._calculate_win_rate(filtered_data)
            profit_factor = await self._calculate_profit_factor(filtered_data)
            recovery_factor = total_return / max_drawdown if max_drawdown > 0 else 0
            
            return {
                'timeframe': timeframe,
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'recovery_factor': recovery_factor
            }
    
    async def _filter_by_timeframe(self, data: List[Dict[str, Any]], timeframe: str) -> List[Dict[str, Any]]:
        """Filter data by timeframe."""
        now = datetime.utcnow()
        
        if timeframe == "1d":
            start_time = now - timedelta(days=1)
        elif timeframe == "7d":
            start_time = now - timedelta(days=7)
        elif timeframe == "30d":
            start_time = now - timedelta(days=30)
        elif timeframe == "90d":
            start_time = now - timedelta(days=90)
        elif timeframe == "1y":
            start_time = now - timedelta(days=365)
        else:  # "all"
            return data
        
        return [entry for entry in data if entry.get('timestamp', now) >= start_time]
    
    async def _calculate_total_return(self, data: List[Dict[str, Any]]) -> float:
        """Calculate total return from performance data."""
        if not data:
            return 0
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.get('timestamp', datetime.min))
        
        # Get first and last portfolio values
        first_value = float(sorted_data[0].get('portfolio_value', 0))
        last_value = float(sorted_data[-1].get('portfolio_value', 0))
        
        if first_value <= 0:
            return 0
        
        return (last_value - first_value) / first_value
    
    async def _calculate_annualized_return(self, data: List[Dict[str, Any]]) -> float:
        """Calculate annualized return from performance data."""
        if not data or len(data) < 2:
            return 0
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.get('timestamp', datetime.min))
        
        # Get first and last portfolio values and timestamps
        first_entry = sorted_data[0]
        last_entry = sorted_data[-1]
        
        first_value = float(first_entry.get('portfolio_value', 0))
        last_value = float(last_entry.get('portfolio_value', 0))
        
        first_timestamp = first_entry.get('timestamp', datetime.min)
        last_timestamp = last_entry.get('timestamp', datetime.max)
        
        if first_value <= 0:
            return 0
        
        # Calculate time difference in years
        time_diff = (last_timestamp - first_timestamp).total_seconds() / (365.25 * 24 * 60 * 60)
        
        if time_diff <= 0:
            return 0
        
        # Calculate annualized return
        total_return = (last_value - first_value) / first_value
        return math.pow(1 + total_return, 1 / time_diff) - 1
    
    async def _calculate_volatility(self, data: List[Dict[str, Any]]) -> float:
        """Calculate volatility (standard deviation of returns)."""
        if not data or len(data) < 2:
            return 0
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.get('timestamp', datetime.min))
        
        # Calculate daily returns
        returns = []
        prev_value = float(sorted_data[0].get('portfolio_value', 0))
        
        for entry in sorted_data[1:]:
            curr_value = float(entry.get('portfolio_value', 0))
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
            prev_value = curr_value
        
        if not returns:
            return 0
        
        # Calculate standard deviation of returns
        return np.std(returns, ddof=1)
    
    async def _calculate_sharpe_ratio(self, data: List[Dict[str, Any]], 
                                     annualized_return: float, 
                                     volatility: float) -> float:
        """Calculate Sharpe ratio."""
        if volatility <= 0:
            return 0
        
        # Sharpe ratio = (Return - Risk-free rate) / Volatility
        return (annualized_return - self.risk_free_rate) / volatility
    
    async def _calculate_sortino_ratio(self, data: List[Dict[str, Any]], 
                                      annualized_return: float) -> float:
        """Calculate Sortino ratio (using only negative returns for volatility)."""
        if not data or len(data) < 2:
            return 0
        
        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.get('timestamp', datetime.min))
        
        # Calculate daily returns
        returns = []
        prev_value = float(sorted_data[0].get('portfolio_value', 0))
        
        for entry in sorted_data[1:]:
            curr_value = float(entry.get('portfolio_value', 0))
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
            prev_value = curr_value
        
        if not returns:
            return 0
        
        # Filter for negative returns only
        negative_returns = [r for r in returns if r < 0]
        
        if not negative_returns:
            return float('inf')  # No negative returns
        
        # Calculate downside deviation (standard deviation of negative returns)
        downside_deviation = np.std(negative_returns, ddof=1)
        
        if downside_deviation <= 0:
            return 0
        
        # Sortino ratio = (Return - Risk-free rate) / Downside Deviation
        return (annualized_return - self.risk_free_rate) / downside_deviation
    
    async def _calculate_win_rate(self, data: List[Dict[str, Any]]) -> float:
        """Calculate win rate (percentage of profitable periods)."""
        if not data:
            return 0
        
        # Count profitable periods
        profitable_periods = sum(1 for entry in data if float(entry.get('profit_loss', 0)) > 0)
        
        return profitable_periods / len(data)
    
    async def _calculate_profit_factor(self, data: List[Dict[str, Any]]) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if not data:
            return 0
        
        # Calculate gross profit and gross loss
        gross_profit = sum(float(entry.get('profit_loss', 0)) for entry in data 
                          if float(entry.get('profit_loss', 0)) > 0)
        
        gross_loss = sum(abs(float(entry.get('profit_loss', 0))) for entry in data 
                        if float(entry.get('profit_loss', 0)) < 0)
        
        if gross_loss <= 0:
            return float('inf') if gross_profit > 0 else 0
        
        return gross_profit / gross_loss
    
    async def get_drawdown_analysis(self, timeframe: str = "all") -> Dict[str, Any]:
        """
        Get detailed drawdown analysis.
        
        Args:
            timeframe: Time frame for analysis ("1d", "7d", "30d", "90d", "1y", "all")
            
        Returns:
            Dictionary with drawdown analysis
        """
        if not self.initialized:
            raise RuntimeError("Performance analyzer not initialized")
        
        async with self.lock:
            # Filter drawdown data by timeframe
            drawdown_data = await self._filter_by_timeframe(self._drawdown_history.get('drawdowns', []), timeframe)
            
            if not drawdown_data:
                return {
                    'timeframe': timeframe,
                    'max_drawdown': 0,
                    'avg_drawdown': 0,
                    'current_drawdown': 0,
                    'drawdown_periods': []
                }
            
            # Calculate max and average drawdown
            max_drawdown = max(d.get('drawdown', 0) for d in drawdown_data)
            avg_drawdown = sum(d.get('drawdown', 0) for d in drawdown_data) / len(drawdown_data)
            
            # Get current drawdown (from most recent entry)
            sorted_data = sorted(drawdown_data, key=lambda x: x.get('timestamp', datetime.min))
            current_drawdown = sorted_data[-1].get('drawdown', 0) if sorted_data else 0
            
            # Identify drawdown periods (continuous periods of drawdown > threshold)
            threshold = float(self.config.get('drawdown_threshold', 0.05))  # 5% drawdown threshold
            drawdown_periods = await self._identify_drawdown_periods(sorted_data, threshold)
            
            return {
                'timeframe': timeframe,
                'max_drawdown': max_drawdown,
                'avg_drawdown': avg_drawdown,
                'current_drawdown': current_drawdown,
                'drawdown_periods': drawdown_periods
            }
    
    async def _identify_drawdown_periods(self, data: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """Identify significant drawdown periods."""
        if not data:
            return []
        
        periods = []
        in_drawdown = False
        start_idx = 0
        
        for i, entry in enumerate(data):
            drawdown = entry.get('drawdown', 0)
            
            if not in_drawdown and drawdown >= threshold:
                # Start of a drawdown period
                in_drawdown = True
                start_idx = i
            elif in_drawdown and drawdown < threshold:
                # End of a drawdown period
                in_drawdown = False
                
                # Calculate drawdown period metrics
                period_data = data[start_idx:i]
                start_time = period_data[0].get('timestamp')
                end_time = period_data[-1].get('timestamp')
                max_dd = max(d.get('drawdown', 0) for d in period_data)
                duration = (end_time - start_time).days if start_time and end_time else 0
                
                periods.append({
                    'start_date': start_time.isoformat() if start_time else None,
                    'end_date': end_time.isoformat() if end_time else None,
                    'duration_days': duration,
                    'max_drawdown': max_dd,
                    'recovery': True
                })
        
        # Check if still in a drawdown period at the end
        if in_drawdown:
            period_data = data[start_idx:]
            start_time = period_data[0].get('timestamp')
            end_time = period_data[-1].get('timestamp')
            max_dd = max(d.get('drawdown', 0) for d in period_data)
            duration = (end_time - start_time).days if start_time and end_time else 0
            
            periods.append({
                'start_date': start_time.isoformat() if start_time else None,
                'end_date': None,  # Still ongoing
                'duration_days': duration,
                'max_drawdown': max_dd,
                'recovery': False
            })
        
        return periods
    
    async def benchmark_performance(self, benchmark_id: str, timeframe: str = "all") -> Dict[str, Any]:
        """
        Compare performance against a benchmark.
        
        Args:
            benchmark_id: Identifier for the benchmark to compare against
            timeframe: Time frame for comparison ("1d", "7d", "30d", "90d", "1y", "all")
            
        Returns:
            Dictionary with benchmark comparison metrics
        """
        if not self.initialized:
            raise RuntimeError("Performance analyzer not initialized")
        
        if benchmark_id not in self._benchmark_data:
            raise ValueError(f"Benchmark data not found for: {benchmark_id}")
        
        async with self.lock:
            # Get performance metrics
            performance_metrics = await self.get_performance_metrics(timeframe)
            
            # Get benchmark data for the timeframe
            benchmark = self._benchmark_data[benchmark_id]
            
            # Convert benchmark timestamps to datetime objects
            timestamps = []
            for ts in benchmark['timestamps']:
                if isinstance(ts, str):
                    timestamps.append(datetime.fromisoformat(ts))
                else:
                    timestamps.append(ts)
            
            # Filter benchmark data by timeframe
            now = datetime.utcnow()
            if timeframe == "1d":
                start_time = now - timedelta(days=1)
            elif timeframe == "7d":
                start_time = now - timedelta(days=7)
            elif timeframe == "30d":
                start_time = now - timedelta(days=30)
            elif timeframe == "90d":
                start_time = now - timedelta(days=90)
            elif timeframe == "1y":
                start_time = now - timedelta(days=365)
            else:  # "all"
                start_time = datetime.min
            
            # Find indices of benchmark data within timeframe
            filtered_indices = [i for i, ts in enumerate(timestamps) if ts >= start_time]
            
            if not filtered_indices:
                return {
                    'benchmark_id': benchmark_id,
                    'timeframe': timeframe,
                    'benchmark_return': 0,
                    'relative_return': performance_metrics.get('total_return', 0),
                    'alpha': 0,
                    'beta': 0,
                    'correlation': 0,
                    'tracking_error': 0,
                    'information_ratio': 0
                }
            
            # Calculate benchmark return
            first_idx = min(filtered_indices)
            last_idx = max(filtered_indices)
            
            first_value = float(benchmark['values'][first_idx])
            last_value = float(benchmark['values'][last_idx])
            
            benchmark_return = (last_value - first_value) / first_value if first_value > 0 else 0
            
            # Calculate relative return
            relative_return = performance_metrics.get('total_return', 0) - benchmark_return
            
            # Calculate alpha and beta (if enough data points)
            alpha, beta = await self._calculate_alpha_beta(timeframe, benchmark_id)
            
            # Calculate correlation
            correlation = await self._calculate_correlation(timeframe, benchmark_id)
            
            # Calculate tracking error and information ratio
            tracking_error = await self._calculate_tracking_error(timeframe, benchmark_id)
            information_ratio = relative_return / tracking_error if tracking_error > 0 else 0
            
            return {
                'benchmark_id': benchmark_id,
                'timeframe': timeframe,
                'benchmark_return': benchmark_return,
                'relative_return': relative_return,
                'alpha': alpha,
                'beta': beta,
                'correlation': correlation,
                'tracking_error': tracking_error,
                'information_ratio': information_ratio
            }
    
    async def _calculate_alpha_beta(self, timeframe: str, benchmark_id: str) -> Tuple[float, float]:
        """Calculate alpha and beta against benchmark."""
        # Filter performance data by timeframe
        performance_data = await self._filter_by_timeframe(self._performance_history, timeframe)
        
        if not performance_data or len(performance_data) < 3:
            return 0, 0
        
        # Get benchmark data
        benchmark = self._benchmark_data.get(benchmark_id, {})
        benchmark_values = benchmark.get('values', [])
        benchmark_timestamps = benchmark.get('timestamps', [])
        
        if not benchmark_values or len(benchmark_values) < 3:
            return 0, 0
        
        # Convert benchmark timestamps to datetime objects
        timestamps = []
        for ts in benchmark_timestamps:
            if isinstance(ts, str):
                timestamps.append(datetime.fromisoformat(ts))
            else:
                timestamps.append(ts)
        
        # Sort performance data by timestamp
        sorted_perf = sorted(performance_data, key=lambda x: x.get('timestamp', datetime.min))
        
        # Calculate daily returns for performance data
        perf_returns = []
        prev_value = float(sorted_perf[0].get('portfolio_value', 0))
        perf_timestamps = []
        
        for entry in sorted_perf[1:]:
            curr_value = float(entry.get('portfolio_value', 0))
            timestamp = entry.get('timestamp')
            
            if prev_value > 0 and timestamp:
                daily_return = (curr_value - prev_value) / prev_value
                perf_returns.append(daily_return)
                perf_timestamps.append(timestamp)
            
            prev_value = curr_value
        
        # Calculate daily returns for benchmark data
        benchmark_returns = []
        benchmark_ts = []
        
        for i in range(1, len(benchmark_values)):
            prev_value = float(benchmark_values[i-1])
            curr_value = float(benchmark_values[i])
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                benchmark_returns.append(daily_return)
                benchmark_ts.append(timestamps[i])
        
        # Match timestamps between performance and benchmark data
        matched_perf_returns = []
        matched_benchmark_returns = []
        
        for i, perf_ts in enumerate(perf_timestamps):
            # Find closest benchmark timestamp
            closest_idx = min(range(len(benchmark_ts)), 
                             key=lambda j: abs((benchmark_ts[j] - perf_ts).total_seconds()))
            
            if abs((benchmark_ts[closest_idx] - perf_ts).total_seconds()) <= 86400:  # Within 1 day
                matched_perf_returns.append(perf_returns[i])
                matched_benchmark_returns.append(benchmark_returns[closest_idx])
        
        if len(matched_perf_returns) < 3:
            return 0, 0
        
        # Calculate beta using covariance and variance
        cov_matrix = np.cov(matched_perf_returns, matched_benchmark_returns)
        if cov_matrix.shape == (2, 2):
            covariance = cov_matrix[0, 1]
            benchmark_variance = cov_matrix[1, 1]
            
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
            
            # Calculate alpha
            avg_perf_return = np.mean(matched_perf_returns)
            avg_benchmark_return = np.mean(matched_benchmark_returns)
            
            alpha = avg_perf_return - (beta * avg_benchmark_return)
            
            return alpha, beta
        
        return 0, 0
    
    async def _calculate_correlation(self, timeframe: str, benchmark_id: str) -> float:
        """Calculate correlation with benchmark."""
