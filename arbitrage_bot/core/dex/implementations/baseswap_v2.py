"""BaseSwap V2 DEX implementation."""

from typing import Dict, Optional, Tuple
from decimal import Decimal
from web3 import Web3

from ..base_dex_v2 import BaseV2DEX, QuoteResult

class BaseSwapV2(BaseV2DEX):
    """BaseSwap V2 implementation using base V2 framework."""

    def __init__(self, web3: Web3, config: dict):
        """Initialize BaseSwap V2."""
        # Ensure required config
        required_keys = ['router', 'factory', 'fee_numerator']
        missing = [key for key in required_keys if key not in config]
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")
            
        super().__init__(web3, config)
        
        # BaseSwap specific initialization
        self.name = "baseswap_v2"
        self.version = "v2"
        self.logger.info(
            f"Initialized {self.name} with router: {config['router']}, "
            f"factory: {config['factory']}, "
            f"fee: {config['fee_numerator']}/{self.fee_denominator}%"
        )

    async def get_quote(self, token_in: str, token_out: str, amount_in: int) -> QuoteResult:
        """
        Get quote using BaseSwap V2 router.
        
        This implementation leverages the base V2 quote logic while adding
        BaseSwap-specific error handling and logging.
        """
        try:
            # Use base class implementation
            quote = await super().get_quote(token_in, token_out, amount_in)
            
            # Add BaseSwap-specific logging
            if quote.success:
                self.logger.debug(
                    f"BaseSwap V2 quote: {quote.amount_out} "
                    f"(fee: {quote.fee})"
                )
            else:
                self.logger.warning(
                    f"BaseSwap V2 quote failed: {quote.error}"
                )
                
            return quote

        except Exception as e:
            self.log_error(e, {
                "method": "get_quote",
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "dex": "baseswap_v2"
            })
            return QuoteResult(
                amount_out=0,
                fee=0,
                price_impact=0.0,
                path=[],
                success=False,
                error=f"BaseSwap V2 error: {str(e)}"
            )

    async def check_liquidity(self, token_in: str, token_out: str) -> Decimal:
        """
        Check liquidity for BaseSwap V2 pair.
        
        Implements BaseSwap-specific liquidity checking while leveraging
        the base V2 pair lookup and reserves logic.
        """
        try:
            # Get reserves using base class implementation
            reserves_in, reserves_out = await self.get_reserves(token_in, token_out)
            
            if reserves_in == 0 or reserves_out == 0:
                self.logger.debug(
                    f"No liquidity for pair {token_in}/{token_out}"
                )
                return Decimal(0)
                
            # Convert to Decimal for precise math
            liquidity = Decimal(str(reserves_in))
            
            self.logger.debug(
                f"BaseSwap V2 liquidity for {token_in}/{token_out}: "
                f"{liquidity}"
            )
            
            return liquidity

        except Exception as e:
            self.log_error(e, {
                "method": "check_liquidity",
                "token_in": token_in,
                "token_out": token_out,
                "dex": "baseswap_v2"
            })
            return Decimal(0)

    async def calculate_price_impact(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ) -> float:
        """
        Calculate price impact for BaseSwap V2 trade.
        
        BaseSwap-specific implementation that considers reserves and fees.
        """
        try:
            reserves_in, reserves_out = await self.get_reserves(token_in, token_out)
            if reserves_in == 0 or reserves_out == 0:
                return 1.0  # 100% price impact for no liquidity
                
            # Calculate price impact considering fees
            fee_adjusted_amount = amount_in * (self.fee_denominator - self.fee_numerator) // self.fee_denominator
            numerator = fee_adjusted_amount * reserves_out
            denominator = (reserves_in * fee_adjusted_amount) + (reserves_in * reserves_out)
            
            if denominator == 0:
                return 1.0
                
            execution_price = numerator / denominator
            optimal_price = reserves_out / reserves_in
            
            price_impact = abs(1 - (execution_price / optimal_price))
            
            self.logger.debug(
                f"BaseSwap V2 price impact for {amount_in} {token_in}: "
                f"{price_impact:.4%}"
            )
            
            return float(price_impact)

        except Exception as e:
            self.log_error(e, {
                "method": "calculate_price_impact",
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "dex": "baseswap_v2"
            })
            return 1.0  # Return 100% price impact on error