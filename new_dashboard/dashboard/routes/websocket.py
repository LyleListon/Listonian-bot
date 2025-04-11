"""WebSocket routes for real-time metrics data."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Any, Set, AsyncIterator
import asyncio
import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from weakref import WeakKeyDictionary
from enum import Enum, auto
from ..core.logging import get_logger
from ..core.dependencies import (
    get_metrics_service,
    get_memory_service,
    get_market_data_service,
    get_system_service,
)
from ..services.metrics_service import MetricsService
from ..services.memory_service import MemoryService
from ..services.market_data_service import MarketDataService
from ..services.system_service import SystemService

router = APIRouter()
logger = get_logger("websocket_routes")


class ConnectionState(Enum):
    """Represents the state of a WebSocket connection."""

    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTING = auto()
    DISCONNECTED = auto()


class ConnectionManager:
    """Manage WebSocket connections with explicit state tracking."""

    def __init__(self):
        # Stores {websocket: {"state": ConnectionState, "tasks": set(), "queues": set()}}
        self._connections: WeakKeyDictionary[WebSocket, Dict[str, Any]] = (
            WeakKeyDictionary()
        )
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def connection(self, websocket: WebSocket) -> AsyncIterator[None]:
        """Context manager for WebSocket connections."""
        try:
            logger.info(f"Accepting new WebSocket connection from {websocket.client}")
            await websocket.accept()
            async with self._lock:
                # Initialize connection state
                self._connections[websocket] = {
                    "state": ConnectionState.CONNECTING,
                    "tasks": set(),
                    "queues": set(),
                }
                # Transition to CONNECTED after successful accept
                self._connections[websocket]["state"] = ConnectionState.CONNECTED
            logger.info(
                f"New WebSocket connection. Total connections: {len(self._connections)}"
            )
            yield
        finally:
            # Ensure cleanup happens even if yield raises an error
            logger.debug(f"Starting cleanup for {websocket.client}")
            await self._cleanup_connection(websocket)
            logger.debug(f"Finished cleanup for {websocket.client}")

    async def _cleanup_connection(self, websocket: WebSocket):
        """Clean up a WebSocket connection."""
        try:
            async with self._lock:
                if websocket in self._connections:
                    # Prevent cleanup if already cleaned up or never fully connected
                    if (
                        websocket not in self._connections
                        or self._connections[websocket]["state"]
                        == ConnectionState.DISCONNECTED
                    ):
                        logger.debug(
                            f"Cleanup already done or connection not present for {websocket.client}"
                        )
                        return

                    logger.info(
                        f"Cleaning up connection for {websocket.client}. Current state: {self._connections[websocket]['state']}"
                    )
                    self._connections[websocket][
                        "state"
                    ] = ConnectionState.DISCONNECTING

                    tasks_to_cancel = list(self._connections[websocket]["tasks"])
                    logger.debug(
                        f"Cancelling {len(tasks_to_cancel)} tasks for {websocket.client}"
                    )
                    for task in tasks_to_cancel:
                        if not task.done():
                            task.cancel()

                    if tasks_to_cancel:
                        # Use gather to potentially catch cancellation errors
                        results = await asyncio.gather(
                            *tasks_to_cancel, return_exceptions=True
                        )
                        for i, result in enumerate(results):
                            if isinstance(result, Exception) and not isinstance(
                                result, asyncio.CancelledError
                            ):
                                logger.warning(
                                    f"Task {tasks_to_cancel[i].get_name()} raised error during cancellation: {result}"
                                )

                    logger.debug(
                        f"Clearing queues and tasks sets for {websocket.client}"
                    )
                    # Clear sets after tasks are handled
                    self._connections[websocket]["queues"].clear()
                    self._connections[websocket]["tasks"].clear()
                    del self._connections[websocket]
            # Final state transition after cleanup
            self._connections[websocket]["state"] = ConnectionState.DISCONNECTED
            logger.info(
                f"WebSocket disconnected and cleaned up for {websocket.client}. Remaining connections: {len(self._connections)}"
            )
            # Remove from dictionary explicitly after cleanup (WeakKeyDictionary might delay removal)
            if websocket in self._connections:
                del self._connections[websocket]
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")

    def add_task(self, websocket: WebSocket, task: asyncio.Task):
        """Add a task to the connection."""
        # Only add tasks if the connection is currently connected
        if (
            websocket in self._connections
            and self._connections[websocket]["state"] == ConnectionState.CONNECTED
        ):
            self._connections[websocket]["tasks"].add(task)
        else:
            logger.warning(
                f"Attempted to add task to non-connected websocket {websocket.client}"
            )

    def add_queue(self, websocket: WebSocket, queue: asyncio.Queue):
        """Add a queue to the connection."""
        # Only add queues if the connection is currently connected
        if (
            websocket in self._connections
            and self._connections[websocket]["state"] == ConnectionState.CONNECTED
        ):
            self._connections[websocket]["queues"].add(queue)
        else:
            logger.warning(
                f"Attempted to add queue to non-connected websocket {websocket.client}"
            )

    def is_active(self, websocket: WebSocket) -> bool:
        """Check if a connection is active."""
        return (
            websocket in self._connections
            and self._connections[websocket]["state"] == ConnectionState.CONNECTED
        )


manager = ConnectionManager()


async def handle_updates(
    websocket: WebSocket, queue: asyncio.Queue, process_update, connection_active
):
    """Handle updates from a queue and send to websocket."""
    try:
        while connection_active():
            update = None  # Initialize update to None
            try:
                logger.info(f"Waiting for update from queue")
                update = await asyncio.wait_for(queue.get(), timeout=1.0)
                logger.debug(
                    f"Received raw update from queue: {update}"
                )  # Log raw update
                if connection_active():
                    # Check connection state *immediately* before sending
                    if connection_active():
                        processed_update = process_update(update)
                        logger.debug(
                            f"Processed update to send: {processed_update}"
                        )  # Log processed update
                        try:
                            await websocket.send_json(processed_update)
                        except (
                            Exception
                        ) as send_error:  # Catch potential errors during send (e.g., connection closed mid-send)
                            logger.warning(
                                f"Error sending JSON update: {send_error}. Connection state likely changed."
                            )
                            break  # Exit loop if send fails
                    else:
                        logger.info("Connection became inactive before sending update.")
                        break
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Update handler cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing update: {e}")
                # Exit loop immediately if connection becomes inactive
                if not connection_active():
                    logger.info("Connection became inactive during update processing.")
                    break
    except Exception as e:
        logger.error(f"Error in update handler: {e}")


@router.websocket("/ws/metrics")
async def websocket_metrics(
    websocket: WebSocket,
    metrics_service: MetricsService = Depends(get_metrics_service),
    memory_service: MemoryService = Depends(get_memory_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """WebSocket endpoint for all metrics updates."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            logger.info("WebSocket client connected to metrics endpoint")

            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            # Send initial state
            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                logger.info(f"Sending initial metrics state via /ws/metrics")
                logger.debug(
                    f"Initial metrics data: {initial_metrics}"
                )  # Log initial data
                try:
                    await websocket.send_json(
                        {
                            "type": "initial_state",
                            "data": initial_metrics,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(f"Error sending initial state: {send_error}")
                    # If initial send fails, don't proceed
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning("Connection inactive before sending initial state.")
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    lambda x: {**x, "_timestamp": datetime.utcnow().isoformat()},
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)

            try:
                await update_task
            except asyncio.CancelledError:
                logger.info("Metrics WebSocket task cancelled")
            except Exception as e:
                logger.error(f"Error in metrics WebSocket task: {e}")

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from metrics endpoint")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


@router.websocket("/ws/profitability")
async def websocket_profitability(
    websocket: WebSocket, metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for profitability metrics."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            logger.info("WebSocket client connected to profitability endpoint")

            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            # Send initial state
            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    await websocket.send_json(
                        {
                            "profitability": initial_metrics.get("metrics", {}).get(
                                "profitability", {}
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(
                        f"Error sending initial profitability state: {send_error}"
                    )
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial profitability state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "profitability": update.get("metrics", {}).get("profitability", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from profitability endpoint")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


@router.websocket("/ws/dex-performance")
async def websocket_dex_performance(
    websocket: WebSocket, metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for DEX performance metrics."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    await websocket.send_json(
                        {
                            "dex_performance": initial_metrics.get("metrics", {}).get(
                                "dex_performance", {}
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(
                        f"Error sending initial dex_performance state: {send_error}"
                    )
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial dex_performance state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "dex_performance": update.get("metrics", {}).get(
                        "dex_performance", {}
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from DEX performance endpoint")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


@router.websocket("/ws/flash-loans")
async def websocket_flash_loans(
    websocket: WebSocket, metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for flash loan metrics."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    await websocket.send_json(
                        {
                            "flash_loans": initial_metrics.get("metrics", {}).get(
                                "flash_loans", {}
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(
                        f"Error sending initial flash_loans state: {send_error}"
                    )
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial flash_loans state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "flash_loans": update.get("metrics", {}).get("flash_loans", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from flash loans endpoint")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


@router.websocket("/ws/execution")
async def websocket_execution(
    websocket: WebSocket, metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for execution metrics."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    await websocket.send_json(
                        {
                            "execution": initial_metrics.get("metrics", {}).get(
                                "execution", {}
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(
                        f"Error sending initial execution state: {send_error}"
                    )
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial execution state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "execution": update.get("metrics", {}).get("execution", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from execution endpoint")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


@router.websocket("/ws/token-performance")
async def websocket_token_performance(
    websocket: WebSocket, metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for token performance metrics."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    await websocket.send_json(
                        {
                            "token_performance": initial_metrics.get("metrics", {}).get(
                                "token_performance", {}
                            ),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(
                        f"Error sending initial token_performance state: {send_error}"
                    )
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial token_performance state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "token_performance": update.get("metrics", {}).get(
                        "token_performance", {}
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from token performance endpoint")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


@router.websocket("/ws/system-performance")
async def websocket_system_performance(
    websocket: WebSocket, metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for system performance metrics."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    await websocket.send_json(
                        {
                            "system_performance": initial_metrics.get(
                                "metrics", {}
                            ).get("system_performance", {}),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(
                        f"Error sending initial system_performance state: {send_error}"
                    )
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial system_performance state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "system_performance": update.get("metrics", {}).get(
                        "system_performance", {}
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info(
                "WebSocket client disconnected from system performance endpoint"
            )
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


# Keep existing endpoints
@router.websocket("/ws/system")
async def websocket_system(
    websocket: WebSocket, metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for system metrics only."""
    metrics_queue = None

    async with manager.connection(websocket):
        try:
            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)

            initial_metrics = await metrics_service.get_current_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    system_metrics = {
                        "system": initial_metrics.get("system", {}),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await websocket.send_json(system_metrics)
                except Exception as send_error:
                    logger.warning(f"Error sending initial system state: {send_error}")
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial system state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "system": update.get("system", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    metrics_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from system endpoint")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)


@router.websocket("/ws/detailed-system")
async def websocket_detailed_system(
    websocket: WebSocket, system_service: SystemService = Depends(get_system_service)
):
    """WebSocket endpoint for detailed system metrics."""
    system_queue = None

    async with manager.connection(websocket):
        try:
            logger.info(
                "WebSocket client connected to detailed system metrics endpoint"
            )

            # Subscribe to system service updates
            system_queue = await system_service.subscribe()
            manager.add_queue(websocket, system_queue)

            # Send initial metrics
            initial_metrics = await system_service.get_detailed_metrics()
            # Check state before sending initial data
            if manager.is_active(websocket):
                try:
                    await websocket.send_json(
                        {
                            "type": "detailed_system_metrics",
                            "data": initial_metrics,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception as send_error:
                    logger.warning(
                        f"Error sending initial detailed_system state: {send_error}"
                    )
                    raise WebSocketDisconnect(
                        code=1008, reason="Failed to send initial state"
                    )
            else:
                logger.warning(
                    "Connection inactive before sending initial detailed_system state."
                )
                raise WebSocketDisconnect(
                    code=1001, reason="Connection closed before initialization"
                )

            def process_update(update):
                return {
                    "type": "detailed_system_metrics",
                    "data": update,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    system_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info(
                "WebSocket client disconnected from detailed system metrics endpoint"
            )
        finally:
            if system_queue:
                await system_service.unsubscribe(system_queue)


@router.websocket("/ws/trades")
async def websocket_trades(
    websocket: WebSocket, memory_service: MemoryService = Depends(get_memory_service)
):
    """WebSocket endpoint for trade history updates only."""
    memory_queue = None

    async with manager.connection(websocket):
        try:
            memory_queue = await memory_service.subscribe()
            manager.add_queue(websocket, memory_queue)

            initial_state = await memory_service.get_current_state()
            if manager.is_active(websocket):
                trade_data = {
                    "trade_history": initial_state.get("trade_history", []),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await websocket.send_json(trade_data)

            def process_update(update):
                return {
                    "trade_history": update.get("trade_history", []),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    memory_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from trades endpoint")
        finally:
            if memory_queue:
                await memory_service.unsubscribe(memory_queue)


@router.websocket("/ws/market")
async def websocket_market(
    websocket: WebSocket,
    market_data_service: MarketDataService = Depends(get_market_data_service),
):
    """WebSocket endpoint for market data updates only."""
    market_queue = None

    async with manager.connection(websocket):
        try:
            market_queue = await market_data_service.subscribe()
            manager.add_queue(websocket, market_queue)

            initial_data = await market_data_service.get_current_market_data()
            if manager.is_active(websocket):
                market_data = {
                    "market_data": initial_data.get("market_data", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await websocket.send_json(market_data)

            def process_update(update):
                market_data = update.get("market_data", {})
                return {
                    "prices": market_data.get("prices", {}),
                    "liquidity": market_data.get("liquidity", {}),
                    "spreads": market_data.get("spreads", {}),
                    "analysis": market_data.get("analysis", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            update_task = asyncio.create_task(
                handle_updates(
                    websocket,
                    market_queue,
                    process_update,
                    lambda: manager.is_active(websocket),
                )
            )

            manager.add_task(websocket, update_task)
            await update_task

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from market endpoint")
        finally:
            if market_queue:
                await market_data_service.unsubscribe(market_queue)
