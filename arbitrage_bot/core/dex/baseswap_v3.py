"""BaseSwap V3 DEX implementation."""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from web3 import Web3

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager

class BaseSwapV3(BaseDEXV3):
    """BaseSwap V3 DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize BaseSwap V3 interface."""
        super().__init__(web3_manager, config)
        self.name = "BaseSwap"

    def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None

        # Only support direct swaps for now
        if len(path) != 2:
            self.logger.warning("Multi-hop paths not supported yet")
            return None

        try:
            # Use quoteExactInputSingle
            result = self._retry_sync(
                lambda: self.quoter.functions.quoteExactInputSingle(
                    Web3.to_checksum_address(path[0]),  # tokenIn
                    Web3.to_checksum_address(path[1]),  # tokenOut
                    self.fee,  # fee
                    amount_in,  # amountIn
                    0  # sqrtPriceLimitX96 (0 for no limit)
                ).call()
            )
            # Return just the amount_out from the tuple
            return result[0] if result else None

        except Exception as e:
            self.logger.error("Failed to get quote: %s", str(e))
            return None

    def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """Get 24-hour trading volume for a token pair."""
        try:
            # Validate and checksum addresses
            token0 = Web3.to_checksum_address(token0)
            token1 = Web3.to_checksum_address(token1)
            
            # Get pool address using V3 factory method
            pool_address = self._retry_sync(
                lambda: self.factory.functions.getPool(
                    token0,
                    token1,
                    self.fee
                ).call()
            )
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return Decimal(0)
            
            # Get pool contract with checksummed address
            pool = self.web3_manager.get_contract(
                address=Web3.to_checksum_address(pool_address),
                abi_name=self.name.lower() + "_v3_pool"
            )
            
            # Get volume from Swap events in last 24h
            current_block = self.web3_manager.w3.eth.block_number
            from_block = current_block - 7200  # ~24h of blocks
            
            swap_filter = pool.events.Swap.create_filter(fromBlock=from_block)
            swap_events = self._retry_sync(
                lambda: swap_filter.get_all_entries()
            )
            
            volume = Decimal(0)
            for event in swap_events:
                amount0 = abs(Decimal(event['args']['amount0']))
                amount1 = abs(Decimal(event['args']['amount1']))
                volume += max(amount0, amount1)
            
            return volume
            
        except Exception as e:
            self.logger.error("Failed to get 24h volume: %s", str(e))
            return Decimal(0)

    def get_total_liquidity(self) -> Decimal:
        """Get total liquidity across all pairs."""
        try:
            total_liquidity = Decimal(0)
            
            # Get pools from PoolCreated events
            pool_created_filter = self.factory.events.PoolCreated.create_filter(fromBlock=0)
            events = self._retry_sync(
                lambda: pool_created_filter.get_all_entries()
            )
            
            # Limit to most recent 100 pools for performance
            for event in events[-100:]:
                try:
                    pool_address = Web3.to_checksum_address(event['args']['pool'])
                    pool = self.web3_manager.get_contract(
                        address=pool_address,
                        abi_name=self.name.lower() + "_v3_pool"
                    )
                    
                    # Get liquidity
                    liquidity = self._retry_sync(
                        lambda: pool.functions.liquidity().call()
                    )
                    total_liquidity += Decimal(liquidity)
                    
                except Exception as e:
                    self.logger.warning("Failed to get liquidity for pool %s: %s", pool_address, str(e))
                    continue
            
            return total_liquidity
            
        except Exception as e:
            self.logger.error("Failed to get total liquidity: %s", str(e))
            return Decimal(0)