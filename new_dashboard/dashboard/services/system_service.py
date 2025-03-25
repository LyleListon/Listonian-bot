"""Service for managing system-level metrics and operations."""

import asyncio
from typing import Dict, Any, Optional
import logging
import psutil
from datetime import datetime
import platform
import os

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
        self.memory_service = memory_service
        self.metrics_service = metrics_service
        self._status = {
            "status": "initializing",
            "uptime": 0,
            "start_time": datetime.utcnow().isoformat(),
            "last_update": None
        }
        self._update_task: Optional[asyncio.Task] = None
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the system service."""
        if self._initialized:
            return
            
        try:
            # Start status update task
            self._update_task = asyncio.create_task(self._update_status_loop())
            
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
            
            self._initialized = False
            logger.info("System service shut down")
            
        except Exception as e:
            logger.error(f"Error during system service cleanup: {e}")
            raise
            
    async def _update_status_loop(self):
        """Background task to update system status."""
        try:
            while True:
                try:
                    async with self._lock:
                        # Update status
                        self._status.update({
                            "status": "running",
                            "uptime": (datetime.utcnow() - datetime.fromisoformat(self._status["start_time"])).total_seconds(),
                            "last_update": datetime.utcnow().isoformat(),
                            "system_info": {
                                "platform": platform.system(),
                                "python_version": platform.python_version(),
                                "cpu_count": psutil.cpu_count(),
                                "memory_total": psutil.virtual_memory().total
                            }
                        })
                        
                except Exception as e:
                    logger.error(f"Error updating system status: {e}")
                    
                # Wait before next update
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("System status update loop cancelled")
            raise
            
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
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
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
                    "system": "ok"
                },
                "uptime": self._status["uptime"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error performing health check: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }