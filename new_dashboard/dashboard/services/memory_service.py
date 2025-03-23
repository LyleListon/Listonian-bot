"""Service for interacting with the memory bank system."""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
import glob

from ..core.logging import get_logger

logger = get_logger("memory_service")

class MemoryService:
    """Service for managing memory bank interactions."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._last_update = datetime.min
        self._subscribers: List[asyncio.Queue] = []
        self.storage_dir = Path("memory-bank")

    async def initialize(self) -> None:
        """Initialize the memory service."""
        try:
            # Initialize directory structure
            logger.info(f"Initializing memory service with storage dir: {self.storage_dir}")
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            (self.storage_dir / 'trades').mkdir(exist_ok=True)
            
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
                logger.debug("Returning cached state")
                return self._cache.copy()

        try:
            # Load trade history
            trades_dir = self.storage_dir / 'trades'
            trade_files = sorted(glob.glob(str(trades_dir / 'trade_*.json')))
            trades = []
            total_profit = 0
            successful_trades = 0
            
            for file in trade_files:
                try:
                    with open(file, 'r') as f:
                        trade = json.load(f)
                        trades.append(trade)
                        if trade['success'] and trade['net_profit'] is not None:
                            total_profit += float(trade['net_profit'])
                            successful_trades += 1
                except Exception as e:
                    logger.error(f"Error reading trade file {file}: {e}")
                    continue

            success_rate = successful_trades / len(trades) if trades else 0

            # Get latest gas price
            latest_gas = trades[-1]['gas_cost'] if trades else 0

            # Calculate profit trend (last 24 hours)
            now = datetime.now()
            profit_trend = []
            for i in range(24):
                start_time = now - timedelta(hours=24-i)
                end_time = now - timedelta(hours=23-i)
                period_trades = [
                    t for t in trades 
                    if t['success'] and 
                    datetime.fromisoformat(t['timestamp']) >= start_time and
                    datetime.fromisoformat(t['timestamp']) < end_time and
                    t['net_profit'] is not None
                ]
                period_profit = sum(float(t['net_profit']) for t in period_trades)
                profit_trend.append({
                    'timestamp': start_time.isoformat(),
                    'profit': period_profit
                })

            # Get active opportunities (trades from last 5 minutes)
            cutoff_time = now - timedelta(minutes=5)
            active_opportunities = [
                t['opportunity'] for t in trades
                if datetime.fromisoformat(t['timestamp']) >= cutoff_time
            ]

            # Build state object
            state = {
                "metrics": {
                    "gas_price": latest_gas,
                    "performance": {
                        "total_profit": total_profit,
                        "success_rate": success_rate,
                        "profit_trend": profit_trend
                    }
                },
                "opportunities": active_opportunities,
                "trade_history": trades[-10:],  # Last 10 trades
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