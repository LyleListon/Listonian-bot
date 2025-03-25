"""
Memory Manager Implementation

This module provides the MemoryManager class for managing persistent storage
and state management in the arbitrage bot.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .memory_bank import MemoryBank
from .file_manager import FileManager

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manager for persistent storage and state management.
    
    This class coordinates access to the memory bank and ensures data consistency
    across bot restarts.
    """
    
    def __init__(
        self,
        storage_path: str = "memory-bank",
        max_trade_history: int = 10000,
        backup_interval_hours: int = 24
    ):
        """
        Initialize the memory manager.
        
        Args:
            storage_path: Path to storage directory
            max_trade_history: Maximum number of trades to keep in history
            backup_interval_hours: Hours between automatic backups
        """
        self._storage_path = Path(storage_path)
        self._max_trade_history = max_trade_history
        self._backup_interval = backup_interval_hours * 3600  # Convert to seconds
        
        # Create storage directories
        self._trades_path = self._storage_path / "trades"
        self._metrics_path = self._storage_path / "metrics"
        self._state_path = self._storage_path / "state"
        
        for path in [self._trades_path, self._metrics_path, self._state_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._memory_bank = MemoryBank()
        self._file_manager = FileManager()
        
        # State
        self._initialized = False
        self._lock = asyncio.Lock()
        self._backup_task = None
        
        # Cache
        self._metrics_cache = {}
        self._state_cache = {}
    
    async def initialize(self) -> None:
        """Initialize the memory manager."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing memory manager")
            
            try:
                # Initialize components
                await self._memory_bank.initialize()
                await self._file_manager.initialize()
                
                # Load existing data
                await self._load_metrics()
                await self._load_state()
                await self._load_trades()
                
                # Start backup task
                self._backup_task = asyncio.create_task(self._backup_loop())
                
                self._initialized = True
                logger.info("Memory manager initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize memory manager: {e}", exc_info=True)
                await self.cleanup()
                raise
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            if not self._initialized:
                return
            
            logger.info("Cleaning up memory manager")
            
            # Cancel backup task
            if self._backup_task:
                self._backup_task.cancel()
                try:
                    await asyncio.wait_for(self._backup_task
, timeout=5.0)
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for backup task to cancel")
            
            # Save final state
            await self._save_metrics()
            await self._save_state()
            
            # Clean up components
            await self._memory_bank.cleanup()
            await self._file_manager.cleanup()
            
            self._initialized = False
    
    async def record_trade(
        self,
        trade_data: Dict[str, Any]
    ) -> None:
        """
        Record a completed trade.
        
        Args:
            trade_data: Trade details to record
        """
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        async with self._lock:
            # Generate filename from timestamp
            timestamp = int(datetime.now().timestamp())
            filename = f"trade_{timestamp}.json"
            
            # Save trade file
            trade_file = self._trades_path / filename
            await self._file_manager.write_json(trade_file, trade_data)
            
            # Update memory bank
            await self._memory_bank.add_trade(trade_data)
            
            # Cleanup old trades if needed
            await self._cleanup_old_trades()
    
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
            raise RuntimeError("Memory manager not initialized")
        
        return await self._memory_bank.get_recent_trades(limit)
    
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
            raise RuntimeError("Memory manager not initialized")
        
        async with self._lock:
            self._metrics_cache.update(metrics)
            await self._save_metrics()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Current metrics
        """
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        return self._metrics_cache.copy()
    
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
            raise RuntimeError("Memory manager not initialized")
        
        async with self._lock:
            self._state_cache.update(state)
            await self._save_state()
    
    async def get_state(self) -> Dict[str, Any]:
        """
        Get current system state.
        
        Returns:
            Current state
        """
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        return self._state_cache.copy()
    
    async def _backup_loop(self):
        """Background task for periodic backups."""
        logger.info("Starting backup loop")
        
        while True:
            try:
                await asyncio.sleep(self._backup_interval)
                
                async with self._lock:
                    await self._save_metrics()
                    await self._save_state()
                    logger.info("Completed periodic backup")
                    
            except asyncio.CancelledError:
                logger.info("Backup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in backup loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _load_metrics(self):
        """Load metrics from storage."""
        metrics_file = self._metrics_path / "metrics.json"
        if metrics_file.exists():
            self._metrics_cache = await self._file_manager.read_json(metrics_file)
    
    async def _save_metrics(self):
        """Save metrics to storage."""
        metrics_file = self._metrics_path / "metrics.json"
        await self._file_manager.write_json(metrics_file, self._metrics_cache)
    
    async def _load_state(self):
        """Load state from storage."""
        state_file = self._state_path / "state.json"
        if state_file.exists():
            self._state_cache = await self._file_manager.read_json(state_file)
    
    async def _save_state(self):
        """Save state to storage."""
        state_file = self._state_path / "state.json"
        await self._file_manager.write_json(state_file, self._state_cache)
    
    async def _load_trades(self):
        """Load trade history from storage."""
        trade_files = sorted(self._trades_path.glob("trade_*.json"))
        
        for trade_file in trade_files[-self._max_trade_history:]:
            try:
                trade_data = await self._file_manager.read_json(trade_file)
                await self._memory_bank.add_trade(trade_data)
            except Exception as e:
                logger.error(f"Error loading trade file {trade_file}: {e}")
    
    async def _cleanup_old_trades(self):
        """Clean up old trade files."""
        trade_files = sorted(self._trades_path.glob("trade_*.json"))
        
        if len(trade_files) > self._max_trade_history:
            files_to_remove = trade_files[:-self._max_trade_history]
            for file in files_to_remove:
                try:
                    file.unlink()
                except Exception as e:
                    logger.error(f"Error removing old trade file {file}: {e}")
