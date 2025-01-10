"""Analytics system for tracking and analyzing trading performance."""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from pathlib import Path

from ..dex.dex_manager import DEXManager
from ..dex.utils import format_amount_with_decimals, COMMON_TOKENS

logger = logging.getLogger(__name__)

class AnalyticsSystem:
    """System for collecting and analyzing trading metrics."""

    def __init__(
        self,
        dex_manager: DEXManager,
        metrics_dir: str = "metrics",
        analysis_window: int = 24  # Hours
    ):
        """Initialize analytics system."""
        self.dex_manager = dex_manager
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        self.analysis_window = analysis_window
        
        # Initialize metrics containers
        self.trade_metrics: List[Dict[str, Any]] = []
        self.dex_metrics: Dict[str, Dict[str, Any]] = {}
        self.token_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Performance thresholds
        self.min_success_rate = 0.95  # 95% success rate required
        self.min_profit_threshold = 10.0  # $10 minimum profit
        self.max_slippage = 0.02  # 2% maximum slippage
        self.max_gas_usage = 500000  # Maximum gas units per trade

    async def record_trade(
        self,
        trade_result: Dict[str, Any],
        opportunity: Dict[str, Any]
    ) -> None:
        """
        Record trade execution metrics.
        
        Args:
            trade_result: Execution result from arbitrage executor
            opportunity: Original opportunity details
        """
        try:
            timestamp = datetime.fromtimestamp(trade_result['timestamp'])
            
            # Calculate metrics
            profit_usd = trade_result['profit_usd']
            gas_cost = trade_result['gas_used'] * trade_result.get('effectiveGasPrice', 0)
            execution_time = trade_result.get('execution_time', 0)
            
            # Create trade record
            trade_record = {
                'timestamp': timestamp.isoformat(),
                'buy_dex': opportunity['buy_dex'],
                'sell_dex': opportunity['sell_dex'],
                'token_in': opportunity['buy_path'][0],
                'token_out': opportunity['buy_path'][-1],
                'amount_in': opportunity['amount_in'],
                'amount_out': opportunity['sell_amount_out'],
                'profit_usd': profit_usd,
                'gas_used': trade_result['gas_used'],
                'gas_cost_usd': trade_result.get('gas_cost_usd', 0),
                'execution_time': execution_time,
                'success': trade_result['success'],
                'price_impact': opportunity['price_impact']
            }
            
            # Update metrics
            self.trade_metrics.append(trade_record)
            self._update_dex_metrics(trade_record)
            self._update_token_metrics(trade_record)
            
            # Save metrics
            await self._save_metrics()
            
        except Exception as e:
            logger.error(f"Error recording trade metrics: {e}")

    async def analyze_performance(
        self,
        time_window: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze trading performance metrics.
        
        Args:
            time_window: Analysis window in hours (default: self.analysis_window)
            
        Returns:
            Dict[str, Any]: Performance analysis results
        """
        try:
            window = time_window or self.analysis_window
            cutoff = datetime.now() - timedelta(hours=window)
            
            # Filter recent trades
            recent_trades = [
                trade for trade in self.trade_metrics
                if datetime.fromisoformat(trade['timestamp']) > cutoff
            ]
            
            if not recent_trades:
                return {
                    'trades': 0,
                    'success_rate': 0,
                    'total_profit': 0,
                    'avg_profit': 0,
                    'avg_gas': 0,
                    'recommendations': ["No trades in analysis window"]
                }
            
            # Calculate metrics
            df = pd.DataFrame(recent_trades)
            
            total_trades = len(df)
            successful_trades = len(df[df['success']])
            success_rate = successful_trades / total_trades
            
            total_profit = df['profit_usd'].sum()
            avg_profit = df['profit_usd'].mean()
            avg_gas = df['gas_used'].mean()
            
            # DEX performance
            dex_stats = {}
            for dex_name in self.dex_metrics:
                dex_trades = df[
                    (df['buy_dex'] == dex_name) | 
                    (df['sell_dex'] == dex_name)
                ]
                if not dex_trades.empty:
                    dex_stats[dex_name] = {
                        'trades': len(dex_trades),
                        'success_rate': len(dex_trades[dex_trades['success']]) / len(dex_trades),
                        'avg_profit': dex_trades['profit_usd'].mean(),
                        'avg_gas': dex_trades['gas_used'].mean()
                    }
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                success_rate=success_rate,
                avg_profit=avg_profit,
                avg_gas=avg_gas,
                dex_stats=dex_stats
            )
            
            return {
                'trades': total_trades,
                'success_rate': success_rate,
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'avg_gas': avg_gas,
                'dex_performance': dex_stats,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return {}

    async def get_dex_metrics(self, dex_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for specific DEX."""
        return self.dex_metrics.get(dex_name)

    async def get_token_metrics(self, token: str) -> Optional[Dict[str, Any]]:
        """Get metrics for specific token."""
        return self.token_metrics.get(token)

    def _update_dex_metrics(self, trade: Dict[str, Any]) -> None:
        """Update DEX-specific metrics."""
        for dex_name in [trade['buy_dex'], trade['sell_dex']]:
            if dex_name not in self.dex_metrics:
                self.dex_metrics[dex_name] = {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'total_profit': 0,
                    'total_gas': 0,
                    'avg_execution_time': 0
                }
            
            metrics = self.dex_metrics[dex_name]
            metrics['total_trades'] += 1
            if trade['success']:
                metrics['successful_trades'] += 1
            metrics['total_profit'] += trade['profit_usd']
            metrics['total_gas'] += trade['gas_used']
            
            # Update moving average of execution time
            n = metrics['total_trades']
            old_avg = metrics['avg_execution_time']
            new_time = trade['execution_time']
            metrics['avg_execution_time'] = ((n - 1) * old_avg + new_time) / n

    def _update_token_metrics(self, trade: Dict[str, Any]) -> None:
        """Update token-specific metrics."""
        for token in [trade['token_in'], trade['token_out']]:
            if token not in self.token_metrics:
                self.token_metrics[token] = {
                    'total_volume': 0,
                    'successful_trades': 0,
                    'failed_trades': 0,
                    'total_profit': 0,
                    'avg_price_impact': 0
                }
            
            metrics = self.token_metrics[token]
            if trade['success']:
                metrics['successful_trades'] += 1
            else:
                metrics['failed_trades'] += 1
            
            # Update volume and profit
            metrics['total_volume'] += trade['amount_in']
            metrics['total_profit'] += trade['profit_usd']
            
            # Update moving average of price impact
            n = metrics['successful_trades'] + metrics['failed_trades']
            old_avg = metrics['avg_price_impact']
            new_impact = trade['price_impact']
            metrics['avg_price_impact'] = ((n - 1) * old_avg + new_impact) / n

    def _generate_recommendations(
        self,
        success_rate: float,
        avg_profit: float,
        avg_gas: float,
        dex_stats: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Generate trading recommendations based on metrics."""
        recommendations = []
        
        # Check success rate
        if success_rate < self.min_success_rate:
            recommendations.append(
                f"Success rate ({success_rate:.2%}) below threshold. "
                "Consider increasing safety margins."
            )
        
        # Check profitability
        if avg_profit < self.min_profit_threshold:
            recommendations.append(
                f"Average profit (${avg_profit:.2f}) below threshold. "
                "Consider adjusting minimum profit requirements."
            )
        
        # Check gas usage
        if avg_gas > self.max_gas_usage:
            recommendations.append(
                f"Average gas usage ({avg_gas:.0f}) above threshold. "
                "Consider optimizing execution paths."
            )
        
        # DEX-specific recommendations
        for dex_name, stats in dex_stats.items():
            if stats['success_rate'] < 0.9:  # 90% threshold for individual DEXs
                recommendations.append(
                    f"{dex_name} success rate ({stats['success_rate']:.2%}) concerning. "
                    "Consider reviewing DEX configuration."
                )
        
        return recommendations

    async def _save_metrics(self) -> None:
        """Save metrics to disk."""
        try:
            # Create metrics file path
            date_str = datetime.now().strftime("%Y%m%d")
            file_path = self.metrics_dir / f"trades_{date_str}.json"
            
            # Save trade metrics
            metrics = {
                'trades': self.trade_metrics,
                'dex_metrics': self.dex_metrics,
                'token_metrics': self.token_metrics,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(metrics, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")

    async def load_historical_metrics(self) -> None:
        """Load historical metrics from disk."""
        try:
            # Find all metrics files
            metric_files = list(self.metrics_dir.glob("trades_*.json"))
            
            for file_path in metric_files:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                # Update metrics
                self.trade_metrics.extend(data.get('trades', []))
                
                for dex_name, metrics in data.get('dex_metrics', {}).items():
                    if dex_name not in self.dex_metrics:
                        self.dex_metrics[dex_name] = metrics
                    else:
                        # Merge metrics
                        for key, value in metrics.items():
                            if key in self.dex_metrics[dex_name]:
                                self.dex_metrics[dex_name][key] += value
                
                for token, metrics in data.get('token_metrics', {}).items():
                    if token not in self.token_metrics:
                        self.token_metrics[token] = metrics
                    else:
                        # Merge metrics
                        for key, value in metrics.items():
                            if key in self.token_metrics[token]:
                                self.token_metrics[token][key] += value
                
        except Exception as e:
            logger.error(f"Error loading historical metrics: {e}")
