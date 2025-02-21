"""SwapBased DEX implementation."""

from typing import Dict, Any, List, Optional
from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager

class SwapBased(BaseDEXV3):
    """SwapBased DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize SwapBased interface."""
        super().__init__(web3_manager, config)
        self.name = "SwapBased"

    def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None

        try:
            # SwapBased only supports quoteExactInputSingle
            result = self._retry_sync(
                lambda: self.quoter.functions.quoteExactInputSingle(
                    path[0],  # tokenIn
                    path[-1],  # tokenOut
                    self.fee,  # fee
                    amount_in,  # amountIn
                    0  # sqrtPriceLimitX96 (0 for no limit)
                ).call()
            )
            if not result:
                return None

            # Result is (amountOut, sqrtPriceX96After, initializedTicksCrossed, gasEstimate)
            amount_out, _, _, gas_estimate = result
            self.logger.debug("Quote result: amount_out=%s, gas_estimate=%s", amount_out, gas_estimate)
            return amount_out

        except Exception as e:
            self.logger.error("Failed to get quote: %s", str(e))
            return None

    def get_quote_with_impact(self, amount_in: int, path: List[str]) -> Optional[Dict[str, Any]]:
        """Get quote with price impact calculation."""
        try:
            # Get quote from quoter
            amount_out = self.get_quote_from_quoter(amount_in, path)
            self.logger.debug("Quote amount_out: %s", amount_out)
            if not amount_out:
                self.logger.warning("Failed to get quote for amount_in: %s, path: %s", amount_in, path)
                return None

            # Calculate price impact
            # Use a smaller amount to get baseline price
            small_amount = amount_in // 1000 if amount_in > 1000 else amount_in
            baseline_out = self.get_quote_from_quoter(small_amount, path)
            self.logger.debug("Baseline quote amount_out: %s", baseline_out)
            if not baseline_out:
                self.logger.warning("Failed to get baseline quote for amount_in: %s, path: %s", small_amount, path)
                return None

            # Calculate impact and validate
            try:
                impact = 1 - (amount_out * small_amount) / (baseline_out * amount_in)
                if impact < -1 or impact > 1:
                    self.logger.warning("Invalid price impact calculated: %s", impact)
                    return None
            except ZeroDivisionError:
                self.logger.error("Division by zero when calculating price impact")
                return None

            # Get gas estimate from quoter
            try:
                _, _, _, gas_estimate = self.quoter.functions.quoteExactInputSingle(
                    path[0],  # tokenIn
                    path[-1],  # tokenOut
                    self.fee,  # fee
                    amount_in,  # amountIn
                    0  # sqrtPriceLimitX96 (0 for no limit)
                ).call()
            except Exception as e:
                self.logger.warning("Failed to get gas estimate: %s", str(e))
                gas_estimate = 250000  # Use default if estimate fails

            return {
                'amount_out': amount_out,
                'impact': impact,
                'fee_rate': float(self.fee) / 1000000,  # Convert to float to avoid decimal division
                'fee': self.fee,  # Include raw fee value
                'estimated_gas': gas_estimate  # Use actual gas estimate from quoter
            }

        except Exception as e:
            self.logger.error("Failed to get quote with impact: %s", str(e))
            return None
