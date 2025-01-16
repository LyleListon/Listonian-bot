"""Analytics system for monitoring and analyzing trading performance."""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from json import JSONEncoder

from ..web3.web3_manager import Web3Manager
from ..execution.trade_executor import TradeExecutor
from ..metrics.portfolio_tracker import PortfolioTracker
from ..gas.gas_optimizer import GasOptimizer
from ...utils.database import Database, DateTimeEncoder

logger = logging.getLogger(__name__)

class AnalyticsSystem:
    """System for analyzing trading performance and market conditions."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        tx_monitor: Any,
        market_analyzer: Any,
        portfolio_tracker: PortfolioTracker,
        gas_optimizer: GasOptimizer,
        config: Dict[str, Any],
        db: Optional[Database] = None
    ):
        """
        Initialize analytics system.

        Args:
            web3_manager: Web3Manager instance
            tx_monitor: Transaction monitor instance
            market_analyzer: Market analyzer instance
            portfolio_tracker: Portfolio tracker instance
            gas_optimizer: Gas optimizer instance
            config: Configuration dictionary
            db: Optional Database instance
        """
        self.web3_manager = web3_manager
        self.tx_monitor = tx_monitor
        self.market_analyzer = market_analyzer
        self.portfolio_tracker = portfolio_tracker
        self.gas_optimizer = gas_optimizer
        self.config = config
        self.db = db if db else Database()
        
        # Initialize analytics
        self.performance_metrics: Dict[str, Any] = {}
        self.market_metrics: Dict[str, Any] = {}
        self.gas_metrics: Dict[str, Any] = {}
        self.risk_metrics: Dict[str, Any] = {}
        
        # WebSocket server reference
        self.websocket_server = None
        
        # Update intervals
        self.update_interval = config.get('analytics', {}).get('update_interval', 60)
        self.history_window = config.get('analytics', {}).get('history_window', 24 * 60 * 60)
        
        # Initialize tracking
        self.start_time = datetime.now()
        self._running = False
        self._update_task = None

    async def initialize(self) -> bool:
        """Initialize analytics system."""
        try:
            # Wait for market analyzer to start
            if not hasattr(self.market_analyzer, '_monitoring_started'):
                await self.market_analyzer.start_monitoring()
                self.market_analyzer._monitoring_started = True
            
            # Wait for initial market data
            start_time = time.time()
            while not self.market_analyzer.market_conditions and time.time() - start_time < 30:
                await asyncio.sleep(1)
            
            if not self.market_analyzer.market_conditions:
                logger.warning("Market analyzer initialized but no data available yet")
            
            # Load historical data
            await self._load_historical_data()
            
            # Start analytics update loop
            self._running = True
            self._update_task = asyncio.create_task(self._update_loop())
            
            # Wait for first metrics update
            await self._update_metrics()
            
            logger.info("Analytics system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics system: {e}")
            return False

    def set_websocket_server(self, server: Any) -> None:
        """Set WebSocket server reference."""
        self.websocket_server = server

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        if not self.performance_metrics:
            # Return default metrics while waiting for data
            return {
                'total_trades': 0,
                'trades_24h': 0,
                'success_rate': 0.0,
                'failed_trades': 0,
                'total_profit_usd': 0.0,
                'profit_24h': 0.0,
                'portfolio_change_24h': 0.0,
                'profit_history': [],
                'volume_history': [],
                'timestamp': datetime.now().isoformat()
            }
        return self.performance_metrics.copy()

    async def get_market_metrics(self) -> Dict[str, Any]:
        """Get current market metrics."""
        return self.market_metrics.copy()

    async def get_gas_metrics(self) -> Dict[str, Any]:
        """Get current gas metrics."""
        return self.gas_metrics.copy()

    async def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        return self.risk_metrics.copy()

    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        def convert_datetime(obj):
            if isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(x) for x in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        metrics = {
            'performance': self.performance_metrics,
            'market': self.market_metrics,
            'gas': self.gas_metrics,
            'risk': self.risk_metrics,
            'timestamp': datetime.now().isoformat()
        }
        return convert_datetime(metrics)

    async def get_historical_metrics(
        self,
        category: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics data.

        Args:
            category: Metrics category
            start_time: Start time for historical data
            end_time: End time for historical data

        Returns:
            List[Dict[str, Any]]: Historical metrics data
        """
        try:
            if not start_time:
                start_time = self.start_time
            if not end_time:
                end_time = datetime.now()
                
            query = {
                "category": category,
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }
            
            metrics = await self.db.get_metrics(query)
            return sorted(metrics, key=lambda x: x['timestamp'])
            
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return []

    async def analyze_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a completed trade.

        Args:
            trade_data: Trade details

        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Get trade metrics
            gas_cost = int(trade_data['gas_used']) * int(trade_data['gas_price'])
            profit = (
                int(trade_data['amount_out']) -
                int(trade_data['amount_in']) -
                gas_cost
            )
            
            # Calculate metrics
            analysis = {
                'profit': profit,
                'gas_cost': gas_cost,
                'gas_efficiency': profit / gas_cost if gas_cost > 0 else 0,
                'execution_time': (
                    trade_data['completion_time'] -
                    trade_data['start_time']
                ).total_seconds(),
                'slippage': (
                    (int(trade_data['expected_out']) - int(trade_data['amount_out'])) /
                    int(trade_data['expected_out'])
                ) if int(trade_data['expected_out']) > 0 else 0
            }
            
            # Save analysis
            trade_data['analysis'] = analysis
            await self.db.update_trade(trade_data['id'], trade_data)
            
            # Update metrics
            await self._update_metrics()
            
            # Broadcast update if WebSocket server available
            if self.websocket_server:
                await self.websocket_server.broadcast_trade(trade_data)
                
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze trade: {e}")
            return {}

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            self._running = False
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
                
            logger.info("Analytics system cleaned up")
            
        except Exception as e:
            logger.error(f"Error during analytics system cleanup: {e}")

    async def _update_loop(self) -> None:
        """Background analytics update loop."""
        while self._running:
            try:
                # Update all metrics
                await self._update_metrics()
                
                # Save snapshot
                await self._save_metrics_snapshot()
                
                # Broadcast update if WebSocket server available
                if self.websocket_server:
                    await self.websocket_server.broadcast_metrics(
                        await self.get_all_metrics()
                    )
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics update loop: {e}")
                await asyncio.sleep(self.update_interval)

    async def _update_metrics(self) -> None:
        """Update all metrics."""
        try:
            # Get performance metrics
            self.performance_metrics = await self.portfolio_tracker.get_performance_metrics()
            
            # Get market metrics from analyzer
            try:
                # Ensure market analyzer is monitoring
                if not hasattr(self.market_analyzer, '_monitoring_started'):
                    await self.market_analyzer.start_monitoring()
                    self.market_analyzer._monitoring_started = True
                
                # First try get_market_metrics for detailed metrics
                if hasattr(self.market_analyzer, 'get_market_metrics'):
                    metrics = await self.market_analyzer.get_market_metrics()
                    if metrics:
                        self.market_metrics = metrics
                    else:
                        # Provide default metrics while waiting for data
                        self.market_metrics = {
                            'WETH': {
                                'price': 0.0,
                                'volume_24h': 0.0,
                                'liquidity': 0.0,
                                'volatility': 0.0,
                                'trend': {
                                    'direction': 'sideways',
                                    'strength': 0.0,
                                    'confidence': 0.0
                                }
                            },
                            'USDC': {
                                'price': 1.0,
                                'volume_24h': 0.0,
                                'liquidity': 0.0,
                                'volatility': 0.0,
                                'trend': {
                                    'direction': 'sideways',
                                    'strength': 0.0,
                                    'confidence': 0.0
                                }
                            }
                        }
                
                # Fall back to get_metrics for basic metrics
                elif hasattr(self.market_analyzer, 'get_metrics'):
                    metrics = await self.market_analyzer.get_metrics()
                    market_condition = await self.market_analyzer.get_market_condition()
                    
                    # Convert basic metrics to market metrics format
                    self.market_metrics = {
                        'system_metrics': metrics or {},
                        'market_conditions': market_condition or {
                            'trend': 'sideways',
                            'volatility': 0.0,
                            'volume': 0.0,
                            'liquidity': 0.0
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                    
                else:
                    raise AttributeError("Market analyzer has no metrics methods available")
                    
            except Exception as e:
                if isinstance(e, AttributeError):
                    logger.error(f"Market analyzer configuration error: {e}")
                else:
                    logger.warning(f"Failed to get market metrics: {e}")
                # Provide default metrics on error
                if not self.market_metrics:
                    self.market_metrics = {
                        'system_metrics': {},
                        'market_conditions': {
                            'trend': 'sideways',
                            'volatility': 0.0,
                            'volume': 0.0,
                            'liquidity': 0.0
                        },
                        'timestamp': datetime.now().isoformat()
                    }
            
            # Get gas metrics
            gas_analysis = await self.gas_optimizer.analyze_gas_usage()
            self.gas_metrics = {
                'current_gas_price': gas_analysis['current_gas_price'],
                'dex_stats': gas_analysis['dex_stats'],
                'protocol_stats': gas_analysis['protocol_stats'],
                'recommendations': gas_analysis['recommendations']
            }
            
            # Calculate risk metrics
            self.risk_metrics = await self._calculate_risk_metrics()
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def _calculate_risk_metrics(self) -> Dict[str, Any]:
        """Calculate current risk metrics."""
        try:
            # Get recent trades
            trades = await self.portfolio_tracker.get_trade_history(
                start_time=datetime.now() - timedelta(hours=24)
            )
            
            if not trades:
                return {}
                
            # Calculate metrics
            total_value = sum(float(t['amount_in']) for t in trades)
            failed_trades = len([t for t in trades if t['status'] != 'completed'])
            
            return {
                'failure_rate': failed_trades / len(trades),
                'avg_trade_value': total_value / len(trades),
                'max_trade_value': max(float(t['amount_in']) for t in trades),
                'active_pairs': len(set(
                    (t['token_in'], t['token_out'])
                    for t in trades
                )),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate risk metrics: {e}")
            return {}

    async def _save_metrics_snapshot(self) -> None:
        """Save current metrics to database."""
        try:
            # Convert all metrics to JSON-serializable format
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'performance': json.loads(json.dumps(self.performance_metrics, cls=DateTimeEncoder)),
                'market': json.loads(json.dumps(self.market_metrics, cls=DateTimeEncoder)),
                'gas': json.loads(json.dumps(self.gas_metrics, cls=DateTimeEncoder)),
                'risk': json.loads(json.dumps(self.risk_metrics, cls=DateTimeEncoder))
            }
            
            # Save metrics
            await self.db.save_metrics(snapshot)
            
        except Exception as e:
            logger.error(f"Failed to save metrics snapshot: {e}")

    async def _load_historical_data(self) -> None:
        """Load historical metrics data."""
        try:
            # Get recent metrics
            start_time = datetime.now() - timedelta(seconds=self.history_window)
            metrics = await self.get_historical_metrics('all', start_time)
            
            if metrics:
                # Use most recent snapshot
                latest = metrics[-1]
                self.performance_metrics = latest.get('performance', {})
                self.market_metrics = latest.get('market', {})
                self.gas_metrics = latest.get('gas', {})
                self.risk_metrics = latest.get('risk', {})
                
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")


async def create_analytics_system(
    web3_manager: Web3Manager,
    tx_monitor: Any,
    market_analyzer: Any,
    portfolio_tracker: PortfolioTracker,
    gas_optimizer: GasOptimizer,
    config: Dict[str, Any],
    db: Optional[Database] = None
) -> Optional[AnalyticsSystem]:
    """
    Create analytics system instance.

    Args:
        web3_manager: Web3Manager instance
        tx_monitor: Transaction monitor instance
        market_analyzer: Market analyzer instance
        portfolio_tracker: Portfolio tracker instance
        gas_optimizer: Gas optimizer instance
        config: Configuration dictionary
        db: Optional Database instance

    Returns:
        Optional[AnalyticsSystem]: Analytics system instance
    """
    try:
        system = AnalyticsSystem(
            web3_manager=web3_manager,
            tx_monitor=tx_monitor,
            market_analyzer=market_analyzer,
            portfolio_tracker=portfolio_tracker,
            gas_optimizer=gas_optimizer,
            config=config,
            db=db
        )
        
        success = await system.initialize()
        if not success:
            raise ValueError("Failed to initialize analytics system")
            
        return system
        
    except Exception as e:
        logger.error(f"Failed to create analytics system: {e}")
        return None
