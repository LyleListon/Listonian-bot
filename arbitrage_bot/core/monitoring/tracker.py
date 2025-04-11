"""Core performance tracking functionality."""

import logging
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import asyncio

from ...utils.database import Database

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time


class PerformanceTracker:
    """Tracks and analyzes trading performance."""

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize performance tracker.

        Args:
            db (Database, optional): Database instance. Creates new one if not provided.
        """
        self.db = db if db else Database()
        self.start_time = time.time()
        self.initialized = False

        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Cache settings
        self.cache_ttl = CACHE_TTL
        self.batch_size = BATCH_SIZE

        # Caches with TTL
        self._metrics_cache = {}  # Cache for metrics
        self._trades_cache = {}  # Cache for trades
        self._summary_cache = {}  # Cache for performance summaries

        # Cache timestamps
        self._metrics_cache_times = {}
        self._trades_cache_times = {}
        self._summary_cache_times = {}

        # Locks for thread safety
        self._cache_lock = asyncio.Lock()
        self._db_lock = asyncio.Lock()

        # Trade batching
        self._trade_batch = []
        self._last_batch_flush = time.time()
        self._batch_lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """Initialize performance tracker."""
        try:
            # Start cache cleanup task
            self._cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())

            # Start batch flush task
            self._batch_task = asyncio.create_task(self._periodic_batch_flush())

            self.initialized = True
            logger.info("Performance tracker initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize performance tracker: {e}")
            return False

    async def track_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Track completed trade with batching."""
        try:
            trade_data["timestamp"] = datetime.utcnow()

            async with self._batch_lock:
                self._trade_batch.append(trade_data)

                # Flush if batch is full
                if len(self._trade_batch) >= self.batch_size:
                    await self._flush_trade_batch()

            logger.debug("Trade queued for tracking: %s", trade_data)
            return True
        except Exception as e:
            logger.error("Error tracking trade: %s", e)
            return False

    async def _flush_trade_batch(self) -> None:
        """Flush trade batch to database."""
        try:
            async with self._batch_lock:
                if not self._trade_batch:
                    return

                # Save batch to database
                await self.db.save_trades(self._trade_batch)

                # Clear batch
                self._trade_batch = []
                self._last_batch_flush = time.time()

        except Exception as e:
            logger.error(f"Error flushing trade batch: {e}")

    async def _periodic_batch_flush(self) -> None:
        """Periodically flush trade batch."""
        try:
            while True:
                # Flush if it's been too long
                if time.time() - self._last_batch_flush > 5:  # 5 seconds
                    await self._flush_trade_batch()
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in periodic batch flush: {e}")

    async def get_trade_metrics(self, token: str) -> Dict[str, Any]:
        """Get metrics for specific token with caching."""
        try:
            # Check cache
            cache_key = f"metrics:{token}"
            metrics = await self._get_cached_data(
                cache_key, self._metrics_cache, self._metrics_cache_times
            )
            if metrics:
                return metrics

            # Get trades from database
            trades = await self.db.get_trades({"token": token})
            if not trades:
                metrics = {
                    "token": token,
                    "total_trades": 0,
                    "success_rate": 0,
                    "total_profit": 0,
                    "average_profit": 0,
                }
            else:
                # Calculate metrics in thread pool
                loop = asyncio.get_event_loop()
                metrics = await loop.run_in_executor(
                    self.executor, self._calculate_trade_metrics, trades, token
                )

            # Update cache
            await self._update_cache(
                cache_key, metrics, self._metrics_cache, self._metrics_cache_times
            )

            return metrics

        except Exception as e:
            logger.error("Error getting trade metrics: %s", e)
            return {}

    def _calculate_trade_metrics(
        self, trades: List[Dict[str, Any]], token: str
    ) -> Dict[str, Any]:
        """Calculate trade metrics (CPU-bound)."""
        try:
            total_trades = len(trades)
            successful_trades = len([t for t in trades if t["status"] == "completed"])
            success_rate = successful_trades / total_trades if total_trades > 0 else 0

            profits = [t.get("profit", 0) for t in trades if t["status"] == "completed"]
            total_profit = sum(profits)
            average_profit = (
                total_profit / successful_trades if successful_trades > 0 else 0
            )

            return {
                "token": token,
                "total_trades": total_trades,
                "success_rate": success_rate,
                "total_profit": total_profit,
                "average_profit": average_profit,
            }
        except Exception as e:
            logger.error(f"Error calculating trade metrics: {e}")
            return {
                "token": token,
                "total_trades": 0,
                "success_rate": 0,
                "total_profit": 0,
                "average_profit": 0,
            }

    async def get_token_performance(
        self, token: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get token performance history with caching."""
        try:
            # Check cache
            cache_key = f"performance:{token}:{days}"
            performance = await self._get_cached_data(
                cache_key, self._trades_cache, self._trades_cache_times
            )
            if performance:
                return performance

            # Get trades from database
            start_date = datetime.utcnow() - timedelta(days=days)
            trades = await self.db.get_trades(
                {"token": token, "timestamp": {"$gte": start_date}}
            )

            # Calculate performance in thread pool
            loop = asyncio.get_event_loop()
            performance = await loop.run_in_executor(
                self.executor, self._calculate_daily_performance, trades
            )

            # Update cache
            await self._update_cache(
                cache_key, performance, self._trades_cache, self._trades_cache_times
            )

            return performance

        except Exception as e:
            logger.error("Error getting token performance: %s", e)
            return []

    def _calculate_daily_performance(
        self, trades: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate daily performance metrics (CPU-bound)."""
        try:
            daily_data = defaultdict(lambda: {"trades": 0, "profit": 0})

            for trade in trades:
                day = trade["timestamp"].date()
                daily_data[day]["date"] = day
                daily_data[day]["trades"] += 1
                if trade["status"] == "completed":
                    daily_data[day]["profit"] += trade.get("profit", 0)

            return list(daily_data.values())

        except Exception as e:
            logger.error(f"Error calculating daily performance: {e}")
            return []

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary with caching."""
        try:
            # Check cache
            cache_key = "summary"
            summary = await self._get_cached_data(
                cache_key, self._summary_cache, self._summary_cache_times
            )
            if summary:
                return summary

            # Get trades from database
            trades = await self.db.get_trades({})
            if not trades:
                summary = {
                    "total_trades": 0,
                    "success_rate": 0,
                    "total_profit": 0,
                    "average_profit": 0,
                    "uptime": time.time() - self.start_time,
                }
            else:
                # Calculate summary in thread pool
                loop = asyncio.get_event_loop()
                summary = await loop.run_in_executor(
                    self.executor, self._calculate_performance_summary, trades
                )

            # Update cache
            await self._update_cache(
                cache_key, summary, self._summary_cache, self._summary_cache_times
            )

            return summary

        except Exception as e:
            logger.error("Error getting performance summary: %s", e)
            return {}

    def _calculate_performance_summary(
        self, trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate performance summary (CPU-bound)."""
        try:
            total_trades = len(trades)
            successful_trades = len([t for t in trades if t["status"] == "completed"])
            success_rate = successful_trades / total_trades if total_trades > 0 else 0

            profits = [t.get("profit", 0) for t in trades if t["status"] == "completed"]
            total_profit = sum(profits)
            average_profit = (
                total_profit / successful_trades if successful_trades > 0 else 0
            )

            return {
                "total_trades": total_trades,
                "success_rate": success_rate,
                "total_profit": total_profit,
                "average_profit": average_profit,
                "uptime": time.time() - self.start_time,
            }
        except Exception as e:
            logger.error(f"Error calculating performance summary: {e}")
            return {
                "total_trades": 0,
                "success_rate": 0,
                "total_profit": 0,
                "average_profit": 0,
                "uptime": time.time() - self.start_time,
            }

    async def get_time_period_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics for recent time period with caching."""
        try:
            # Check cache
            cache_key = f"period:{hours}"
            metrics = await self._get_cached_data(
                cache_key, self._metrics_cache, self._metrics_cache_times
            )
            if metrics:
                return metrics

            # Get trades from database
            start_time = datetime.utcnow() - timedelta(hours=hours)
            trades = await self.db.get_trades({"timestamp": {"$gte": start_time}})

            # Calculate metrics in thread pool
            loop = asyncio.get_event_loop()
            metrics = await loop.run_in_executor(
                self.executor, self._calculate_period_metrics, trades, hours
            )

            # Update cache
            await self._update_cache(
                cache_key, metrics, self._metrics_cache, self._metrics_cache_times
            )

            return metrics

        except Exception as e:
            logger.error("Error getting time period metrics: %s", e)
            return {}

    def _calculate_period_metrics(
        self, trades: List[Dict[str, Any]], hours: int
    ) -> Dict[str, Any]:
        """Calculate time period metrics (CPU-bound)."""
        try:
            if not trades:
                return {
                    "period_hours": hours,
                    "trades": 0,
                    "profit": 0,
                    "success_rate": 0,
                }

            total_trades = len(trades)
            successful_trades = len([t for t in trades if t["status"] == "completed"])
            success_rate = successful_trades / total_trades if total_trades > 0 else 0

            profits = [t.get("profit", 0) for t in trades if t["status"] == "completed"]
            total_profit = sum(profits)

            return {
                "period_hours": hours,
                "trades": total_trades,
                "profit": total_profit,
                "success_rate": success_rate,
            }
        except Exception as e:
            logger.error(f"Error calculating period metrics: {e}")
            return {
                "period_hours": hours,
                "trades": 0,
                "profit": 0,
                "success_rate": 0,
            }

    async def _get_cached_data(
        self, key: str, cache: Dict[str, Any], cache_times: Dict[str, float]
    ) -> Optional[Any]:
        """Get data from cache if not expired."""
        try:
            current_time = time.time()

            async with self._cache_lock:
                if key in cache:
                    last_update = cache_times.get(key, 0)
                    if current_time - last_update < self.cache_ttl:
                        return cache[key]
            return None

        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None

    async def _update_cache(
        self, key: str, data: Any, cache: Dict[str, Any], cache_times: Dict[str, float]
    ) -> None:
        """Update cache with new data."""
        try:
            async with self._cache_lock:
                cache[key] = data
                cache_times[key] = time.time()
        except Exception as e:
            logger.error(f"Error updating cache: {e}")

    async def _cleanup_caches(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()

            async with self._cache_lock:
                # Clean up metrics cache
                expired_metrics = [
                    key
                    for key, last_update in self._metrics_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_metrics:
                    del self._metrics_cache[key]
                    del self._metrics_cache_times[key]

                # Clean up trades cache
                expired_trades = [
                    key
                    for key, last_update in self._trades_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_trades:
                    del self._trades_cache[key]
                    del self._trades_cache_times[key]

                # Clean up summary cache
                expired_summaries = [
                    key
                    for key, last_update in self._summary_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_summaries:
                    del self._summary_cache[key]
                    del self._summary_cache_times[key]

        except Exception as e:
            logger.error(f"Error cleaning up caches: {e}")

    async def _periodic_cache_cleanup(self) -> None:
        """Periodically clean up caches."""
        try:
            while True:
                await self._cleanup_caches()
                await asyncio.sleep(self.cache_ttl / 2)  # Clean up every half TTL
        except Exception as e:
            logger.error(f"Error in periodic cache cleanup: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Flush any remaining trades
            await self._flush_trade_batch()

            # Cancel cleanup task
            if hasattr(self, "_cleanup_task"):
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Cancel batch task
            if hasattr(self, "_batch_task"):
                self._batch_task.cancel()
                try:
                    await self._batch_task
                except asyncio.CancelledError:
                    pass

            # Shutdown thread pool
            self.executor.shutdown(wait=True)

            logger.info("Performance tracker cleanup complete")
        except Exception as e:
            logger.error(f"Error during performance tracker cleanup: {e}")


async def create_performance_tracker(
    web3_manager=None, wallet_address=None, config=None, db: Optional[Database] = None
) -> PerformanceTracker:
    """
    Create performance tracker instance.

    Args:
        web3_manager: Web3 manager instance
        wallet_address: Wallet address to track
        config: Configuration dictionary
        db (Database, optional): Database instance

    Returns:
        PerformanceTracker: Performance tracker instance
    """
    tracker = PerformanceTracker(db)
    await tracker.initialize()
    return tracker


# Export the create function
__all__ = ["create_performance_tracker"]
