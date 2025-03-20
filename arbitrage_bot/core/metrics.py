"""
Metrics collector for system monitoring.

This module provides:
1. Real-time system metrics collection
2. Performance monitoring
3. Resource tracking
4. Error rate calculation
"""

import os
import time
import psutil
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from .cache import get_cache
from .web3 import get_web3_manager
from .websocket import get_ws_manager

# Configure logging
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and manages system metrics."""
    
    def __init__(self):
        """Initialize the metrics collector."""
        self._lock = asyncio.Lock()
        self._cache = get_cache()
        self._web3 = get_web3_manager()
        self._ws = get_ws_manager()
        self._active = False
        self._collection_task: Optional[asyncio.Task] = None
        self._start_time = datetime.utcnow()
        self._error_counts: Dict[str, int] = {}
        self._last_block = 0
        
    async def start(self) -> None:
        """Start metrics collection."""
        async with self._lock:
            if not self._active:
                self._active = True
                self._collection_task = asyncio.create_task(self._collect_loop())
                logger.info("Metrics collector started")
    
    async def stop(self) -> None:
        """Stop metrics collection."""
        async with self._lock:
            if self._active:
                self._active = False
                if self._collection_task:
                    self._collection_task.cancel()
                    try:
                        await self._collection_task
                    except asyncio.CancelledError:
                        pass
                    self._collection_task = None
                logger.info("Metrics collector stopped")

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        process = psutil.Process(os.getpid())
        
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_info": {
                "rss": process.memory_info().rss,
                "vms": process.memory_info().vms
            },
            "thread_count": process.num_threads(),
            "uptime": str(datetime.utcnow() - self._start_time)
        }

    async def get_blockchain_metrics(self) -> Dict[str, Any]:
        """Get current blockchain metrics."""
        try:
            current_block = await self._web3.get_block_number()
            blocks_per_minute = 0
            
            if self._last_block > 0:
                blocks_per_minute = (current_block - self._last_block) * 60
            
            self._last_block = current_block
            
            return {
                "current_block": current_block,
                "blocks_per_minute": blocks_per_minute,
                "chain_id": self._web3.chain_id
            }
        except Exception as e:
            logger.error(f"Error getting blockchain metrics: {e}")
            return {
                "current_block": 0,
                "blocks_per_minute": 0,
                "chain_id": 0,
                "error": str(e)
            }

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from cache."""
        try:
            metrics = await self._cache.get("performance_metrics") or {}
            return {
                "transaction_count": metrics.get("tx_count", 0),
                "success_rate": metrics.get("success_rate", 0),
                "average_latency": metrics.get("avg_latency", 0),
                "gas_efficiency": metrics.get("gas_efficiency", 0),
                "cache_hit_ratio": metrics.get("cache_hits", 0)
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                "error": str(e)
            }

    async def get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics."""
        total_errors = sum(self._error_counts.values())
        uptime_hours = (datetime.utcnow() - self._start_time).total_seconds() / 3600
        
        return {
            "total_errors": total_errors,
            "errors_per_hour": total_errors / uptime_hours if uptime_hours > 0 else 0,
            "error_types": self._error_counts.copy()
        }

    async def record_error(self, error_type: str) -> None:
        """Record an error occurrence."""
        async with self._lock:
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

    async def _collect_loop(self) -> None:
        """Main metrics collection loop."""
        while self._active:
            try:
                # Collect all metrics
                metrics = {
                    "system": await self.get_system_metrics(),
                    "blockchain": await self.get_blockchain_metrics(),
                    "performance": await self.get_performance_metrics(),
                    "errors": await self.get_error_metrics(),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Cache the metrics
                await self._cache.set(
                    "system_metrics",
                    metrics,
                    expire=300  # 5 minutes TTL
                )
                
                # Broadcast via WebSocket
                await self._ws.broadcast("metrics_update", metrics)
                
                # Wait before next collection
                await asyncio.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def __aenter__(self) -> 'MetricsCollector':
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None

def get_metrics_collector() -> MetricsCollector:
    """Get the metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector