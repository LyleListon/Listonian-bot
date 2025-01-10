"""Monte Carlo simulation for backtesting arbitrage strategies."""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import asyncio
from pathlib import Path

from ..analytics.analytics_system import AnalyticsSystem
from ..ml.ml_system import MLSystem
from ..dex.dex_manager import DEXManager
from ..dex.utils import COMMON_TOKENS
from ..gas.gas_optimizer import GasOptimizer

logger = logging.getLogger(__name__)

class MonteCarloSimulator:
    """Monte Carlo simulation for strategy validation."""

    def __init__(
        self,
        analytics: AnalyticsSystem,
        ml_system: MLSystem,
        dex_manager: DEXManager,
        gas_optimizer: GasOptimizer,
        results_dir: str = "simulation_results",
        num_simulations: int = 1000,
        time_horizon: int = 24  # hours
    ):
        """Initialize simulator."""
        self.analytics = analytics
        self.ml_system = ml_system
        self.dex_manager = dex_manager
        self.gas_optimizer = gas_optimizer
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.num_simulations = num_simulations
        self.time_horizon = time_horizon
        
        # Simulation parameters
        self.volatility_factor = 1.5  # Increased market volatility
        self.competition_factor = 1.2  # Increased competition
        self.slippage_factor = 1.1  # Increased slippage
        
        # Risk metrics
        self.var_confidence = 0.95  # 95% VaR
        self.max_drawdown = 0.1  # 10% maximum drawdown
        self.min_sharpe = 1.5  # Minimum Sharpe ratio

    async def run_simulation(
        self,
        initial_capital: float = 10000.0,  # $10k starting capital
        min_trade_size: float = 100.0,  # Minimum $100 per trade
        max_trade_size: float = 1000.0  # Maximum $1k per trade
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation.
        
        Args:
            initial_capital: Starting capital in USD
            min_trade_size: Minimum trade size in USD
            max_trade_size: Maximum trade size in USD
            
        Returns:
            Dict[str, Any]: Simulation results and analysis
        """
        try:
            # Initialize simulation state
            results = []
            capital_trajectories = []
            
            # Get historical data
            historical_trades = self.analytics.trade_metrics
            if not historical_trades:
                return self._empty_results()
            
            # Run simulations in parallel
            with ThreadPoolExecutor() as executor:
                futures = []
                for i in range(self.num_simulations):
                    futures.append(
                        executor.submit(
                            self._run_single_simulation,
                            initial_capital,
                            min_trade_size,
                            max_trade_size,
                            historical_trades
                        )
                    )
                
                # Collect results
                for future in futures:
                    sim_result = future.result()
                    if sim_result:
                        results.append(sim_result['metrics'])
                        capital_trajectories.append(sim_result['trajectory'])
            
            # Analyze results
            analysis = self._analyze_results(results, capital_trajectories)
            
            # Save results
            self._save_results(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error running simulation: {e}")
            return self._empty_results()

    def _run_single_simulation(
        self,
        initial_capital: float,
        min_trade_size: float,
        max_trade_size: float,
        historical_trades: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Run single simulation path."""
        try:
            capital = initial_capital
            trades_executed = 0
            successful_trades = 0
            total_profit = 0.0
            total_gas = 0.0
            capital_history = [capital]
            
            # Simulate time periods
            current_time = datetime.now()
            end_time = current_time + timedelta(hours=self.time_horizon)
            
            while current_time < end_time:
                # Simulate market conditions
                market_conditions = self._simulate_market_conditions(historical_trades)
                
                # Generate trade opportunity
                opportunity = self._generate_opportunity(
                    historical_trades,
                    min_trade_size,
                    max_trade_size,
                    market_conditions
                )
                
                if opportunity:
                    # Get ML predictions
                    success_prob, _ = asyncio.run(
                        self.ml_system.predict_trade_success(opportunity)
                    )
                    predicted_profit, _ = asyncio.run(
                        self.ml_system.predict_profit(opportunity)
                    )
                    
                    # Execute trade if predictions are favorable
                    if (
                        success_prob > 0.7 and  # 70% success probability
                        predicted_profit > opportunity['gas_cost_usd'] * 2  # 2x gas cost
                    ):
                        trades_executed += 1
                        
                        # Simulate trade outcome
                        success, profit, gas = self._simulate_trade_outcome(
                            opportunity,
                            market_conditions
                        )
                        
                        if success:
                            successful_trades += 1
                            total_profit += profit
                            capital += profit
                        
                        total_gas += gas
                        capital -= gas
                
                # Record capital
                capital_history.append(capital)
                
                # Move time forward
                current_time += timedelta(minutes=5)  # 5-minute intervals
            
            # Calculate metrics
            roi = (capital - initial_capital) / initial_capital
            success_rate = successful_trades / trades_executed if trades_executed > 0 else 0
            avg_profit = total_profit / trades_executed if trades_executed > 0 else 0
            
            return {
                'metrics': {
                    'final_capital': capital,
                    'roi': roi,
                    'trades_executed': trades_executed,
                    'success_rate': success_rate,
                    'total_profit': total_profit,
                    'total_gas': total_gas,
                    'avg_profit': avg_profit
                },
                'trajectory': capital_history
            }
            
        except Exception as e:
            logger.error(f"Error in simulation path: {e}")
            return None

    def _simulate_market_conditions(
        self,
        historical_trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Simulate market conditions based on historical data."""
        try:
            # Get base conditions
            base_conditions = asyncio.run(self.ml_system.analyze_market_conditions())
            
            # Add random volatility
            for dex in base_conditions['volatility']:
                base_conditions['volatility'][dex] *= (
                    1 + np.random.normal(0, 0.2) * self.volatility_factor
                )
            
            # Adjust competition
            base_conditions['competition']['rate'] *= (
                1 + np.random.normal(0, 0.1) * self.competition_factor
            )
            
            # Adjust liquidity
            for token in base_conditions['liquidity']:
                base_conditions['liquidity'][token] *= (
                    1 + np.random.normal(0, 0.15)
                )
            
            return base_conditions
            
        except Exception as e:
            logger.error(f"Error simulating market conditions: {e}")
            return {
                'volatility': {},
                'liquidity': {},
                'competition': {'rate': 0.5}
            }

    def _generate_opportunity(
        self,
        historical_trades: List[Dict[str, Any]],
        min_size: float,
        max_size: float,
        market_conditions: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate simulated trade opportunity."""
        try:
            if not historical_trades:
                return None
            
            # Sample historical trade
            base_trade = np.random.choice(historical_trades)
            
            # Adjust parameters based on market conditions
            dex_volatility = market_conditions['volatility'].get(
                base_trade['buy_dex'],
                0.1
            )
            
            # Adjust amounts
            amount_in = np.random.uniform(min_size, max_size)
            price_impact = base_trade.get('price_impact', 0.001) * self.slippage_factor
            amount_out = amount_in * (1 - price_impact)
            
            # Get gas estimate
            gas_price = asyncio.run(self.gas_optimizer.get_optimal_gas_price())
            gas_limit = asyncio.run(
                self.gas_optimizer.estimate_gas_limit(
                    base_trade['buy_dex'],
                    base_trade.get('buy_path', []),
                    'v3' if 'quoter' in base_trade else 'v2'
                )
            )
            gas_cost_usd = (gas_price * gas_limit) / 1e18 * 2000  # Rough ETH price
            
            return {
                'buy_dex': base_trade['buy_dex'],
                'sell_dex': base_trade['sell_dex'],
                'buy_path': base_trade.get('buy_path', []),
                'sell_path': base_trade.get('sell_path', []),
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price_impact': price_impact,
                'gas_cost_usd': gas_cost_usd,
                'market_volatility': dex_volatility,
                'competition_rate': market_conditions['competition']['rate']
            }
            
        except Exception as e:
            logger.error(f"Error generating opportunity: {e}")
            return None

    def _simulate_trade_outcome(
        self,
        opportunity: Dict[str, Any],
        market_conditions: Dict[str, Any]
    ) -> Tuple[bool, float, float]:
        """
        Simulate trade execution outcome.
        
        Returns:
            Tuple[bool, float, float]: Success flag, profit, gas cost
        """
        try:
            # Base success probability on market conditions
            base_prob = 1.0 - market_conditions['competition']['rate']
            
            # Adjust for volatility
            volatility = market_conditions['volatility'].get(
                opportunity['buy_dex'],
                0.1
            )
            success_prob = base_prob * (1 - volatility * self.volatility_factor)
            
            # Determine success
            success = np.random.random() < success_prob
            
            if success:
                # Calculate profit with random variation
                base_profit = opportunity['amount_out'] - opportunity['amount_in']
                profit_variation = np.random.normal(0, 0.1)  # 10% standard deviation
                actual_profit = base_profit * (1 + profit_variation)
                
                # Ensure profit covers gas
                if actual_profit < opportunity['gas_cost_usd']:
                    success = False
                    actual_profit = 0
            else:
                actual_profit = 0
            
            return success, actual_profit, opportunity['gas_cost_usd']
            
        except Exception as e:
            logger.error(f"Error simulating trade outcome: {e}")
            return False, 0.0, 0.0

    def _analyze_results(
        self,
        results: List[Dict[str, Any]],
        trajectories: List[List[float]]
    ) -> Dict[str, Any]:
        """Analyze simulation results."""
        try:
            if not results:
                return self._empty_results()
            
            # Convert to DataFrame
            df = pd.DataFrame(results)
            
            # Calculate risk metrics
            returns = df['roi'].values
            var = np.percentile(returns, (1 - self.var_confidence) * 100)
            
            # Calculate maximum drawdown
            max_dd = 0
            for trajectory in trajectories:
                peaks = pd.Series(trajectory).expanding(min_periods=1).max()
                drawdowns = (pd.Series(trajectory) - peaks) / peaks
                max_dd = min(max_dd, drawdowns.min())
            
            # Calculate Sharpe ratio (assuming risk-free rate of 2%)
            rf_rate = 0.02
            excess_returns = returns - rf_rate
            sharpe = np.mean(excess_returns) / np.std(excess_returns) if len(returns) > 1 else 0
            
            return {
                'summary_stats': {
                    'mean_roi': float(df['roi'].mean()),
                    'median_roi': float(df['roi'].median()),
                    'roi_std': float(df['roi'].std()),
                    'success_rate': float(df['success_rate'].mean()),
                    'avg_trades': float(df['trades_executed'].mean()),
                    'avg_profit_per_trade': float(df['avg_profit'].mean()),
                    'total_gas_spent': float(df['total_gas'].sum())
                },
                'risk_metrics': {
                    'value_at_risk': float(var),
                    'max_drawdown': float(max_dd),
                    'sharpe_ratio': float(sharpe)
                },
                'recommendations': self._generate_recommendations(
                    df,
                    var,
                    max_dd,
                    sharpe
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing results: {e}")
            return self._empty_results()

    def _generate_recommendations(
        self,
        results_df: pd.DataFrame,
        var: float,
        max_dd: float,
        sharpe: float
    ) -> List[str]:
        """Generate strategy recommendations."""
        recommendations = []
        
        # Check Sharpe ratio
        if sharpe < self.min_sharpe:
            recommendations.append(
                f"Low Sharpe ratio ({sharpe:.2f}). Consider increasing "
                "minimum profit threshold or reducing gas costs."
            )
        
        # Check maximum drawdown
        if abs(max_dd) > self.max_drawdown:
            recommendations.append(
                f"High maximum drawdown ({max_dd:.2%}). Consider implementing "
                "stricter risk controls or position sizing."
            )
        
        # Check success rate
        mean_success = results_df['success_rate'].mean()
        if mean_success < 0.8:  # 80% target
            recommendations.append(
                f"Low success rate ({mean_success:.2%}). Consider increasing "
                "ML prediction thresholds."
            )
        
        # Check gas efficiency
        avg_profit = results_df['avg_profit'].mean()
        avg_gas = results_df['total_gas'].mean() / results_df['trades_executed'].mean()
        if avg_profit < avg_gas * 3:  # 3x gas cost target
            recommendations.append(
                "Low profit/gas ratio. Consider optimizing gas usage or "
                "focusing on higher-value opportunities."
            )
        
        return recommendations

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            'summary_stats': {
                'mean_roi': 0.0,
                'median_roi': 0.0,
                'roi_std': 0.0,
                'success_rate': 0.0,
                'avg_trades': 0.0,
                'avg_profit_per_trade': 0.0,
                'total_gas_spent': 0.0
            },
            'risk_metrics': {
                'value_at_risk': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0
            },
            'recommendations': ["Insufficient data for analysis"]
        }

    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save simulation results."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.results_dir / f"simulation_{timestamp}.json"
            
            with open(file_path, 'w') as f:
                import json
                json.dump(
                    {
                        'results': results,
                        'parameters': {
                            'num_simulations': self.num_simulations,
                            'time_horizon': self.time_horizon,
                            'volatility_factor': self.volatility_factor,
                            'competition_factor': self.competition_factor,
                            'slippage_factor': self.slippage_factor
                        },
                        'timestamp': timestamp
                    },
                    f,
                    indent=2
                )
                
        except Exception as e:
            logger.error(f"Error saving results: {e}")
