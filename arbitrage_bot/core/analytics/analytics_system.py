"""Analytics system for tracking and analyzing trading performance."""

import logging
import asyncio
from ...utils.async_manager import manager
from typing import Dict, Any, Optional, List, Tuple, Set
from decimal import Decimal
from datetime import datetime, timedelta
from ..models.analytics_models import (
    TradeMetrics,
    GasMetrics,
    PerformanceMetrics,
    MarketMetrics
)

logger = logging.getLogger(__name__)

class AnalyticsSystem:
    """Manages analytics and performance tracking."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize analytics system."""
        self.config = config
        self.dex_manager = None
        self.web3_manager = None
        self.wallet_address = None
        self.trade_metrics = {}
        self.gas_metrics = {}
        self.performance_metrics = {}
        self.market_metrics = {}
        
        # Initialize locks for thread safety
        self._trade_lock = asyncio.Lock()
        self._gas_lock = asyncio.Lock()
        self._performance_lock = asyncio.Lock()
        self._market_lock = asyncio.Lock()
        self._init_lock = asyncio.Lock()
        self._initialized = False
        
        logger.debug("Analytics system created")

    async def initialize(self):
        """Initialize analytics system."""
        async with self._init_lock:
            if self._initialized:
                return
            
            self._initialize_metrics()
            self._initialized = True
            logger.debug("Analytics system initialized")

    def set_dex_manager(self, dex_manager: Any):
        """Set the DEX manager instance."""
        self.dex_manager = dex_manager
        # Get web3_manager from dex_manager
        if hasattr(dex_manager, 'web3_manager'):
            self.web3_manager = dex_manager.web3_manager
            self.wallet_address = self.web3_manager.wallet_address
        logger.debug("DEX manager set in analytics system")

    def _initialize_metrics(self):
        """Initialize metrics storage."""
        # Initialize trade metrics
        self.trade_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_volume': Decimal('0'),
            'total_profit': Decimal('0'),
            'average_profit_per_trade': Decimal('0'),
            'success_rate': 0.0,
            'trades_by_pair': {},
            'trades_by_dex': {},
            'profit_by_pair': {},
            'profit_by_dex': {},
            'last_24h': {
                'trades': 0,
                'volume': Decimal('0'),
                'profit': Decimal('0')
            }
        }

        # Initialize gas metrics
        self.gas_metrics = {
            'total_gas_used': 0,
            'total_gas_cost': Decimal('0'),
            'average_gas_per_trade': 0,
            'average_gas_cost': Decimal('0'),
            'gas_by_dex': {},
            'gas_by_pair': {},
            'last_24h': {
                'gas_used': 0,
                'gas_cost': Decimal('0')
            }
        }

        # Initialize performance metrics
        self.performance_metrics = {
            'uptime': 0,
            'total_opportunities': 0,
            'executed_opportunities': 0,
            'missed_opportunities': 0,
            'execution_success_rate': 0.0,
            'average_response_time': 0.0,
            'error_rate': 0.0,
            'errors_by_type': {},
            'last_24h': {
                'opportunities': 0,
                'executions': 0,
                'errors': 0
            }
        }

        # Initialize market metrics
        self.market_metrics = {
            'total_liquidity': {},
            'volume_24h': {},
            'price_volatility': {},
            'spread_by_pair': {},
            'last_update': datetime.now()
        }

    async def update_trade_metrics(self, trade_data: Dict[str, Any]):
        """Update trade-related metrics."""
        try:
            async with self._trade_lock:
                # Extract trade data
                success = trade_data.get('success', False)
                volume = Decimal(str(trade_data.get('volume', 0)))
                profit = Decimal(str(trade_data.get('profit', 0)))
                pair = trade_data.get('pair')
                dex = trade_data.get('dex')

                # Update total metrics
                self.trade_metrics['total_trades'] += 1
                if success:
                    self.trade_metrics['successful_trades'] += 1
                else:
                    self.trade_metrics['failed_trades'] += 1

                self.trade_metrics['total_volume'] += volume
                self.trade_metrics['total_profit'] += profit

                # Update success rate
                total = self.trade_metrics['total_trades']
                if total > 0:
                    self.trade_metrics['success_rate'] = (
                        self.trade_metrics['successful_trades'] / total * 100
                    )

                # Update average profit
                if self.trade_metrics['successful_trades'] > 0:
                    self.trade_metrics['average_profit_per_trade'] = (
                        self.trade_metrics['total_profit'] /
                        self.trade_metrics['successful_trades']
                    )

                # Update pair metrics
                if pair:
                    if pair not in self.trade_metrics['trades_by_pair']:
                        self.trade_metrics['trades_by_pair'][pair] = 0
                        self.trade_metrics['profit_by_pair'][pair] = Decimal('0')
                    self.trade_metrics['trades_by_pair'][pair] += 1
                    self.trade_metrics['profit_by_pair'][pair] += profit

                # Update DEX metrics
                if dex:
                    if dex not in self.trade_metrics['trades_by_dex']:
                        self.trade_metrics['trades_by_dex'][dex] = 0
                        self.trade_metrics['profit_by_dex'][dex] = Decimal('0')
                    self.trade_metrics['trades_by_dex'][dex] += 1
                    self.trade_metrics['profit_by_dex'][dex] += profit

                # Update 24h metrics
                self.trade_metrics['last_24h']['trades'] += 1
                self.trade_metrics['last_24h']['volume'] += volume
                self.trade_metrics['last_24h']['profit'] += profit

                logger.debug("Updated trade metrics: %s", trade_data)

        except Exception as e:
            logger.error("Failed to update trade metrics: %s", str(e))

    async def update_gas_metrics(self, gas_data: Dict[str, Any]):
        """Update gas-related metrics."""
        try:
            async with self._gas_lock:
                # Extract gas data
                gas_used = int(gas_data.get('gas_used', 0))
                gas_cost = Decimal(str(gas_data.get('gas_cost', 0)))
                dex = gas_data.get('dex')
                pair = gas_data.get('pair')

                # Update total metrics
                self.gas_metrics['total_gas_used'] += gas_used
                self.gas_metrics['total_gas_cost'] += gas_cost

                # Update average metrics
                total_trades = self.trade_metrics['total_trades']
                if total_trades > 0:
                    self.gas_metrics['average_gas_per_trade'] = (
                        self.gas_metrics['total_gas_used'] / total_trades
                    )
                    self.gas_metrics['average_gas_cost'] = (
                        self.gas_metrics['total_gas_cost'] / total_trades
                    )

                # Update DEX metrics
                if dex:
                    if dex not in self.gas_metrics['gas_by_dex']:
                        self.gas_metrics['gas_by_dex'][dex] = {
                            'total_gas': 0,
                            'total_cost': Decimal('0')
                        }
                    self.gas_metrics['gas_by_dex'][dex]['total_gas'] += gas_used
                    self.gas_metrics['gas_by_dex'][dex]['total_cost'] += gas_cost

                # Update pair metrics
                if pair:
                    if pair not in self.gas_metrics['gas_by_pair']:
                        self.gas_metrics['gas_by_pair'][pair] = {
                            'total_gas': 0,
                            'total_cost': Decimal('0')
                        }
                    self.gas_metrics['gas_by_pair'][pair]['total_gas'] += gas_used
                    self.gas_metrics['gas_by_pair'][pair]['total_cost'] += gas_cost

                # Update 24h metrics
                self.gas_metrics['last_24h']['gas_used'] += gas_used
                self.gas_metrics['last_24h']['gas_cost'] += gas_cost

                logger.debug("Updated gas metrics: %s", gas_data)

        except Exception as e:
            logger.error("Failed to update gas metrics: %s", str(e))

    async def update_performance_metrics(self, performance_data: Dict[str, Any]):
        """Update performance-related metrics."""
        try:
            async with self._performance_lock:
                # Extract performance data
                opportunities = performance_data.get('opportunities', 0)
                executions = performance_data.get('executions', 0)
                response_time = performance_data.get('response_time', 0.0)
                error = performance_data.get('error')

                # Update total metrics
                self.performance_metrics['total_opportunities'] += opportunities
                self.performance_metrics['executed_opportunities'] += executions
                self.performance_metrics['missed_opportunities'] += (
                    opportunities - executions
                )

                # Update execution success rate
                if self.performance_metrics['total_opportunities'] > 0:
                    self.performance_metrics['execution_success_rate'] = (
                        self.performance_metrics['executed_opportunities'] /
                        self.performance_metrics['total_opportunities'] * 100
                    )

                # Update response time
                current_avg = self.performance_metrics['average_response_time']
                total_ops = self.performance_metrics['executed_opportunities']
                if total_ops > 0:
                    self.performance_metrics['average_response_time'] = (
                        (current_avg * (total_ops - 1) + response_time) / total_ops
                    )

                # Update error metrics
                if error:
                    error_type = error.get('type', 'unknown')
                    if error_type not in self.performance_metrics['errors_by_type']:
                        self.performance_metrics['errors_by_type'][error_type] = 0
                    self.performance_metrics['errors_by_type'][error_type] += 1

                    total_ops = self.performance_metrics['total_opportunities']
                    total_errors = sum(
                        self.performance_metrics['errors_by_type'].values()
                    )
                    if total_ops > 0:
                        self.performance_metrics['error_rate'] = (
                            total_errors / total_ops * 100
                        )

                # Update 24h metrics
                self.performance_metrics['last_24h']['opportunities'] += opportunities
                self.performance_metrics['last_24h']['executions'] += executions
                if error:
                    self.performance_metrics['last_24h']['errors'] += 1

                logger.debug("Updated performance metrics: %s", performance_data)

        except Exception as e:
            logger.error("Failed to update performance metrics: %s", str(e))

    async def update_market_metrics(self, market_data: Dict[str, Any]):
        """Update market-related metrics."""
        try:
            async with self._market_lock:
                # Extract market data
                pair = market_data.get('pair')
                liquidity = Decimal(str(market_data.get('liquidity', 0)))
                volume = Decimal(str(market_data.get('volume', 0)))
                volatility = float(market_data.get('volatility', 0))
                spread = Decimal(str(market_data.get('spread', 0)))

                if pair:
                    # Update liquidity
                    self.market_metrics['total_liquidity'][pair] = liquidity

                    # Update volume
                    self.market_metrics['volume_24h'][pair] = volume

                    # Update volatility
                    self.market_metrics['price_volatility'][pair] = volatility

                    # Update spread
                    self.market_metrics['spread_by_pair'][pair] = spread

                self.market_metrics['last_update'] = datetime.now()

                logger.debug("Updated market metrics: %s", market_data)

        except Exception as e:
            logger.error("Failed to update market metrics: %s", str(e))

    async def get_analytics_summary(self) -> Dict[str, Any]:
        """Get a summary of all analytics metrics."""
        try:
            async with self._trade_lock, self._gas_lock, self._performance_lock, self._market_lock:
                return {
                    'trade_metrics': self.trade_metrics,
                    'gas_metrics': self.gas_metrics,
                    'performance_metrics': self.performance_metrics,
                    'market_metrics': self.market_metrics,
                    'timestamp': datetime.now().timestamp()
                }
        except Exception as e:
            logger.error("Failed to get analytics summary: %s", str(e))
            return {}

    async def get_profit_analysis(self) -> Dict[str, Any]:
        """Get detailed profit analysis."""
        try:
            async with self._trade_lock, self._gas_lock:
                return {
                    'total_profit': self.trade_metrics['total_profit'],
                    'profit_by_pair': self.trade_metrics['profit_by_pair'],
                    'profit_by_dex': self.trade_metrics['profit_by_dex'],
                    'average_profit': self.trade_metrics['average_profit_per_trade'],
                    'gas_impact': self.gas_metrics['total_gas_cost'],
                    'net_profit': (
                        self.trade_metrics['total_profit'] -
                        self.gas_metrics['total_gas_cost']
                    ),
                    'timestamp': datetime.now().timestamp()
                }
        except Exception as e:
            logger.error("Failed to get profit analysis: %s", str(e))
            return {}

    async def get_performance_analysis(self) -> Dict[str, Any]:
        """Get detailed performance analysis."""
        try:
            async with self._trade_lock, self._performance_lock, self._gas_lock:
                return {
                    'success_rate': self.trade_metrics['success_rate'],
                    'execution_rate': self.performance_metrics['execution_success_rate'],
                    'error_rate': self.performance_metrics['error_rate'],
                    'response_time': self.performance_metrics['average_response_time'],
                    'gas_efficiency': {
                        'average_gas': self.gas_metrics['average_gas_per_trade'],
                        'average_cost': self.gas_metrics['average_gas_cost']
                    },
                    'timestamp': datetime.now().timestamp()
                }
        except Exception as e:
            logger.error("Failed to get performance analysis: %s", str(e))
            return {}

    async def get_market_analysis(self) -> Dict[str, Any]:
        """Get detailed market analysis."""
        try:
            async with self._market_lock:
                return {
                    'liquidity': self.market_metrics['total_liquidity'],
                    'volume': self.market_metrics['volume_24h'],
                    'volatility': self.market_metrics['price_volatility'],
                    'spreads': self.market_metrics['spread_by_pair'],
                    'last_update': self.market_metrics['last_update'].timestamp()
                }
        except Exception as e:
            logger.error("Failed to get market analysis: %s", str(e))
            return {}

    async def cleanup_old_metrics(self):
        """Clean up metrics older than 24 hours."""
        try:
            async with self._trade_lock, self._gas_lock, self._performance_lock:
                cutoff = datetime.now() - timedelta(hours=24)

                # Reset 24h metrics
                self.trade_metrics['last_24h'] = {
                    'trades': 0,
                    'volume': Decimal('0'),
                    'profit': Decimal('0')
                }

                self.gas_metrics['last_24h'] = {
                    'gas_used': 0,
                    'gas_cost': Decimal('0')
                }

                self.performance_metrics['last_24h'] = {
                    'opportunities': 0,
                    'executions': 0,
                    'errors': 0
                }

                logger.debug("Cleaned up old metrics")

        except Exception as e:
            logger.error("Failed to cleanup old metrics: %s", str(e))


async def create_analytics_system(config: Dict[str, Any]) -> AnalyticsSystem:
    """Create and initialize analytics system."""
    try:
        analytics = AnalyticsSystem(config)
        await analytics.initialize()
        logger.debug("Created and initialized analytics system")
        return analytics
    except Exception as e:
        logger.error("Failed to create analytics system: %s", str(e))
        raise
