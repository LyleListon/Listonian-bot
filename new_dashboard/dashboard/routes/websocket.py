"""WebSocket routes for real-time metrics data."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List, Any, Set, AsyncIterator
import asyncio
import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from weakref import WeakKeyDictionary

from ..core.logging import get_logger
from ..core.dependencies import (
    get_metrics_service,
    get_memory_service,
    get_market_data_service
)
from ..services.metrics_service import MetricsService
from ..services.memory_service import MemoryService
from ..services.market_data_service import MarketDataService

router = APIRouter()
logger = get_logger("websocket_routes")

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self._connections = WeakKeyDictionary()
        self._lock = asyncio.Lock()
        
    @asynccontextmanager
    async def connection(self, websocket: WebSocket) -> AsyncIterator[None]:
        """Context manager for WebSocket connections."""
        try:
            await websocket.accept()
            async with self._lock:
                self._connections[websocket] = {
                    "active": True,
                    "tasks": set(),
                    "queues": set()
                }
            logger.info(f"New WebSocket connection. Total connections: {len(self._connections)}")
            yield
        finally:
            await self._cleanup_connection(websocket)
            
    async def _cleanup_connection(self, websocket: WebSocket):
        """Clean up a WebSocket connection."""
        try:
            async with self._lock:
                if websocket in self._connections:
                    # Mark connection as inactive first
                    self._connections[websocket]["active"] = False
                    
                    # Cancel all tasks
                    tasks = list(self._connections[websocket]["tasks"])
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    
                    # Wait for tasks to complete
                    if tasks:
                        try:
                            await asyncio.wait(tasks, timeout=1.0)
                        except asyncio.TimeoutError:
                            logger.warning("Timeout waiting for tasks to cancel")
                    
                    # Clear queues and tasks
                    self._connections[websocket]["queues"].clear()
                    self._connections[websocket]["tasks"].clear()
                    
                    # Remove connection
                    del self._connections[websocket]
                    
            logger.info(f"WebSocket disconnected. Remaining connections: {len(self._connections)}")
            
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
            
    def add_task(self, websocket: WebSocket, task: asyncio.Task):
        """Add a task to the connection."""
        if websocket in self._connections and self._connections[websocket]["active"]:
            self._connections[websocket]["tasks"].add(task)
            
    def add_queue(self, websocket: WebSocket, queue: asyncio.Queue):
        """Add a queue to the connection."""
        if websocket in self._connections and self._connections[websocket]["active"]:
            self._connections[websocket]["queues"].add(queue)
            
    def is_active(self, websocket: WebSocket) -> bool:
        """Check if a connection is active."""
        return (
            websocket in self._connections and 
            self._connections[websocket]["active"]
        )

manager = ConnectionManager()

async def handle_updates(
    websocket: WebSocket,
    queue: asyncio.Queue,
    process_update,
    connection_active
):
    """Handle updates from a queue and send to websocket."""
    try:
        while connection_active():
            try:
                # Use wait_for to prevent hanging
                update = await asyncio.wait_for(queue.get(), timeout=1.0)
                if connection_active():
                    processed_update = process_update(update)
                    await websocket.send_json(processed_update)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Update handler cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing update: {e}")
                if not connection_active():
                    break
    except Exception as e:
        logger.error(f"Error in update handler: {e}")

@router.websocket("/ws/metrics")
async def websocket_metrics(
    websocket: WebSocket,
    metrics_service: MetricsService = Depends(get_metrics_service),
    memory_service: MemoryService = Depends(get_memory_service),
    market_data_service: MarketDataService = Depends(get_market_data_service)
):
    """WebSocket endpoint for real-time metrics updates."""
    metrics_queue = None
    memory_queue = None
    market_queue = None
    
    async with manager.connection(websocket):
        try:
            logger.info("WebSocket client connected to metrics endpoint")
            
            # Subscribe to updates
            metrics_queue = await metrics_service.subscribe()
            memory_queue = await memory_service.subscribe()
            market_queue = await market_data_service.subscribe()
            
            # Track queues
            manager.add_queue(websocket, metrics_queue)
            manager.add_queue(websocket, memory_queue)
            manager.add_queue(websocket, market_queue)
            
            # Send initial state
            initial_metrics = await metrics_service.get_current_metrics()
            if manager.is_active(websocket):
                await websocket.send_json({
                    "type": "initial_state",
                    "data": initial_metrics,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Create update handlers
            metrics_handler = handle_updates(
                websocket,
                metrics_queue,
                lambda x: {**x, "_timestamp": datetime.utcnow().isoformat()},
                lambda: manager.is_active(websocket)
            )
            
            memory_handler = handle_updates(
                websocket,
                memory_queue,
                lambda x: {**x, "_timestamp": datetime.utcnow().isoformat()},
                lambda: manager.is_active(websocket)
            )

            market_handler = handle_updates(
                websocket,
                market_queue,
                lambda x: {**x, "_timestamp": datetime.utcnow().isoformat()},
                lambda: manager.is_active(websocket)
            )
            
            # Start handlers
            metrics_task = asyncio.create_task(metrics_handler)
            memory_task = asyncio.create_task(memory_handler)
            market_task = asyncio.create_task(market_handler)
            
            # Track tasks
            manager.add_task(websocket, metrics_task)
            manager.add_task(websocket, memory_task)
            manager.add_task(websocket, market_task)
            
            # Wait for completion
            try:
                await asyncio.gather(metrics_task, memory_task, market_task)
            except asyncio.CancelledError:
                logger.info("WebSocket tasks cancelled")
            except Exception as e:
                logger.error(f"Error in WebSocket tasks: {e}")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from metrics endpoint")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)
            if memory_queue:
                await memory_service.unsubscribe(memory_queue)
            if market_queue:
                await market_data_service.unsubscribe(market_queue)

@router.websocket("/ws/system")
async def websocket_system(
    websocket: WebSocket,
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """WebSocket endpoint for system metrics only."""
    metrics_queue = None
    
    async with manager.connection(websocket):
        try:
            logger.info("WebSocket client connected to system endpoint")
            
            metrics_queue = await metrics_service.subscribe()
            manager.add_queue(websocket, metrics_queue)
            
            # Send initial state
            initial_metrics = await metrics_service.get_current_metrics()
            if manager.is_active(websocket):
                system_metrics = {
                    'system': initial_metrics.get('system', {}),
                    'timestamp': datetime.utcnow().isoformat()
                }
                await websocket.send_json(system_metrics)
            
            # Create update handler
            def process_update(update):
                return {
                    'system': update.get('system', {}),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            update_task = asyncio.create_task(handle_updates(
                websocket,
                metrics_queue,
                process_update,
                lambda: manager.is_active(websocket)
            ))
            
            # Track task
            manager.add_task(websocket, update_task)
            
            # Wait for completion
            try:
                await update_task
            except asyncio.CancelledError:
                logger.info("System WebSocket task cancelled")
            except Exception as e:
                logger.error(f"Error in system WebSocket task: {e}")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from system endpoint")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if metrics_queue:
                await metrics_service.unsubscribe(metrics_queue)

@router.websocket("/ws/trades")
async def websocket_trades(
    websocket: WebSocket,
    memory_service: MemoryService = Depends(get_memory_service)
):
    """WebSocket endpoint for trade history updates only."""
    memory_queue = None
    
    async with manager.connection(websocket):
        try:
            logger.info("WebSocket client connected to trades endpoint")
            
            memory_queue = await memory_service.subscribe()
            manager.add_queue(websocket, memory_queue)
            
            # Send initial state
            initial_state = await memory_service.get_current_state()
            if manager.is_active(websocket):
                trade_data = {
                    'trade_history': initial_state.get('trade_history', []),
                    'timestamp': datetime.utcnow().isoformat()
                }
                await websocket.send_json(trade_data)
            
            # Create update handler
            def process_update(update):
                return {
                    'trade_history': update.get('trade_history', []),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            update_task = asyncio.create_task(handle_updates(
                websocket,
                memory_queue,
                process_update,
                lambda: manager.is_active(websocket)
            ))
            
            # Track task
            manager.add_task(websocket, update_task)
            
            # Wait for completion
            try:
                await update_task
            except asyncio.CancelledError:
                logger.info("Trades WebSocket task cancelled")
            except Exception as e:
                logger.error(f"Error in trades WebSocket task: {e}")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from trades endpoint")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if memory_queue:
                await memory_service.unsubscribe(memory_queue)

@router.websocket("/ws/market")
async def websocket_market(
    websocket: WebSocket,
    market_data_service: MarketDataService = Depends(get_market_data_service)
):
    """WebSocket endpoint for market data updates only."""
    market_queue = None
    
    async with manager.connection(websocket):
        try:
            logger.info("WebSocket client connected to market endpoint")
            
            market_queue = await market_data_service.subscribe()
            manager.add_queue(websocket, market_queue)
            
            # Send initial state
            initial_data = await market_data_service.get_current_market_data()
            if manager.is_active(websocket):
                market_data = {
                    'market_data': initial_data.get('market_data', {}),
                    'timestamp': datetime.utcnow().isoformat()
                }
                await websocket.send_json(market_data)
            
            # Create update handler
            def process_update(update):
                market_data = update.get('market_data', {})
                return {
                    'prices': market_data.get('prices', {}),
                    'liquidity': market_data.get('liquidity', {}),
                    'spreads': market_data.get('spreads', {}),
                    'analysis': market_data.get('analysis', {}),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            update_task = asyncio.create_task(handle_updates(
                websocket,
                market_queue,
                process_update,
                lambda: manager.is_active(websocket)
            ))
            
            # Track task
            manager.add_task(websocket, update_task)
            
            # Wait for completion
            try:
                await update_task
            except asyncio.CancelledError:
                logger.info("Market WebSocket task cancelled")
            except Exception as e:
                logger.error(f"Error in market WebSocket task: {e}")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from market endpoint")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if market_queue:
                await market_data_service.unsubscribe(market_queue)