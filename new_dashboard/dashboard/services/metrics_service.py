"""Service for collecting and analyzing system metrics."""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
import statistics
import logging

from ..core.logging import get_logger

logger = get_logger("metrics_service")

class MetricsService:
    """Service for managing system metrics and analytics."""

    def __init__(self, memory_service):
        self.memory_service = memory_service
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._last_update = datetime.min
        self._subscribers: List[asyncio.Queue] = []

    async def initialize(self) -> None:
        """Initialize the metrics service."""
        try:
            # Start background update task
            self._update_task = asyncio.create_task(self._background_update())
            logger.info("Started metrics update task")

        except Exception as e:
            logger.error(f"Failed to initialize metrics service: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the metrics service."""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
        logger.info("Metrics service shut down")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to metrics updates."""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from metrics updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        async with self._cache_lock:
            # Return cached data if it's fresh enough
            if (datetime.now() - self._last_update) < timedelta(seconds=5):
                return self._metrics_cache.copy()

        try:
            # Get current memory state
            memory_state = await self.memory_service.get_current_state()
            
            # Calculate metrics
            metrics = {
                "performance": await self._calculate_performance_metrics(memory_state),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Update cache
            async with self._cache_lock:
                self._metrics_cache = metrics.copy()
                self._last_update = datetime.now()

            return metrics

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _background_update(self) -> None:
        """Background task to keep metrics updated."""
        while True:
            try:
                # Get current metrics
                metrics = await self.get_current_metrics()

                # Notify subscribers
                for queue in self._subscribers:
                    try:
                        await queue.put(metrics)
                    except Exception as e:
                        logger.error(f"Error notifying subscriber: {e}")

                await asyncio.sleep(5)  # Update every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background update: {e}")
                await asyncio.sleep(5)

    async def _calculate_performance_metrics(self, memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance-related metrics."""
        try:
            # Get metrics from memory state
            metrics = memory_state.get("metrics", {})
            performance = metrics.get("performance", {})
            
            # Log metrics for debugging
            logger.debug(f"Processing metrics from memory state: {metrics}")
            
            # Return performance metrics directly
            # The memory service already calculates these correctly
            return {
                "success_rate": performance.get("success_rate", 0),
                "total_profit": performance.get("total_profit", 0),
                "profit_trend": performance.get("profit_trend", [])
            }

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }