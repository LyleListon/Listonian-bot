"""System Monitor Service for collecting system resource metrics."""

import asyncio
import logging
import os
import platform
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import psutil
import json

from ..core.logging import get_logger

logger = get_logger("system_monitor")

class SystemMonitor:
    """Service for monitoring system resources and performance."""
    
    def __init__(self):
        """Initialize system monitor service."""
        self._subscribers: List[asyncio.Queue] = []
        self._current_metrics: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._initialized = False
        self._collection_interval = 5  # seconds
        
        # Initialize metrics structure
        self._metrics = {
            "cpu": {
                "usage_percent": 0.0,
                "per_core": [],
                "load_avg": [0.0, 0.0, 0.0]
            },
            "memory": {
                "total": 0,
                "available": 0,
                "used": 0,
                "percent": 0.0,
                "swap_total": 0,
                "swap_used": 0,
                "swap_percent": 0.0
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
                    "write_bytes": 0
                }
            },
            "network": {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
                "connections": 0
            },
            "process": {
                "pid": os.getpid(),
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "threads": 0,
                "open_files": 0
            },
            "system": {
                "boot_time": 0,
                "uptime": 0,
                "platform": platform.system(),
                "platform_release": platform.release(),
                "hostname": platform.node()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Previous network stats for calculating rates
        self._prev_net_io = None
        self._prev_net_time = None
        
        # Previous disk stats for calculating rates
        self._prev_disk_io = None
        self._prev_disk_time = None
        
    async def initialize(self):
        """Initialize the system monitor service."""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing system monitor service")
            
            # Collect initial metrics
            await self._collect_metrics()
            
            # Start update task
            self._update_task = asyncio.create_task(self._update_loop())
            
            self._initialized = True
            logger.info("System monitor service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing system monitor service: {e}")
            await self.cleanup()
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Cancel update task
            if self._update_task:
                self._update_task.cancel()
                try:
                    await asyncio.wait_for(self._update_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                self._update_task = None
            
            # Clear subscribers
            self._subscribers.clear()
            
            self._initialized = False
            logger.info("System monitor service shut down")
            
        except Exception as e:
            logger.error(f"Error during system monitor service cleanup: {e}")
            # Don't raise here to allow other cleanup to proceed
            
    async def _update_loop(self):
        """Background task to periodically update system metrics."""
        try:
            while True:
                try:
                    await self._collect_metrics()
                    await self._notify_subscribers()
                except Exception as e:
                    logger.error(f"Error updating system metrics: {e}")
                
                # Wait before next update
                await asyncio.sleep(self._collection_interval)
                
        except asyncio.CancelledError:
            logger.info("System metrics update loop cancelled")
            # No need to raise CancelledError here
            
    async def _collect_metrics(self):
        """Collect system metrics."""
        async with self._lock:
            try:
                # CPU metrics
                self._metrics["cpu"]["usage_percent"] = psutil.cpu_percent(interval=0.1)
                self._metrics["cpu"]["per_core"] = psutil.cpu_percent(interval=0.1, percpu=True)
                
                # Load average (on Unix systems)
                try:
                    self._metrics["cpu"]["load_avg"] = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]
                except (AttributeError, NotImplementedError):
                    # Windows doesn't have getloadavg
                    self._metrics["cpu"]["load_avg"] = [0.0, 0.0, 0.0]
                
                # Memory metrics
                mem = psutil.virtual_memory()
                self._metrics["memory"]["total"] = mem.total
                self._metrics["memory"]["available"] = mem.available
                self._metrics["memory"]["used"] = mem.used
                self._metrics["memory"]["percent"] = mem.percent
                
                # Swap metrics
                swap = psutil.swap_memory()
                self._metrics["memory"]["swap_total"] = swap.total
                self._metrics["memory"]["swap_used"] = swap.used
                self._metrics["memory"]["swap_percent"] = swap.percent
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                self._metrics["disk"]["total"] = disk.total
                self._metrics["disk"]["used"] = disk.used
                self._metrics["disk"]["free"] = disk.free
                self._metrics["disk"]["percent"] = disk.percent
                
                # Disk I/O metrics
                try:
                    disk_io = psutil.disk_io_counters()
                    current_time = time.time()
                    
                    if disk_io and self._prev_disk_io and self._prev_disk_time:
                        time_delta = current_time - self._prev_disk_time
                        
                        # Calculate rates
                        read_rate = (disk_io.read_bytes - self._prev_disk_io.read_bytes) / time_delta
                        write_rate = (disk_io.write_bytes - self._prev_disk_io.write_bytes) / time_delta
                        
                        self._metrics["disk"]["io_counters"] = {
                            "read_count": disk_io.read_count,
                            "write_count": disk_io.write_count,
                            "read_bytes": disk_io.read_bytes,
                            "write_bytes": disk_io.write_bytes,
                            "read_rate": read_rate,
                            "write_rate": write_rate
                        }
                    else:
                        self._metrics["disk"]["io_counters"] = {
                            "read_count": disk_io.read_count if disk_io else 0,
                            "write_count": disk_io.write_count if disk_io else 0,
                            "read_bytes": disk_io.read_bytes if disk_io else 0,
                            "write_bytes": disk_io.write_bytes if disk_io else 0,
                            "read_rate": 0,
                            "write_rate": 0
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
                        sent_rate = (net_io.bytes_sent - self._prev_net_io.bytes_sent) / time_delta
                        recv_rate = (net_io.bytes_recv - self._prev_net_io.bytes_recv) / time_delta
                        
                        self._metrics["network"] = {
                            "bytes_sent": net_io.bytes_sent,
                            "bytes_recv": net_io.bytes_recv,
                            "packets_sent": net_io.packets_sent,
                            "packets_recv": net_io.packets_recv,
                            "sent_rate": sent_rate,
                            "recv_rate": recv_rate,
                            "connections": len(psutil.net_connections(kind='inet'))
                        }
                    else:
                        self._metrics["network"] = {
                            "bytes_sent": net_io.bytes_sent if net_io else 0,
                            "bytes_recv": net_io.bytes_recv if net_io else 0,
                            "packets_sent": net_io.packets_sent if net_io else 0,
                            "packets_recv": net_io.packets_recv if net_io else 0,
                            "sent_rate": 0,
                            "recv_rate": 0,
                            "connections": len(psutil.net_connections(kind='inet'))
                        }
                    
                    self._prev_net_io = net_io
                    self._prev_net_time = current_time
                    
                except (AttributeError, NotImplementedError, psutil.AccessDenied):
                    # Some systems might not support network I/O counters or connections
                    pass
                
                # Process metrics
                try:
                    process = psutil.Process(os.getpid())
                    self._metrics["process"]["cpu_percent"] = process.cpu_percent(interval=0.1)
                    self._metrics["process"]["memory_percent"] = process.memory_percent()
                    self._metrics["process"]["threads"] = process.num_threads()
                    self._metrics["process"]["open_files"] = len(process.open_files())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                # System metrics
                self._metrics["system"]["boot_time"] = psutil.boot_time()
                self._metrics["system"]["uptime"] = time.time() - psutil.boot_time()
                
                # Update timestamp
                self._metrics["timestamp"] = datetime.utcnow().isoformat()
                
                # Update current metrics
                self._current_metrics = self._metrics.copy()
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                raise
            
    async def _notify_subscribers(self):
        """Notify subscribers of metrics updates."""
        if not self._subscribers:
            return
            
        try:
            # Create a deep copy to prevent modification issues
            metrics_copy = json.loads(json.dumps(self._current_metrics))
            
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
            
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to system metrics updates.
        
        Returns:
            Queue that will receive system metrics updates
        """
        queue = asyncio.Queue(maxsize=10)  # Limit queue size
        self._subscribers.append(queue)
        
        # Send initial metrics
        try:
            metrics_copy = json.loads(json.dumps(self._current_metrics))
            await queue.put(metrics_copy)
        except Exception as e:
            logger.error(f"Error sending initial metrics to subscriber: {e}")
            
        return queue
        
    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from system metrics updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics.
        
        Returns:
            Current system metrics dictionary
        """
        async with self._lock:
            # Return a deep copy
            return json.loads(json.dumps(self._current_metrics))
            
    def set_collection_interval(self, interval: int):
        """Set the collection interval in seconds."""
        if interval < 1:
            raise ValueError("Collection interval must be at least 1 second")
        self._collection_interval = interval