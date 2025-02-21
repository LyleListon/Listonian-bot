"""RocketSwap V3 DEX implementation."""

from typing import Dict, Any, List, Optional
from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager

class RocketSwapV3(BaseDEXV3):
    """RocketSwap V3 DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize RocketSwap V3 interface."""
        super().__init__(web3_manager, config)
        self.name = "RocketSwap"

    def get_quote_from_quoter(self, amount_in: int, path: List[str]) -> Optional[int]:
        """Get quote from quoter contract if available."""
        if not self.quoter:
            return None

        try:
            # Try quoteExactInput first for better gas estimation
            encoded_path = self._encode_path(path)
            amount_out = self._retry_sync(
                lambda: self.quoter.functions.quoteExactInput(
                    encoded_path,
                    amount_in
                ).call()
            )
            if amount_out:
                self.logger.debug("Got quote from quoteExactInput: %s", amount_out)
                return amount_out

            # Fallback to quoteExactInputSingle
            amount_out = self._retry_sync(
                lambda: self.quoter.functions.quoteExactInputSingle(
                    path[0],  # tokenIn
                    path[-1],  # tokenOut
                    self.fee,  # fee
                    amount_in,  # amountIn
                    0  # sqrtPriceLimitX96 (0 for no limit)
                ).call()
            )
            if amount_out:
                self.logger.debug("Got quote from quoteExactInputSingle: %s", amount_out)
                return amount_out

            return None

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

            return {
                'amount_out': amount_out,
                'impact': impact,
                'fee_rate': float(self.fee) / 1000000,  # Convert to float to avoid decimal division
                'fee': self.fee,  # Include raw fee value
                'estimated_gas': 250000  # Base estimate for V3 swaps
            }

        except Exception as e:
            self.logger.error("Failed to get quote with impact: %s", str(e))
            return None