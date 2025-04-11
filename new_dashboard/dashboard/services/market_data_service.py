"""Service for managing market data and analysis."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..core.logging import get_logger
from .memory_service import MemoryService
from .metrics_service import MetricsService
from arbitrage_bot.core.arbitrage.enhanced_market_data_provider import (
    EnhancedMarketDataProvider,
)
from arbitrage_bot.core.web3.web3_manager import Web3Manager

logger = get_logger("market_data_service")


# Mock Web3Manager for dashboard use when real one can't be initialized
class MockWeb3Manager:
    """Mock Web3Manager for dashboard use."""

    async def initialize(self):
        """Initialize the mock Web3Manager."""
        logger.info("Mock Web3Manager initialized")

    async def cleanup(self):
        """Clean up the mock Web3Manager."""
        logger.info("Mock Web3Manager cleaned up")

    async def get_balance(self, address):
        """Get mock balance."""
        return 1000000000000000000  # 1 ETH

    def from_wei(self, value, unit):
        """Convert from wei."""
        if unit == "ether":
            return value / 1000000000000000000
        return value


class MarketDataService:
    """Service for managing market data and analysis."""

    def __init__(
        self,
        memory_service: MemoryService,
        metrics_service: MetricsService,
        config: Dict[str, Any],
    ):
        """Initialize market data service.

        Args:
            memory_service: Memory service instance
            metrics_service: Metrics service instance
            config: Configuration dictionary
        """
        self.memory_service = memory_service
        self.metrics_service = metrics_service
        self._config = config
        self._subscribers: List[asyncio.Queue] = []
        self._current_data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._initialized = False

        # Create a modified config for EnhancedMarketDataProvider
        # It expects provider_url at the top level, but our config has it under web3.rpc_url
        enhanced_config = config.copy()
        logger.info(f"Creating enhanced config for market data provider")

        # Check if web3 config exists, if not create it
        if "web3" not in config:
            logger.info("Adding default web3 configuration")
            config["web3"] = {"rpc_url": "https://mainnet.base.org", "chain_id": 8453}

        if "web3" in config and "rpc_url" in config["web3"]:
            enhanced_config["provider_url"] = config["web3"]["rpc_url"]
            enhanced_config["chain_id"] = config["web3"].get("chain_id")
            logger.info(f"Added provider_url: {enhanced_config['provider_url']}")

        # Add market_data configuration if it doesn't exist
        if "market_data" not in enhanced_config:
            logger.info("Adding default market_data configuration")
            enhanced_config["market_data"] = {
                "update_interval_seconds": 5,
                "price_cache_ttl": 30,
                "liquidity_cache_ttl": 60,
                "max_price_deviation": 5.0,
                "min_liquidity_threshold": 10000,
            }
        logger.info(
            f"Enhanced config created with keys: {list(enhanced_config.keys())}"
        )

        # Initialize market data components
        try:
            logger.info("Initializing EnhancedMarketDataProvider")
            self._market_data_provider = EnhancedMarketDataProvider(enhanced_config)
            logger.info("EnhancedMarketDataProvider initialized")

            # Create a mock Web3Manager if we can't initialize the real one
            try:
                logger.info("Initializing Web3Manager")
                self._web3 = Web3Manager(config["web3"])
                logger.info("Web3Manager initialized")
            except Exception as e:
                logger.error(f"Error initializing Web3Manager: {e}")
                logger.info("Creating mock Web3Manager for dashboard")
                self._web3 = MockWeb3Manager()
        except Exception as e:
            logger.error(f"Error initializing market data components: {e}")
            raise

        # Cache for market data
        self._price_cache = {}
        self._liquidity_cache = {}
        self._last_update = None

    async def initialize(self):
        """Initialize the market data service."""
        if self._initialized:
            return

        try:
            logger.info("Initializing market data service")

            # Initialize components
            await self._web3.initialize()
            await self._market_data_provider.initialize()

            # Load initial state
            await self._load_state()

            # Start update task
            self._update_task = asyncio.create_task(self._update_loop())

            self._initialized = True
            logger.info("Market data service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing market data service: {e}")
            await self.cleanup()
            raise

    async def cleanup(self):
        """Clean up resources."""
        try:
            # Cancel update task
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
                self._update_task = None

            # Clean up components
            await self._market_data_provider.cleanup()
            await self._web3.cleanup()

            # Clear subscribers and cache
            self._subscribers.clear()
            self._price_cache.clear()
            self._liquidity_cache.clear()

            self._initialized = False
            logger.info("Market data service cleaned up")

        except Exception as e:
            logger.error(f"Error during market data service cleanup: {e}")
            raise

    async def _load_state(self):
        """Load state from memory service."""
        try:
            state = await self.memory_service.get_current_state()
            async with self._lock:
                self._current_data = state.get("market_data", {})

        except Exception as e:
            logger.error(f"Error loading state: {e}")
            raise

    async def _update_loop(self):
        """Background task to update market data."""
        try:
            while True:
                try:
                    # Get current market condition
                    market_condition = (
                        await self._market_data_provider.get_current_market_condition()
                    )

                    async with self._lock:
                        # Update market data
                        self._current_data.update(
                            {
                                "prices": market_condition.get("prices", {}),
                                "liquidity": market_condition.get("liquidity", {}),
                                "analysis": market_condition.get("analysis", {}),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                        # Track price updates
                        for dex, price in market_condition.get("prices", {}).items():
                            if dex in self._price_cache:
                                old_price = self._price_cache[dex]
                                await self.metrics_service.record_price_update(
                                    {
                                        "dex": dex,
                                        "old_price": old_price,
                                        "new_price": price,
                                    }
                                )

                        # Update caches
                        self._price_cache = dict(market_condition.get("prices", {}))
                        self._liquidity_cache = dict(
                            market_condition.get("liquidity", {})
                        )
                        self._last_update = datetime.utcnow()

                        # Calculate price spreads
                        if "prices" in market_condition:
                            prices = market_condition["prices"]
                            spreads = {}
                            best_spread = 0.0
                            best_spread_pair = None

                            for dex1 in prices:
                                for dex2 in prices:
                                    if dex1 < dex2:  # Ensure unique pairs
                                        price1 = prices[dex1]
                                        price2 = prices[dex2]
                                        spread = abs(price1 - price2)
                                        spread_percent = (
                                            spread / min(price1, price2)
                                        ) * 100
                                        spreads[f"{dex1}-{dex2}"] = {
                                            "spread": spread,
                                            "spread_percent": spread_percent,
                                            "profitable": spread_percent
                                            > 0.5,  # Minimum threshold
                                        }

                                        if spread_percent > best_spread:
                                            best_spread = spread_percent
                                            best_spread_pair = (dex1, dex2)

                            self._current_data["spreads"] = spreads

                            # Record potential opportunity if spread is significant
                            if best_spread > 0.5 and best_spread_pair:
                                await self.metrics_service.record_opportunity(
                                    {
                                        "dex_pair": best_spread_pair,
                                        "spread": best_spread,
                                        "profit_potential": best_spread
                                        * min(
                                            self._liquidity_cache.get(
                                                best_spread_pair[0], 0
                                            ),
                                            self._liquidity_cache.get(
                                                best_spread_pair[1], 0
                                            ),
                                        )
                                        / 100,
                                    }
                                )

                        # Save to memory service
                        await self.memory_service.update_state(
                            {"market_data": dict(self._current_data)}
                        )

                        # Notify subscribers
                        await self._notify_subscribers()

                except Exception as e:
                    logger.error(f"Error updating market data: {e}")

                # Wait before next update
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Market data update loop cancelled")
            raise

    async def _notify_subscribers(self):
        """Notify subscribers of market data updates."""
        if not self._subscribers:
            return

        try:
            # Create a copy of the data
            data_copy = {
                "market_data": dict(self._current_data),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Send to all subscribers
            for queue in self._subscribers:
                try:
                    await queue.put(data_copy)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")

        except Exception as e:
            logger.error(f"Error in notify subscribers: {e}")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to market data updates.

        Returns:
            Queue that will receive market data updates
        """
        queue = asyncio.Queue()
        self._subscribers.append(queue)

        # Send initial data
        try:
            data_copy = {
                "market_data": dict(self._current_data),
                "timestamp": datetime.utcnow().isoformat(),
            }
            await queue.put(data_copy)
        except Exception as e:
            logger.error(f"Error sending initial data to subscriber: {e}")

        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from market data updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def get_current_market_data(self) -> Dict[str, Any]:
        """Get current market data.

        Returns:
            Current market data dictionary
        """
        async with self._lock:
            return {
                "market_data": dict(self._current_data),
                "timestamp": datetime.utcnow().isoformat(),
            }
