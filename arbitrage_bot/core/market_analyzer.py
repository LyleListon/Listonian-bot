"""
Market Analyzer Module

Analyzes market conditions and identifies arbitrage opportunities.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

from .dex.dex_manager import DexManager

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""

    token_id: str
    token_address: str
    buy_dex: str
    sell_dex: str
    buy_price: Decimal
    sell_price: Decimal
    profit_margin: Decimal
    timestamp: datetime
    tx_hash: Optional[str] = None
    gas_cost: Optional[Decimal] = None
    ml_score: Optional[float] = None


class MarketAnalyzer:
    """Analyzes market conditions for arbitrage opportunities."""

    def __init__(
        self,
        dex_manager: DexManager,
        config: Optional[Dict[str, Any]] = None,
        ml_system: Optional[Any] = None,
    ):
        """
        Initialize the market analyzer.

        Args:
            dex_manager: DEX manager instance
            config: Optional configuration
            ml_system: Optional ML system for opportunity scoring
        """
        self.dex_manager = dex_manager
        self.config = config or {}
        self.ml_system = ml_system
        self.initialized = False
        self.lock = asyncio.Lock()

        # Configuration
        self.min_profit_threshold = Decimal(
            str(self.config.get("min_profit_threshold", 0.001))
        )
        self.max_price_impact = Decimal(str(self.config.get("max_price_impact", 0.01)))
        self.min_liquidity = Decimal(str(self.config.get("min_liquidity", 1000)))

        # Cache for price data
        self._price_cache = {}
        self._liquidity_cache = {}

        # Cache TTL in seconds
        self.cache_ttl = int(self.config.get("price_cache_ttl", 5))

    async def initialize(self) -> bool:
        """
        Initialize the market analyzer.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize price monitoring
            await self._update_prices()

            # Start background price updates
            asyncio.create_task(self._price_monitor())

            self.initialized = True
            logger.info("Market analyzer initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize market analyzer: {e}")
            return False

    async def _price_monitor(self):
        """Monitor prices in the background."""
        while True:
            try:
                await self._update_prices()
                await asyncio.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Error updating prices: {e}")
                await asyncio.sleep(30)  # Longer delay on error

    async def _update_dex_prices(self, dex: str, tokens: List[str]) -> None:
        """Update prices for a single DEX."""
        try:
            # Create tasks for each token
            tasks = []
            for token in tokens:
                tasks.append(self._update_token_price(dex, token))

            # Run all tasks in parallel
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Failed to update prices for DEX {dex}: {e}")

    async def _update_token_price(self, dex: str, token: str) -> None:
        """Update price for a single token on a DEX."""
        try:
            # Get pool address
            pool_address = await self.dex_manager.get_pool_address(dex, token, None)
            if not pool_address:
                return

            # Get liquidity and price in parallel
            liquidity, price = await asyncio.gather(
                self.dex_manager.get_pool_liquidity(dex, pool_address),
                self.dex_manager.get_token_price(dex, pool_address, token),
            )

            if not liquidity or liquidity < self.min_liquidity:
                return

            # Update caches
            current_time = asyncio.get_event_loop().time()
            cache_key = f"{dex}:{token}"
            self._liquidity_cache[cache_key] = (current_time, liquidity)
            self._price_cache[cache_key] = (current_time, price)

        except Exception as e:
            logger.error(f"Failed to update price for {token} on {dex}: {e}")

    async def _update_prices(self):
        """Update current prices."""
        try:
            # Get all DEXs
            dexes = await self.dex_manager.get_all_dexes()

            # Get DEX info in parallel
            dex_infos = await asyncio.gather(
                *[self.dex_manager.get_dex_info(dex) for dex in dexes]
            )

            # Update prices for all DEXs in parallel
            update_tasks = []
            for dex, dex_info in zip(dexes, dex_infos):
                if dex_info:
                    update_tasks.append(
                        self._update_dex_prices(dex, list(dex_info.supported_tokens))
                    )

            await asyncio.gather(*update_tasks)

        except Exception as e:
            logger.error(f"Failed to update prices: {e}")

    async def get_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Get current arbitrage opportunities.

        Returns:
            List of arbitrage opportunities
        """
        if not self.initialized:
            raise RuntimeError("Market analyzer not initialized")

        opportunities = []

        try:
            # Get all DEXs
            dexes = await self.dex_manager.get_all_dexes()

            # Get common tokens and current prices in parallel
            common_tokens = await self._get_common_tokens(dexes)

            # Create tasks for each token-DEX combination
            price_tasks = []
            for token in common_tokens:
                for dex in dexes:
                    price_tasks.append(self._get_price(dex, token))

            # Get all prices in parallel
            prices = await asyncio.gather(*price_tasks)

            # Create price map
            price_map = {}
            idx = 0
            for token in common_tokens:
                for dex in dexes:
                    if prices[idx] is not None:
                        price_map[f"{dex}:{token}"] = prices[idx]
                    idx += 1

            # Find opportunities for all tokens in parallel
            opportunity_tasks = []
            for token in common_tokens:
                opportunity_tasks.append(
                    self._find_token_opportunities(token, dexes, price_map)
                )

            # Gather all opportunities
            all_opportunities = await asyncio.gather(*opportunity_tasks)
            for token_opportunities in all_opportunities:
                opportunities.extend(token_opportunities)

            # Score opportunities with ML system if available
            if self.ml_system and opportunities:
                scores = await self.ml_system.score_opportunities(opportunities)
                for opp, score in zip(opportunities, scores):
                    opp.ml_score = score

                # Sort by ML score if available, otherwise by profit margin
                opportunities.sort(
                    key=lambda x: getattr(x, "ml_score", x.profit_margin), reverse=True
                )
            else:
                # Sort by profit margin
                opportunities.sort(key=lambda x: x.profit_margin, reverse=True)

            # Log opportunity count
            if opportunities:
                logger.info(
                    f"Found {len(opportunities)} opportunities, "
                    f"best profit margin: {opportunities[0].profit_margin:.2%}"
                )

            return opportunities

        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return []

    async def _get_common_tokens(self, dexes: List[str]) -> List[str]:
        """Get tokens supported by multiple DEXs."""
        common_tokens = set()
        first = True

        # Get DEX info in parallel
        dex_infos = await asyncio.gather(
            *[self.dex_manager.get_dex_info(dex) for dex in dexes]
        )

        for dex_info in dex_infos:
            if not dex_info:
                continue

            if first:
                common_tokens = dex_info.supported_tokens
                first = False
            else:
                common_tokens &= dex_info.supported_tokens

        return list(common_tokens)

    async def _get_price(self, dex: str, token: str) -> Optional[Decimal]:
        """Get price from cache or update."""
        cache_key = f"{dex}:{token}"

        if cache_key in self._price_cache:
            timestamp, price = self._price_cache[cache_key]
            if asyncio.get_event_loop().time() - timestamp < self.cache_ttl:
                return price

        # Price not in cache or expired
        try:
            # Get pool address
            pool_address = await self.dex_manager.get_pool_address(dex, token, None)
            if not pool_address:
                return None

            # Get liquidity and price in parallel
            liquidity, price = await asyncio.gather(
                self.dex_manager.get_pool_liquidity(dex, pool_address),
                self.dex_manager.get_token_price(dex, pool_address, token),
            )

            if not liquidity or liquidity < self.min_liquidity:
                return None

            if price:
                # Update cache
                self._price_cache[cache_key] = (asyncio.get_event_loop().time(), price)
                return price

            return None

        except Exception as e:
            logger.error(f"Failed to get price for {token} on {dex}: {e}")
            return None

    async def _find_token_opportunities(
        self, token: str, dexes: List[str], price_map: Dict[str, Decimal]
    ) -> List[ArbitrageOpportunity]:
        """Find arbitrage opportunities for a specific token."""
        opportunities = []

        for buy_dex in dexes:
            buy_key = f"{buy_dex}:{token}"
            if buy_key not in price_map:
                continue

            buy_price = price_map[buy_key]

            for sell_dex in dexes:
                if buy_dex == sell_dex:
                    continue

                sell_key = f"{sell_dex}:{token}"
                if sell_key not in price_map:
                    continue

                sell_price = price_map[sell_key]

                # Calculate profit margin
                profit_margin = (sell_price - buy_price) / buy_price

                # Check if profitable
                if profit_margin > self.min_profit_threshold:
                    opportunities.append(
                        ArbitrageOpportunity(
                            token_id=token,
                            token_address=token,
                            buy_dex=buy_dex,
                            sell_dex=sell_dex,
                            buy_price=buy_price,
                            sell_price=sell_price,
                            profit_margin=profit_margin,
                            timestamp=datetime.utcnow(),
                        )
                    )

        return opportunities


async def create_market_analyzer(
    dex_manager: DexManager,
    config: Optional[Dict[str, Any]] = None,
    ml_system: Optional[Any] = None,
) -> MarketAnalyzer:
    """
    Create and initialize a market analyzer.

    Args:
        dex_manager: DEX manager instance
        config: Optional configuration
        ml_system: Optional ML system

    Returns:
        Initialized MarketAnalyzer instance
    """
    analyzer = MarketAnalyzer(dex_manager, config, ml_system)
    if not await analyzer.initialize():
        raise RuntimeError("Failed to initialize market analyzer")
    return analyzer
