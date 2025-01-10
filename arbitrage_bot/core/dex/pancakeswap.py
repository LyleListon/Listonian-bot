"""PancakeSwap V3 DEX implementation."""

from typing import Dict, Any, Optional, List
from web3.types import TxReceipt

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager
from .utils import (
    validate_config,
    estimate_gas_cost,
    calculate_price_impact,
    encode_path_for_v3,
    get_common_base_tokens
)

class PancakeSwapDEX(BaseDEXV3):
    """Implementation of PancakeSwap V3 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize PancakeSwap V3 interface."""
        # PancakeSwap V3 uses 0.25% fee by default
        config['fee'] = config.get('fee', 2500)
        
        # Validate config
        is_valid, error = validate_config(config, {
            'router': str,
            'factory': str,
            'quoter': str,
            'fee': int
        })
        if not is_valid:
            raise ValueError(f"Invalid config: {error}")
            
        super().__init__(web3_manager, config)
        self.name = "PancakeSwap"

    async def get_pool_fee(self, token0: str, token1: str) -> Optional[int]:
        """
        Get the fee tier for a specific pool.
        
        Args:
            token0: First token address
            token1: Second token address
            
        Returns:
            Optional[int]: Fee in basis points (e.g., 2500 for 0.25%) or None if pool doesn't exist
        """
        try:
            # Common fee tiers in PancakeSwap V3
            fee_tiers = [100, 500, 2500, 10000]  # 0.01%, 0.05%, 0.25%, 1%
            
            for fee in fee_tiers:
                pool = await self.factory.functions.getPool(
                    token0,
                    token1,
                    fee
                ).call()
                
                if pool != "0x0000000000000000000000000000000000000000":
                    return fee
                    
            return None
            
        except Exception as e:
            self._handle_error(e, "Pool fee lookup")
            return None

    async def get_best_pool(self, token0: str, token1: str) -> Optional[Dict[str, Any]]:
        """
        Find the pool with the best liquidity for a pair.
        
        Args:
            token0: First token address
            token1: Second token address
            
        Returns:
            Optional[Dict[str, Any]]: Pool details including:
                - address: Pool contract address
                - fee: Fee tier
                - liquidity: Pool liquidity
                - sqrt_price_x96: Current sqrt price
        """
        try:
            best_pool = None
            max_liquidity = 0
            
            # Check all fee tiers
            fee_tiers = [100, 500, 2500, 10000]
            
            for fee in fee_tiers:
                pool_address = await self.factory.functions.getPool(
                    token0,
                    token1,
                    fee
                ).call()
                
                if pool_address == "0x0000000000000000000000000000000000000000":
                    continue
                    
                pool = self.w3.eth.contract(
                    address=pool_address,
                    abi=self.pool_abi
                )
                
                liquidity = await pool.functions.liquidity().call()
                if liquidity > max_liquidity:
                    slot0 = await pool.functions.slot0().call()
                    best_pool = {
                        'address': pool_address,
                        'fee': fee,
                        'liquidity': liquidity,
                        'sqrt_price_x96': slot0[0]
                    }
                    max_liquidity = liquidity
                    
            return best_pool
            
        except Exception as e:
            self._handle_error(e, "Best pool lookup")
            return None

    async def estimate_gas_cost(self, path: List[str]) -> int:
        """
        Estimate gas cost for a swap path.
        
        Args:
            path: List of token addresses in the swap path
            
        Returns:
            int: Estimated gas cost in wei
        """
        return estimate_gas_cost(path, 'v3')

    def _encode_path(self, path: List[str]) -> bytes:
        """
        Encode path with fees for V3 swap.
        
        Args:
            path: List of token addresses
            
        Returns:
            bytes: Encoded path with fees
        """
        return encode_path_for_v3(path, self.fee)

    async def get_common_pairs(self) -> List[str]:
        """Get list of common base tokens for routing."""
        return get_common_base_tokens()

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get quote including price impact and liquidity depth analysis.
        
        Args:
            amount_in: Input amount in wei
            path: List of token addresses in the swap path
            
        Returns:
            Optional[Dict[str, Any]]: Quote details including:
                - amount_in: Input amount
                - amount_out: Expected output amount
                - price_impact: Estimated price impact percentage
                - liquidity_depth: Available liquidity
                - fee_rate: DEX fee rate
                - estimated_gas: Estimated gas cost
                - min_out: Minimum output with slippage
        """
        try:
            if not self.quoter_address:
                raise ValueError("Quoter address not configured")
                
            # Get pool info
            pool_address = await self.factory.functions.getPool(
                path[0],
                path[1],
                self.fee
            ).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return None
                
            # Get pool contract
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get pool state
            slot0 = await pool.functions.slot0().call()
            liquidity = await pool.functions.liquidity().call()
            
            # Get quote from quoter
            encoded_path = self._encode_path(path)
            quote = await self.quoter.functions.quoteExactInput(
                encoded_path,
                amount_in
            ).call()
            
            # Calculate price impact using shared utility
            price_impact = calculate_price_impact(
                amount_in=amount_in,
                amount_out=quote,
                reserve_in=liquidity,  # Use liquidity as reserve proxy
                reserve_out=liquidity,
                sqrt_price_x96=slot0[0]
            )
            
            return {
                'amount_in': amount_in,
                'amount_out': quote,
                'price_impact': price_impact,
                'liquidity_depth': liquidity,
                'fee_rate': self.fee / 1000000,  # Convert from basis points
                'estimated_gas': estimate_gas_cost(path, 'v3'),
                'min_out': int(quote * 0.995)  # 0.5% slippage default
            }
            
        except Exception as e:
            self._handle_error(e, "V3 quote calculation")
            return None
