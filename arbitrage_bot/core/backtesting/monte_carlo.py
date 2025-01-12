"""Monte Carlo simulation system for backtesting and risk analysis."""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path

from ..analytics.analytics_system import AnalyticsSystem
from ..ml.ml_system import MLSystem
from ...utils.database import Database

logger = logging.getLogger(__name__)

class MonteCarloSystem:
    """Monte Carlo simulation system for strategy analysis."""

    def __init__(
        self,
        analytics: AnalyticsSystem,
        market_analyzer: Any,
        ml_system: MLSystem,
        config: Dict[str, Any],
        db: Optional[Database] = None,
        simulations_dir: str = "simulations"
    ):
        """
        Initialize Monte Carlo system.

        Args:
            analytics: Analytics system instance
            market_analyzer: Market analyzer instance
            ml_system: ML system instance
            config: Configuration dictionary
            db: Optional Database instance
            simulations_dir: Directory for saving simulation results
        """
        self.analytics = analytics
        self.market_analyzer = market_analyzer
        self.ml_system = ml_system
        self.config = config
        self.db = db if db else Database()
        self.simulations_dir = Path(simulations_dir)
        self.simulations_dir.mkdir(exist_ok=True)
        
        # Simulation settings
        self.num_simulations = config.get('monte_carlo', {}).get('num_simulations', 1000)
        self.time_horizon = config.get('monte_carlo', {}).get('time_horizon', 30)  # days
        self.confidence_level = config.get('monte_carlo', {}).get('confidence_level', 0.95)
        
        # Results storage
        self.simulation_results: Dict[str, Any] = {}
        self.risk_metrics: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize Monte Carlo system."""
        try:
            # Load historical data
            await self._load_historical_data()
            
            # Run initial simulations
            await self.run_simulations()
            
            logger.info("Monte Carlo system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Monte Carlo system: {e}")
            return False

    async def run_simulations(self) -> Dict[str, Any]:
        """Run Monte Carlo simulations."""
        try:
            # Get historical data
            trades = await self.db.get_trades({})
            if not trades:
                return {}
                
            # Calculate historical metrics
            returns = self._calculate_returns(trades)
            volatility = np.std(returns)
            mean_return = np.mean(returns)
            
            # Run simulations
            paths = []
            initial_value = 1000.0  # Starting with $1000
            
            for _ in range(self.num_simulations):
                path = [initial_value]
                current_value = initial_value
                
                for _ in range(self.time_horizon * 24):  # Hourly simulations
                    # Generate random return using historical distribution
                    daily_return = np.random.normal(mean_return, volatility)
                    current_value *= (1 + daily_return)
                    path.append(current_value)
                
                paths.append(path)
            
            # Calculate metrics
            paths_array = np.array(paths)
            final_values = paths_array[:, -1]
            
            self.simulation_results = {
                'paths': paths,
                'metrics': {
                    'mean_final_value': float(np.mean(final_values)),
                    'std_final_value': float(np.std(final_values)),
                    'max_final_value': float(np.max(final_values)),
                    'min_final_value': float(np.min(final_values)),
                    'var_95': float(np.percentile(final_values, 5)),
                    'expected_shortfall': float(np.mean(
                        final_values[final_values < np.percentile(final_values, 5)]
                    ))
                }
            }
            
            # Update risk metrics
            await self._update_risk_metrics()
            
            # Save results
            await self._save_simulation_results()
            
            return self.simulation_results
            
        except Exception as e:
            logger.error(f"Error running simulations: {e}")
            return {}

    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        return self.risk_metrics.copy()

    async def analyze_strategy(
        self,
        strategy_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze trading strategy using Monte Carlo simulations.

        Args:
            strategy_params: Strategy parameters to analyze

        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Get historical performance with strategy
            trades = await self._simulate_strategy_trades(strategy_params)
            if not trades:
                return {}
                
            # Run simulations with strategy
            returns = self._calculate_returns(trades)
            volatility = np.std(returns)
            mean_return = np.mean(returns)
            
            paths = []
            initial_value = 1000.0
            
            for _ in range(self.num_simulations):
                path = [initial_value]
                current_value = initial_value
                
                for _ in range(self.time_horizon * 24):
                    # Apply strategy constraints
                    max_trade_size = strategy_params.get('max_trade_size', current_value * 0.1)
                    min_profit_threshold = strategy_params.get('min_profit_threshold', 0.001)
                    
                    # Generate return with strategy constraints
                    trade_return = np.random.normal(mean_return, volatility)
                    if abs(trade_return) > min_profit_threshold:
                        trade_size = min(max_trade_size, current_value * 0.1)
                        current_value += trade_size * trade_return
                    
                    path.append(current_value)
                
                paths.append(path)
            
            # Calculate strategy metrics
            paths_array = np.array(paths)
            final_values = paths_array[:, -1]
            
            return {
                'expected_return': float(np.mean(final_values) / initial_value - 1),
                'volatility': float(np.std(final_values) / initial_value),
                'sharpe_ratio': float(
                    (np.mean(final_values) - initial_value) /
                    (np.std(final_values) + 1e-10)
                ),
                'max_drawdown': float(self._calculate_max_drawdown(paths_array)),
                'success_rate': float(np.mean(final_values > initial_value)),
                'var_95': float(np.percentile(final_values, 5)),
                'expected_shortfall': float(np.mean(
                    final_values[final_values < np.percentile(final_values, 5)]
                ))
            }
            
        except Exception as e:
            logger.error(f"Error analyzing strategy: {e}")
            return {}

    async def optimize_parameters(
        self,
        param_ranges: Dict[str, Tuple[float, float]],
        num_iterations: int = 100
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters using Monte Carlo simulations.

        Args:
            param_ranges: Dictionary of parameter ranges to optimize
            num_iterations: Number of optimization iterations

        Returns:
            Dict[str, Any]: Optimal parameters and performance metrics
        """
        try:
            best_params = {}
            best_performance = float('-inf')
            
            for _ in range(num_iterations):
                # Generate random parameters within ranges
                params = {
                    name: np.random.uniform(low, high)
                    for name, (low, high) in param_ranges.items()
                }
                
                # Analyze strategy with parameters
                results = await self.analyze_strategy(params)
                if not results:
                    continue
                
                # Calculate performance score
                performance = (
                    results['expected_return'] * 0.4 +
                    results['sharpe_ratio'] * 0.3 +
                    (1 - results['max_drawdown']) * 0.2 +
                    results['success_rate'] * 0.1
                )
                
                if performance > best_performance:
                    best_performance = performance
                    best_params = params
            
            # Run final analysis with best parameters
            final_results = await self.analyze_strategy(best_params)
            
            return {
                'optimal_params': best_params,
                'performance_metrics': final_results
            }
            
        except Exception as e:
            logger.error(f"Error optimizing parameters: {e}")
            return {}

    def _calculate_returns(self, trades: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate returns from trades."""
        try:
            if not trades:
                return np.array([])
                
            returns = []
            for trade in trades:
                if trade['status'] == 'completed':
                    profit = float(trade.get('profit', 0))
                    value = float(trade.get('value', 0))
                    if value > 0:
                        returns.append(profit / value)
            
            return np.array(returns)
            
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return np.array([])

    def _calculate_max_drawdown(self, paths: np.ndarray) -> float:
        """Calculate maximum drawdown from paths."""
        try:
            max_drawdown = 0
            for path in paths:
                peaks = np.maximum.accumulate(path)
                drawdowns = (peaks - path) / peaks
                max_drawdown = max(max_drawdown, np.max(drawdowns))
            return max_drawdown
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 1.0

    async def _simulate_strategy_trades(
        self,
        strategy_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Simulate trades with strategy parameters."""
        try:
            # Get historical market data
            market_data = await self.market_analyzer.get_historical_data(
                days=self.time_horizon
            )
            
            simulated_trades = []
            portfolio_value = 1000.0  # Initial value
            
            for timestamp, data in market_data.items():
                # Check strategy conditions
                if await self._check_strategy_conditions(data, strategy_params):
                    # Simulate trade
                    trade_size = min(
                        portfolio_value * strategy_params.get('position_size', 0.1),
                        strategy_params.get('max_trade_size', float('inf'))
                    )
                    
                    # Predict trade outcome
                    success_prob, _ = await self.ml_system.predict_trade_success({
                        'market_volatility': data['volatility'],
                        'competition_rate': data['competition_rate'],
                        'gas_price': data['gas_price']
                    })
                    
                    if success_prob > strategy_params.get('min_success_prob', 0.5):
                        # Simulate trade outcome
                        profit = trade_size * (
                            np.random.normal(
                                data['expected_return'],
                                data['volatility']
                            )
                        )
                        
                        simulated_trades.append({
                            'timestamp': timestamp,
                            'value': trade_size,
                            'profit': profit,
                            'status': 'completed' if profit > 0 else 'failed'
                        })
                        
                        portfolio_value += profit
            
            return simulated_trades
            
        except Exception as e:
            logger.error(f"Error simulating strategy trades: {e}")
            return []

    async def _check_strategy_conditions(
        self,
        market_data: Dict[str, Any],
        strategy_params: Dict[str, Any]
    ) -> bool:
        """Check if strategy conditions are met."""
        try:
            # Check volatility conditions
            if market_data['volatility'] > strategy_params.get('max_volatility', float('inf')):
                return False
                
            # Check competition conditions
            if market_data['competition_rate'] > strategy_params.get('max_competition', float('inf')):
                return False
                
            # Check gas price conditions
            if market_data['gas_price'] > strategy_params.get('max_gas_price', float('inf')):
                return False
                
            # Check minimum profit potential
            if market_data['expected_return'] < strategy_params.get('min_return', float('-inf')):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking strategy conditions: {e}")
            return False

    async def _update_risk_metrics(self) -> None:
        """Update risk metrics from simulation results."""
        try:
            if not self.simulation_results:
                return
                
            metrics = self.simulation_results['metrics']
            paths = np.array(self.simulation_results['paths'])
            
            # Calculate additional risk metrics
            self.risk_metrics = {
                'value_at_risk': metrics['var_95'],
                'expected_shortfall': metrics['expected_shortfall'],
                'volatility': float(np.std(paths[:, -1])),
                'skewness': float(stats.skew(paths[:, -1])),
                'kurtosis': float(stats.kurtosis(paths[:, -1])),
                'max_drawdown': float(self._calculate_max_drawdown(paths)),
                'success_rate': float(np.mean(paths[:, -1] > paths[:, 0])),
                'sharpe_ratio': float(
                    (np.mean(paths[:, -1]) - paths[0, 0]) /
                    (np.std(paths[:, -1]) + 1e-10)
                )
            }
            
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")

    async def _save_simulation_results(self) -> None:
        """Save simulation results to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.simulations_dir / f"simulation_{timestamp}.json"
            
            results = {
                'timestamp': datetime.now().isoformat(),
                'parameters': {
                    'num_simulations': self.num_simulations,
                    'time_horizon': self.time_horizon,
                    'confidence_level': self.confidence_level
                },
                'metrics': self.simulation_results['metrics'],
                'risk_metrics': self.risk_metrics
            }
            
            # Save results as JSON
            import json
            with open(file_path, 'w') as f:
                json.dump(results, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving simulation results: {e}")

    async def _load_historical_data(self) -> None:
        """Load historical simulation results."""
        try:
            files = list(self.simulations_dir.glob("simulation_*.json"))
            if not files:
                return
                
            # Load most recent simulation
            latest_file = max(files, key=lambda p: p.stat().st_mtime)
            
            import json
            with open(latest_file, 'r') as f:
                data = json.load(f)
                
            self.risk_metrics = data.get('risk_metrics', {})
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")


async def create_monte_carlo_system(
    analytics: AnalyticsSystem,
    market_analyzer: Any,
    ml_system: MLSystem,
    config: Dict[str, Any],
    db: Optional[Database] = None
) -> Optional[MonteCarloSystem]:
    """
    Create Monte Carlo system instance.

    Args:
        analytics: Analytics system instance
        market_analyzer: Market analyzer instance
        ml_system: ML system instance
        config: Configuration dictionary
        db: Optional Database instance

    Returns:
        Optional[MonteCarloSystem]: Monte Carlo system instance
    """
    try:
        system = MonteCarloSystem(
            analytics=analytics,
            market_analyzer=market_analyzer,
            ml_system=ml_system,
            config=config,
            db=db
        )
        
        success = await system.initialize()
        if not success:
            raise ValueError("Failed to initialize Monte Carlo system")
            
        return system
        
    except Exception as e:
        logger.error(f"Failed to create Monte Carlo system: {e}")
        return None
