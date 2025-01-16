"""BaseSwap V2 DEX implementation."""

import sys
from typing import Dict, Any, Optional, List
from web3.types import TxReceipt

from .base_dex_v2 import BaseDEXV2
from ..web3.web3_manager import Web3Manager
from .utils import (
    validate_config,
    estimate_gas_cost,
    calculate_price_impact,
    get_common_base_tokens
)

# Increase recursion limit
sys.setrecursionlimit(10000)

class BaseSwapDEX(BaseDEXV2):
    """Implementation of BaseSwap V2 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize BaseSwap V2 interface."""
        # BaseSwap uses 0.3% fee by default
        config['fee'] = config.get('fee', 3000)
        
        # Validate config
        is_valid, error = validate_config(config, {
            'router': str,
            'factory': str,
            'fee': int
        })
        if not is_valid:
            raise ValueError(f"Invalid config: {error}")
            
        super().__init__(web3_manager, config)
        self.name = "BaseSwap"

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
            # Get pair address
            pair_address = await self.factory.functions.getPair(token0, token1).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
                
            # Get pair contract
            pair = self.w3.eth.contract(
                address=pair_address,
                abi=self.pair_abi
            )
            
            # Get reserves
            reserves = await pair.functions.getReserves().call()
            
            return {
                'reserve0': reserves[0],
                'reserve1': reserves[1],
                'timestamp': reserves[2]
            }
            
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            return None

    async def get_best_path(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        max_hops: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best trading path between tokens.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei
            max_hops: Maximum number of hops (default: 3)
            
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
            direct_amounts = await self.get_amounts_out(
                amount_in,
                [token_in, token_out]
            )
            if direct_amounts and direct_amounts[-1] > max_output:
                max_output = direct_amounts[-1]
                best_path = {
                    'path': [token_in, token_out],
                    'amounts': direct_amounts,
                    'fees': [self.fee],
                    'gas_estimate': estimate_gas_cost([token_in, token_out], 'v2')
                }
            
            # Only try multi-hop if max_hops > 1
            if max_hops > 1:
                # Get common pairs
                common_tokens = await self.get_common_pairs()
                
                # Try paths through each common token
                for mid_token in common_tokens:
                    path = [token_in, mid_token, token_out]
                    amounts = await self.get_amounts_out(amount_in, path)
                    
                    if amounts and amounts[-1] > max_output:
                        max_output = amounts[-1]
                        best_path = {
                            'path': path,
                            'amounts': amounts,
                            'fees': [self.fee] * 2,  # Fee for each hop
                            'gas_estimate': estimate_gas_cost(path, 'v2')
                        }
            
            return best_path
            
        except Exception as e:
            self._handle_error(e, "Path finding")
            return None

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
            # Get reserves
            reserves = await self.get_reserves(path[0], path[1])
            if not reserves:
                return None
                
            # Get amounts out
            amounts = await self.get_amounts_out(amount_in, path)
            if not amounts or len(amounts) < 2:
                return None
                
            amount_out = amounts[1]
            
            # Calculate price impact using shared utility
            price_impact = calculate_price_impact(
                amount_in=amount_in,
                amount_out=amount_out,
                reserve_in=reserves['reserve0'],
                reserve_out=reserves['reserve1']
            )
            
            return {
                'amount_in': amount_in,
                'amount_out': amount_out,
                'price_impact': price_impact,
                'liquidity_depth': min(reserves['reserve0'], reserves['reserve1']),
                'fee_rate': self.fee / 1000000,  # Convert from basis points
                'estimated_gas': estimate_gas_cost(path, 'v2'),
                'min_out': int(amount_out * 0.995)  # 0.5% slippage default
            }
            
        except Exception as e:
            self._handle_error(e, "V2 quote calculation")
            return None

    async def estimate_gas_cost(self, path: List[str]) -> int:
        """
        Estimate gas cost for a swap path.
        
        Args:
            path: List of token addresses in the swap path
            
        Returns:
            int: Estimated gas cost in wei
        """
        return estimate_gas_cost(path, 'v2')
