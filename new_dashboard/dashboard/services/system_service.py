"""Service for monitoring system health and resources."""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
import psutil
import platform
import logging
from pathlib import Path

from dashboard.core.logging import get_logger

logger = get_logger("system_service")

class SystemService:
    """Service for managing system health and monitoring."""

    def __init__(self, memory_service, metrics_service):
        self.memory_service = memory_service
        self.metrics_service = metrics_service
        self._status_cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._last_update = datetime.min
        self._subscribers: List[asyncio.Queue] = []
        self._process_start_time = datetime.now()
        self._error_log: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize the system service."""
        try:
            # Start background update task
            self._update_task = asyncio.create_task(self._background_update())
            logger.info("Started system status update task")

        except Exception as e:
            logger.error(f"Failed to initialize system service: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the system service."""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
        logger.info("System service shut down")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to system status updates."""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from system status updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        async with self._cache_lock:
            # Return cached data if it's fresh enough
            if (datetime.now() - self._last_update) < timedelta(seconds=15):
                return self._status_cache.copy()

        try:
            # Collect system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(str(Path.cwd()))
            
            # Get component health status
            component_status = await self._check_component_health()
            
            # Get network status
            network_status = await self._check_network_status()
            
            status = {
                "system": {
                    "cpu_usage": cpu_percent,
                    "memory_usage": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent
                    },
                    "disk_usage": {
                        "total": disk.total,
                        "free": disk.free,
                        "percent": disk.percent
                    },
                    "platform": {
                        "system": platform.system(),
                        "version": platform.version(),
                        "machine": platform.machine()
                    },
                    "uptime": (datetime.now() - self._process_start_time).total_seconds()
                },
                "components": component_status,
                "network": network_status,
                "errors": self._get_recent_errors(),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Update cache
            async with self._cache_lock:
                self._status_cache = status.copy()
                self._last_update = datetime.now()

            return status

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _background_update(self) -> None:
        """Background task to keep system status updated."""
        while True:
            try:
                # Get current status
                status = await self.get_system_status()

                # Notify subscribers
                for queue in self._subscribers:
                    try:
                        await queue.put(status)
                    except Exception as e:
                        logger.error(f"Error notifying subscriber: {e}")

                await asyncio.sleep(15)  # Update every 15 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background update: {e}")
                await asyncio.sleep(15)

    async def _check_component_health(self) -> Dict[str, Any]:
        """Check health status of all system components."""
        try:
            components = {
                "memory_bank": self.memory_service,
                "metrics": self.metrics_service
            }
            
            status = {}
            for name, component in components.items():
                try:
                    # Check if component is responding
                    is_healthy = True
                    error_message = None
                    
                    try:
                        if hasattr(component, "get_current_state"):
                            await component.get_current_state()
                        elif hasattr(component, "get_current_metrics"):
                            await component.get_current_metrics()
                    except Exception as e:
                        is_healthy = False
                        error_message = str(e)

                    status[name] = {
                        "status": "healthy" if is_healthy else "error",
                        "last_check": datetime.utcnow().isoformat(),
                        "error": error_message
                    }

                except Exception as e:
                    status[name] = {
                        "status": "error",
                        "error": str(e),
                        "last_check": datetime.utcnow().isoformat()
                    }

            return status

        except Exception as e:
            logger.error(f"Error checking component health: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _check_network_status(self) -> Dict[str, Any]:
        """Check network connectivity and status."""
        try:
            # Get memory bank status as proxy for network health
            memory_state = await self.memory_service.get_current_state()
            is_connected = "error" not in memory_state
            
            return {
                "connected": is_connected,
                "last_update": datetime.utcnow().isoformat(),
                "error": memory_state.get("error") if not is_connected else None
            }

        except Exception as e:
            logger.error(f"Error checking network status: {e}")
            return {
                "connected": False,
                "error": str(e),
                "last_update": datetime.utcnow().isoformat()
            }

    def log_error(self, error: str, component: str, severity: str = "error") -> None:
        """Log an error to the error history."""
        try:
            self._error_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": error,
                "component": component,
                "severity": severity
            })
            
            # Trim error log to last 1000 entries
            if len(self._error_log) > 1000:
                self._error_log = self._error_log[-1000:]
                
        except Exception as e:
            logger.error(f"Error logging error: {e}")

    def _get_recent_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent errors from the error log."""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            return [
                error for error in self._error_log
                if datetime.fromisoformat(error["timestamp"]) > cutoff
            ]
        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            return []