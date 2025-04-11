"""Memory-based market analyzer for efficient market analysis."""

import logging
import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from ..web3.web3_manager import Web3Manager
# from ..models.market_models import MarketCondition, MarketTrend, PricePoint # Removed unused imports

logger = logging.getLogger(__name__)


class MemoryMarketAnalyzer:
    """Analyzes market conditions using in-memory data."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize memory market analyzer."""
        self.web3_manager = web3_manager
        self.config = config
        self.dex_manager = None
        self._price_cache = {}  # type: Dict[str, Tuple[datetime, float]]
        self._cache_duration = timedelta(seconds=30)
        self.market_conditions = {}
        self._cache_lock = asyncio.Lock()
        self._market_lock = asyncio.Lock()
        self._init_lock = asyncio.Lock()
        self.initialized = False
        logger.debug("Memory market analyzer initialized")

    async def initialize(self) -> bool:
        """Initialize the market analyzer."""
        if self.initialized:
            return True

        async with self._init_lock:
            if self.initialized:  # Double-check under lock
                return True

            try:
                async with self._market_lock:
                    # Initialize market conditions
                    self.market_conditions = {
                        "prices": {},
                        "trends": {},
                        "volumes": {},
                        "liquidity": {},
                        "volatility": {},
                        "last_update": datetime.now(),
                    }

                self.initialized = True
                logger.debug("Memory market analyzer initialized successfully")
                return True

            except Exception as e:
                logger.error("Failed to initialize memory market analyzer: %s", str(e))
                return False

    def set_dex_manager(self, dex_manager: Any) -> None:
        """Set the DEX manager instance."""
        self.dex_manager = dex_manager
        logger.debug("DEX manager set in market analyzer")

    async def get_market_condition(
        self, token: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get current market condition for token."""
        try:
            if not self.initialized and not await self.initialize():
                return None

            # If token is a string (symbol), get token data from config
            if isinstance(token, str):
                token_data = self.config.get("tokens", {}).get(token)
                if not token_data:
                    logger.error("Token %s not found in config", token)
                    return None
            else:
                token_data = token

            # Get real price data
            if not token_data or "address" not in token_data:
                logger.error("Invalid token data: %s", str(token_data))
                return None

            price = await self._fetch_real_price(token_data)
            if price is None:
                return None

            price_decimal = Decimal(str(price))

            # Create market condition
            condition = {
                "price": float(price_decimal),
                "trend": {
                    "direction": "sideways",
                    "strength": 0.0,
                    "duration": 0.0,
                    "volatility": 0.0,
                    "confidence": 0.0,
                },
                "volume_24h": 0.0,
                "liquidity": 0.0,
                "volatility_24h": 0.0,
                "price_impact": 0.0,
                "last_updated": datetime.now().timestamp(),
            }

            return condition

        except Exception as e:
            logger.error("Failed to get market condition: %s", str(e))
            return None

    async def _fetch_real_price(self, token: Dict[str, Any]) -> Optional[float]:
        """Fetch real price data from all enabled DEXes."""
        try:
            # Check cache first
            async with self._cache_lock:
                cache_entry = self._price_cache.get(token["address"])
                if cache_entry:
                    timestamp, price = cache_entry
                    if datetime.now() - timestamp < self._cache_duration:
                        return price

            # Ensure token address is valid
            address = token["address"]
            if not address or not self.web3_manager.w3.is_address(address):
                raise ValueError("Invalid token address: %s" % address)

            # Get all enabled DEXes
            enabled_dexes = [
                name
                for name, config in self.config.get("dexes", {}).items()
                if config.get("enabled", False)
            ]

            if not enabled_dexes:
                raise ValueError("No enabled DEXes found in config")

            prices = []
            errors = []

            # Try to get price from each enabled DEX
            for dex_name in enabled_dexes:
                try:
                    dex = self.dex_manager.get_dex(dex_name)
                    if not dex:
                        logger.debug("Failed to get %s instance", dex_name)
                        continue

                    # Ensure DEX is initialized
                    if not dex.initialized:
                        if not await dex.initialize():
                            logger.debug("Failed to initialize %s", dex_name)
                            continue

                    price = await dex.get_token_price(address)
                    if self._validate_price(price):
                        prices.append(price)
                    else:
                        logger.debug("Invalid price from %s: %s", dex_name, str(price))

                except Exception as e:
                    errors.append("%s: %s" % (dex_name, str(e)))
                    continue

            if not prices:
                error_msg = "Failed to get valid price from any DEX"
                if errors:
                    error_msg += ". Errors: %s" % "; ".join(errors)
                logger.error(error_msg)
                return None

            # Sort prices and calculate median
            prices.sort()
            mid = len(prices) // 2

            # Calculate median price
            if len(prices) % 2 == 0 and len(prices) > 0:
                median_price = (prices[mid - 1] + prices[mid]) / 2
            else:
                median_price = prices[mid]

            # Update cache
            async with self._cache_lock:
                self._price_cache[address] = (datetime.now(), median_price)

            return median_price

        except Exception as e:
            logger.error("Error fetching real price: %s", str(e))
            return None

    def _validate_price(self, price: float) -> bool:
        """Validate if a price is valid."""
        if not isinstance(price, (int, float, Decimal)):
            return False
        try:
            float_price = float(price)
            return float_price > 0 and not (
                float_price == float("inf") or float_price != float_price
            )  # Check for inf and nan
        except (ValueError, TypeError):
            return False

    async def get_market_summary(self) -> Dict[str, Any]:
        """Get current market summary."""
        try:
            async with self._market_lock:
                return {
                    "conditions": self.market_conditions.copy(),
                    "timestamp": datetime.now().timestamp(),
                }
        except Exception as e:
            logger.error("Failed to get market summary: %s", str(e))
            return {}


async def create_memory_market_analyzer(
    web3_manager: Web3Manager, config: Dict[str, Any]
) -> MemoryMarketAnalyzer:
    """Create and initialize memory market analyzer."""
    try:
        analyzer = MemoryMarketAnalyzer(web3_manager, config)
        if not await analyzer.initialize():
            raise RuntimeError("Failed to initialize memory market analyzer")
        logger.debug("Created memory market analyzer")
        return analyzer
    except Exception as e:
        logger.error("Failed to create memory market analyzer: %s", str(e))
        raise
