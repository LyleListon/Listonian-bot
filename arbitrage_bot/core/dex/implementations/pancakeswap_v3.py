"""PancakeSwap V3 DEX implementation."""

from typing import Dict, Optional
from web3 import Web3

from ..base_dex_v3 import BaseV3DEX, QuoteResult

class PancakeSwapV3(BaseV3DEX):
    """PancakeSwap V3 implementation using base V3 framework."""

    def __init__(self, web3: Web3, config: dict):
        """Initialize PancakeSwap V3."""
        # Ensure required config
        required_keys = ['quoter', 'factory', 'fee_tiers']
        missing = [key for key in required_keys if key not in config]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")
            
        super().__init__(web3, config)
        
        # PancakeSwap specific initialization
        self.name = "pancakeswap_v3"
        self.version = "v3"
        self.logger.info(
            f"Initialized {self.name} with quoter: {config['quoter']}, "
            f"factory: {config['factory']}"
        )

    async def get_quote(self, token_in: str, token_out: str, amount_in: int) -> QuoteResult:
        """
        Get quote using PancakeSwap V3 quoter.
        
        This implementation leverages the base V3 path encoding while adding
        PancakeSwap-specific error handling and logging.
        """
        try:
            # Use base class implementation
            quote = await super().get_quote(token_in, token_out, amount_in)
            
            # Add PancakeSwap-specific logging
            if quote.success:
                self.logger.debug(
                    f"PancakeSwap V3 quote: {quote.amount_out} "
                    f"(fee tier: {quote.fee})"
                )
            else:
                self.logger.warning(
                    f"PancakeSwap V3 quote failed: {quote.error}"
                )
                
            return quote

        except Exception as e:
            self.log_error(e, {
                "method": "get_quote",
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "dex": "pancakeswap_v3"
            })
            return QuoteResult(
                amount_out=0,
                fee=0,
                price_impact=0.0,
                path=[],
                success=False,
                error=f"PancakeSwap V3 error: {str(e)}"
            )

    async def check_liquidity(self, token_in: str, token_out: str) -> int:
        """
        Check liquidity across all PancakeSwap V3 fee tiers.
        
        Implements PancakeSwap-specific liquidity checking logic while
        leveraging the base V3 pool address lookup.
        """
        total_liquidity = 0
        
        for fee in self.default_fee_tiers:
            try:
                pool = await self.get_pool_address(token_in, token_out, fee)
                if not pool or pool == "0x" + "0" * 40:
                    continue
                    
                # Get pool contract
                pool_abi = self.config.get('pool_abi')
                if not pool_abi:
                    self.logger.warning("No pool ABI provided, loading from default")
                    # Implement ABI loading
                    
                pool_contract = self.w3.eth.contract(address=pool, abi=pool_abi)
                
                # Get liquidity from slot0
                slot0 = await pool_contract.functions.slot0().call()
                liquidity = await pool_contract.functions.liquidity().call()
                
                if liquidity > 0:
                    total_liquidity += liquidity
                    self.logger.debug(
                        f"Pool {pool} liquidity: {liquidity} "
                        f"(fee tier: {fee})"
                    )
                    
            except Exception as e:
                self.log_error(e, {
                    "method": "check_liquidity",
                    "token_in": token_in,
                    "token_out": token_out,
                    "fee": fee,
                    "dex": "pancakeswap_v3"
                })
                
        return total_liquidity