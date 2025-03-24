"""Connection Manager for Dashboard.

This module implements a connection manager that handles service connections
and ensures proper dependency management with the service manager.
"""

import asyncio
import logging
from typing import Dict, Optional, Set, List, Any
from dataclasses import dataclass
from enum import Enum, auto

from .service_manager import ServiceManager
from .logging import get_logger

logger = get_logger(__name__)

class ConnectionState(Enum):
    """Connection states."""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()
    DISCONNECTING = auto()

@dataclass
class ConnectionInfo:
    """Information about a service connection."""
    name: str
    state: ConnectionState
    last_error: Optional[Exception] = None
    retry_count: int = 0
    max_retries: int = 3
    backoff_factor: float = 1.5

class ConnectionManager:
    """Manages service connections and dependencies."""

    def __init__(self, service_manager: ServiceManager):
        self._service_manager = service_manager
        self._connections: Dict[str, ConnectionInfo] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._logger = logger
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None

        # Initialize core connection info
        for service_name in ["memory", "metrics", "system"]:
            self._connections[service_name] = ConnectionInfo(
                name=service_name,
                state=ConnectionState.DISCONNECTED
            )

    async def initialize(self) -> None:
        """Initialize connections to all services."""
        async with self._lock:
            if self._initialized:
                return

            self._logger.info("Initializing connection manager")

            try:
                # Ensure service manager is initialized
                service_status = await self._service_manager.get_status()
                
                # Connect to services in dependency order
                for service_name, info in service_status.items():
                    if info["state"] != "READY":
                        raise RuntimeError(
                            f"Service {service_name} not ready: {info['state']}"
                        )
                    await self._connect_service(service_name)

                # Start health check task
                self._health_check_task = asyncio.create_task(
                    self._health_check_loop()
                )

                self._initialized = True
                self._logger.info("Connection manager initialized successfully")

            except Exception as e:
                error_msg = f"Failed to initialize connection manager: {e}"
                self._logger.error(error_msg, exc_info=True)
                await self.cleanup()
                raise RuntimeError(error_msg)

    async def _connect_service(self, service_name: str) -> None:
        """Establish connection to a service."""
        connection = self._connections[service_name]
        connection.state = ConnectionState.CONNECTING

        try:
            # Get service instance
            service = await self._service_manager.get_service(service_name)

            # Verify service health
            if service_name == "memory":
                health_status = await service.get_health_status()
                if health_status.status != "healthy":
                    raise RuntimeError(
                        f"Memory service unhealthy: {health_status.message}"
                    )

            connection.state = ConnectionState.CONNECTED
            connection.retry_count = 0
            self._logger.info(f"Connected to {service_name} service")

        except Exception as e:
            connection.state = ConnectionState.ERROR
            connection.last_error = e
            connection.retry_count += 1
            raise

    async def _health_check_loop(self) -> None:
        """Periodic health check of all connections."""
        while True:
            try:
                for service_name, connection in self._connections.items():
                    if connection.state == ConnectionState.CONNECTED:
                        try:
                            service = await self._service_manager.get_service(
                                service_name
                            )
                            
                            # Check service health
                            if service_name == "memory":
                                health_status = await service.get_health_status()
                                if health_status.status != "healthy":
                                    self._logger.warning(
                                        f"Memory service health check failed: "
                                        f"{health_status.message}"
                                    )
                                    await self._handle_connection_error(
                                        service_name,
                                        RuntimeError(health_status.message)
                                    )

                        except Exception as e:
                            await self._handle_connection_error(service_name, e)

                await asyncio.sleep(self._health_check_interval)

            except asyncio.CancelledError:
                self._logger.info("Health check loop cancelled")
                break
            except Exception as e:
                self._logger.error(
                    f"Error in health check loop: {e}",
                    exc_info=True
                )
                await asyncio.sleep(self._health_check_interval)

    async def _handle_connection_error(
        self,
        service_name: str,
        error: Exception
    ) -> None:
        """Handle connection errors with retry logic."""
        connection = self._connections[service_name]
        connection.state = ConnectionState.ERROR
        connection.last_error = error

        if connection.retry_count < connection.max_retries:
            backoff = connection.backoff_factor ** connection.retry_count
            self._logger.info(
                f"Retrying {service_name} connection in {backoff:.1f}s "
                f"(attempt {connection.retry_count + 1})"
            )
            await asyncio.sleep(backoff)
            try:
                await self._connect_service(service_name)
            except Exception as e:
                self._logger.error(
                    f"Retry failed for {service_name}: {e}",
                    exc_info=True
                )
        else:
            self._logger.error(
                f"Max retries ({connection.max_retries}) reached for "
                f"{service_name}"
            )

    async def get_connection_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connections."""
        return {
            name: {
                "state": info.state.name,
                "error": str(info.last_error) if info.last_error else None,
                "retry_count": info.retry_count,
                "max_retries": info.max_retries
            }
            for name, info in self._connections.items()
        }

    async def cleanup(self) -> None:
        """Clean up all connections."""
        async with self._lock:
            if not self._initialized:
                return

            self._logger.info("Cleaning up connections")

            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Disconnect services in reverse order
            for service_name in reversed(list(self._connections.keys())):
                connection = self._connections[service_name]
                if connection.state == ConnectionState.CONNECTED:
                    try:
                        connection.state = ConnectionState.DISCONNECTING
                        # Any additional cleanup needed for specific services
                        connection.state = ConnectionState.DISCONNECTED
                        self._logger.info(
                            f"{service_name} connection closed successfully"
                        )
                    except Exception as e:
                        self._logger.error(
                            f"Error disconnecting {service_name}: {e}",
                            exc_info=True
                        )
                        connection.state = ConnectionState.ERROR
                        connection.last_error = e

            self._initialized = False
            self._logger.info("Connection cleanup completed")