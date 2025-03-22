"""Service for interacting with the memory bank system."""

from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime, timedelta
import logging
from pathlib import Path

from ..core.logging import get_logger
from arbitrage_bot.core.memory.memory_bank import MemoryBank

logger = get_logger("memory_service")

class MemoryService:
    """Service for managing memory bank interactions."""

    def __init__(self):
        self.memory_bank: Optional[MemoryBank] = None
        self._cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._last_update = datetime.min
        self._subscribers: List[asyncio.Queue] = []

    async def initialize(self) -> None:
        """Initialize the memory service."""
        try:
            # Initialize memory bank with default storage directory
            self.memory_bank = MemoryBank(storage_dir="data/memory_bank")
            await self.memory_bank.initialize()
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
        
        if self.memory_bank:
            await self.memory_bank.save_final_state()
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
            metrics = await self.memory_bank._load_metrics()
            opportunities = await self._load_opportunities()
            history = await self._load_execution_history()

            # Process and format data
            state = {
                "metrics": metrics,
                "opportunities": self._process_opportunities(opportunities),
                "trade_history": self._process_trade_history(history),
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

    async def _load_opportunities(self) -> List[Dict[str, Any]]:
        """Load opportunities from storage."""
        try:
            opps_file = self.memory_bank.storage_dir / 'metrics' / 'opportunities.json'
            
            if not opps_file.exists():
                return []
            
            with open(opps_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load opportunities: {e}")
            return []

    async def _load_execution_history(self) -> List[Dict[str, Any]]:
        """Load execution history from storage."""
        try:
            history_file = self.memory_bank.storage_dir / 'history' / 'execution_history.json'
            
            if not history_file.exists():
                return []
            
            with open(history_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load execution history: {e}")
            return []

    def _process_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and format opportunity data."""
        processed = []
        for opp in opportunities:
            try:
                processed.append({
                    "token_pair": opp.get("token_pair", "unknown"),
                    "profit_potential": float(opp.get("profit_potential", 0)),
                    "confidence": float(opp.get("confidence", 0)),
                    "timestamp": opp.get("timestamp")
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
                    "token_pair": trade.get("token_pair"),
                    "success": trade.get("success", False),
                    "profit": float(trade.get("profit", 0)),
                    "gas_used": int(trade.get("gas_used", 0)),
                    "execution_time": float(trade.get("execution_time", 0))
                })
            except Exception as e:
                logger.error(f"Error processing trade: {e}")
        return processed