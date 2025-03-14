"""Service manager for coordinating all dashboard services."""

from typing import Dict, Any, Optional
import asyncio
import logging

from ..core.logging import get_logger
from .memory_service import MemoryService
from .metrics_service import MetricsService
from .system_service import SystemService

logger = get_logger("service_manager")

class ServiceManager:
    """Manager for coordinating all dashboard services."""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize all services in the correct order."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:  # Double-check after acquiring lock
                return

            try:
                logger.info("Initializing services...")

                # Create services in dependency order
                memory_service = MemoryService()
                metrics_service = MetricsService(memory_service)
                system_service = SystemService(memory_service, metrics_service)

                # Store services
                self._services.update({
                    "memory": memory_service,
                    "metrics": metrics_service,
                    "system": system_service
                })

                # Initialize services in order
                await memory_service.initialize()
                logger.info("Memory service initialized")

                await metrics_service.initialize()
                logger.info("Metrics service initialized")

                await system_service.initialize()
                logger.info("System service initialized")

                self._initialized = True
                logger.info("All services initialized successfully")

            except Exception as e:
                logger.error(f"Error initializing services: {e}")
                # Attempt to shutdown any initialized services
                await self.shutdown()
                raise

    async def shutdown(self) -> None:
        """Shutdown all services in reverse order."""
        if not self._initialized:
            return

        async with self._lock:
            if not self._initialized:  # Double-check after acquiring lock
                return

            logger.info("Shutting down services...")

            # Shutdown in reverse dependency order
            shutdown_order = ["system", "metrics", "memory"]
            
            for service_name in shutdown_order:
                service = self._services.get(service_name)
                if service:
                    try:
                        await service.shutdown()
                        logger.info(f"{service_name.capitalize()} service shut down")
                    except Exception as e:
                        logger.error(f"Error shutting down {service_name} service: {e}")

            self._services.clear()
            self._initialized = False
            logger.info("All services shut down")

    def get_service(self, name: str) -> Any:
        """Get a service by name."""
        if not self._initialized:
            raise RuntimeError("Services not initialized")
        
        service = self._services.get(name)
        if not service:
            raise KeyError(f"Service {name} not found")
            
        return service

    @property
    def memory_service(self) -> MemoryService:
        """Get the memory service."""
        return self.get_service("memory")

    @property
    def metrics_service(self) -> MetricsService:
        """Get the metrics service."""
        return self.get_service("metrics")

    @property
    def system_service(self) -> SystemService:
        """Get the system service."""
        return self.get_service("system")

    async def get_system_overview(self) -> Dict[str, Any]:
        """Get a complete system overview from all services."""
        if not self._initialized:
            raise RuntimeError("Services not initialized")

        try:
            # Gather data from all services
            memory_state = await self.memory_service.get_current_state()
            metrics = await self.metrics_service.get_current_metrics()
            system_status = await self.system_service.get_system_status()

            return {
                "memory": memory_state,
                "metrics": metrics,
                "system": system_status,
                "timestamp": system_status.get("timestamp")
            }

        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {
                "error": str(e),
                "timestamp": system_status.get("timestamp")
            }

# Global service manager instance
service_manager = ServiceManager()