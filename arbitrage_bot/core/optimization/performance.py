"""Performance optimization for arbitrage bot."""

import time
import logging
import asyncio
import psutil
# import psutil # Redundant import
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data."""

    memory_usage: float  # MB
    cpu_usage: float  # %
    network_rx: float  # MB/s
    network_tx: float  # MB/s
    api_latency: float  # ms
    cache_hits: int
    cache_misses: int
    active_tasks: int


class PerformanceOptimizer:
    """Optimizes system performance."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize performance optimizer."""
        self.config = config

        # Performance thresholds
        self.max_memory = config.get("process", {}).get("max_memory_mb", 1024)  # MB
        self.max_cpu = config.get("process", {}).get("max_cpu_percent", 50)  # %
        self.max_tasks = config.get("process", {}).get(
            "max_tasks", 100
        )  # concurrent tasks

        # Process instance
        self._process = None

        # Cache settings
        self.cache_size = config.get("optimization", {}).get("cache_size", 1000)
        self.cache_ttl = config.get("optimization", {}).get("cache_ttl", 10)  # seconds

        # Metrics history
        self.metrics_history = deque(maxlen=1000)
        self.last_network_stats = None

        # Performance cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Task tracking
        self._active_tasks: List[asyncio.Task] = []

        # Initialize system resources
        self._init_resources()

    def _get_process(self):
        """Get or create process instance."""
        if self._process is None:
            self._process = psutil.Process()
        return self._process

    def _init_resources(self):
        """Initialize system resources."""
        try:
            # Get current process
            process = self._get_process()

            # Set memory limit (Windows doesn't support hard limits)
            # Instead, we'll monitor and manage memory usage
            self.initial_memory = process.memory_info().rss
            logger.info(
                f"Initial memory usage: {self.initial_memory / (1024*1024):.2f} MB"
            )

            # Set process priority in a cross-platform way
            try:
                if hasattr(psutil, "NORMAL_PRIORITY_CLASS"):  # Windows
                    process.nice(psutil.NORMAL_PRIORITY_CLASS)
                else:  # Unix/Linux
                    process.nice(0)  # Normal priority
            except Exception as e:
                logger.warning(f"Could not set process priority: {e}")

            logger.info("System resources initialized")

        except Exception as e:
            logger.error(f"Failed to initialize resources: {e}")

    async def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        try:
            process = self._get_process()

            # Memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            # CPU usage
            cpu_percent = process.cpu_percent()

            # Network stats
            net_stats = psutil.net_io_counters()
            if self.last_network_stats:
                time_diff = time.time() - self.last_network_stats[0]
                rx_mb = (net_stats.bytes_recv - self.last_network_stats[1]) / (
                    1024 * 1024 * time_diff
                )
                tx_mb = (net_stats.bytes_sent - self.last_network_stats[2]) / (
                    1024 * 1024 * time_diff
                )
            else:
                rx_mb = tx_mb = 0

            self.last_network_stats = (
                time.time(),
                net_stats.bytes_recv,
                net_stats.bytes_sent,
            )

            # Create metrics
            metrics = PerformanceMetrics(
                memory_usage=memory_mb,
                cpu_usage=cpu_percent,
                network_rx=rx_mb,
                network_tx=tx_mb,
                api_latency=0.0,  # Updated by API calls
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
                active_tasks=len(self._active_tasks),
            )

            # Store history
            self.metrics_history.append(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return None

    def cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if key not in self._cache:
                self._cache_misses += 1
                return None

            # Check TTL
            if time.time() - self._cache_timestamps[key] > self.cache_ttl:
                del self._cache[key]
                del self._cache_timestamps[key]
                self._cache_misses += 1
                return None

            self._cache_hits += 1
            return self._cache[key]

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def cache_set(self, key: str, value: Any):
        """Set value in cache."""
        try:
            # Enforce cache size limit
            if len(self._cache) >= self.cache_size:
                oldest_key = min(self._cache_timestamps.items(), key=lambda x: x[1])[0]
                del self._cache[oldest_key]
                del self._cache_timestamps[oldest_key]

            self._cache[key] = value
            self._cache_timestamps[key] = time.time()

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def track_task(self, task: asyncio.Task):
        """Track an active task."""
        self._active_tasks.append(task)
        task.add_done_callback(self._remove_task)

    def _remove_task(self, task: asyncio.Task):
        """Remove completed task."""
        try:
            self._active_tasks.remove(task)
        except ValueError:
            pass

    async def optimize_resources(self):
        """Optimize system resource usage."""
        while True:
            try:
                metrics = await self.get_metrics()
                if not metrics:
                    continue

                # Memory optimization
                if metrics.memory_usage > self.max_memory * 0.9:  # 90% threshold
                    logger.warning("High memory usage - clearing caches")
                    self._cache.clear()
                    self._cache_timestamps.clear()

                # CPU optimization
                if metrics.cpu_usage > self.max_cpu * 0.9:  # 90% threshold
                    logger.warning("High CPU usage - limiting tasks")
                    while (
                        len(self._active_tasks) > self.max_tasks * 0.8
                    ):  # 80% threshold
                        # Cancel lowest priority tasks
                        for task in sorted(
                            self._active_tasks, key=lambda t: getattr(t, "priority", 0)
                        )[:5]:
                            task.cancel()

                # Network optimization
                if metrics.network_rx > 50 or metrics.network_tx > 50:  # MB/s
                    logger.warning("High network usage - increasing cache TTL")
                    self.cache_ttl = min(30, self.cache_ttl * 1.5)  # Max 30s
                else:
                    self.cache_ttl = max(
                        self.config.get("optimization", {}).get("cache_ttl", 10),
                        self.cache_ttl * 0.9,
                    )

            except Exception as e:
                logger.error(f"Resource optimization error: {e}")

            await asyncio.sleep(1)

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        try:
            if not self.metrics_history:
                return {}

            # Calculate averages
            avg_metrics = {
                "memory_usage": sum(m.memory_usage for m in self.metrics_history)
                / len(self.metrics_history),
                "cpu_usage": sum(m.cpu_usage for m in self.metrics_history)
                / len(self.metrics_history),
                "network_rx": sum(m.network_rx for m in self.metrics_history)
                / len(self.metrics_history),
                "network_tx": sum(m.network_tx for m in self.metrics_history)
                / len(self.metrics_history),
                "api_latency": sum(m.api_latency for m in self.metrics_history)
                / len(self.metrics_history),
            }

            # Cache stats
            cache_stats = {
                "size": len(self._cache),
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_ratio": (
                    self._cache_hits / (self._cache_hits + self._cache_misses)
                    if (self._cache_hits + self._cache_misses) > 0
                    else 0
                ),
                "ttl": self.cache_ttl,
            }

            # Task stats
            task_stats = {"active": len(self._active_tasks), "max": self.max_tasks}

            return {"metrics": avg_metrics, "cache": cache_stats, "tasks": task_stats}

        except Exception as e:
            logger.error(f"Failed to get optimization stats: {e}")
            return {}
