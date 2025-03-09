"""Backtesting system for strategy validation and optimization."""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import json
from ..analytics.analytics_system import AnalyticsSystem
from ..analysis.market_analyzer import MarketAnalyzer
from ..ml.ml_system import MLSystem

logger = logging.getLogger(__name__)

class BacktestResult:
    """Results from a backtest run."""
    
    def __init__(
        self,
        total_trades: int,
        successful_trades: int,
        total_profit_usd: Decimal,
        total_gas_cost_eth: Decimal,
        max_drawdown: Decimal,
        sharpe_ratio: float,
        win_rate: float,
        avg_profit_per_trade: Decimal,
        avg_gas_per_trade: Decimal,
        roi: float,
        trades: List[Dict[str, Any]]
    ):
        """Initialize backtest result.

        Args:
            total_trades: Total number of trades executed
            successful_trades: Number of profitable trades
            total_profit_usd: Total profit in USD
            total_gas_cost_eth: Total gas cost in ETH
            max_drawdown: Maximum drawdown percentage
            sharpe_ratio: Sharpe ratio of returns
            win_rate: Percentage of profitable trades
            avg_profit_per_trade: Average profit per trade in USD
            avg_gas_per_trade: Average gas cost per trade in ETH
            roi: Return on investment percentage
            trades: List of individual trade details
        """
        self.total_trades = total_trades
        self.successful_trades = successful_trades
        self.total_profit_usd = total_profit_usd
        self.total_gas_cost_eth = total_gas_cost_eth
        self.max_drawdown = max_drawdown
        self.sharpe_ratio = sharpe_ratio
        self.win_rate = win_rate
        self.avg_profit_per_trade = avg_profit_per_trade
        self.avg_gas_per_trade = avg_gas_per_trade
        self.roi = roi
        self.trades = trades

