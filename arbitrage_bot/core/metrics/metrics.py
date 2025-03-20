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
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from ..cache import get_cache
from ..web3 import get_web3_manager
from ..websocket import get_ws_manager

# Configure logging
logger = logging.getLogger(__name__)

def format_bytes(bytes: int) -> str:
    """Format bytes into human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

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
        
        # Performance tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._total_latency = 0.0
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_gas_price = 0
        self._min_gas_price = float('inf')
        self._max_gas_price = 0
        
        # Initialize process monitoring
        self._process = psutil.Process(os.getpid())
        self._initial_memory = self._process.memory_info().rss
        logger.info(f"Initial memory baseline: {format_bytes(self._initial_memory)}")
        
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
        # Get current memory info
        mem_info = self._process.memory_info()
        rss = mem_info.rss
        vms = mem_info.vms
        
        # Calculate memory increase
        memory_increase = rss - self._initial_memory
        memory_percent = (memory_increase / self._initial_memory) * 100 if self._initial_memory > 0 else 0
        
        # Get CPU usage with interval=None to avoid blocking
        cpu_percent = self._process.cpu_percent(interval=None)
        
        # Get system memory info
        system = psutil.virtual_memory()
        
        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_info": {
                "rss": format_bytes(rss),
                "vms": format_bytes(vms),
                "rss_bytes": rss,
                "vms_bytes": vms,
                "increase_from_baseline": format_bytes(memory_increase),
                "increase_percent": f"{memory_percent:.1f}%"
            },
            "system_memory": {
                "total": format_bytes(system.total),
                "available": format_bytes(system.available),
                "used_percent": system.percent
            },
            "thread_count": self._process.num_threads(),
            "uptime": str(datetime.utcnow() - self._start_time)
        }
        
        logger.debug(f"Memory metrics: RSS={metrics['memory_info']['rss']}, "
                    f"Increase={metrics['memory_info']['increase_from_baseline']}")
        
        return metrics

    async def get_blockchain_metrics(self) -> Dict[str, Any]:
        """Get current blockchain metrics."""
        try:
            current_block = await self._web3.get_block_number()
            blocks_per_minute = 0
            
            if self._last_block > 0:
                blocks_per_minute = (current_block - self._last_block) * 60
            
            self._last_block = current_block
            
            # Get current gas price
            gas_price = await self._web3.get_gas_price()
            self._last_gas_price = gas_price
            self._min_gas_price = min(self._min_gas_price, gas_price)
            self._max_gas_price = max(self._max_gas_price, gas_price)
            
            return {
                "current_block": current_block,
                "blocks_per_minute": blocks_per_minute,
                "chain_id": self._web3.chain_id,
                "gas_price": {
                    "current": gas_price,
                    "min": self._min_gas_price,
                    "max": self._max_gas_price
                }
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
            # Calculate success rate
            success_rate = (self._successful_requests / self._total_requests * 100) if self._total_requests > 0 else 0
            
            # Calculate average latency
            avg_latency = (self._total_latency / self._total_requests) if self._total_requests > 0 else 0
            
            # Calculate cache hit ratio
            total_cache_ops = self._cache_hits + self._cache_misses
            cache_hit_ratio = (self._cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
            
            # Get cache stats
            cache_stats = await self._cache.get_stats()
            
            return {
                "success_rate": success_rate,
                "average_latency": avg_latency,
                "cache_hit_ratio": cache_hit_ratio,
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "cache_stats": cache_stats
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

    async def record_request(self, success: bool, latency: float) -> None:
        """Record a request's outcome and latency."""
        async with self._lock:
            self._total_requests += 1
            if success:
                self._successful_requests += 1
            self._total_latency += latency

    async def record_cache_operation(self, hit: bool) -> None:
        """Record a cache hit or miss."""
        async with self._lock:
            if hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

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