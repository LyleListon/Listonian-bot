"""Service manager for coordinating all dashboard services."""

from typing import Dict, Any, Optional
import os
import asyncio
import json
from pathlib import Path

from ..core.logging import get_logger
from .memory_service import MemoryService
from .metrics_service import MetricsService
from .system_service import SystemService
from .market_data_service import MarketDataService

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

                # Set up memory bank directory
                project_root = Path(__file__).parent.parent.parent.parent
                memory_bank_dir = project_root / "memory-bank"
                logger.info(f"Project root: {project_root}")
                memory_bank_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Memory bank directory: {memory_bank_dir}")

                # Load configuration
                config_path = project_root / "config.json"
                with open(config_path) as f:
                    config = json.loads(f.read())

                # Create services in dependency order
                memory_service = MemoryService(str(memory_bank_dir))
                metrics_service = MetricsService(memory_service)
                system_service = SystemService(memory_service, metrics_service)
                market_data_service = MarketDataService(memory_service, metrics_service, config)

                # Store services
                self._services.update({
                    "memory": memory_service,
                    "metrics": metrics_service,
                    "system": system_service,
                    "market": market_data_service
                })

                # Initialize services in order
                await memory_service.initialize()
                logger.info("Memory service initialized")

                await metrics_service.initialize()
                logger.info("Metrics service initialized")

                await system_service.initialize()
                logger.info("System service initialized")

                await market_data_service.initialize()
                logger.info("Market data service initialized")

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
            shutdown_order = ["market", "system", "metrics", "memory"]
            
            for service_name in shutdown_order:
                service = self._services.get(service_name)
                if service:
                    try:
                        await service.cleanup()
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

    @property
    def market_data_service(self) -> MarketDataService:
        """Get the market data service."""
        return self.get_service("market")

    async def get_system_overview(self) -> Dict[str, Any]:
        """Get a complete system overview from all services."""
        if not self._initialized:
            raise RuntimeError("Services not initialized")

        try:
            # Gather data from all services
            memory_state = await self.memory_service.get_current_state()
            metrics = await self.metrics_service.get_current_metrics()
            system_status = await self.system_service.get_system_status()
            market_data = await self.market_data_service.get_current_market_data()

            return {
                "memory": memory_state,
                "metrics": metrics,
                "system": system_status,
                "market": market_data,
                "timestamp": system_status.get("timestamp")
            }

        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {
                "error": str(e),
                "timestamp": system_status.get("timestamp") if "system_status" in locals() else None
            }

# Global service manager instance
service_manager = ServiceManager()