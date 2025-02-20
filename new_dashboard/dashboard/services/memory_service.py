"""Service for interacting with the memory bank system."""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path

from dashboard.core.logging import get_logger
from dashboard.core.mock_memory import create_memory_bank, MockMemoryBank

logger = get_logger("memory_service")

class MemoryService:
    """Service for managing memory bank interactions."""

    def __init__(self):
        self.memory_bank: Optional[MockMemoryBank] = None
        self._cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._last_update = datetime.min
        self._subscribers: List[asyncio.Queue] = []

    async def initialize(self) -> None:
        """Initialize the memory service."""
        try:
            # Initialize memory bank
            self.memory_bank = await create_memory_bank()
            logger.info("Memory bank initialized")

            # Start background update task
            self._update_task = asyncio.create_task(self._background_update())
            logger.info("Started background update task")

        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the memory service."""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
        logger.info("Memory service shut down")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to memory updates."""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from memory updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def get_current_state(self) -> Dict[str, Any]:
        """Get current memory bank state."""
        async with self._cache_lock:
            # Return cached data if it's fresh enough
            if (datetime.now() - self._last_update) < timedelta(seconds=1):
                return self._cache.copy()

        try:
            if not self.memory_bank:
                raise RuntimeError("Memory bank not initialized")

            # Get latest data
            opportunities = await self.memory_bank.get_recent_opportunities(max_age=300)
            trade_history = await self.memory_bank.get_trade_history(limit=100)
            memory_stats = await self.memory_bank.get_memory_stats()

            # Process and format data
            state = {
                "opportunities": self._process_opportunities(opportunities),
                "trade_history": self._process_trade_history(trade_history),
                "memory_stats": self._process_memory_stats(memory_stats),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Update cache
            async with self._cache_lock:
                self._cache = state.copy()
                self._last_update = datetime.now()

            return state

        except Exception as e:
            logger.error(f"Error getting memory state: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _background_update(self) -> None:
        """Background task to keep memory state updated."""
        while True:
            try:
                # Get current state
                state = await self.get_current_state()

                # Notify subscribers
                for queue in self._subscribers:
                    try:
                        await queue.put(state)
                    except Exception as e:
                        logger.error(f"Error notifying subscriber: {e}")

                await asyncio.sleep(5)  # Update every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background update: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    def _process_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and format opportunity data."""
        processed = []
        for opp in opportunities:
            try:
                processed.append({
                    "id": opp.get("id", "unknown"),
                    "profit": float(opp.get("profit", 0)),
                    "dex_pair": opp.get("dex_pair", "unknown"),
                    "timestamp": opp.get("timestamp"),
                    "status": opp.get("status", "unknown"),
                    "gas_estimate": float(opp.get("gas_estimate", 0)),
                    "confidence": float(opp.get("confidence", 0))
                })
            except Exception as e:
                logger.error(f"Error processing opportunity: {e}")
        return processed

    def _process_trade_history(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and format trade history data."""
        processed = []
        for trade in trades:
            try:
                processed.append({
                    "timestamp": trade.get("timestamp"),
                    "success": trade.get("success", False),
                    "net_profit": float(trade.get("net_profit", 0)),
                    "gas_cost": float(trade.get("gas_cost", 0)),
                    "tx_hash": trade.get("tx_hash"),
                    "error": trade.get("error")
                })
            except Exception as e:
                logger.error(f"Error processing trade: {e}")
        return processed

    def _process_memory_stats(self, stats: Any) -> Dict[str, Any]:
        """Process and format memory statistics."""
        try:
            return {
                "cache_size": stats.cache_size,
                "total_size_bytes": stats.total_size_bytes,
                "total_entries": stats.total_entries,
                "categories": stats.categories,
                "cache_hits": stats.cache_hits,
                "cache_misses": stats.cache_misses
            }
        except Exception as e:
            logger.error(f"Error processing memory stats: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }