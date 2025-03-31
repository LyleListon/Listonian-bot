"""Connection management for WebSocket connections.

This module provides a robust connection management system with proper
state tracking, lifecycle management, and resource cleanup.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Set, List, Callable, Coroutine
from enum import Enum, auto
import time
from datetime import datetime
from weakref import WeakKeyDictionary, WeakSet
from aiohttp import web

from .task_manager import TaskManager, TaskState

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """Connection lifecycle states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ConnectionManager:
    """Manages WebSocket connections with proper lifecycle tracking.
    
    This class provides a centralized way to manage WebSocket connections
    with proper state tracking, resource cleanup, and connection pooling.
    
    Attributes:
        _connections: WeakKeyDictionary mapping WebSocket objects to their metadata
        _task_manager: TaskManager for handling async tasks
        _lock: Asyncio lock for thread safety
        _connection_limit: Maximum number of concurrent connections
        _connection_timeout: Timeout for connection operations
    """

    def __init__(self, task_manager: Optional[TaskManager] = None):
        """Initialize the connection manager.
        
        Args:
            task_manager: Optional TaskManager instance to use
        """
        self._connections = WeakKeyDictionary()
        self._task_manager = task_manager or TaskManager()
        self._lock = asyncio.Lock()
        self._connection_limit = 100  # Maximum concurrent connections
        self._connection_timeout = 10.0  # seconds
        self._active_count = 0
        self._total_connections = 0
        self._connection_stats = {
            "total_connected": 0,
            "total_disconnected": 0,
            "connection_errors": 0,
            "last_connection_time": None,
            "last_disconnection_time": None
        }
        logger.debug("ConnectionManager initialized")

    async def connect(self, websocket: web.WebSocketResponse) -> bool:
        """Establish and track a new WebSocket connection.
        
        Args:
            websocket: WebSocket response object
            
        Returns:
            True if connection was successful, False otherwise
        """
        async with self._lock:
            # Check if we're at the connection limit
            if self._active_count >= self._connection_limit:
                logger.warning(f"Connection limit reached ({self._connection_limit}), rejecting new connection")
                return False
                
            # Initialize connection metadata
            self._connections[websocket] = {
                "state": ConnectionState.CONNECTING,
                "connected_at": datetime.utcnow(),
                "last_activity": time.time(),
                "tasks": set(),
                "queues": set(),
                "client_info": {
                    "id": f"client_{self._total_connections}",
                    "ip": getattr(websocket, "_req", {}).get("remote", "unknown"),
                    "user_agent": getattr(websocket, "_req", {}).get("headers", {}).get("User-Agent", "unknown")
                }
            }
            
            # Update connection stats
            self._active_count += 1
            self._total_connections += 1
            self._connection_stats["total_connected"] += 1
            self._connection_stats["last_connection_time"] = datetime.utcnow()
            
            try:
                # Accept the WebSocket connection
                await asyncio.wait_for(websocket.prepare(getattr(websocket, "_req", None)), 
                                      timeout=self._connection_timeout)
                
                # Update connection state
                self._connections[websocket]["state"] = ConnectionState.CONNECTED
                logger.debug(f"WebSocket connection established: {self._connections[websocket]['client_info']['id']}")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"Connection timeout for {self._connections[websocket]['client_info']['id']}")
                self._handle_connection_error(websocket)
                return False
                
            except Exception as e:
                logger.error(f"Connection error: {str(e)}")
                self._handle_connection_error(websocket)
                return False

    async def disconnect(self, websocket: web.WebSocketResponse) -> bool:
        """Disconnect and cleanup a WebSocket connection.
        
        Args:
            websocket: WebSocket response object
            
        Returns:
            True if disconnection was successful, False otherwise
        """
        async with self._lock:
            if websocket not in self._connections:
                logger.warning("Attempted to disconnect non-existent connection")
                return False
                
            # Update connection state
            self._connections[websocket]["state"] = ConnectionState.DISCONNECTING
            
            try:
                # Cancel all tasks associated with this connection
                await self._cleanup_tasks(websocket)
                
                # Clean up queues
                await self._cleanup_queues(websocket)
                
                # Close the WebSocket connection
                if not websocket.closed:
                    await asyncio.wait_for(websocket.close(), timeout=self._connection_timeout)
                
                # Update connection state and stats
                self._connections[websocket]["state"] = ConnectionState.DISCONNECTED
                self._connections[websocket]["disconnected_at"] = datetime.utcnow()
                self._active_count -= 1
                self._connection_stats["total_disconnected"] += 1
                self._connection_stats["last_disconnection_time"] = datetime.utcnow()
                
                logger.debug(f"WebSocket connection closed: {self._connections[websocket]['client_info']['id']}")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"Disconnection timeout for {self._connections[websocket]['client_info']['id']}")
                self._handle_connection_error(websocket)
                return False
                
            except Exception as e:
                logger.error(f"Disconnection error: {str(e)}")
                self._handle_connection_error(websocket)
                return False

    async def disconnect_all(self) -> None:
        """Disconnect all active connections."""
        async with self._lock:
            connections = list(self._connections.keys())
            
        for websocket in connections:
            await self.disconnect(websocket)
            
        logger.debug(f"All connections disconnected ({len(connections)})")

    async def register_task(self, websocket: web.WebSocketResponse, task_name: str, 
                           coro: Coroutine, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a task associated with a connection.
        
        Args:
            websocket: WebSocket response object
            task_name: Unique name for the task
            coro: Coroutine to be executed as a task
            metadata: Optional metadata to store with the task
            
        Returns:
            True if task was registered successfully, False otherwise
        """
        async with self._lock:
            if websocket not in self._connections:
                logger.warning(f"Attempted to register task for non-existent connection: {task_name}")
                return False
                
            if self._connections[websocket]["state"] != ConnectionState.CONNECTED:
                logger.warning(f"Attempted to register task for non-connected websocket: {task_name}")
                return False
                
            # Add connection info to metadata
            task_metadata = metadata or {}
            task_metadata["connection_id"] = self._connections[websocket]["client_info"]["id"]
            
            # Create the task
            full_task_name = f"{self._connections[websocket]['client_info']['id']}_{task_name}"
            task = await self._task_manager.add_task(full_task_name, coro, task_metadata)
            
            # Register the task with this connection
            self._connections[websocket]["tasks"].add(full_task_name)
            self._connections[websocket]["last_activity"] = time.time()
            
            logger.debug(f"Task {full_task_name} registered for connection {self._connections[websocket]['client_info']['id']}")
            return True

    async def register_queue(self, websocket: web.WebSocketResponse, 
                            queue: asyncio.Queue, queue_name: str) -> bool:
        """Register a queue associated with a connection.
        
        Args:
            websocket: WebSocket response object
            queue: Asyncio queue to register
            queue_name: Name for the queue
            
        Returns:
            True if queue was registered successfully, False otherwise
        """
        async with self._lock:
            if websocket not in self._connections:
                logger.warning(f"Attempted to register queue for non-existent connection: {queue_name}")
                return False
                
            if self._connections[websocket]["state"] != ConnectionState.CONNECTED:
                logger.warning(f"Attempted to register queue for non-connected websocket: {queue_name}")
                return False
                
            # Register the queue with this connection
            self._connections[websocket]["queues"].add((queue, queue_name))
            self._connections[websocket]["last_activity"] = time.time()
            
            logger.debug(f"Queue {queue_name} registered for connection {self._connections[websocket]['client_info']['id']}")
            return True

    async def update_activity(self, websocket: web.WebSocketResponse) -> bool:
        """Update the last activity timestamp for a connection.
        
        Args:
            websocket: WebSocket response object
            
        Returns:
            True if update was successful, False otherwise
        """
        async with self._lock:
            if websocket not in self._connections:
                return False
                
            self._connections[websocket]["last_activity"] = time.time()
            return True

    async def get_connection_info(self, websocket: web.WebSocketResponse) -> Optional[Dict[str, Any]]:
        """Get information about a specific connection.
        
        Args:
            websocket: WebSocket response object
            
        Returns:
            Dictionary with connection information or None if connection not found
        """
        async with self._lock:
            if websocket not in self._connections:
                return None
                
            info = dict(self._connections[websocket])
            
            # Add task information
            tasks_info = []
            for task_name in info["tasks"]:
                task_info = await self._task_manager.get_task_info(task_name)
                if task_info:
                    tasks_info.append(task_info)
                    
            info["tasks_info"] = tasks_info
            
            # Add queue information
            queues_info = []
            for queue, queue_name in info["queues"]:
                queues_info.append({
                    "name": queue_name,
                    "size": queue.qsize(),
                    "full": queue.full()
                })
                
            info["queues_info"] = queues_info
            
            return info

    async def get_all_connections_info(self) -> List[Dict[str, Any]]:
        """Get information about all connections.
        
        Returns:
            List of dictionaries with connection information
        """
        async with self._lock:
            result = []
            for websocket, info in self._connections.items():
                connection_info = dict(info)
                
                # Add basic WebSocket info
                connection_info["closed"] = websocket.closed
                
                # Don't include the actual task and queue objects
                connection_info["task_count"] = len(connection_info["tasks"])
                connection_info["queue_count"] = len(connection_info["queues"])
                connection_info.pop("tasks", None)
                connection_info.pop("queues", None)
                
                result.append(connection_info)
                
            return result

    async def get_connection_metrics(self) -> Dict[str, Any]:
        """Get metrics about managed connections.
        
        Returns:
            Dictionary with connection metrics
        """
        async with self._lock:
            # Count connections by state
            state_counts = {state: 0 for state in ConnectionState}
            for info in self._connections.values():
                state = info["state"]
                state_counts[state] += 1
                
            # Calculate connection age statistics
            now = time.time()
            connection_ages = []
            for info in self._connections.values():
                if info["state"] == ConnectionState.CONNECTED:
                    connected_at = info["connected_at"].timestamp()
                    age = now - connected_at
                    connection_ages.append(age)
                    
            avg_age = sum(connection_ages) / len(connection_ages) if connection_ages else 0
            max_age = max(connection_ages) if connection_ages else 0
            
            # Calculate activity statistics
            activity_times = []
            for info in self._connections.values():
                activity_times.append(now - info["last_activity"])
                
            avg_idle = sum(activity_times) / len(activity_times) if activity_times else 0
            max_idle = max(activity_times) if activity_times else 0
            
            return {
                "active_connections": self._active_count,
                "total_connections_ever": self._total_connections,
                "by_state": {str(state): count for state, count in state_counts.items()},
                "connection_stats": self._connection_stats,
                "age_stats": {
                    "average_age_seconds": avg_age,
                    "max_age_seconds": max_age
                },
                "activity_stats": {
                    "average_idle_seconds": avg_idle,
                    "max_idle_seconds": max_idle
                }
            }

    async def _cleanup_tasks(self, websocket: web.WebSocketResponse) -> None:
        """Clean up tasks associated with a connection.
        
        Args:
            websocket: WebSocket response object
        """
        if websocket not in self._connections:
            return
            
        tasks = list(self._connections[websocket]["tasks"])
        for task_name in tasks:
            try:
                await self._task_manager.cancel_task(task_name)
                self._connections[websocket]["tasks"].remove(task_name)
            except Exception as e:
                logger.error(f"Error cancelling task {task_name}: {str(e)}")

    async def _cleanup_queues(self, websocket: web.WebSocketResponse) -> None:
        """Clean up queues associated with a connection.
        
        Args:
            websocket: WebSocket response object
        """
        if websocket not in self._connections:
            return
            
        queues = list(self._connections[websocket]["queues"])
        for queue, queue_name in queues:
            try:
                # Clear the queue
                while not queue.empty():
                    try:
                        queue.get_nowait()
                        queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                        
                self._connections[websocket]["queues"].remove((queue, queue_name))
            except Exception as e:
                logger.error(f"Error cleaning up queue {queue_name}: {str(e)}")

    def _handle_connection_error(self, websocket: web.WebSocketResponse) -> None:
        """Handle connection errors.
        
        Args:
            websocket: WebSocket response object
        """
        if websocket in self._connections:
            self._connections[websocket]["state"] = ConnectionState.ERROR
            self._connections[websocket]["error_at"] = datetime.utcnow()
            self._active_count -= 1
            self._connection_stats["connection_errors"] += 1