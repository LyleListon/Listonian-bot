"""
Memory Bank Implementation

This module provides the MemoryBank class for in-memory storage and caching
of arbitrage bot data.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Deque
from .file_manager import FileManager

logger = logging.getLogger(__name__)

class MemoryBank:
    """
    In-memory storage for arbitrage bot data.
    
    This class provides fast access to recent trades, metrics, and other
    frequently accessed data.
    """
    
    def __init__(
        self,
        max_trades: int = 10000,
        metrics_ttl: int = 300,  # 5 minutes
        state_ttl: int = 60,  # 1 minute
        storage_dir: Path = Path("memory-bank")
    ):
        """
        Initialize the memory bank.
        
        Args:
            max_trades: Maximum number of trades to keep in memory
            metrics_ttl: Time to live for metrics cache in seconds
            state_ttl: Time to live for state cache in seconds
            storage_dir: Directory for persistent storage
        """
        # Configuration
        self._max_trades = max_trades
        self._metrics_ttl = metrics_ttl
        self._state_ttl = state_ttl
        self._storage_dir = storage_dir
        self._trades_dir = storage_dir / "trades"
        self._file_manager = FileManager()
        
        # Trade storage
        self._trades: Deque[Dict[str, Any]] = deque(maxlen=max_trades)
        self._trade_index: Dict[str, Dict[str, Any]] = {}  # trade_id -> trade
        
        # Metrics storage
        self._metrics: Dict[str, Any] = {}
        self._metrics_timestamp = None
        
        # State storage
        self._state: Dict[str, Any] = {}
        self._state_timestamp = None
        
        # Analytics storage
        self._daily_stats: Dict[str, Dict[str, Any]] = {}
        self._hourly_stats: Dict[str, Dict[str, Any]] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the memory bank."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing memory bank")
            
            # Initialize file manager
            await self._file_manager.initialize()
            
            # Create storage directories
            await self._file_manager.ensure_directory(self._storage_dir)
            await self._file_manager.ensure_directory(self._trades_dir)
            self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            # Clear all storage
            self._trades.clear()
            self._trade_index.clear()
            self._metrics.clear()
            self._state.clear()
            self._daily_stats.clear()
            self._hourly_stats.clear()
            await self._file_manager.cleanup()
            
            self._initialized = False
    
    async def add_trade(
        self,
        trade: Dict[str, Any]
    ) -> None:
        """
        Add a trade to storage.
        
        Args:
            trade: Trade data to store
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        async with self._lock:
            trade_id = trade['id']
            timestamp = datetime.fromisoformat(trade['timestamp'])
            
            # Add to trades list and index
            self._trades.append(trade)
            self._trade_index[trade_id] = trade
            
            # Persist trade to file
            try:
                file_path = self._trades_dir / f"trade_{int(timestamp.timestamp())}.json"
                await self._file_manager.write_json(file_path, trade)
                logger.debug(f"Persisted trade {trade_id} to {file_path}")
            except Exception as e:
                logger.error(f"Failed to persist trade {trade_id}: {e}")
                raise
            
            # Update statistics
            await self._update_stats(trade)
    
    async def get_trade(
        self,
        trade_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific trade by ID.
        
        Args:
            trade_id: ID of trade to retrieve
            
        Returns:
            Trade data if found, None otherwise
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        return self._trade_index.get(trade_id)
    
    async def get_recent_trades(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of recent trades
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        async with self._lock:
            try:
                # List trade files
                trade_files = await self._file_manager.list_files(
                    self._trades_dir,
                    "trade_*.json"
                )
                
                # Sort by timestamp (newest first)
                trade_files.sort(reverse=True)
                
                # Load trades
                trades = []
                for file_path in trade_files[:limit]:
                    try:
                        trade = await self._file_manager.read_json(file_path)
                        trades.append(trade)
                    except Exception as e:
                        logger.error(f"Error reading trade file {file_path}: {e}")
                        continue
                
                return trades
            except Exception as e:
                logger.error(f"Error getting recent trades: {e}")
                return list(self._trades)[-limit:]  # Fallback to in-memory trades
    
    async def update_metrics(
        self,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Update system metrics.
        
        Args:
            metrics: Metrics to update
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        async with self._lock:
            self._metrics.update(metrics)
            timestamp = datetime.now()
            self._metrics_timestamp = timestamp
            
            # Persist metrics
            try:
                file_path = self._storage_dir / "metrics.json"
                await self._file_manager.write_json(file_path, {
                    "timestamp": timestamp.isoformat(),
                    "metrics": self._metrics
                })
            except Exception as e:
                logger.error(f"Failed to persist metrics: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Current metrics if not expired, empty dict otherwise
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        if not self._metrics_timestamp:
            return {}
        
        # Check if metrics have expired
        if (datetime.now() - self._metrics_timestamp).total_seconds() > self._metrics_ttl:
            return {}
        
        return self._metrics.copy()
    
    async def update_state(
        self,
        state: Dict[str, Any]
    ) -> None:
        """
        Update system state.
        
        Args:
            state: State to update
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        async with self._lock:
            self._state.update(state)
            timestamp = datetime.now()
            self._state_timestamp = timestamp
            
            # Persist state
            try:
                file_path = self._storage_dir / "state.json"
                await self._file_manager.write_json(file_path, {
                    "timestamp": timestamp.isoformat(),
                    "state": self._state
                })
            except Exception as e:
                logger.error(f"Failed to persist state: {e}")
    
    async def get_state(self) -> Dict[str, Any]:
        """
        Get current system state.
        
        Returns:
            Current state if not expired, empty dict otherwise
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        if not self._state_timestamp:
            return {}
        
        # Check if state has expired
        if (datetime.now() - self._state_timestamp).total_seconds() > self._state_ttl:
            return {}
        
        return self._state.copy()
    
    async def get_daily_stats(
        self,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get daily statistics.
        
        Args:
            days: Number of days of stats to return
            
        Returns:
            List of daily statistics
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        cutoff = datetime.now() - timedelta(days=days)
        stats = []
        
        for date, data in sorted(self._daily_stats.items()):
            if datetime.fromisoformat(date) >= cutoff:
                stats.append(data)
        
        return stats
    
    async def get_hourly_stats(
        self,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get hourly statistics.
        
        Args:
            hours: Number of hours of stats to return
            
        Returns:
            List of hourly statistics
        """
        if not self._initialized:
            raise RuntimeError("Memory bank not initialized")
        
        cutoff = datetime.now() - timedelta(hours=hours)
        stats = []
        
        for hour, data in sorted(self._hourly_stats.items()):
            if datetime.fromisoformat(hour) >= cutoff:
                stats.append(data)
        
        return stats
    
    async def _update_stats(
        self,
        trade: Dict[str, Any]
    ) -> None:
        """
        Update statistics with new trade data.
        
        Args:
            trade: Trade data to process
        """
        timestamp = datetime.fromisoformat(trade['timestamp'])
        
        # Update daily stats
        date = timestamp.date().isoformat()
        if date not in self._daily_stats:
            self._daily_stats[date] = {
                'date': date,
                'total_trades': 0,
                'total_profit_wei': 0,
                'total_gas_wei': 0,
                'successful_trades': 0,
                'failed_trades': 0
            }
        
        daily_stats = self._daily_stats[date]
        daily_stats['total_trades'] += 1
        
        if trade.get('status') == 'SUCCESSFUL':
            daily_stats['successful_trades'] += 1
            daily_stats['total_profit_wei'] += trade.get('actual_profit_wei', 0)
            daily_stats['total_gas_wei'] += trade.get('gas_cost_wei', 0)
        else:
            daily_stats['failed_trades'] += 1
        
        # Update hourly stats
        hour = timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        if hour not in self._hourly_stats:
            self._hourly_stats[hour] = {
                'hour': hour,
                'total_trades': 0,
                'total_profit_wei': 0,
                'total_gas_wei': 0,
                'successful_trades': 0,
                'failed_trades': 0
            }
        
        hourly_stats = self._hourly_stats[hour]
        hourly_stats['total_trades'] += 1
        
        if trade.get('status') == 'SUCCESSFUL':
            hourly_stats['successful_trades'] += 1
            hourly_stats['total_profit_wei'] += trade.get('actual_profit_wei', 0)
            hourly_stats['total_gas_wei'] += trade.get('gas_cost_wei', 0)
        else:
            hourly_stats['failed_trades'] += 1
        
        # Clean up old stats
        self._cleanup_stats()