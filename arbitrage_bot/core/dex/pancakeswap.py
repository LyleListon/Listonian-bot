"""PancakeSwap DEX implementation."""

from typing import Dict, Any, List, Optional
import logging
import asyncio
from decimal import Decimal

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager
from .utils import validate_config

logger = logging.getLogger(__name__)

class PancakeSwap(BaseDEXV3):
    """Implementation of PancakeSwap V3 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize PancakeSwap interface."""
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
        self.name = "PancakeSwap"
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize PancakeSwap interface."""
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
            logger.info(f"PancakeSwap V3 interface initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PancakeSwap: {e}")
            return False

    async def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pools."""
        try:
            total_liquidity = Decimal(0)
            
            # Get pools from PoolCreated events
            pool_created_filter = self.factory.events.PoolCreated.create_filter(fromBlock=0)
            events = await self._retry_async(
                lambda: pool_created_filter.get_all_entries()
            )
            
            # Limit to most recent 100 pools for performance
            for event in events[-100:]:
                try:
                    pool_address = event['args']['pool']
                    pool = await self.web3_manager.get_contract_async(
                        address=pool_address,
                        abi=self.pool_abi
                    )
                    
                    # Get liquidity
                    liquidity = await self._retry_async(
                        lambda: pool.functions.liquidity().call()
                    )
                    total_liquidity += Decimal(liquidity)
                    
                except Exception as e:
                    logger.warning(f"Failed to get liquidity for pool {pool_address}: {e}")
                    continue
            
            return total_liquidity
            
        except Exception as e:
            logger.error(f"Failed to get total liquidity: {e}")
            return Decimal(0)

    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        try:
            # Get pool address using V3 factory method
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
            
            # Get volume from Swap events in last 24h
            current_block = await self.web3_manager.w3.eth.block_number
            from_block = current_block - 7200  # ~24h of blocks
            
            swap_filter = pool.events.Swap.create_filter(fromBlock=from_block)
            swap_events = await self._retry_async(
                lambda: swap_filter.get_all_entries()
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

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote including price impact and liquidity depth analysis."""
        try:
            if len(path) != 2:
                raise ValueError("V3 quotes only support direct pairs")

            # Get pool address
            pool_address = await self._retry_async(
                lambda: self.factory.functions.getPool(
                    path[0],
                    path[1],
                    self.config['fee']
                ).call()
            )

            if pool_address == "0x0000000000000000000000000000000000000000":
                return None

            # Get pool contract
            pool = await self.web3_manager.get_contract_async(
                address=pool_address,
                abi=self.pool_abi
            )

            # Get pool state
            slot0 = await self._retry_async(
                lambda: pool.functions.slot0().call()
            )
            liquidity = await self._retry_async(
                lambda: pool.functions.liquidity().call()
            )

            # Calculate amounts
            sqrt_price_x96 = slot0[0]
            amount_out = amount_in * sqrt_price_x96 / (2 ** 96)

            # Calculate price impact
            price_impact = self._calculate_price_impact(
                amount_in=amount_in,
                amount_out=int(amount_out),
                sqrt_price_x96=sqrt_price_x96,
                liquidity=liquidity
            )

            return {
                'amount_in': amount_in,
                'amount_out': int(amount_out),
                'price_impact': price_impact,
                'liquidity_depth': liquidity,
                'fee_rate': self.config['fee'] / 1000000,
                'estimated_gas': 200000,  # V3 swaps use more gas
                'min_out': int(amount_out * 0.995)  # 0.5% slippage
            }

        except Exception as e:
            logger.error(f"Failed to get V3 quote: {e}")
            return None
