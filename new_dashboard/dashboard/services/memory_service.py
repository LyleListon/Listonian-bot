"""Service for interacting with the memory bank system."""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import glob
import psutil

from ..utils.logging import get_logger

logger = get_logger("memory_service")

class MemoryService:
    """Service for managing memory bank interactions."""

    def __init__(self, storage_dir: Optional[str] = None):
        self._cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._last_update = datetime.min.replace(tzinfo=timezone.utc)
        self._subscribers: List[asyncio.Queue] = []
        
        # Set storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(__file__).parent.parent.parent.parent / "memory-bank"
            
        logger.info(f"Setting storage directory to absolute path: {self.storage_dir.absolute()}")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory service."""
        if self._initialized:
            return

        try:
            # Initialize directory structure
            logger.info(f"Initializing memory service with storage dir: {self.storage_dir}")
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Create required subdirectories
            for subdir in ['trades', 'state', 'metrics']:
                (self.storage_dir / subdir).mkdir(exist_ok=True)
            
            # Initialize state files if they don't exist
            state_files = {
                'opportunities.json': {'opportunities': []},
                'executions.json': {},
                'market_state.json': {'network_status': 'initializing', 'gas_price': 0},
                'pool_metrics.json': {'pools': {}}
            }
            
            for filename, default_content in state_files.items():
                state_file = self.storage_dir / 'state' / filename
                if not state_file.exists():
                    with open(state_file, 'w') as f:
                        json.dump(default_content, f, indent=2)
                    logger.info(f"Created state file: {filename}")
            
            # Start background update task
            self._update_task = asyncio.create_task(self._background_update())
            self._initialized = True
            logger.info("Memory service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the memory service."""
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
        if not self._initialized:
            raise RuntimeError("Memory service not initialized")

        async with self._cache_lock:
            # Return cached data if it's fresh enough
            now = datetime.now(timezone.utc)
            if (now - self._last_update) < timedelta(seconds=1):
                logger.debug("Returning cached state")
                return self._cache.copy()

        try:
            state = await self._aggregate_state()
            return state
        except Exception as e:
            logger.error(f"Error getting memory state: {e}")
            return self._get_default_state()
            
    async def _aggregate_state(self) -> Dict[str, Any]:
        """Aggregate state from all memory bank files."""
        try:
            now = datetime.now(timezone.utc)
            logger.info("Aggregating state from memory bank files...")
            trades = []
            total_profit = 0
            successful_trades = 0
            
            # Load trade history
            trades_dir = self.storage_dir / 'trades'
            trade_files = sorted(glob.glob(str(trades_dir / 'trade_*.json')))
            
            for file in trade_files:
                try:
                    with open(file, 'r') as f:
                        trade = json.load(f)
                        trades.append(trade)
                        if trade.get('success', False) and trade.get('net_profit') is not None:
                            total_profit += float(trade['net_profit'])
                            successful_trades += 1
                except Exception as e:
                    logger.error(f"Error reading trade file {file}: {e}")
            
            # Load state files with defaults
            state_files = {
                'opportunities': {'opportunities': []},
                'executions': {},
                'market_state': {'network_status': 'initializing', 'gas_price': 0},
                'pool_metrics': {'pools': {}}
            }
            
            for name, default in state_files.items():
                file_path = self.storage_dir / 'state' / f'{name}.json'
                try:
                    logger.info(f"Reading state file: {file_path}")
                    if file_path.exists():
                        logger.debug(f"Reading state file: {file_path}")
                        with open(file_path, 'r') as f:
                            state_files[name] = json.load(f)
                            logger.info(f"Successfully loaded {name} with content: {json.dumps(state_files[name], indent=2)}")
                        logger.debug(f"Successfully loaded {name} with content length: {len(str(state_files[name]))}")
                except Exception as e:
                    logger.error(f"Error reading {name} file: {e}")
                    state_files[name] = default
            
            # Get system metrics
            try:
                system_metrics = {
                    "cpu_usage": psutil.cpu_percent(),
                    "memory_usage": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent
                }
            except Exception as e:
                logger.error(f"Error getting system metrics: {e}")
                system_metrics = {"cpu_usage": 0, "memory_usage": 0, "disk_usage": 0}
            
            # Check bot status
            bot_process = None
            try:
                for proc in psutil.process_iter(['name', 'cmdline']):
                    if 'python' in proc.info['name'].lower() and any(
                        'run_bot.py' in cmd for cmd in proc.info.get('cmdline', [])
                    ):
                        bot_process = proc
                        break
            except Exception as e:
                logger.error(f"Error checking bot process: {e}")
            
            success_rate = successful_trades / len(trades) if trades else 0
            latest_gas = float(trades[-1].get('gas_cost', 0)) if trades else 0

            # Calculate profit trend (last 24 hours)
            profit_trend = []
            for i in range(24):
                start_time = now - timedelta(hours=24-i)
                end_time = now - timedelta(hours=23-i)
                period_trades = [
                    t for t in trades 
                    if t.get('success', False) and 
                    datetime.fromisoformat(t['timestamp']).replace(tzinfo=timezone.utc) >= start_time and
                    datetime.fromisoformat(t['timestamp']).replace(tzinfo=timezone.utc) < end_time and
                    t.get('net_profit') is not None
                ]
                period_profit = sum(float(t['net_profit']) for t in period_trades)
                profit_trend.append({
                    'timestamp': start_time.isoformat(),
                    'profit': period_profit
                })

            # Build state object
            state = {
                "metrics": {
                    "gas_price": state_files['market_state'].get('gas_price', latest_gas),
                    "performance": {
                        "total_profit_eth": total_profit,
                        "success_rate": success_rate,
                        "profit_trend": profit_trend,
                        "successful_trades": successful_trades,
                        "total_trades": len(trades)
                    },
                    "system": system_metrics,
                    "pools": {
                        pool_id: {
                            "liquidity": metrics["metrics"]["liquidity"],
                            "volume_24h": metrics["metrics"]["volume_24h"],
                            "fees_24h": metrics["metrics"]["fees_24h"]
                        }
                        for pool_id, metrics in state_files['pool_metrics'].get("pools", {}).items()
                    }
                },
                "opportunities": state_files['opportunities'].get('opportunities', []),
                "trade_history": trades[-10:] if trades else [],  # Last 10 trades
                "executions": state_files['executions'],
                "system_status": {
                    "bot_status": "running" if bot_process else "stopped",
                    "network_status": state_files['market_state'].get('network_status', 'unknown'),
                    "last_update": now.isoformat()
                },
                "timestamp": now.isoformat(),
                "market_data": state_files['market_state']
            }

            # Update cache
            async with self._cache_lock:
                self._cache = state.copy()
                self._last_update = now

            return state

        except Exception as e:
            logger.error(f"Error aggregating state: {e}")
            return self._get_default_state()
            
    def _get_default_state(self) -> Dict[str, Any]:
        """Get default state structure with empty/zero values."""
        now = datetime.now(timezone.utc)
        return {
            "metrics": {
                "gas_price": 0,
                "performance": {
                    "total_profit_eth": 0,
                    "success_rate": 0,
                    "profit_trend": [
                        {
                            'timestamp': (now - timedelta(hours=i)).isoformat(),
                            'profit': 0
                        } for i in range(24, 0, -1)
                    ],
                    "successful_trades": 0,
                    "total_trades": 0
                },
                "system": {
                    "cpu_usage": 0,
                    "memory_usage": 0,
                    "disk_usage": 0
                },
                "pools": {}
            },
            "opportunities": [],
            "trade_history": [],
            "executions": {},
            "system_status": {
                "bot_status": "initializing",
                "network_status": "initializing",
                "last_update": now.isoformat()
            },
            "timestamp": now.isoformat(),
            "market_data": {
                "network_status": "initializing",
                "gas_price": 0
            }
        }

    async def _background_update(self) -> None:
        """Background task to keep memory state updated."""
        while True:
            try:
                # Get current metrics
                metrics = await self.get_current_state()

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