"""Service Manager for Dashboard.

This module implements a service manager that enforces proper initialization order
and handles service dependencies correctly.
"""

import asyncio
import logging
from typing import Dict, Optional, Set, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum, auto

from ...utils.memory_bank.monitor import MemoryBankMonitor
from ...utils.memory_bank.initializer import MemoryBankInitializer
from .logging import get_logger

logger = get_logger(__name__)


class ServiceState(Enum):
    """Service lifecycle states."""

    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()
    SHUTDOWN = auto()


@dataclass
class ServiceInfo:
    """Information about a service instance."""

    name: str
    state: ServiceState
    dependencies: Set[str]
    instance: Optional[object]
    error: Optional[Exception] = None


class ServiceManager:
    """Manages service lifecycle and dependencies."""

    def __init__(self, base_path: Path):
        self._base_path = Path(base_path)
        self._services: Dict[str, ServiceInfo] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._logger = logger

        # Initialize core service info
        self._services["memory"] = ServiceInfo(
            name="memory",
            state=ServiceState.UNINITIALIZED,
            dependencies=set(),
            instance=None,
        )
        self._services["metrics"] = ServiceInfo(
            name="metrics",
            state=ServiceState.UNINITIALIZED,
            dependencies={"memory"},
            instance=None,
        )
        self._services["system"] = ServiceInfo(
            name="system",
            state=ServiceState.UNINITIALIZED,
            dependencies={"memory", "metrics"},
            instance=None,
        )

    async def initialize(self) -> None:
        """Initialize services in correct dependency order."""
        async with self._lock:
            if self._initialized:
                return

            self._logger.info("Initializing service manager")

            try:
                # Initialize memory service first
                await self._initialize_memory_service()

                # Initialize remaining services in dependency order
                uninitialized = {
                    name
                    for name, info in self._services.items()
                    if info.state == ServiceState.UNINITIALIZED and name != "memory"
                }

                while uninitialized:
                    ready_to_init = {
                        name
                        for name in uninitialized
                        if all(
                            self._services[dep].state == ServiceState.READY
                            for dep in self._services[name].dependencies
                        )
                    }

                    if not ready_to_init:
                        raise RuntimeError(
                            f"Circular dependency detected in services: {uninitialized}"
                        )

                    for service_name in ready_to_init:
                        await self._initialize_service(service_name)
                        uninitialized.remove(service_name)

                self._initialized = True
                self._logger.info("Service manager initialized successfully")

            except Exception as e:
                error_msg = f"Failed to initialize service manager: {e}"
                self._logger.error(error_msg, exc_info=True)
                await self.cleanup()
                raise RuntimeError(error_msg)

    async def _initialize_memory_service(self) -> None:
        """Initialize the memory service."""
        service = self._services["memory"]
        service.state = ServiceState.INITIALIZING

        try:
            # Initialize memory bank
            initializer = MemoryBankInitializer(self._base_path / "memory_bank")
            await initializer.initialize()

            # Set up monitoring
            monitor = MemoryBankMonitor(self._base_path / "memory_bank")
            await monitor.initialize()

            service.instance = monitor
            service.state = ServiceState.READY
            self._logger.info("Memory service initialized successfully")

        except Exception as e:
            service.state = ServiceState.ERROR
            service.error = e
            raise

    async def _initialize_service(self, service_name: str) -> None:
        """Initialize a specific service."""
        service = self._services[service_name]
        service.state = ServiceState.INITIALIZING

        try:
            # Initialize service based on type
            if service_name == "metrics":
                # Initialize metrics service
                from ..services.metrics import MetricsService

                service.instance = MetricsService(
                    memory_service=self._services["memory"].instance
                )
                await service.instance.initialize()

            elif service_name == "system":
                # Initialize system service
                from ..services.system import SystemService

                service.instance = SystemService(
                    memory_service=self._services["memory"].instance,
                    metrics_service=self._services["metrics"].instance,
                )
                await service.instance.initialize()

            service.state = ServiceState.READY
            self._logger.info(f"{service_name} service initialized successfully")

        except Exception as e:
            service.state = ServiceState.ERROR
            service.error = e
            raise

    async def get_service(self, service_name: str) -> object:
        """Get an initialized service instance."""
        if not self._initialized:
            raise RuntimeError("Service manager not initialized")

        service = self._services.get(service_name)
        if not service:
            raise ValueError(f"Unknown service: {service_name}")

        if service.state != ServiceState.READY:
            raise RuntimeError(
                f"Service {service_name} not ready (state: {service.state.name})"
            )

        return service.instance

    async def get_status(self) -> Dict[str, Dict]:
        """Get status of all services."""
        return {
            name: {
                "state": info.state.name,
                "error": str(info.error) if info.error else None,
                "dependencies": list(info.dependencies),
            }
            for name, info in self._services.items()
        }

    async def cleanup(self) -> None:
        """Clean up all services in reverse dependency order."""
        async with self._lock:
            if not self._initialized:
                return

            self._logger.info("Cleaning up services")

            # Get services in reverse dependency order
            services_to_cleanup = self._get_reverse_dependency_order()

            for service_name in services_to_cleanup:
                service = self._services[service_name]
                if service.state in (ServiceState.READY, ServiceState.ERROR):
                    try:
                        service.state = ServiceState.SHUTTING_DOWN
                        if hasattr(service.instance, "cleanup"):
                            await service.instance.cleanup()
                        service.state = ServiceState.SHUTDOWN
                        self._logger.info(
                            f"{service_name} service cleaned up successfully"
                        )
                    except Exception as e:
                        self._logger.error(
                            f"Error cleaning up {service_name} service: {e}",
                            exc_info=True,
                        )
                        service.state = ServiceState.ERROR
                        service.error = e

            self._initialized = False
            self._logger.info("Service cleanup completed")

    def _get_reverse_dependency_order(self) -> List[str]:
        """Get services in reverse dependency order."""
        visited = set()
        order = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            # Visit services that depend on this one
            for dep_name, dep_info in self._services.items():
                if name in dep_info.dependencies:
                    visit(dep_name)
            order.append(name)

        # Start with services that have no dependencies
        for name, info in self._services.items():
            if not info.dependencies:
                visit(name)

        return order
