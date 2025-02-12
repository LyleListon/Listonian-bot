"""SwapBased DEX implementation."""

from typing import Dict, Any
import logging
import asyncio
from decimal import Decimal

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager
from .utils import validate_config

logger = logging.getLogger(__name__)

class SwapBased(BaseDEXV3):
    """Implementation of SwapBased V3 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize SwapBased interface."""
        # Validate config
        is_valid, error = validate_config(config, {
            'router': str,
            'factory': str,
            'fee': int,
            'tick_spacing': int
        })
        if not is_valid:
            raise ValueError(f"Invalid config: {error}")
            
        super().__init__(web3_manager, config)
        self.name = "SwapBased"
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize SwapBased interface."""
        try:
            # Initialize base V3 DEX
            if not await super().initialize():
                return False
            
            # Initialize contracts
            self.router = self.w3.eth.contract(
                address=self.router_address,
                abi=self.router_abi
            )
            self.factory = self.w3.eth.contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            
            self.initialized = True
            logger.info(f"SwapBased V3 interface initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SwapBased: {e}")
            return False

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pools."""
        try:
            total_liquidity = Decimal(0)
            
            # Get all pools
            pool_count = await self._retry_async(
                self.factory.functions.allPoolsLength().call
            )
            
            for i in range(min(pool_count, 100)):  # Limit to 100 pools for performance
                try:
                    pool_address = await self._retry_async(
                        lambda: self.factory.functions.allPools(i).call()
                    )
                    
                    pool = await self.web3_manager.get_contract_async(
                        address=pool_address,
                        abi=self.pool_abi
                    )
                    
                    # Get liquidity
                    liquidity = await self._retry_async(
                        pool.functions.liquidity().call
                    )
                    total_liquidity += Decimal(liquidity)
                    
                except Exception as e:
                    logger.warning(f"Failed to get liquidity for pool {i}: {e}")
                    continue
            
            return total_liquidity
            
        except Exception as e:
            logger.error(f"Failed to get total liquidity: {e}")
            return Decimal(0)

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        try:
            # Get pool address
            pool_address = await self._retry_async(
                lambda: self.factory.functions.getPool(
                    token0,
                    token1,
                    self.config['fee']
                ).call()
            )
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return Decimal(0)
            
            # Get pool contract
            pool = await self.web3_manager.get_contract_async(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get volume from events in last 24h
            current_block = await self.web3_manager.w3.eth.block_number
            from_block = current_block - 7200  # ~24h of blocks
            
            swap_events = await self._retry_async(
                lambda: pool.events.Swap.get_logs(
                    fromBlock=from_block
                )
            )
            
            volume = Decimal(0)
            for event in swap_events:
                amount0 = abs(Decimal(event['args']['amount0']))
                amount1 = abs(Decimal(event['args']['amount1']))
                volume += max(amount0, amount1)
            
            return volume
            
        except Exception as e:
            logger.error(f"Failed to get 24h volume: {e}")
            return Decimal(0)
