"""Dependency management for the dashboard."""

from typing import AsyncGenerator, Dict, Any, Optional
from fastapi import Depends
from contextlib import asynccontextmanager
import asyncio
from .config import settings
from .logging import get_logger, LoggerMixin

logger = get_logger("dependencies")

class ServiceRegistry:
    """Registry for managing service instances."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
        self.logger = get_logger("ServiceRegistry")

    async def initialize(self) -> None:
        """Initialize all registered services."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:  # Double-check after acquiring lock
                 return

            self.logger.info("Initializing service registry")
            for name, service in self._services.items():
                # Look for start() or initialize()
                init_method_name = None
                if hasattr(service, 'start') and callable(service.start):
                    init_method_name = 'start'
                elif hasattr(service, 'initialize') and callable(service.initialize):
                    init_method_name = 'initialize'

                if init_method_name:
                    init_method = getattr(service, init_method_name)
                    try:
                        if asyncio.iscoroutinefunction(init_method):
                            await init_method()
                        else:
                            init_method()
                        self.logger.info(f"Called {init_method_name}() on service: {name}")
                    except Exception as e:
                        self.logger.error(f"Failed to call {init_method_name}() on service {name}: {e}", exc_info=True)
                        raise

            self._initialized = True
            self.logger.info("Service registry initialization complete")

    async def shutdown(self) -> None:
        """Shutdown all registered services."""
        if not self._initialized:
            return

        async with self._lock:
            if not self._initialized:  # Double-check after acquiring lock
                 return

            self.logger.info("Shutting down service registry")
            for name, service in reversed(list(self._services.items())):
                # Look for stop() or shutdown()
                shutdown_method_name = None
                if hasattr(service, 'stop') and callable(service.stop):
                    shutdown_method_name = 'stop'
                elif hasattr(service, 'shutdown') and callable(service.shutdown):
                    shutdown_method_name = 'shutdown'

                if shutdown_method_name:
                    shutdown_method = getattr(service, shutdown_method_name)
                    try:
                        if asyncio.iscoroutinefunction(shutdown_method):
                            await shutdown_method()
                        else:
                            shutdown_method()
                        self.logger.info(f"Called {shutdown_method_name}() on service: {name}")
                    except Exception as e:
                        self.logger.error(f"Error calling {shutdown_method_name}() on service {name}: {e}", exc_info=True)

            self._initialized = False
            self.logger.info("Service registry shutdown complete")

    def register(self, name: str, service: Any) -> None:
        """Register a service instance."""
        if name in self._services:
            raise ValueError(f"Service {name} already registered")
        self._services[name] = service
        self.logger.debug(f"Registered service: {name}")

    def get(self, name: str) -> Any:
        """Get a service instance by name."""
        if not self._initialized:
            raise RuntimeError("Service registry not initialized")
        if name not in self._services:
            raise KeyError(f"Service {name} not found")
        return self._services[name]

# Global service registry instance
registry = ServiceRegistry()

class ServiceProvider:
    """Base class for service providers."""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.logger = get_logger(self.__class__.__name__)

    async def initialize(self) -> None:
        """Initialize the service provider."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the service provider."""
        pass

@asynccontextmanager
async def lifespan(app: "FastAPI"):  # type: ignore
    """Lifespan context manager for FastAPI application."""
    try:
        # Initialize services
        await registry.initialize()
        yield
    finally:
        # Shutdown services
        await registry.shutdown()

async def get_memory_service():
    """Dependency provider for memory service."""
    return registry.get("memory_service")

async def get_metrics_service():
    """Dependency provider for metrics service."""
    return registry.get("metrics_service")

async def get_system_service():
    """Dependency provider for system service."""
    return registry.get("system_service")

class RequiresService:
    """Decorator to inject service dependencies."""
    
    def __init__(self, *service_names: str):
        self.service_names = service_names

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # Inject required services
            for name in self.service_names:
                if name not in kwargs:
                    kwargs[name] = registry.get(name)
            return await func(*args, **kwargs)
        return wrapper

def register_services() -> None:
    """Register all required services."""
    # logger.info("--- Attempting to register services ---")
 # Reverted log
    from ..services.memory_service import MemoryService
    # logger.info("Imported MemoryService")
 # Reverted log
    from ..services.metrics_service import MetricsService
    # logger.info("Imported MetricsService")
 # Reverted log
    from ..services.system_service import SystemService

    # logger.info("Imported SystemService")
 # Reverted log

    # Register core services
    # logger.info("Registering MemoryService...")
 # Reverted log
    registry.register("memory_service", MemoryService(registry))
    # logger.info("Registering MetricsService...")
 # Reverted log
    registry.register("metrics_service", MetricsService(registry))
    # logger.info("Registering SystemService...")
 # Reverted log
    registry.register("system_service", SystemService(registry))
    # logger.info("--- Finished registering services ---") # Reverted log