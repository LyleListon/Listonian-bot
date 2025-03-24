"""Service for collecting and analyzing system metrics."""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta, timezone
import statistics
import json
from pathlib import Path
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
        self._last_update = datetime.min.replace(tzinfo=timezone.utc)
        self._subscribers: List[asyncio.Queue] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the metrics service."""
        if self._initialized:
            return

        try:
            # Ensure memory service is initialized
            if not hasattr(self.memory_service, '_initialized') or not self.memory_service._initialized:
                raise RuntimeError("Memory service not initialized")

            # Initialize metrics cache
            metrics = await self.get_current_metrics()
            async with self._cache_lock:
                self._metrics_cache = metrics
                self._last_update = datetime.now(timezone.utc)

            # Start background update task
            self._update_task = asyncio.create_task(self._background_update())
            self._initialized = True
            logger.info("Metrics service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize metrics service: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the metrics service."""
        if not self._initialized:
            return

        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None

        self._initialized = False
        logger.info("Metrics service shut down")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to metrics updates."""
        if not self._initialized:
            raise RuntimeError("Metrics service not initialized")
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from metrics updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        if not self._initialized and self._metrics_cache:
            async with self._cache_lock:
                return self._metrics_cache.copy()

        try:
            logger.info("Getting current metrics...")
            
            # Get current memory state
            memory_state = await self.memory_service.get_current_state()
            
            # Get metrics from memory state
            metrics = {
                "metrics": await self._calculate_performance_metrics(memory_state),
                "gas_price": memory_state.get("market_data", {}).get("gas_price", 0),
                "system": memory_state.get("system_status", {}).get("system", {
                    "cpu_usage": memory_state.get("system", {}).get("cpu_usage", 0),
                    "memory_usage": memory_state.get("system", {}).get("memory_usage", 0),
                    "disk_usage": memory_state.get("system", {}).get("disk_usage", 0)
                }),
                "opportunities": await self._get_active_opportunities(memory_state),
                "trade_history": await self._get_trade_history(memory_state),
                "timestamp": datetime.utcnow().isoformat()
            }

            logger.info(f"Retrieved metrics: {json.dumps(metrics, indent=2)}")

            # Update cache
            async with self._cache_lock:
                self._metrics_cache = metrics.copy()
                self._last_update = datetime.now(timezone.utc)

            return metrics

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return self._get_default_metrics()

    def _get_default_metrics(self) -> Dict[str, Any]:
        """Get default metrics structure."""
        return {
            "metrics": {
                "success_rate": 0,
                "total_profit_eth": 0,
                "total_trades": 0,
                "profit_trend": []
            },
            "gas_price": 0,
            "system": {
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0
            },
            "opportunities": [],
            "trade_history": [],
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _background_update(self) -> None:
        """Background task to keep metrics updated."""
        while True:
            try:
                if not self._initialized:
                    break

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
            
            # Calculate success rate from trade history
            trades = memory_state.get("trade_history", [])
            success_rate = len([t for t in trades if t.get("success", False)]) / len(trades) if trades else 0
            
            return {
                "success_rate": success_rate,
                "total_profit_eth": sum(float(t.get("net_profit", 0)) for t in trades if t.get("success", False)),
                "total_trades": len(trades),
                "profit_trend": self._calculate_profit_trend(trades)
            }

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {
                "success_rate": 0,
                "total_profit_eth": 0,
                "total_trades": 0,
                "profit_trend": []
            }

    def _calculate_profit_trend(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate profit trend over time."""
        try:
            now = datetime.now(timezone.utc)
            trend = []
            
            for i in range(24):
                start_time = now - timedelta(hours=24-i)
                end_time = now - timedelta(hours=23-i)
                period_trades = [
                    t for t in trades 
                    if t.get("success", False) and 
                    datetime.fromisoformat(t["timestamp"]).replace(tzinfo=timezone.utc) >= start_time and
                    datetime.fromisoformat(t["timestamp"]).replace(tzinfo=timezone.utc) < end_time
                ]
                trend.append({
                    "timestamp": start_time.isoformat(),
                    "profit": sum(float(t.get("net_profit", 0)) for t in period_trades)
                })
            return trend
        except Exception as e:
            logger.error(f"Error calculating profit trend: {e}")
            return []

    async def _get_active_opportunities(self, memory_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get current active opportunities."""
        try:
            opportunities = memory_state.get("opportunities", [])
            return [
                {
                    "token_pair": opp.get("token_pair", "Unknown"),
                    "dex_1": opp.get("dex_1", "Unknown"),
                    "dex_2": opp.get("dex_2", "Unknown"),
                    "potential_profit": opp.get("potential_profit", 0),
                    "confidence": opp.get("confidence", 0),
                }
                for opp in opportunities
            ]
        except Exception as e:
            logger.error(f"Error getting active opportunities: {e}")
            return []

    async def _get_trade_history(self, memory_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recent trade history."""
        try:
            trades = memory_state.get("trade_history", [])
            return [
                {
                    "timestamp": trade.get("timestamp", datetime.utcnow().isoformat()),
                    "opportunity": {
                        "token_pair": trade.get("token_pair", "Unknown"),
                        "dex_1": trade.get("dex_1", "Unknown"),
                        "dex_2": trade.get("dex_2", "Unknown"),
                    },
                    "net_profit": trade.get("net_profit", 0),
                    "success": trade.get("success", False),
                }
                for trade in trades[-10:]  # Only return last 10 trades
            ]
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []