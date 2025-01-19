"""SwapBased V3 DEX implementation."""

from typing import Dict, Any, Optional, List
from web3.types import TxReceipt

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager
from .utils import (
    validate_config,
    estimate_gas_cost,
    calculate_price_impact,
    get_common_base_tokens,
    COMMON_TOKENS
)

class SwapBasedV3(BaseDEXV3):
    """Implementation of SwapBased V3 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize SwapBased V3 interface."""
        # SwapBased uses 0.3% fee by default
        config['fee'] = config.get('fee', 3000)
        
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
        self.name = "SwapBased"

    async def get_reserves(self, token0: str, token1: str) -> Optional[Dict[str, int]]:
        """
        Get reserves for a token pair.
        
        Args:
            token0: First token address
            token1: Second token address
            
        Returns:
            Optional[Dict[str, int]]: Reserve details including:
                - reserve0: Reserve of first token
                - reserve1: Reserve of second token
                - timestamp: Last update timestamp
        """
        try:
            # Get pool address
            pool_address = await self.factory.functions.getPool(
                token0,
                token1,
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
            
            return {
                'reserve0': liquidity,  # V3 uses liquidity instead of reserves
                'reserve1': liquidity,
                'timestamp': slot0[2]  # Last observation timestamp
            }
            
        except Exception as e:
            self._handle_error(e, "Reserve lookup")
            return None

    async def get_best_path(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        max_hops: int = 2  # SwapBased works better with fewer hops
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best trading path between tokens.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei
            max_hops: Maximum number of hops (default: 2)
            
        Returns:
            Optional[Dict[str, Any]]: Path details including:
                - path: List of token addresses
                - amounts: Expected amounts at each hop
                - fees: Cumulative fees
                - gas_estimate: Estimated gas cost
        """
        try:
            best_path = None
            max_output = 0
            
            # Direct path
            quote = await self.get_quote_with_impact(
                amount_in,
                [token_in, token_out]
            )
            if quote and quote['amount_out'] > max_output:
                max_output = quote['amount_out']
                best_path = {
                    'path': [token_in, token_out],
                    'amounts': [amount_in, quote['amount_out']],
                    'fees': [self.fee],
                    'gas_estimate': estimate_gas_cost([token_in, token_out], 'v3')
                }
            
            # Only try multi-hop if max_hops > 1
            if max_hops > 1:
                # SwapBased prefers WETH and USDC for routing
                common_tokens = [
                    COMMON_TOKENS['WETH'],
                    COMMON_TOKENS['USDC']
                ]
                
                # Try paths through each common token
                for mid_token in common_tokens:
                    first_hop = await self.get_quote_with_impact(
                        amount_in,
                        [token_in, mid_token]
                    )
                    if first_hop:
                        second_hop = await self.get_quote_with_impact(
                            first_hop['amount_out'],
                            [mid_token, token_out]
                        )
                        if second_hop and second_hop['amount_out'] > max_output:
                            max_output = second_hop['amount_out']
                            best_path = {
                                'path': [token_in, mid_token, token_out],
                                'amounts': [
                                    amount_in,
                                    first_hop['amount_out'],
                                    second_hop['amount_out']
                                ],
                                'fees': [self.fee] * 2,  # Fee for each hop
                                'gas_estimate': estimate_gas_cost([token_in, mid_token, token_out], 'v3')
                            }
            
            return best_path
            
        except Exception as e:
            self._handle_error(e, "Path finding")
            return None

    async def check_liquidity_depth(
        self,
        token0: str,
        token1: str,
        min_liquidity: int = 1000000  # Minimum $1M liquidity
    ) -> bool:
        """
        Check if a pair has sufficient liquidity.
        
        Args:
            token0: First token address
            token1: Second token address
            min_liquidity: Minimum required liquidity in USD
            
        Returns:
            bool: True if liquidity is sufficient
        """
        try:
            # Get pool address
            pool_address = await self.factory.functions.getPool(
                token0,
                token1,
                self.fee
            ).call()
            
            if pool_address == "0x0000000000000000000000000000000000000000":
                return False
                
            # Get pool contract
            pool = self.w3.eth.contract(
                address=pool_address,
                abi=self.pool_abi
            )
            
            # Get liquidity
            liquidity = await pool.functions.liquidity().call()
            return liquidity >= min_liquidity
            
        except Exception as e:
            self._handle_error(e, "Liquidity check")
            return False