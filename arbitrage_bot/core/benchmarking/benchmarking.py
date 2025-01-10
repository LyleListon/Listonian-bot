"""Benchmarking system for strategy performance analysis."""

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

class BenchmarkResult:
    """Results from a benchmark analysis."""
    
    def __init__(
        self,
        strategy_returns: List[float],
        market_returns: List[float],
        alpha: float,
        beta: float,
        information_ratio: float,
        tracking_error: float,
        correlation: float,
        metrics: Dict[str, Any]
    ):
        """Initialize benchmark result.

        Args:
            strategy_returns: List of strategy returns
            market_returns: List of market returns
            alpha: Strategy alpha (excess return)
            beta: Strategy beta (market sensitivity)
            information_ratio: Risk-adjusted excess return
            tracking_error: Standard deviation of excess returns
            correlation: Strategy-market correlation
            metrics: Additional performance metrics
        """
        self.strategy_returns = strategy_returns
        self.market_returns = market_returns
        self.alpha = alpha
        self.beta = beta
        self.information_ratio = information_ratio
        self.tracking_error = tracking_error
        self.correlation = correlation
        self.metrics = metrics

class BenchmarkingSystem:
    """System for performance benchmarking."""

    def __init__(
        self,
        analytics: AnalyticsSystem,
        market_analyzer: MarketAnalyzer,
        ml_system: MLSystem,
        config: Dict[str, Any]
    ):
        """Initialize benchmarking system.

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
        
        # Results storage
        self.results_dir = Path("benchmark_results")
        self.results_dir.mkdir(exist_ok=True)
        
        logger.info("Benchmarking system initialized")

    def calculate_performance_metrics(
        self,
        strategy_returns: np.ndarray,
        market_returns: np.ndarray,
        risk_free_rate: float = 0.02
    ) -> Dict[str, float]:
        """Calculate performance metrics.

        Args:
            strategy_returns: Strategy return series
            market_returns: Market return series
            risk_free_rate: Annual risk-free rate

        Returns:
            Dictionary of performance metrics
        """
        daily_rf = (1 + risk_free_rate)**(1/252) - 1
        excess_returns = strategy_returns - daily_rf
        market_excess = market_returns - daily_rf
        
        # Calculate alpha and beta
        cov = np.cov(strategy_returns, market_returns)[0, 1]
        market_var = np.var(market_returns)
        beta = cov / market_var if market_var > 0 else 0
        alpha = np.mean(strategy_returns) - beta * np.mean(market_returns)
        
        # Calculate ratios
        sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        sortino = np.mean(excess_returns) / np.std(excess_returns[excess_returns < 0]) * np.sqrt(252)
        
        # Calculate drawdown
        cumulative = np.cumprod(1 + strategy_returns)
        rolling_max = np.maximum.accumulate(cumulative)
        drawdowns = (rolling_max - cumulative) / rolling_max
        max_drawdown = np.max(drawdowns)
        
        # Calculate tracking error
        tracking_diff = strategy_returns - market_returns
        tracking_error = np.std(tracking_diff) * np.sqrt(252)
        
        # Calculate information ratio
        excess_return = np.mean(strategy_returns) - np.mean(market_returns)
        information_ratio = excess_return / tracking_error if tracking_error > 0 else 0
        
        # Calculate correlation
        correlation = np.corrcoef(strategy_returns, market_returns)[0, 1]
        
        return {
            'alpha': alpha,
            'beta': beta,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_drawdown,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'correlation': correlation,
            'annualized_return': np.mean(strategy_returns) * 252,
            'annualized_volatility': np.std(strategy_returns) * np.sqrt(252),
            'win_rate': np.mean(strategy_returns > 0),
            'profit_factor': abs(np.sum(strategy_returns[strategy_returns > 0]) / 
                               np.sum(strategy_returns[strategy_returns < 0]))
                               if np.sum(strategy_returns[strategy_returns < 0]) != 0 else np.inf
        }

    async def analyze_strategy(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        strategy_returns: List[float]
    ) -> BenchmarkResult:
        """Analyze strategy performance against market benchmark.

        Args:
            symbol: Token symbol
            start_date: Analysis start date
            end_date: Analysis end date
            strategy_returns: List of strategy returns

        Returns:
            BenchmarkResult instance with analysis metrics
        """
        try:
            # Get market data from price history
            market_data = []
            price_points = self.market_analyzer.price_history.get(symbol, [])
            
            # Filter points within date range
            start_ts = start_date.timestamp()
            end_ts = end_date.timestamp()
            filtered_points = [p for p in price_points if start_ts <= p.timestamp <= end_ts]
            
            for point in filtered_points:
                market_data.append({
                    'timestamp': datetime.fromtimestamp(point.timestamp),
                    'price': float(point.price)
                })
                
            df = pd.DataFrame(market_data)
            
            # Calculate market returns
            df['market_return'] = df['price'].pct_change()
            market_returns = df['market_return'].dropna().values
            
            # Align return series
            min_len = min(len(strategy_returns), len(market_returns))
            strategy_returns = np.array(strategy_returns[-min_len:])
            market_returns = market_returns[-min_len:]
            
            # Calculate metrics
            metrics = self.calculate_performance_metrics(
                strategy_returns,
                market_returns
            )
            
            result = BenchmarkResult(
                strategy_returns=strategy_returns.tolist(),
                market_returns=market_returns.tolist(),
                alpha=metrics['alpha'],
                beta=metrics['beta'],
                information_ratio=metrics['information_ratio'],
                tracking_error=metrics['tracking_error'],
                correlation=metrics['correlation'],
                metrics=metrics
            )
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_path = self.results_dir / f"benchmark_{symbol}_{timestamp}.json"
            
            with open(result_path, 'w') as f:
                json.dump({
                    'symbol': symbol,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'metrics': metrics,
                    'returns': {
                        'strategy': strategy_returns.tolist(),
                        'market': market_returns.tolist()
                    }
                }, f, indent=2, default=str)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze strategy: {e}")
            raise

    async def compare_strategies(
        self,
        symbol: str,
        strategies: Dict[str, List[float]],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, BenchmarkResult]:
        """Compare multiple strategies.

        Args:
            symbol: Token symbol
            strategies: Dictionary of strategy names and returns
            start_date: Analysis start date
            end_date: Analysis end date

        Returns:
            Dictionary of strategy names and benchmark results
        """
        try:
            results = {}
            
            for name, returns in strategies.items():
                result = await self.analyze_strategy(
                    symbol,
                    start_date,
                    end_date,
                    returns
                )
                results[name] = result
                
            # Save comparison
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_path = self.results_dir / f"comparison_{symbol}_{timestamp}.json"
            
            comparison = {
                'symbol': symbol,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'strategies': {
                    name: {
                        'metrics': result.metrics,
                        'returns': {
                            'strategy': result.strategy_returns,
                            'market': result.market_returns
                        }
                    }
                    for name, result in results.items()
                }
            }
            
            with open(result_path, 'w') as f:
                json.dump(comparison, f, indent=2, default=str)
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to compare strategies: {e}")
            raise

    async def analyze_market_impact(
        self,
        symbol: str,
        trades: List[Dict[str, Any]],
        window_size: int = 10
    ) -> Dict[str, Any]:
        """Analyze market impact of trades.

        Args:
            symbol: Token symbol
            trades: List of trade details
            window_size: Analysis window size (in minutes)

        Returns:
            Dictionary containing market impact analysis
        """
        try:
            # Get market data around trades
            impacts = []
            
            for trade in trades:
                entry_time = datetime.fromtimestamp(trade['entry_time'])
                exit_time = datetime.fromtimestamp(trade['exit_time'])
                
                # Get data before and after trade from price history
                price_points = self.market_analyzer.price_history.get(symbol, [])
                
                # Filter points for before and after trade
                before_start = (entry_time - timedelta(minutes=window_size)).timestamp()
                before_points = [p for p in price_points if before_start <= p.timestamp <= entry_time.timestamp()]
                after_points = [p for p in price_points if exit_time.timestamp() <= p.timestamp <= (exit_time + timedelta(minutes=window_size)).timestamp()]
                
                # Calculate price impact
                before_prices = [float(p.price) for p in before_points]
                after_prices = [float(p.price) for p in after_points]
                
                if before_prices and after_prices:
                    before_avg = np.mean(before_prices)
                    after_avg = np.mean(after_prices)
                    impact = (after_avg - before_avg) / before_avg
                    
                    impacts.append({
                        'entry_time': trade['entry_time'],
                        'exit_time': trade['exit_time'],
                        'size': trade['size'],
                        'impact': impact,
                        'before_price': before_avg,
                        'after_price': after_avg
                    })
                    
            # Calculate aggregate metrics
            if impacts:
                impact_values = [i['impact'] for i in impacts]
                size_values = [i['size'] for i in impacts]
                
                analysis = {
                    'average_impact': np.mean(impact_values),
                    'impact_std': np.std(impact_values),
                    'max_impact': np.max(impact_values),
                    'min_impact': np.min(impact_values),
                    'size_correlation': np.corrcoef(size_values, impact_values)[0, 1],
                    'impacts': impacts
                }
                
            else:
                analysis = {
                    'average_impact': 0.0,
                    'impact_std': 0.0,
                    'max_impact': 0.0,
                    'min_impact': 0.0,
                    'size_correlation': 0.0,
                    'impacts': []
                }
                
            # Save analysis
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_path = self.results_dir / f"impact_{symbol}_{timestamp}.json"
            
            with open(result_path, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
                
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze market impact: {e}")
            raise

async def create_benchmarking_system(
    analytics: AnalyticsSystem,
    market_analyzer: MarketAnalyzer,
    ml_system: MLSystem,
    config: Dict[str, Any]
) -> BenchmarkingSystem:
    """Create benchmarking system."""
    try:
        return BenchmarkingSystem(analytics, market_analyzer, ml_system, config)
    except Exception as e:
        logger.error(f"Failed to create benchmarking system: {e}")
        raise
