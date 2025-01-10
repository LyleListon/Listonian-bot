"""Price validation utility using MCP crypto price server"""

import logging
import json
import subprocess
from typing import Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class PriceValidator:
    """Validates prices against market rates using MCP crypto price server"""

    def __init__(self, max_price_deviation_percent: float = 2.0):
        """Initialize price validator

        Args:
            max_price_deviation_percent: Maximum allowed deviation from market price
        """
        self.max_deviation = max_price_deviation_percent

    def _execute_mcp_tool(
        self, coins: List[str], include_24h_change: bool = False
    ) -> Optional[Dict]:
        """Execute MCP tool to get crypto prices

        Args:
            coins: List of cryptocurrency IDs
            include_24h_change: Whether to include 24h price changes

        Returns:
            Dict containing price data or None if error
        """
        try:
            # Construct MCP tool command
            command = {
                "server_name": "crypto-price",
                "tool_name": "get_prices",
                "arguments": {"coins": coins, "include_24h_change": include_24h_change},
            }

            # Execute command through MCP
            result = subprocess.run(
                ["cline", "mcp", "execute"],
                input=json.dumps(command),
                text=True,
                capture_output=True,
            )

            if result.returncode != 0:
                logger.error(f"MCP tool execution failed: {result.stderr}")
                return None

            return json.loads(result.stdout)

        except Exception as e:
            logger.error(f"Error executing MCP tool: {e}")
            return None

    def validate_price(self, token: str, dex_price: Decimal) -> bool:
        """Validate DEX price against market price

        Args:
            token: Token identifier (e.g. 'ethereum')
            dex_price: Price from DEX to validate

        Returns:
            bool: True if price is within acceptable deviation
        """
        try:
            # Get market price
            result = self._execute_mcp_tool([token])
            if not result or "prices" not in result:
                logger.error("Failed to get market price for validation")
                return False

            # Extract market price
            market_price = Decimal(str(result["prices"][token]["price_usd"]))

            # Calculate deviation
            deviation = abs((dex_price - market_price) / market_price * 100)

            # Validate against maximum allowed deviation
            is_valid = deviation <= self.max_deviation

            if not is_valid:
                logger.warning(
                    f"Price deviation too high for {token}: "
                    f"DEX price: {dex_price}, Market price: {market_price}, "
                    f"Deviation: {deviation}%"
                )

            return is_valid

        except Exception as e:
            logger.error(f"Error validating price: {e}")
            return False

    def get_market_context(self, tokens: List[str]) -> Dict:
        """Get market context for multiple tokens

        Args:
            tokens: List of token identifiers

        Returns:
            Dict containing market prices and 24h changes
        """
        try:
            result = self._execute_mcp_tool(tokens, include_24h_change=True)
            if not result or "prices" not in result:
                logger.error("Failed to get market context")
                return {}

            return result["prices"]

        except Exception as e:
            logger.error(f"Error getting market context: {e}")
            return {}


def create_price_validator(max_deviation: Optional[float] = None) -> PriceValidator:
    """Factory function to create PriceValidator instance

    Args:
        max_deviation: Optional maximum price deviation percentage

    Returns:
        Configured PriceValidator instance
    """
    if max_deviation is not None:
        return PriceValidator(max_deviation)
    return PriceValidator()
