"""Gas optimization utilities for efficient transaction execution."""

import logging
import time
from typing import Dict, Any, Optional
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
        self.gas_metrics = {}
        
        # Initialize gas metrics
        self.gas_metrics = {
            'average_gas_used': 0,
            'total_gas_saved': 0,
            'optimization_rate': 0.0,
            'historical_prices': [],
            'dex_gas_usage': {}
        }
        self.initialized = False
        
        # Load gas settings from config
        config = load_config()
        self.max_priority_fee = config.get('gas', {}).get('max_priority_fee', 5)
        self.max_fee = config.get('gas', {}).get('max_fee', 200)
        self.min_base_fee = config.get('gas', {}).get('min_base_fee', 0.05)
        
        logger.debug("Gas optimizer initialized")

    async def initialize(self) -> bool:
        """Initialize gas optimization system."""
        try:
            # Ensure web3_manager is connected
            if not hasattr(self.web3_manager, 'w3') or self.web3_manager.w3 is None:
                logger.debug("Connecting web3_manager...")
                await self.web3_manager.connect()
                logger.debug("Web3Manager connected successfully")

            # Get initial gas prices
            await self._update_gas_prices()

            self.initialized = True
            logger.debug("Gas optimizer initialized successfully")
            return True

        except Exception as e:
            logger.error("Failed to initialize gas optimizer: %s", str(e))
            return False

    async def _update_gas_prices(self):
        """Update current gas prices."""
        try:
            # Ensure web3_manager is connected
            if not hasattr(self.web3_manager, 'w3') or self.web3_manager.w3 is None:
                logger.debug("Connecting web3_manager...")
                await self.web3_manager.connect()

            # Get latest block for base fee
            latest_block = await self.web3_manager.w3.eth.get_block('latest', full_transactions=False)
            base_fee = latest_block['baseFeePerGas']
            base_fee = max(base_fee, int(self.min_base_fee * 1e9))  # Ensure minimum base fee
            
            # Try to get max priority fee, fall back to default if not available
            try:
                priority_fee = await self.web3_manager.w3.eth.max_priority_fee
            except (AttributeError, ValueError) as e:
                logger.debug("Could not get max_priority_fee_per_gas: %s", str(e))
                # Use default priority fee from config
                priority_fee = int(self.max_priority_fee * 1e9)
                logger.debug("Using default priority fee: %s", priority_fee)

            # Ensure priority fee is not zero
            priority_fee = max(priority_fee, int(0.1 * 1e9))  # Minimum 0.1 Gwei
            
            # Get pending transaction count
            pending_block = await self.web3_manager.w3.eth.get_block('pending', full_transactions=False)
            pending_txs = len(pending_block['transactions'])
            
            # Calculate dynamic multipliers based on network congestion
            if pending_txs > 20:  # High congestion
                fast_base_multiplier = 2.0
                standard_base_multiplier = 1.5
                slow_base_multiplier = 1.2
                priority_multiplier = 1.5
            elif pending_txs > 10:  # Medium congestion
                fast_base_multiplier = 1.5
                standard_base_multiplier = 1.3
                slow_base_multiplier = 1.1
                priority_multiplier = 1.2
            else:  # Low congestion
                fast_base_multiplier = 1.3
                standard_base_multiplier = 1.2
                slow_base_multiplier = 1.1
                priority_multiplier = 1.1

            # Calculate gas prices with limits from config
            max_fee_gwei = int(self.max_fee * 1e9)
            max_priority_gwei = int(self.max_priority_fee * 1e9)

            # Update gas prices
            current_time = time.time()
            self.gas_prices = {
                'fast': {
                    'maxFeePerGas': min(int(base_fee * fast_base_multiplier + priority_fee * priority_multiplier), max_fee_gwei),
                    'maxPriorityFeePerGas': min(int(priority_fee * priority_multiplier), max_priority_gwei)
                },
                'standard': {
                    'maxFeePerGas': min(int(base_fee * standard_base_multiplier + priority_fee), max_fee_gwei),
                    'maxPriorityFeePerGas': min(priority_fee, max_priority_gwei)
                },
                'slow': {
                    'maxFeePerGas': min(int(base_fee * slow_base_multiplier + priority_fee), max_fee_gwei),
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

            # Keep only last 24 hours of historical data
            cutoff_time = current_time - 86400  # 24 hours
            self.gas_metrics['historical_prices'] = [
                price for price in self.gas_metrics['historical_prices']
                if price['timestamp'] > cutoff_time
            ]

            logger.debug("Updated gas prices")

        except Exception as e:
            logger.error("Failed to update gas prices: %s", str(e))

    async def optimize_gas(self, tx_params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize gas parameters for a transaction."""
        try:
            # Ensure web3_manager is connected
            if not hasattr(self.web3_manager, 'w3') or self.web3_manager.w3 is None:
                logger.debug("Connecting web3_manager...")
                await self.web3_manager.connect()

            # Update gas prices first
            await self._update_gas_prices()

            # Get base gas estimate
            base_gas = await self.web3_manager.estimate_gas(tx_params)

            # Get current network conditions
            pending_txs = self.gas_prices['pending_txs']
            
            # Calculate optimal gas limit with buffer
            if pending_txs > 20:  # High congestion
                gas_limit = int(base_gas * 1.15)  # 15% buffer
            elif pending_txs > 10:  # Medium congestion
                gas_limit = int(base_gas * 1.1)  # 10% buffer
            else:  # Low congestion
                gas_limit = int(base_gas * 1.05)  # 5% buffer

            # Select appropriate gas price based on priority
            priority = tx_params.get('priority', 'standard')

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

            # Calculate potential savings
            standard_cost = base_gas * self.gas_prices['standard']['maxFeePerGas']
            optimized_cost = gas_limit * self.gas_prices[priority]['maxFeePerGas']
            gas_saved = standard_cost - optimized_cost
            self.gas_metrics['total_gas_saved'] += gas_saved

            # Update average gas used
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

            # Update optimization rate
            if total_txs > 0:
                self.gas_metrics['optimization_rate'] = (
                    self.gas_metrics['total_gas_saved'] /
                    (total_txs * standard_cost)
                )

            # Return optimized parameters
            return {
                'gas': gas_limit,
                'maxFeePerGas': self.gas_prices[priority]['maxFeePerGas'],
                'maxPriorityFeePerGas': self.gas_prices[priority]['maxPriorityFeePerGas']
            }

        except Exception as e:
            logger.error("Failed to optimize gas: %s", str(e))
            # Return safe default values within config limits
            try:
                if not hasattr(self.web3_manager, 'w3') or self.web3_manager.w3 is None:
                    logger.debug("Connecting web3_manager...")
                    await self.web3_manager.connect()
            except Exception as connect_error:
                logger.error("Failed to connect web3_manager: %s", str(connect_error))

            latest_block = await self.web3_manager.w3.eth.get_block('latest', full_transactions=False)
            base_fee = latest_block['baseFeePerGas']
            
            # Try to get max priority fee, fall back to default if not available
            try:
                priority_fee = await self.web3_manager.w3.eth.max_priority_fee
            except (AttributeError, ValueError) as e:
                logger.debug("Could not get max_priority_fee_per_gas: %s", str(e))
                # Use default priority fee from config
                priority_fee = int(self.max_priority_fee * 1e9)
                logger.debug("Using default priority fee: %s", priority_fee)

            # Ensure priority fee is not zero
            priority_fee = max(priority_fee, int(0.1 * 1e9))  # Minimum 0.1 Gwei
            
            return {
                'gas': tx_params.get('gas', 300000),
                'maxFeePerGas': min(base_fee * 2 + priority_fee, int(self.max_fee * 1e9)),
                'maxPriorityFeePerGas': min(priority_fee, int(self.max_priority_fee * 1e9))
            }

    async def get_gas_price(self, priority: str = 'standard') -> Dict[str, int]:
        """
        Get current gas price parameters for given priority level.
        
        Returns:
            Dict with maxFeePerGas and maxPriorityFeePerGas
        """
        try:
            # Ensure web3_manager is connected
            if not hasattr(self.web3_manager, 'w3') or self.web3_manager.w3 is None:
                logger.debug("Connecting web3_manager...")
                await self.web3_manager.connect()

            await self._update_gas_prices()
            gas_data = self.gas_prices.get(priority, self.gas_prices['standard'])
            return {
                'maxFeePerGas': gas_data['maxFeePerGas'],
                'maxPriorityFeePerGas': gas_data['maxPriorityFeePerGas'],
                'baseFee': self.gas_prices['base_fee']
            }
        except Exception as e:
            logger.error("Failed to get gas price: %s", str(e))
            try:
                if not hasattr(self.web3_manager, 'w3') or self.web3_manager.w3 is None:
                    logger.debug("Connecting web3_manager...")
                    await self.web3_manager.connect()
            except Exception as connect_error:
                logger.error("Failed to connect web3_manager: %s", str(connect_error))

            latest_block = await self.web3_manager.w3.eth.get_block('latest', full_transactions=False)
            base_fee = latest_block['baseFeePerGas']
            
            # Try to get max priority fee, fall back to default if not available
            try:
                priority_fee = await self.web3_manager.w3.eth.max_priority_fee
            except (AttributeError, ValueError) as e:
                logger.debug("Could not get max_priority_fee_per_gas: %s", str(e))
                # Use default priority fee from config
                priority_fee = int(self.max_priority_fee * 1e9)
                logger.debug("Using default priority fee: %s", priority_fee)

            # Ensure priority fee is not zero
            priority_fee = max(priority_fee, int(0.1 * 1e9))  # Minimum 0.1 Gwei
            
            return {
                'maxFeePerGas': min(base_fee * 2 + priority_fee, int(self.max_fee * 1e9)),
                'maxPriorityFeePerGas': min(priority_fee, int(self.max_priority_fee * 1e9)),
                'baseFee': base_fee
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get current gas metrics."""
        return {
            'gas_prices': self.gas_prices,
            'metrics': self.gas_metrics
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
