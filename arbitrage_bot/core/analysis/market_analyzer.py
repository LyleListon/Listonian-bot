"""Market analysis utilities."""

__all__ = ["MarketAnalyzer", "create_market_analyzer"]

import logging
import math
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from ..web3.web3_manager import Web3Manager
from ..models.opportunity import Opportunity
# from ..models.market_models import MarketCondition, MarketTrend, PricePoint # Removed unused imports

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Analyzes market conditions and opportunities."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize market analyzer."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        # Type hint as comment to maintain compatibility
        self._price_cache = {}  # type: Dict[str, Tuple[datetime, float]]
        self._cache_duration = timedelta(seconds=30)  # Cache prices for 30 seconds
        self.market_conditions = {}  # Store market conditions for each token
        self.dex_instances = {}  # Store DEX instances
        self.dex_manager = None  # Will be set by DEX manager
        self._init_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._cleanup_lock = asyncio.Lock()
        self.initialized = False
        logger.debug("Market analyzer initialized")

    def set_dex_manager(self, dex_manager: Any) -> None:
        """Set the DEX manager instance."""
        self.dex_manager = dex_manager
        logger.debug("DEX manager set in market analyzer")

    async def initialize(self) -> bool:
        """Initialize the market analyzer."""
        if self.initialized:
            return True

        async with self._init_lock:
            # Double-check under lock
            if self.initialized:
                return True

            if not self.dex_manager:
                logger.error("DEX manager not set")
                return False

            try:
                # Verify DEX manager is ready
                if not self.dex_manager.is_ready():
                    logger.error("DEX manager not ready")
                    return False

                self.initialized = True
                return True
            except Exception as e:
                logger.error("Failed to initialize market analyzer: %s", str(e))
                return False

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if not self.initialized:
            return

        async with self._cleanup_lock:
            try:
                # Clear caches
                self._price_cache.clear()
                self.market_conditions.clear()
                self.initialized = False
                logger.debug("Market analyzer cleaned up")
            except Exception as e:
                logger.error("Error during cleanup: %s", str(e))

    def _validate_token_data(self, token_data: Optional[Dict[str, Any]]) -> bool:
        """Validate token data structure."""
        if not token_data or not isinstance(token_data, dict):
            return False
        if "address" not in token_data:
            return False
        if not self.w3.is_address(token_data["address"]):
            return False
        return True

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
                if not self._validate_token_data(token_data):
                    logger.error("Token %s not found in config", token)
                    return None
            else:
                token_data = token

            if not self._validate_token_data(token_data):
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

    async def _get_dex_instance(self, dex_name: str) -> Any:
        """Get DEX instance by name."""
        if not self.dex_manager:
            raise ValueError("DEX manager not set")
        return await self.dex_manager.get_dex(dex_name)

    async def _fetch_real_price(self, token: Dict[str, Any]) -> Optional[float]:
        """Fetch real price data from all enabled DEXes."""
        try:
            if not self.initialized and not await self.initialize():
                return None

            # Ensure token address is valid
            address = token["address"]
            if not address or not self.w3.is_address(address):
                raise ValueError("Invalid token address: %s", address)

            # Get prices from enabled DEXes
            prices = await self.dex_manager.get_token_price(address)
            if not prices:
                logger.error("No valid prices found for token %s", address)
                return None

            # Calculate median price to filter out outliers
            price_list = list(prices.values())
            price_list.sort()
            mid = len(price_list) // 2
            if len(price_list) % 2 == 0:
                return float((price_list[mid - 1] + price_list[mid]) / 2)
            else:
                return float(price_list[mid])

        except Exception as e:
            logger.error(
                "Error fetching real price for %s: %s",
                token.get("address", "unknown"),
                str(e),
            )
            return None

    async def validate_price(self, price: float) -> bool:
        """Validate if a price is valid."""
        if not isinstance(price, (int, float, Decimal)):
            return False
        try:
            float_price = float(price)
            return (
                float_price > 0
                and not math.isinf(float_price)
                and not math.isnan(float_price)
            )
        except (ValueError, TypeError):
            return False

    async def get_cached_price(self, token: str) -> Optional[float]:
        """Get price from cache if available and not expired."""
        async with self._cache_lock:
            cache_entry = self._price_cache.get(token)
            if cache_entry:
                timestamp, price = cache_entry
                if datetime.now() - timestamp < self._cache_duration:
                    return price
            return None

    async def get_current_price(self, token: str) -> float:
        """Get current price, using cache if available."""
        if not self.initialized and not await self.initialize():
            raise RuntimeError("Market analyzer not initialized")

        cached_price = await self.get_cached_price(token)
        if cached_price is not None:
            return cached_price

        token_data = self.config.get("tokens", {}).get(token)
        if not self._validate_token_data(token_data):
            raise ValueError("Token {} not found in config".format(token))

        price = await self._fetch_real_price(token_data)
        if price is None:
            raise ValueError("Could not fetch price for token {}".format(token))

        if not await self.validate_price(price):
            raise ValueError("Invalid price received for {}: {}".format(token, price))

        async with self._cache_lock:
            self._price_cache[token] = (datetime.now(), price)
            return price

    async def calculate_price_difference(self, price1: float, price2: float) -> float:
        """Calculate percentage difference between two prices."""
        if not all(
            await asyncio.gather(
                self.validate_price(price1), self.validate_price(price2)
            )
        ):
            raise ValueError("Invalid prices provided")
        return abs(float(price2) - float(price1)) / float(price1)

    async def get_opportunities(self) -> List[Opportunity]:
        """Get current arbitrage opportunities."""
        try:
            if not self.initialized and not await self.initialize():
                return []

            opportunities = []
            tokens = self.config.get("tokens", {})

            async def process_token(
                token_id: str, token_data: Dict[str, Any]
            ) -> Optional[Opportunity]:
                try:
                    if not token_data or "address" not in token_data:
                        logger.debug("Invalid token data for %s", token_id)
                        return None

                    # Get prices from enabled DEXes
                    prices = await self.dex_manager.get_token_price(
                        token_data["address"]
                    )
                    if not prices:
                        logger.debug("No prices found for token %s", token_id)
                        return None

                    # Find arbitrage opportunities
                    if len(prices) >= 2:
                        min_price = min(prices.values())
                        max_price = max(prices.values())
                        price_diff = (max_price - min_price) / min_price

                        # If price difference > 0.5%
                        if price_diff > Decimal("0.005"):
                            buy_dex = min(prices.items(), key=lambda x: x[1])[0]
                            sell_dex = max(prices.items(), key=lambda x: x[1])[0]

                            return Opportunity(
                                token_id=token_id,
                                token_address=token_data["address"],
                                buy_dex=buy_dex,
                                sell_dex=sell_dex,
                                buy_price=min_price,
                                sell_price=max_price,
                                profit_margin=price_diff,
                                market_condition=None,  # No market condition needed for opportunities
                                timestamp=datetime.now().timestamp(),
                            )
                    return None
                except Exception as e:
                    logger.error("Error processing token %s: %s", token_id, str(e))
                    return None

            opportunities = [
                opp
                for opp in await asyncio.gather(
                    *[
                        process_token(token_id, token_data)
                        for token_id, token_data in tokens.items()
                    ]
                )
                if opp is not None
            ]

            return opportunities

        except Exception as e:
            logger.error("Failed to get opportunities: %s", str(e))
            return []

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        try:
            return {
                "market_conditions": self.market_conditions,
                "dex_performance": {
                    dex: {"success_rate": 1.0, "avg_response_time": 0}
                    for dex in self.config.get("dexes", {}).keys()
                },
                "timestamp": datetime.now().timestamp(),
            }
        except Exception as e:
            logger.error("Failed to get performance metrics: %s", str(e))
            return {}


async def create_market_analyzer(
    web3_manager: Optional[Web3Manager] = None,
    config: Optional[Dict[str, Any]] = None,
    dex_manager: Optional[Any] = None,
) -> MarketAnalyzer:
    """Create and initialize a market analyzer instance."""
    try:
        if not web3_manager:
            web3_manager = Web3Manager()
            web3_manager.connect()

        if not config:
            from ...utils.config_loader import load_config

            config = load_config()

        analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)

        # Set DEX manager if provided
        if dex_manager:
            analyzer.set_dex_manager(dex_manager)

        # Initialize the analyzer
        if not await analyzer.initialize():
            await analyzer.cleanup()
            raise RuntimeError("Failed to initialize market analyzer")

        logger.debug("Market analyzer created and initialized successfully")
        return analyzer

    except Exception as e:
        logger.error("Failed to create market analyzer: %s", str(e))
        raise
