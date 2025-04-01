"""Metrics service for real-time data collection and distribution.

This module provides a centralized metrics service with caching, throttling,
and efficient distribution to subscribers.
"""

import asyncio
import logging
import time
import json
import psutil
import os
from typing import Dict, Any, Optional, Set, List, Callable, Coroutine
from enum import Enum, auto
from datetime import datetime
import weakref

logger = logging.getLogger(__name__)


class MetricsType(str, Enum):
    """Types of metrics collected by the service."""
    SYSTEM = "system"
    MARKET = "market"
    PORTFOLIO = "portfolio"
    MEMORY = "memory"
    STORAGE = "storage"
    DISTRIBUTION = "distribution"
    EXECUTION = "execution"
    GAS = "gas"
    TASKS = "tasks"
    CONNECTIONS = "connections"
    CUSTOM = "custom"


class MetricsService:
    """Centralized service for metrics collection and distribution.
    
    This class provides efficient metrics collection with caching, TTL,
    throttling, and distribution to subscribers.
    
    Attributes:
        _cache: Dictionary mapping metric types to cached data
        _collectors: Dictionary mapping metric types to collector functions
        _subscribers: Set of subscriber queues
        _lock: Asyncio lock for thread safety
    """

    def __init__(self):
        """Initialize the metrics service."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._collectors: Dict[str, Callable[[], Coroutine]] = {}
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._update_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self._cache_ttl: Dict[str, float] = {
            MetricsType.SYSTEM: 1.0,  # 1 second TTL for system metrics
            MetricsType.MARKET: 5.0,  # 5 seconds TTL for market data
            MetricsType.PORTFOLIO: 10.0,  # 10 seconds TTL for portfolio data
            MetricsType.MEMORY: 30.0,  # 30 seconds TTL for memory data
            MetricsType.STORAGE: 60.0,  # 60 seconds TTL for storage data
            MetricsType.DISTRIBUTION: 5.0,  # 5 seconds TTL for distribution data
            MetricsType.EXECUTION: 2.0,  # 2 seconds TTL for execution data
            MetricsType.GAS: 15.0,  # 15 seconds TTL for gas data
            MetricsType.TASKS: 2.0,  # 2 seconds TTL for task metrics
            MetricsType.CONNECTIONS: 2.0,  # 2 seconds TTL for connection metrics
            MetricsType.CUSTOM: 10.0,  # 10 seconds TTL for custom metrics
        }
        
        self._throttle_interval: Dict[str, float] = {
            MetricsType.SYSTEM: 1.0,  # Update system metrics every 1 second
            MetricsType.MARKET: 5.0,  # Update market data every 5 seconds
            MetricsType.PORTFOLIO: 10.0,  # Update portfolio data every 10 seconds
            MetricsType.MEMORY: 30.0,  # Update memory data every 30 seconds
            MetricsType.STORAGE: 60.0,  # Update storage data every 60 seconds
            MetricsType.DISTRIBUTION: 5.0,  # Update distribution data every 5 seconds
            MetricsType.EXECUTION: 2.0,  # Update execution data every 2 seconds
            MetricsType.GAS: 15.0,  # Update gas data every 15 seconds
            MetricsType.TASKS: 2.0,  # Update task metrics every 2 seconds
            MetricsType.CONNECTIONS: 2.0,  # Update connection metrics every 2 seconds
            MetricsType.CUSTOM: 10.0,  # Update custom metrics every 10 seconds
        }
        
        # Initialize system metrics collector
        self.register_collector(MetricsType.SYSTEM, self._collect_system_metrics)
        
        logger.debug("MetricsService initialized")

    async def start(self) -> None:
        logger.info("--- MetricsService.start() CALLED ---")
        """Start the metrics service."""
        # Start update tasks for all registered collectors
        for metric_type in self._collectors:
            await self._start_update_task(metric_type)
            
        logger.debug("MetricsService started")

    async def stop(self) -> None:
        """Stop the metrics service."""
        # Cancel all update tasks
        for metric_type, task in self._update_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        self._update_tasks.clear()
        
        # Clear subscribers
        self._subscribers.clear()
        
        logger.debug("MetricsService stopped")

    def register_collector(self, metric_type: str, collector: Callable[[], Coroutine]) -> None:
        """Register a metrics collector function.
        
        Args:
            metric_type: Type of metrics collected
            collector: Async function that returns metrics data
        """
        self._collectors[metric_type] = collector
        logger.debug(f"Collector registered for {metric_type} metrics")

    async def register_subscriber(self, queue: asyncio.Queue) -> None:
        """Register a subscriber queue.
        
        Args:
            queue: Asyncio queue to receive metrics updates
        """
        async with self._lock:
            self._subscribers.add(queue)
            
        logger.debug(f"Subscriber registered (total: {len(self._subscribers)})")

    async def unregister_subscriber(self, queue: asyncio.Queue) -> None:
        """Unregister a subscriber queue.
        
        Args:
            queue: Asyncio queue to remove
        """
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
                
        logger.debug(f"Subscriber unregistered (remaining: {len(self._subscribers)})")

    async def get_metrics(self, metric_type: str) -> Dict[str, Any]:
        """Get metrics of a specific type.
        
        Args:
            metric_type: Type of metrics to retrieve
            
        Returns:
            Dictionary with metrics data
            
        Raises:
            ValueError: If the metric type is not registered
        """
        if metric_type not in self._collectors:
            raise ValueError(f"No collector registered for {metric_type} metrics")
            
        async with self._lock:
            now = time.time()
            
            # Check if we have cached data that's still valid
            if (metric_type in self._cache and 
                now - self._cache[metric_type]["timestamp"] < self._cache_ttl.get(metric_type, 10.0)):
                return self._cache[metric_type]["data"]
                
            # Collect fresh metrics
            metrics = await self._collectors[metric_type]()
            
            # Update cache
            self._cache[metric_type] = {
                "data": metrics,
                "timestamp": now
            }
            
            return metrics

    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all available metrics.
        
        Returns:
            Dictionary mapping metric types to their data
        """
        result = {}
        for metric_type in self._collectors:
            try:
                result[metric_type] = await self.get_metrics(metric_type)
            except Exception as e:
                logger.error(f"Error getting {metric_type} metrics: {str(e)}")
                result[metric_type] = {"error": str(e)}
                
        return result

    async def broadcast_metrics(self, metric_type: str, metrics: Dict[str, Any]) -> int:
        """Broadcast metrics to all subscribers.
        
        Args:
            metric_type: Type of metrics being broadcast
            metrics: Metrics data to broadcast
            
        Returns:
            Number of subscribers that received the update
        """
        if not self._subscribers:
            return 0
            
        # Prepare the message
        message = {
            "type": f"{metric_type}_update",
            "data": metrics,
            "timestamp": time.time()
        }
        
        logger.debug(f"[_collect_system_metrics] Collected data: {message}") # Log collected data
        # Send to all subscribers
        count = 0
        for subscriber in list(self._subscribers):
            try:
                if not subscriber.full():
                    subscriber.put_nowait(message)
                    count += 1
            except Exception as e:
                logger.error(f"Error sending to subscriber: {str(e)}")
                
        return count

    async def _start_update_task(self, metric_type: str) -> None:
        """Start an update task for a specific metric type.
        
        Args:
            metric_type: Type of metrics to update
        """
        if metric_type in self._update_tasks and not self._update_tasks[metric_type].done():
            self._update_tasks[metric_type].cancel()
            
        self._update_tasks[metric_type] = asyncio.create_task(
            self._update_loop(metric_type),
            name=f"metrics_update_{metric_type}"
        )

    async def _update_loop(self, metric_type: str) -> None:
        """Update loop for a specific metric type.
        
        Args:
            metric_type: Type of metrics to update
        """
        throttle_interval = self._throttle_interval.get(metric_type, 10.0)
        
        while True:
            try:
                # Only update if we have subscribers
                logger.debug(f"Update loop {metric_type}: Checking subscribers. Count = {len(self._subscribers)}") # Log subscriber count
                if self._subscribers:
                    # Get fresh metrics
                    metrics = await self.get_metrics(metric_type)
                    
                    # Broadcast to subscribers
                    logger.info(f"Update loop {metric_type}: Attempting to broadcast metrics...") # Log before broadcast
                    await self.broadcast_metrics(metric_type, metrics)
                    
                # Wait for the throttle interval
                await asyncio.sleep(throttle_interval)
                
            except asyncio.CancelledError:
                logger.debug(f"Update loop for {metric_type} metrics cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in {metric_type} metrics update loop: {str(e)}")
                await asyncio.sleep(1.0)  # Brief delay before retry

    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics.
        
        Returns:
            Dictionary with system metrics
        """
        try:
            logger.debug("Attempting to collect system metrics in _collect_system_metrics...") # Add log
            # Get CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Get process-specific metrics
            process = psutil.Process(os.getpid())
            process_cpu = process.cpu_percent(interval=0.1)
            process_memory = process.memory_info()
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            
            # Get network stats
            net_io = psutil.net_io_counters()
            
            return {
                # ... (rest of the data structure)
            }
            data = { # Assign to variable to log before returning
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used": memory.used,
                    "memory_total": memory.total,
                    "disk_percent": disk.percent,
                    "disk_used": disk.used,
                    "disk_total": disk.total
                },
                "process": {
                    "cpu_percent": process_cpu,
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "threads": process.num_threads()
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                },
                "timestamp": time.time()
            }
            logger.debug(f"[_collect_system_metrics] Returning data: {data}") # Log data before return
            return data
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {
                "error": str(e),
                "timestamp": time.time()
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the metrics cache.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "total_metrics": len(self._cache),
            "metrics_by_type": {},
            "cache_age": {}
        }
        
        now = time.time()
        for metric_type, cache_data in self._cache.items():
            age = now - cache_data["timestamp"]
            ttl = self._cache_ttl.get(metric_type, 10.0)
            freshness = max(0, 1 - (age / ttl)) if ttl > 0 else 0
            
            stats["metrics_by_type"][metric_type] = True
            stats["cache_age"][metric_type] = {
                "age_seconds": age,
                "ttl_seconds": ttl,
                "freshness": freshness
            }
            
        return stats

    def get_subscriber_stats(self) -> Dict[str, Any]:
        """Get statistics about subscribers.
        
        Returns:
            Dictionary with subscriber statistics
        """
        queue_sizes = []
        for subscriber in self._subscribers:
            queue_sizes.append(subscriber.qsize())
            
        return {
            "total_subscribers": len(self._subscribers),
            "queue_stats": {
                "average_size": sum(queue_sizes) / len(queue_sizes) if queue_sizes else 0,
                "max_size": max(queue_sizes) if queue_sizes else 0,
                "min_size": min(queue_sizes) if queue_sizes else 0
            }
        }