"""Service for managing system-level metrics and operations."""

import asyncio
from typing import Dict, Any, Optional, List
import logging
import json
import psutil
from datetime import datetime
import platform
import os
import time

from ..core.logging import get_logger
from .memory_service import MemoryService
from .metrics_service import MetricsService

logger = get_logger("system_service")


class SystemService:
    """Service for managing system-level operations."""

    def __init__(self, memory_service: MemoryService, metrics_service: MetricsService):
        """Initialize system service.

        Args:
            memory_service: Memory service instance
            metrics_service: Metrics service instance
        """
        logger.info("=== SystemService.__init__ called ===")
        logger.info("memory_service type: %s", type(memory_service).__name__)
        logger.info("metrics_service type: %s", type(metrics_service).__name__)

        self.memory_service = memory_service
        self.metrics_service = metrics_service
        self._status = {
            "status": "initializing",
            "uptime": 0,
            "start_time": datetime.utcnow().isoformat(),
            "last_update": None,
        }
        self._update_task: Optional[asyncio.Task] = None
        self._initialized = False
        self._lock = asyncio.Lock()

        # Enhanced metrics tracking
        self._detailed_metrics = {
            "cpu": {"usage_percent": 0.0, "per_core": [], "load_avg": [0.0, 0.0, 0.0]},
            "memory": {
                "total": 0,
                "available": 0,
                "used": 0,
                "percent": 0.0,
                "swap_total": 0,
                "swap_used": 0,
                "swap_percent": 0.0,
            },
            "disk": {
                "total": 0,
                "used": 0,
                "free": 0,
                "percent": 0.0,
                "io_counters": {
                    "read_count": 0,
                    "write_count": 0,
                    "read_bytes": 0,
                    "write_bytes": 0,
                },
            },
            "network": {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "connections": 0,
            },
            "process": {
                "pid": os.getpid(),
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "threads": 0,
                "open_files": 0,
            },
            "system": {
                "boot_time": 0,
                "uptime": 0,
                "platform": platform.system(),
                "platform_release": platform.release(),
                "hostname": platform.node(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._collection_interval = 5  # seconds

        # Previous values for rate calculations
        self._prev_net_io = None
        self._prev_net_time = None
        self._prev_disk_io = None
        self._prev_disk_time = None

        # Subscribers for real-time updates
        self._subscribers: List[asyncio.Queue] = []

    async def initialize(self):
        """Initialize the system service."""
        if self._initialized:
            return

        logger.info("=== SystemService.initialize() called ===")
        try:
            # Collect initial detailed metrics
            await self._collect_detailed_metrics()

            # Start update task
            self._update_task = asyncio.create_task(self._update_metrics_loop())

            self._initialized = True
            logger.info("System service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing system service: {e}")
            await self.cleanup()
            raise

    async def cleanup(self):
        """Clean up resources."""
        try:
            # Cancel update task
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
                self._update_task = None

            # Clear subscribers
            self._subscribers.clear()

            self._initialized = False
            logger.info("System service shut down")

        except Exception as e:
            logger.error(f"Error during system service cleanup: {e}")
            raise

    async def _update_metrics_loop(self):
        """Background task to update system metrics."""
        try:
            while True:
                try:
                    async with self._lock:
                        # Update status
                        self._status.update(
                            {
                                "status": "running",
                                "uptime": (
                                    datetime.utcnow()
                                    - datetime.fromisoformat(self._status["start_time"])
                                ).total_seconds(),
                                "last_update": datetime.utcnow().isoformat(),
                                "system_info": {
                                    "platform": platform.system(),
                                    "python_version": platform.python_version(),
                                    "cpu_count": psutil.cpu_count(),
                                    "memory_total": psutil.virtual_memory().total,
                                },
                            }
                        )

                        # Collect detailed metrics
                        await self._collect_detailed_metrics()

                        # Update memory service with system metrics
                        await self.memory_service.update_state(
                            {"system_metrics": self._detailed_metrics}
                        )

                        # Notify subscribers
                        await self._notify_subscribers()

                except Exception as e:
                    logger.error(f"Error updating system metrics: {e}")

                # Wait before next update
                await asyncio.sleep(self._collection_interval)

        except asyncio.CancelledError:
            logger.info("System metrics update loop cancelled")
            raise

    async def _collect_detailed_metrics(self):
        """Collect detailed system metrics."""
        try:
            # CPU metrics
            self._detailed_metrics["cpu"]["usage_percent"] = psutil.cpu_percent(
                interval=0.1
            )
            self._detailed_metrics["cpu"]["per_core"] = psutil.cpu_percent(
                interval=0.1, percpu=True
            )

            # Load average (on Unix systems)
            try:
                self._detailed_metrics["cpu"]["load_avg"] = [
                    x / psutil.cpu_count() * 100 for x in psutil.getloadavg()
                ]
            except (AttributeError, NotImplementedError):
                # Windows doesn't have getloadavg
                self._detailed_metrics["cpu"]["load_avg"] = [0.0, 0.0, 0.0]

            # Memory metrics
            mem = psutil.virtual_memory()
            self._detailed_metrics["memory"]["total"] = mem.total
            self._detailed_metrics["memory"]["available"] = mem.available
            self._detailed_metrics["memory"]["used"] = mem.used
            self._detailed_metrics["memory"]["percent"] = mem.percent

            # Swap metrics
            swap = psutil.swap_memory()
            self._detailed_metrics["memory"]["swap_total"] = swap.total
            self._detailed_metrics["memory"]["swap_used"] = swap.used
            self._detailed_metrics["memory"]["swap_percent"] = swap.percent

            # Disk metrics
            disk = psutil.disk_usage("/")
            self._detailed_metrics["disk"]["total"] = disk.total
            self._detailed_metrics["disk"]["used"] = disk.used
            self._detailed_metrics["disk"]["free"] = disk.free
            self._detailed_metrics["disk"]["percent"] = disk.percent

            # Disk I/O metrics
            try:
                disk_io = psutil.disk_io_counters()
                current_time = time.time()

                if disk_io and self._prev_disk_io and self._prev_disk_time:
                    time_delta = current_time - self._prev_disk_time

                    # Calculate rates
                    read_rate = (
                        disk_io.read_bytes - self._prev_disk_io.read_bytes
                    ) / time_delta
                    write_rate = (
                        disk_io.write_bytes - self._prev_disk_io.write_bytes
                    ) / time_delta

                    self._detailed_metrics["disk"]["io_counters"] = {
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count,
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes,
                        "read_rate": read_rate,
                        "write_rate": write_rate,
                    }
                else:
                    self._detailed_metrics["disk"]["io_counters"] = {
                        "read_count": disk_io.read_count if disk_io else 0,
                        "write_count": disk_io.write_count if disk_io else 0,
                        "read_bytes": disk_io.read_bytes if disk_io else 0,
                        "write_bytes": disk_io.write_bytes if disk_io else 0,
                        "read_rate": 0,
                        "write_rate": 0,
                    }

                self._prev_disk_io = disk_io
                self._prev_disk_time = current_time

            except (AttributeError, NotImplementedError):
                # Some systems might not support disk I/O counters
                pass

            # Network metrics
            try:
                net_io = psutil.net_io_counters()
                current_time = time.time()

                if net_io and self._prev_net_io and self._prev_net_time:
                    time_delta = current_time - self._prev_net_time

                    # Calculate rates
                    sent_rate = (
                        net_io.bytes_sent - self._prev_net_io.bytes_sent
                    ) / time_delta
                    recv_rate = (
                        net_io.bytes_recv - self._prev_net_io.bytes_recv
                    ) / time_delta

                    self._detailed_metrics["network"] = {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                        "sent_rate": sent_rate,
                        "recv_rate": recv_rate,
                        "connections": len(psutil.net_connections(kind="inet")),
                    }
                else:
                    self._detailed_metrics["network"] = {
                        "bytes_sent": net_io.bytes_sent if net_io else 0,
                        "bytes_recv": net_io.bytes_recv if net_io else 0,
                        "packets_sent": net_io.packets_sent if net_io else 0,
                        "packets_recv": net_io.packets_recv if net_io else 0,
                        "sent_rate": 0,
                        "recv_rate": 0,
                        "connections": len(psutil.net_connections(kind="inet")),
                    }

                self._prev_net_io = net_io
                self._prev_net_time = current_time

            except (AttributeError, NotImplementedError, psutil.AccessDenied):
                # Some systems might not support network I/O counters or connections
                pass

            # Process metrics
            try:
                process = psutil.Process(os.getpid())
                self._detailed_metrics["process"] = {
                    "pid": process.pid,
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_percent": process.memory_percent(),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # System metrics
            self._detailed_metrics["system"]["boot_time"] = psutil.boot_time()
            self._detailed_metrics["system"]["uptime"] = (
                time.time() - psutil.boot_time()
            )
            self._detailed_metrics["timestamp"] = datetime.utcnow().isoformat()

        except Exception as e:
            logger.error(f"Error collecting detailed metrics: {e}")

    async def _notify_subscribers(self):
        """Notify subscribers of metrics updates."""
        if not self._subscribers:
            return

        try:
            # Create a deep copy to prevent modification issues
            metrics_copy = json.loads(json.dumps(self._detailed_metrics))

            # Send to all subscribers
            for queue in self._subscribers[:]:  # Iterate over a copy
                try:
                    await asyncio.wait_for(queue.put(metrics_copy), timeout=1.0)
                except asyncio.TimeoutError:
                    logger.warning("Subscriber queue full or unresponsive, skipping.")
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")

        except Exception as e:
            logger.error(f"Error preparing notification for subscribers: {e}")

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status.

        Returns:
            System status dictionary
        """
        if not self._initialized:
            raise RuntimeError("System service not initialized")

        async with self._lock:
            return dict(self._status)

    async def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage.

        Returns:
            Resource usage dictionary
        """
        if not self._initialized:
            raise RuntimeError("System service not initialized")

        try:
            # Return a deep copy of the detailed metrics
            async with self._lock:
                return {
                    "cpu": self._detailed_metrics["cpu"],
                    "memory": self._detailed_metrics["memory"],
                    "disk": self._detailed_metrics["disk"],
                    "network": self._detailed_metrics["network"],
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed system metrics.

        Returns:
            Detailed system metrics dictionary
        """
        if not self._initialized:
            raise RuntimeError("System service not initialized")

        async with self._lock:
            return json.loads(json.dumps(self._detailed_metrics))

    async def get_health_check(self) -> Dict[str, Any]:
        """Get system health status.

        Returns:
            Health check dictionary
        """
        if not self._initialized:
            raise RuntimeError("System service not initialized")

        try:
            # Check services
            memory_state = await self.memory_service.get_current_state()
            metrics = await self.metrics_service.get_current_metrics()

            return {
                "status": "healthy",
                "services": {
                    "memory": "ok" if memory_state else "error",
                    "metrics": "ok" if metrics else "error",
                    "system": "ok",
                },
                "uptime": self._status["uptime"],
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error performing health check: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to system metrics updates.

        Returns:
            Queue that will receive system metrics updates
        """
        queue = asyncio.Queue(maxsize=10)  # Limit queue size
        self._subscribers.append(queue)

        # Send initial metrics
        try:
            metrics_copy = json.loads(json.dumps(self._detailed_metrics))
            await queue.put(metrics_copy)
        except Exception as e:
            logger.error(f"Error sending initial metrics to subscriber: {e}")

        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from system metrics updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def set_collection_interval(self, interval: int):
        """Set the collection interval in seconds."""
        if interval < 1:
            raise ValueError("Collection interval must be at least 1 second")
        self._collection_interval = interval
