"""Gas optimization utilities for efficient transaction execution."""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from ..dex.dex_manager import DexManager
from ..web3.web3_manager import Web3Manager
from ...utils.config_loader import load_config

logger = logging.getLogger(__name__)

class GasOptimizer:
    """Manages gas optimization strategies."""

    def __init__(self, dex_manager: DexManager, web3_manager: Web3Manager):
        """Initialize gas optimizer."""
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager
        self.gas_prices = {}
        self.gas_metrics = {
            'average_gas_used': 0,
            'total_gas_saved': 0,
            'optimization_rate': 0.0,
            'historical_prices': [],
            'dex_gas_usage': {}
        }
        self._lock = asyncio.Lock()
        self._update_lock = asyncio.Lock()
        self.initialized = False
        
        # Load gas settings from config
        config = load_config()
        self.max_priority_fee = config.get('gas', {}).get('max_priority_fee', 5)
        self.max_fee = config.get('gas', {}).get('max_fee', 200)
        self.min_base_fee = config.get('gas', {}).get('min_base_fee', 0.05)
        self.history_window = 86400  # 24 hours
        self.max_history_size = 1000  # Maximum number of historical entries
        
        logger.debug("Gas optimizer initialized")

    async def ensure_web3_connected(self) -> None:
        """Ensure web3 manager is connected."""
        if not hasattr(self.web3_manager, 'w3') or self.web3_manager.w3 is None:
            logger.debug("Connecting web3_manager...")
            await self.web3_manager.connect()

    async def initialize(self) -> bool:
        """Initialize gas optimization system."""
        if self.initialized:
            return True

        async with self._lock:
            if self.initialized:  # Double-check under lock
                return True
                
            try:
                await self.ensure_web3_connected()
                await self._update_gas_prices()
                self.initialized = True
                logger.debug("Gas optimizer initialized successfully")
                return True

            except Exception as e:
                logger.error("Failed to initialize gas optimizer: %s", str(e))
                return False

    async def _cleanup_historical_prices(self) -> None:
        """Clean up old historical prices."""
        current_time = time.time()
        cutoff_time = current_time - self.history_window

        self.gas_metrics['historical_prices'] = [
            price for price in self.gas_metrics['historical_prices']
            if price['timestamp'] > cutoff_time
        ][:self.max_history_size]

    async def _update_gas_prices(self) -> None:
        """Update current gas prices."""
        async with self._update_lock:  # Prevent concurrent updates
            try:
                await self.ensure_web3_connected()

                # Get latest block for base fee
                latest_block = await self.web3_manager.w3.eth.get_block('latest', full_transactions=False)
                base_fee = latest_block['baseFeePerGas']
                base_fee = max(base_fee, int(self.min_base_fee * 1e9))  # Ensure minimum base fee
                
                # Get priority fee
                try:
                    priority_fee = await self.web3_manager.w3.eth.max_priority_fee
                except (AttributeError, ValueError) as e:
                    logger.debug("Could not get max_priority_fee_per_gas: %s", str(e))
                    priority_fee = int(self.max_priority_fee * 1e9)
                    logger.debug("Using default priority fee: %s", priority_fee)

                priority_fee = max(priority_fee, int(0.1 * 1e9))  # Minimum 0.1 Gwei
                
                # Get pending transaction count
                pending_block = await self.web3_manager.w3.eth.get_block('pending', full_transactions=False)
                pending_txs = len(pending_block['transactions'])
                
                # Calculate multipliers based on network congestion
                multipliers = self._calculate_multipliers(pending_txs)
                
                # Calculate gas prices with limits
                max_fee_gwei = int(self.max_fee * 1e9)
                max_priority_gwei = int(self.max_priority_fee * 1e9)

                current_time = time.time()
                
                async with self._lock:
                    # Update gas prices
                    self.gas_prices = {
                        'fast': {
                            'maxFeePerGas': min(int(base_fee * multipliers['fast_base'] + priority_fee * multipliers['priority']), max_fee_gwei),
                            'maxPriorityFeePerGas': min(int(priority_fee * multipliers['priority']), max_priority_gwei)
                        },
                        'standard': {
                            'maxFeePerGas': min(int(base_fee * multipliers['standard_base'] + priority_fee), max_fee_gwei),
                            'maxPriorityFeePerGas': min(priority_fee, max_priority_gwei)
                        },
                        'slow': {
                            'maxFeePerGas': min(int(base_fee * multipliers['slow_base'] + priority_fee), max_fee_gwei),
                            'maxPriorityFeePerGas': priority_fee
                        },
                        'base_fee': base_fee,
                        'priority_fee': priority_fee,
                        'pending_txs': pending_txs,
                        'timestamp': current_time
                    }

                    # Update historical prices
                    self.gas_metrics['historical_prices'].append({
                        'base_fee': base_fee,
                        'priority_fee': priority_fee,
                        'timestamp': current_time
                    })

                    # Cleanup old data
                    await self._cleanup_historical_prices()

                logger.debug("Updated gas prices")

            except Exception as e:
                logger.error("Failed to update gas prices: %s", str(e))
                raise

    def _calculate_multipliers(self, pending_txs: int) -> Dict[str, float]:
        """Calculate gas price multipliers based on network congestion."""
        if pending_txs > 20:  # High congestion
            return {
                'fast_base': 2.0,
                'standard_base': 1.5,
                'slow_base': 1.2,
                'priority': 1.5
            }
        elif pending_txs > 10:  # Medium congestion
            return {
                'fast_base': 1.5,
                'standard_base': 1.3,
                'slow_base': 1.1,
                'priority': 1.2
            }
        else:  # Low congestion
            return {
                'fast_base': 1.3,
                'standard_base': 1.2,
                'slow_base': 1.1,
                'priority': 1.1
            }

    async def optimize_gas(self, tx_params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize gas parameters for a transaction."""
        try:
            await self.ensure_web3_connected()
            await self._update_gas_prices()

            # Get base gas estimate
            base_gas = await self.web3_manager.estimate_gas(tx_params)
            
            async with self._lock:
                pending_txs = self.gas_prices['pending_txs']
                
                # Calculate optimal gas limit with buffer
                gas_limit = int(base_gas * (1.15 if pending_txs > 20 else 1.1 if pending_txs > 10 else 1.05))

                # Select appropriate gas price based on priority
                priority = tx_params.get('priority', 'standard')
                gas_data = self.gas_prices[priority]

                # Update metrics
                dex = tx_params.get('dex')
                if dex:
                    if dex not in self.gas_metrics['dex_gas_usage']:
                        self.gas_metrics['dex_gas_usage'][dex] = {
                            'total_gas': 0,
                            'transaction_count': 0
                        }
                    self.gas_metrics['dex_gas_usage'][dex]['total_gas'] += gas_limit
                    self.gas_metrics['dex_gas_usage'][dex]['transaction_count'] += 1

                # Calculate and update metrics
                await self._update_metrics(base_gas, gas_limit, gas_data['maxFeePerGas'])

                return {
                    'gas': gas_limit,
                    'maxFeePerGas': gas_data['maxFeePerGas'],
                    'maxPriorityFeePerGas': gas_data['maxPriorityFeePerGas']
                }

        except Exception as e:
            logger.error("Failed to optimize gas: %s", str(e))
            return await self._get_safe_gas_params(tx_params)

    async def _update_metrics(self, base_gas: int, gas_limit: int, max_fee: int) -> None:
        """Update gas optimization metrics."""
        standard_cost = base_gas * self.gas_prices['standard']['maxFeePerGas']
        optimized_cost = gas_limit * max_fee
        gas_saved = standard_cost - optimized_cost
        
        self.gas_metrics['total_gas_saved'] += gas_saved

        total_txs = sum(
            dex_data['transaction_count']
            for dex_data in self.gas_metrics['dex_gas_usage'].values()
        )

        if total_txs > 0:
            total_gas = sum(
                dex_data['total_gas']
                for dex_data in self.gas_metrics['dex_gas_usage'].values()
            )
            self.gas_metrics['average_gas_used'] = total_gas / total_txs
            self.gas_metrics['optimization_rate'] = (
                self.gas_metrics['total_gas_saved'] /
                (total_txs * standard_cost)
            )

    async def _get_safe_gas_params(self, tx_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get safe gas parameters when optimization fails."""
        try:
            await self.ensure_web3_connected()
            latest_block = await self.web3_manager.w3.eth.get_block('latest', full_transactions=False)
            base_fee = latest_block['baseFeePerGas']
            
            try:
                priority_fee = await self.web3_manager.w3.eth.max_priority_fee
            except (AttributeError, ValueError):
                priority_fee = int(self.max_priority_fee * 1e9)
            
            priority_fee = max(priority_fee, int(0.1 * 1e9))  # Minimum 0.1 Gwei
            
            return {
                'gas': tx_params.get('gas', 300000),
                'maxFeePerGas': min(base_fee * 2 + priority_fee, int(self.max_fee * 1e9)),
                'maxPriorityFeePerGas': min(priority_fee, int(self.max_priority_fee * 1e9))
            }
        except Exception as e:
            logger.error("Failed to get safe gas params: %s", str(e))
            return {
                'gas': 300000,
                'maxFeePerGas': int(self.max_fee * 1e9),
                'maxPriorityFeePerGas': int(self.max_priority_fee * 1e9)
            }

    async def get_gas_price(self, priority: str = 'standard') -> Dict[str, int]:
        """Get current gas price parameters for given priority level."""
        try:
            await self.ensure_web3_connected()
            await self._update_gas_prices()
            
            async with self._lock:
                gas_data = self.gas_prices.get(priority, self.gas_prices['standard'])
                return {
                    'maxFeePerGas': gas_data['maxFeePerGas'],
                    'maxPriorityFeePerGas': gas_data['maxPriorityFeePerGas'],
                    'baseFee': self.gas_prices['base_fee']
                }
        except Exception as e:
            logger.error("Failed to get gas price: %s", str(e))
            return await self._get_safe_gas_params({})

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current gas metrics."""
        async with self._lock:
            return {
                'gas_prices': self.gas_prices.copy(),
                'metrics': {
                    k: v.copy() if isinstance(v, dict) else v
                    for k, v in self.gas_metrics.items()
                }
            }

async def create_gas_optimizer(dex_manager: DexManager, web3_manager: Web3Manager) -> GasOptimizer:
    """Create and initialize gas optimizer."""
    try:
        optimizer = GasOptimizer(dex_manager, web3_manager)
        if not await optimizer.initialize():
            raise RuntimeError("Failed to initialize gas optimizer")
        logger.debug("Created gas optimizer")
        return optimizer
    except Exception as e:
        logger.error("Failed to create gas optimizer: %s", str(e))
        raise