class BacktestingSystem:
    """System for backtesting trading strategies."""

    def __init__(
        self,
        analytics: AnalyticsSystem,
        market_analyzer: MarketAnalyzer,
        ml_system: MLSystem,
        config: Dict[str, Any]
    ):
        """Initialize backtesting system.

        Args:
            analytics: Analytics system instance
            market_analyzer: Market analyzer instance
            ml_system: ML system instance
            config: Configuration dictionary
        """
        self.analytics = analytics
        self.market_analyzer = market_analyzer
        self.ml_system = ml_system
        self.config = config
        
        # Historical data storage
        self.data_dir = Path("historical_data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Results storage
        self.results_dir = Path("backtest_results")
        self.results_dir.mkdir(exist_ok=True)
        
        logger.info("Backtesting system initialized")

    async def collect_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Collect historical market data.

        Args:
            symbol: Token symbol
            start_date: Start date for data collection
            end_date: End date for data collection

        Returns:
            DataFrame containing historical data
        """
        try:
            # Get historical data from market analyzer
            market_data = []
            metrics = self.market_analyzer.get_market_history(
                symbol,
                start_time=start_date.timestamp(),
                end_time=end_date.timestamp()
            )
            
            for m in metrics:
                market_data.append({
                    'timestamp': datetime.fromtimestamp(m.timestamp),
                    'price': float(m.price),
                    'volume': float(m.volume_24h),
                    'liquidity': float(m.liquidity),
                    'volatility': float(m.volatility),
                    'trend_strength': float(m.trend.strength),
                    'trend_direction': m.trend.direction
                })
                
            df = pd.DataFrame(market_data)
            
            # Save to file
            file_path = self.data_dir / f"{symbol}_{start_date.date()}_{end_date.date()}.csv"
            df.to_csv(file_path, index=False)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to collect historical data: {e}")
            raise

    def calculate_metrics(
        self,
        trades: List[Dict[str, Any]],
        initial_balance: Decimal
    ) -> BacktestResult:
        """Calculate performance metrics from trades.

        Args:
            trades: List of trade details
            initial_balance: Initial portfolio balance in USD

        Returns:
            BacktestResult instance with calculated metrics
        """
        try:
            if not trades:
                return BacktestResult(
                    total_trades=0,
                    successful_trades=0,
                    total_profit_usd=Decimal("0"),
                    total_gas_cost_eth=Decimal("0"),
                    max_drawdown=Decimal("0"),
                    sharpe_ratio=0.0,
                    win_rate=0.0,
                    avg_profit_per_trade=Decimal("0"),
                    avg_gas_per_trade=Decimal("0"),
                    roi=0.0,
                    trades=[]
                )
                
            # Calculate basic metrics
            total_trades = len(trades)
            successful_trades = sum(1 for t in trades if t['profit_usd'] > 0)
            total_profit = sum(Decimal(str(t['profit_usd'])) for t in trades)
            total_gas = sum(Decimal(str(t['gas_cost_eth'])) for t in trades)
            
            # Calculate returns
            returns = [float(t['profit_usd']) / float(initial_balance) for t in trades]
            
            # Calculate Sharpe ratio (assuming risk-free rate of 0)
            if len(returns) > 1:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(365)  # Annualized
            else:
                sharpe = 0.0
                
            # Calculate drawdown
            cumulative_returns = np.cumsum(returns)
            rolling_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (rolling_max - cumulative_returns) / rolling_max
            max_drawdown = Decimal(str(np.max(drawdowns)))
            
            # Calculate averages
            avg_profit = total_profit / Decimal(total_trades) if total_trades > 0 else Decimal("0")
            avg_gas = total_gas / Decimal(total_trades) if total_trades > 0 else Decimal("0")
            
            # Calculate ROI
            roi = float(total_profit) / float(initial_balance) if initial_balance > 0 else 0.0
            
            return BacktestResult(
                total_trades=total_trades,
                successful_trades=successful_trades,
                total_profit_usd=total_profit,
                total_gas_cost_eth=total_gas,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe,
                win_rate=successful_trades / total_trades if total_trades > 0 else 0.0,
                avg_profit_per_trade=avg_profit,
                avg_gas_per_trade=avg_gas,
                roi=roi,
                trades=trades
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate metrics: {e}")
            raise

    async def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_balance: Decimal,
        strategy_params: Dict[str, Any]
    ) -> BacktestResult:
        """Run backtest simulation.

        Args:
            symbol: Token symbol
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_balance: Initial portfolio balance in USD
            strategy_params: Strategy parameters

        Returns:
            BacktestResult instance with performance metrics
        """
        try:
            # Get historical data
            df = await self.collect_historical_data(symbol, start_date, end_date)
            
            # Initialize simulation state
            balance = initial_balance
            trades = []
            position = None
            
            # Run simulation
            for i in range(len(df) - 1):
                current_data = df.iloc[i]
                next_data = df.iloc[i + 1]
                
                # Get ML predictions
                predictions = await self.ml_system.predict_price(symbol)
                patterns = await self.ml_system.detect_patterns(symbol)
                risk_score = await self.ml_system.calculate_risk_score(symbol)
                
                # Apply strategy rules
                should_enter = (
                    risk_score < strategy_params.get('max_risk', 0.7) and
                    patterns['confidence'] > strategy_params.get('min_confidence', 0.6) and
                    predictions[0] > float(current_data['price']) * (1 + strategy_params.get('min_profit', 0.01))
                )
                
                should_exit = (
                    position and (
                        float(next_data['price']) < position['entry_price'] * (1 - strategy_params.get('stop_loss', 0.02)) or
                        float(next_data['price']) > position['entry_price'] * (1 + strategy_params.get('take_profit', 0.03))
                    )
                )
                
                # Execute trades
                if should_enter and not position:
                    # Enter position
                    position = {
                        'entry_time': current_data['timestamp'],
                        'entry_price': float(current_data['price']),
                        'size': float(strategy_params.get('position_size', 0.1) * balance)
                    }
                    
                elif should_exit and position:
                    # Exit position
                    exit_price = float(next_data['price'])
                    profit = (exit_price - position['entry_price']) * position['size']
                    gas_cost = Decimal("0.001")  # Estimated gas cost
                    
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': next_data['timestamp'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'profit_usd': Decimal(str(profit)),
                        'gas_cost_eth': gas_cost,
                        'success': profit > 0
                    })
                    
                    # Update balance
                    balance += Decimal(str(profit)) - (gas_cost * Decimal("2000"))  # Assuming ETH price of $2000
                    position = None
                    
            # Calculate metrics
            result = self.calculate_metrics(trades, initial_balance)
            
            # Save results
            result_path = self.results_dir / f"backtest_{symbol}_{start_date.date()}_{end_date.date()}.json"
            with open(result_path, 'w') as f:
                json.dump({
                    'symbol': symbol,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'initial_balance': str(initial_balance),
                    'strategy_params': strategy_params,
                    'metrics': {
                        'total_trades': result.total_trades,
                        'successful_trades': result.successful_trades,
                        'total_profit_usd': str(result.total_profit_usd),
                        'total_gas_cost_eth': str(result.total_gas_cost_eth),
                        'max_drawdown': str(result.max_drawdown),
                        'sharpe_ratio': result.sharpe_ratio,
                        'win_rate': result.win_rate,
                        'avg_profit_per_trade': str(result.avg_profit_per_trade),
                        'avg_gas_per_trade': str(result.avg_gas_per_trade),
                        'roi': result.roi
                    },
                    'trades': trades
                }, f, indent=2, default=str)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to run backtest: {e}")
            raise

    async def optimize_strategy(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_balance: Decimal,
        param_ranges: Dict[str, Tuple[float, float, float]]
    ) -> Dict[str, Any]:
        """Optimize strategy parameters.

        Args:
            symbol: Token symbol
            start_date: Start date for optimization
            end_date: End date for optimization
            initial_balance: Initial portfolio balance in USD
            param_ranges: Dictionary of parameter ranges (min, max, step)

        Returns:
            Dictionary containing optimal parameters
        """
        try:
            best_result = None
            best_params = None
            best_roi = float('-inf')
            
            # Generate parameter combinations
            param_combinations = []
            for param, (min_val, max_val, step) in param_ranges.items():
                values = np.arange(min_val, max_val + step, step)
                param_combinations.append([(param, val) for val in values])
                
            # Test each combination
            from itertools import product
            for params in product(*param_combinations):
                strategy_params = dict(params)
                
                # Run backtest
                result = await self.run_backtest(
                    symbol,
                    start_date,
                    end_date,
                    initial_balance,
                    strategy_params
                )
                
                # Update best result
                if result.roi > best_roi:
                    best_roi = result.roi
                    best_result = result
                    best_params = strategy_params
                    
            # Save optimization results
            result_path = self.results_dir / f"optimization_{symbol}_{start_date.date()}_{end_date.date()}.json"
            with open(result_path, 'w') as f:
                json.dump({
                    'symbol': symbol,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'initial_balance': str(initial_balance),
                    'param_ranges': {k: list(v) for k, v in param_ranges.items()},
                    'best_params': best_params,
                    'best_metrics': {
                        'total_trades': best_result.total_trades,
                        'successful_trades': best_result.successful_trades,
                        'total_profit_usd': str(best_result.total_profit_usd),
                        'total_gas_cost_eth': str(best_result.total_gas_cost_eth),
                        'max_drawdown': str(best_result.max_drawdown),
                        'sharpe_ratio': best_result.sharpe_ratio,
                        'win_rate': best_result.win_rate,
                        'avg_profit_per_trade': str(best_result.avg_profit_per_trade),
                        'avg_gas_per_trade': str(best_result.avg_gas_per_trade),
                        'roi': best_result.roi
                    }
                }, f, indent=2, default=str)
                
            return best_params
            
        except Exception as e:
            logger.error(f"Failed to optimize strategy: {e}")
            raise

async def create_backtesting_system(
    analytics: AnalyticsSystem,
    market_analyzer: MarketAnalyzer,
    ml_system: MLSystem,
    config: Dict[str, Any]
) -> BacktestingSystem:
    """Create backtesting system."""
    try:
        return BacktestingSystem(analytics, market_analyzer, ml_system, config)
    except Exception as e:
        logger.error(f"Failed to create backtesting system: {e}")
        raise
