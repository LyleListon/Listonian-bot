"""Market analysis utilities."""

import logging
import math
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .mcp_helper import call_mcp_tool

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Analyzes market conditions and opportunities."""

    def __init__(self):
        """Initialize market analyzer."""
        logger.info("Market analyzer initialized")
        self._price_cache = {}
        self._cache_duration = timedelta(seconds=30)  # Cache prices for 30 seconds

    def validate_price(self, price: float) -> bool:
        """
        Validate if a price is valid.

        Args:
            price (float): Price to validate

        Returns:
            bool: True if price is valid, False otherwise
        """
        if not isinstance(price, (int, float)):
            return False

        return price > 0 and not math.isinf(price) and not math.isnan(price)

    async def calculate_price_difference(self, price1: float, price2: float) -> float:
        """
        Calculate percentage difference between two prices.

        Args:
            price1 (float): First price
            price2 (float): Second price

        Returns:
            float: Price difference as a decimal (e.g., 0.05 for 5%)
        """
        if not (self.validate_price(price1) and self.validate_price(price2)):
            raise ValueError("Invalid prices provided")

        return abs(price2 - price1) / price1

    def get_current_price(self, token: str) -> float:
        """
        Get current price from cache if available and not expired.

        Args:
            token (str): Token identifier

        Returns:
            float: Current price
        """
        cache_entry = self._price_cache.get(token)
        if cache_entry:
            timestamp, price = cache_entry
            if datetime.now() - timestamp < self._cache_duration:
                return price

        # Return mock price for testing - in production this would fetch from API
        price = 1000.0  # Mock price
        self._price_cache[token] = (datetime.now(), price)
        return price

    async def get_prices(self, tokens: List[str]) -> Dict[str, float]:
        """
        Get prices for multiple tokens.

        Args:
            tokens (List[str]): List of token identifiers

        Returns:
            Dict[str, float]: Token prices

        Raises:
            Exception: If price fetching fails
        """
        try:
            prices = await self.get_mcp_prices(tokens)
            if not prices:
                raise Exception("Failed to fetch prices")

            # Validate all prices
            for token, price in prices.items():
                if not self.validate_price(price):
                    raise ValueError(f"Invalid price for {token}: {price}")

            # Update cache
            now = datetime.now()
            for token, price in prices.items():
                self._price_cache[token] = (now, price)

            return prices

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            raise

    async def analyze_market_conditions(self, token: str) -> Dict[str, Any]:
        """
        Analyze market conditions for token.

        Args:
            token (str): Token to analyze

        Returns:
            Dict[str, Any]: Market conditions
        """
        try:
            # Get market analysis from MCP
            response = await call_mcp_tool(
                server_name="market-analysis",
                tool_name="assess_market_conditions",
                arguments={
                    "token": token,
                    "metrics": ["volatility", "volume", "liquidity", "trend"],
                },
            )

            if not response.get("data"):
                raise ValueError("No market data received")

            return response["data"]

        except Exception as e:
            logger.error(f"Failed to analyze market conditions: {e}")
            return {"success_rate": 0, "liquidity": 0, "volatility": 1}

    async def get_mcp_prices(self, tokens: List[str]) -> Dict[str, float]:
        """
        Get current prices from MCP.

        Args:
            tokens (List[str]): List of token identifiers

        Returns:
            Dict[str, float]: Current prices

        Raises:
            Exception: If price fetching fails
        """
        try:
            response = await call_mcp_tool(
                server_name="crypto-price",
                tool_name="get_prices",
                arguments={"coins": tokens, "include_24h_change": True},
            )

            if not response.get("data"):
                raise ValueError("No price data received")

            return response["data"]

        except Exception as e:
            logger.error(f"Failed to get prices: {e}")
            raise

    async def monitor_prices(self, tokens: List[str]):
        """
        Monitor prices for tokens.

        Args:
            tokens (List[str]): List of token identifiers

        Yields:
            Dict[str, float]: Updated prices
        """
        while True:
            try:
                prices = await self.get_mcp_prices(tokens)
                if prices:
                    yield prices
            except Exception as e:
                logger.error(f"Price monitoring error: {e}")
                yield {}
