"""
Optimized Metrics Service with Shared Memory Support

This module extends the MetricsService with shared memory support for
efficient metrics storage and retrieval across processes.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, Coroutine

from .metrics_service import MetricsService, MetricsType
from arbitrage_bot.core.optimization.shared_memory import (
    SharedMemoryManager,
    SharedMetricsStore
)

logger = logging.getLogger(__name__)

class OptimizedMetricsService(MetricsService):
    """
    Optimized metrics service with shared memory support.
    
    This class extends the base MetricsService with:
    - Shared memory for metrics storage
    - Efficient cross-process metrics sharing
    - TTL-based cache invalidation
    """
    
    def __init__(self, use_shared_memory: bool = True, base_dir: Optional[str] = None):
        """
        Initialize the optimized metrics service.
        
        Args:
            use_shared_memory: Whether to use shared memory
            base_dir: Base directory for shared memory files
        """
        super().__init__()
        
        # Shared memory components
        self._use_shared_memory = False
        self._memory_manager = None
        self._metrics_store = None
        self._base_dir = base_dir
        
        # Enable shared memory if requested
        if use_shared_memory:
            self._init_shared_memory_task = asyncio.create_task(self.enable_shared_memory(base_dir))
    
    async def enable_shared_memory(self, base_dir: Optional[str] = None) -> None:
        """
        Enable shared memory for metrics storage.
        
        Args:
            base_dir: Base directory for shared memory files
        """
        try:
            # Create shared memory manager
            self._memory_manager = SharedMemoryManager(base_dir=base_dir or self._base_dir)
            
            # Create metrics store
            self._metrics_store = SharedMetricsStore(self._memory_manager)
            await self._metrics_store.initialize()
            
            # Set TTL values
            for metric_type, ttl in self._cache_ttl.items():
                await self._metrics_store.set_ttl(metric_type, ttl)
            
            self._use_shared_memory = True
            logger.info("Shared memory enabled for metrics storage")
        except Exception as e:
            logger.error(f"Failed to enable shared memory: {e}")
    
    async def start(self) -> None:
        """Start the metrics service."""
        # Wait for shared memory initialization if needed
        if hasattr(self, '_init_shared_memory_task'):
            try:
                await self._init_shared_memory_task
            except Exception as e:
                logger.error(f"Error initializing shared memory: {e}")
        
        # Start update tasks for all registered collectors
        for metric_type in self._collectors:
            await self._start_update_task(metric_type)
            
        logger.info("OptimizedMetricsService started")
    
    async def stop(self) -> None:
        """Stop the metrics service."""
        # Call parent implementation
        await super().stop()
        
        # Clean up shared memory
        if self._use_shared_memory and self._memory_manager:
            try:
                # Clean up shared memory regions
                for region in await self._memory_manager.list_regions():
                    await self._memory_manager.delete_region(region.name)
            except Exception as e:
                logger.error(f"Error cleaning up shared memory: {e}")
    
    async def get_metrics(self, metric_type: str) -> Dict[str, Any]:
        """
        Get metrics of a specific type.
        
        Args:
            metric_type: Type of metrics to retrieve
            
        Returns:
            Dictionary with metrics data
            
        Raises:
            ValueError: If the metric type is not registered
        """
        if metric_type not in self._collectors:
            raise ValueError(f"No collector registered for {metric_type} metrics")
        
        # Try to get from shared memory if enabled
        if self._use_shared_memory and self._metrics_store:
            try:
                shared_metrics = await self._metrics_store.get_metrics(metric_type)
                if shared_metrics:
                    return shared_metrics
            except Exception as e:
                logger.error(f"Error getting metrics from shared memory: {e}")
        
        # Fall back to parent implementation
        metrics = await super().get_metrics(metric_type)
        
        # Store in shared memory if enabled
        if self._use_shared_memory and self._metrics_store and metrics:
            try:
                await self._metrics_store.store_metrics(metric_type, metrics)
            except Exception as e:
                logger.error(f"Error storing metrics in shared memory: {e}")
        
        return metrics
    
    async def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available metrics.
        
        Returns:
            Dictionary mapping metric types to their data
        """
        # Try to get from shared memory if enabled
        if self._use_shared_memory and self._metrics_store:
            try:
                shared_metrics = await self._metrics_store.get_all_metrics()
                if shared_metrics:
                    return shared_metrics
            except Exception as e:
                logger.error(f"Error getting all metrics from shared memory: {e}")
        
        # Fall back to parent implementation
        return await super().get_all_metrics()
    
    def get_shared_memory_stats(self) -> Dict[str, Any]:
        """
        Get shared memory statistics.
        
        Returns:
            Dictionary with shared memory statistics
        """
        stats = {
            "enabled": self._use_shared_memory,
            "memory_manager": None,
            "metrics_store": None
        }
        
        if self._use_shared_memory and self._memory_manager:
            try:
                # Get memory manager stats
                regions = asyncio.run(self._memory_manager.list_regions())
                stats["memory_manager"] = {
                    "regions": [region.name for region in regions],
                    "region_count": len(regions)
                }
            except Exception as e:
                logger.error(f"Error getting memory manager stats: {e}")
        
        return stats