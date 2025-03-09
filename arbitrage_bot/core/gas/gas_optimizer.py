"""
Gas Optimizer Module

Handles gas optimization strategies for arbitrage transactions.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from web3 import Web3

from ...utils.async_manager import manager
from ..dex.dex_manager import DexManager

logger = logging.getLogger(__name__)

@dataclass
class GasStrategy:
    """Gas strategy configuration."""
    max_priority_fee: float
    max_fee: float
    gas_limit: int
    buffer_percent: float

class GasOptimizer:
    """Optimizes gas usage for arbitrage transactions."""
    
    def __init__(
        self,
        dex_manager: DexManager,
        web3_manager: Any,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize gas optimizer."""
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()
        
        # Default gas strategy
        self.strategy = GasStrategy(
            max_priority_fee=float(self.config.get('max_priority_fee', 2.5)),
            max_fee=float(self.config.get('max_fee', 5.0)),
            gas_limit=int(self.config.get('gas_limit', 500000)),
            buffer_percent=float(self.config.get('gas_limit_buffer', 1.1))
        )
        
        # Cache for gas prices
        self._gas_price_cache = {}
        self._last_base_fee = None
        self._last_priority_fee = None
        
    async def initialize(self) -> bool:
        """Initialize the gas optimizer."""
        try:
            # Initialize gas price monitoring
            await self._update_gas_prices()
            
            # Start background gas price updates
            asyncio.create_task(self._gas_price_monitor())
            
            self.initialized = True
            logger.info("Gas optimizer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize gas optimizer: {e}")
            return False
            
    async def _gas_price_monitor(self):
        """Monitor gas prices in the background."""
        while True:
            try:
                await self._update_gas_prices()
                await asyncio.sleep(10)  # Update every 10 seconds
            except Exception as e:
                logger.error(f"Error updating gas prices: {e}")
                await asyncio.sleep(30)  # Longer delay on error
                
    async def _update_gas_prices(self):
        """Update current gas prices."""
        try:
            # Get latest block
            block = await self.web3_manager.w3.eth.get_block('latest')
            self._last_base_fee = block.get('baseFeePerGas', 0)
            
            # Get priority fee suggestions
            self._last_priority_fee = await self.web3_manager.w3.eth.max_priority_fee_per_gas
            
            logger.debug(
                f"Updated gas prices - Base fee: {Web3.from_wei(self._last_base_fee, 'gwei')} gwei, "
                f"Priority fee: {Web3.from_wei(self._last_priority_fee, 'gwei')} gwei"
            )
            
        except Exception as e:
            logger.error(f"Failed to update gas prices: {e}")
            
    async def estimate_gas(
        self,
        tx_params: Dict[str, Any],
        dex_name: Optional[str] = None
    ) -> int:
        """
        Estimate gas for a transaction.
        
        Args:
            tx_params: Transaction parameters
            dex_name: Optional DEX name for specific estimation
            
        Returns:
            Estimated gas amount with buffer
        """
        async with self.lock:
            try:
                # Get base estimation
                gas_estimate = await self.web3_manager.w3.eth.estimate_gas(tx_params)
                
                # Add buffer
                buffered_estimate = int(gas_estimate * self.strategy.buffer_percent)
                
                # Cap at max gas limit
                final_estimate = min(buffered_estimate, self.strategy.gas_limit)
                
                logger.debug(
                    f"Gas estimation - Base: {gas_estimate}, "
                    f"Buffered: {buffered_estimate}, "
                    f"Final: {final_estimate}"
                )
                
                return final_estimate
                
            except Exception as e:
                logger.error(f"Failed to estimate gas: {e}")
                return self.strategy.gas_limit
                
    async def get_gas_strategy(self) -> Dict[str, Any]:
        """
        Get current gas strategy parameters.
        
        Returns:
            Dictionary with gas strategy parameters
        """
        async with self.lock:
            return {
                'maxPriorityFeePerGas': Web3.to_wei(self.strategy.max_priority_fee, 'gwei'),
                'maxFeePerGas': Web3.to_wei(self.strategy.max_fee, 'gwei'),
                'gasLimit': self.strategy.gas_limit
            }
            
    async def update_strategy(self, new_strategy: Dict[str, Any]):
        """
        Update gas strategy parameters.
        
        Args:
            new_strategy: New strategy parameters
        """
        async with self.lock:
            self.strategy = GasStrategy(
                max_priority_fee=float(new_strategy.get('max_priority_fee', self.strategy.max_priority_fee)),
                max_fee=float(new_strategy.get('max_fee', self.strategy.max_fee)),
                gas_limit=int(new_strategy.get('gas_limit', self.strategy.gas_limit)),
                buffer_percent=float(new_strategy.get('buffer_percent', self.strategy.buffer_percent))
            )
            logger.info("Updated gas strategy")

async def create_gas_optimizer(
    dex_manager: DexManager,
    web3_manager: Any,
    config: Optional[Dict[str, Any]] = None
) -> GasOptimizer:
    """
    Create and initialize a gas optimizer instance.
    
    Args:
        dex_manager: DEX manager instance
        web3_manager: Web3 manager instance
        config: Optional configuration
        
    Returns:
        Initialized GasOptimizer instance
    """
    optimizer = GasOptimizer(dex_manager, web3_manager, config)
    if not await optimizer.initialize():
        raise RuntimeError("Failed to initialize gas optimizer")
    return optimizer
