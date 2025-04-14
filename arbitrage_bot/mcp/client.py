"""MCP client for distributed processing."""

import json
import logging
import socket
import threading
import time
import uuid
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for MCP server."""
    
    def __init__(
        self,
        server_host: str,
        server_port: int,
        worker_id: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ):
        """Initialize the MCP client.
        
        Args:
            server_host: MCP server host.
            server_port: MCP server port.
            worker_id: Worker ID. If None, a random ID will be generated.
            capabilities: List of task types the worker can handle.
        """
        self.server_host = server_host
        self.server_port = server_port
        self.worker_id = worker_id or f"worker-{uuid.uuid4()}"
        self.capabilities = capabilities or []
        
        # Initialize state
        self.running = False
        self.registered = False
        self.current_task = None
        self.heartbeat_thread = None
        self.task_thread = None
        
        # Initialize task handlers
        self.task_handlers: Dict[str, Callable] = {}
        
        logger.info(f"MCP client initialized with worker ID {self.worker_id}")
    
    def register_task_handler(self, task_type: str, handler: Callable) -> None:
        """Register a task handler.
        
        Args:
            task_type: Task type.
            handler: Task handler function.
        """
        self.capabilities.append(task_type)
        self.task_handlers[task_type] = handler
        
        logger.info(f"Registered handler for task type {task_type}")
    
    def start(self) -> None:
        """Start the MCP client."""
        if self.running:
            logger.warning("MCP client already running")
            return
        
        self.running = True
        logger.info("Starting MCP client")
        
        # Register with server
        self._register()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        # Start task thread
        self.task_thread = threading.Thread(target=self._task_loop)
        self.task_thread.daemon = True
        self.task_thread.start()
        
        logger.info("MCP client started")
    
    def stop(self) -> None:
        """Stop the MCP client."""
        if not self.running:
            logger.warning("MCP client not running")
            return
        
        self.running = False
        logger.info("Stopping MCP client")
        
        # Unregister from server
        self._unregister()
        
        # Wait for threads to stop
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5.0)
            self.heartbeat_thread = None
        
        if self.task_thread:
            self.task_thread.join(timeout=5.0)
            self.task_thread = None
        
        logger.info("MCP client stopped")
    
    def add_task(
        self, task_type: str, data: Dict[str, Any], priority: int = 0
    ) -> Optional[str]:
        """Add a task to the server.
        
        Args:
            task_type: Task type.
            data: Task data.
            priority: Task priority (higher values have higher priority).
            
        Returns:
            Task ID, or None if the task could not be added.
        """
        # Send request to server
        response = self._send_request({
            "type": "add_task",
            "task_type": task_type,
            "data": data,
            "priority": priority,
        })
        
        if response and response.get("success"):
            return response.get("data", {}).get("task_id")
        
        return None
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID.
        
        Args:
            task_id: Task ID.
            
        Returns:
            Task dictionary, or None if not found.
        """
        # Send request to server
        response = self._send_request({
            "type": "get_task",
            "task_id": task_id,
        })
        
        if response and response.get("success"):
            return response.get("data")
        
        return None
    
    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks.
        
        Args:
            status: Filter by status.
            
        Returns:
            List of task dictionaries.
        """
        # Send request to server
        response = self._send_request({
            "type": "get_tasks",
            "status": status,
        })
        
        if response and response.get("success"):
            return response.get("data", {}).get("tasks", [])
        
        return []
    
    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get a worker by ID.
        
        Args:
            worker_id: Worker ID.
            
        Returns:
            Worker dictionary, or None if not found.
        """
        # Send request to server
        response = self._send_request({
            "type": "get_worker",
            "worker_id": worker_id,
        })
        
        if response and response.get("success"):
            return response.get("data")
        
        return None
    
    def get_workers(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all workers.
        
        Args:
            status: Filter by status.
            
        Returns:
            List of worker dictionaries.
        """
        # Send request to server
        response = self._send_request({
            "type": "get_workers",
            "status": status,
        })
        
        if response and response.get("success"):
            return response.get("data", {}).get("workers", [])
        
        return []
    
    def _register(self) -> bool:
        """Register with the server.
        
        Returns:
            True if registration was successful, False otherwise.
        """
        # Send request to server
        response = self._send_request({
            "type": "register",
            "worker_id": self.worker_id,
            "capabilities": self.capabilities,
        })
        
        if response and response.get("success"):
            self.registered = True
            logger.info(f"Registered with MCP server as {self.worker_id}")
            return True
        
        logger.error("Failed to register with MCP server")
        return False
    
    def _unregister(self) -> bool:
        """Unregister from the server.
        
        Returns:
            True if unregistration was successful, False otherwise.
        """
        if not self.registered:
            return True
        
        # Send request to server
        response = self._send_request({
            "type": "unregister",
            "worker_id": self.worker_id,
        })
        
        if response and response.get("success"):
            self.registered = False
            logger.info(f"Unregistered from MCP server")
            return True
        
        logger.error("Failed to unregister from MCP server")
        return False
    
    def _heartbeat(self) -> bool:
        """Send heartbeat to the server.
        
        Returns:
            True if heartbeat was successful, False otherwise.
        """
        if not self.registered:
            return False
        
        # Send request to server
        response = self._send_request({
            "type": "heartbeat",
            "worker_id": self.worker_id,
        })
        
        return response and response.get("success", False)
    
    def _request_task(self) -> Optional[Dict[str, Any]]:
        """Request a task from the server.
        
        Returns:
            Task dictionary, or None if no task is available.
        """
        if not self.registered:
            return None
        
        # Send request to server
        response = self._send_request({
            "type": "request_task",
            "worker_id": self.worker_id,
        })
        
        if response and response.get("success"):
            return response.get("data")
        
        return None
    
    def _start_task(self, task_id: str) -> bool:
        """Start a task.
        
        Args:
            task_id: Task ID.
            
        Returns:
            True if task was started, False otherwise.
        """
        if not self.registered:
            return False
        
        # Send request to server
        response = self._send_request({
            "type": "start_task",
            "worker_id": self.worker_id,
            "task_id": task_id,
        })
        
        return response and response.get("success", False)
    
    def _complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        """Complete a task.
        
        Args:
            task_id: Task ID.
            result: Task result.
            
        Returns:
            True if task was completed, False otherwise.
        """
        if not self.registered:
            return False
        
        # Send request to server
        response = self._send_request({
            "type": "complete_task",
            "worker_id": self.worker_id,
            "task_id": task_id,
            "result": result,
        })
        
        return response and response.get("success", False)
    
    def _fail_task(self, task_id: str, error: str) -> bool:
        """Fail a task.
        
        Args:
            task_id: Task ID.
            error: Error message.
            
        Returns:
            True if task was failed, False otherwise.
        """
        if not self.registered:
            return False
        
        # Send request to server
        response = self._send_request({
            "type": "fail_task",
            "worker_id": self.worker_id,
            "task_id": task_id,
            "error": error,
        })
        
        return response and response.get("success", False)
    
    def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to the server.
        
        Args:
            request: Request dictionary.
            
        Returns:
            Response dictionary, or None if the request failed.
        """
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            
            # Connect to server
            sock.connect((self.server_host, self.server_port))
            
            # Send request
            sock.sendall(json.dumps(request).encode("utf-8"))
            
            # Receive response
            data = sock.recv(4096).decode("utf-8")
            
            # Close socket
            sock.close()
            
            # Parse response
            return json.loads(data)
        
        except Exception as e:
            logger.error(f"Error sending request to MCP server: {e}")
            return None
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat loop."""
        while self.running:
            try:
                # Send heartbeat
                if not self._heartbeat():
                    # Try to register again
                    self._register()
                
                # Sleep for a bit
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    def _task_loop(self) -> None:
        """Task loop."""
        while self.running:
            try:
                # Check if we're already processing a task
                if self.current_task:
                    # Sleep for a bit
                    time.sleep(1)
                    continue
                
                # Request a task
                task = self._request_task()
                
                if not task:
                    # No task available, sleep for a bit
                    time.sleep(1)
                    continue
                
                # Get task info
                task_id = task.get("task_id")
                task_type = task.get("task_type")
                task_data = task.get("data", {})
                
                # Check if we have a handler for this task type
                if task_type not in self.task_handlers:
                    logger.warning(f"No handler for task type {task_type}")
                    self._fail_task(task_id, f"No handler for task type {task_type}")
                    continue
                
                # Set current task
                self.current_task = task
                
                # Start task
                if not self._start_task(task_id):
                    logger.warning(f"Failed to start task {task_id}")
                    self.current_task = None
                    continue
                
                # Get handler
                handler = self.task_handlers[task_type]
                
                # Execute handler
                try:
                    logger.info(f"Executing task {task_id} of type {task_type}")
                    result = handler(task_data)
                    
                    # Complete task
                    if not self._complete_task(task_id, result):
                        logger.warning(f"Failed to complete task {task_id}")
                    
                    logger.info(f"Completed task {task_id}")
                
                except Exception as e:
                    logger.error(f"Error executing task {task_id}: {e}")
                    
                    # Fail task
                    if not self._fail_task(task_id, str(e)):
                        logger.warning(f"Failed to fail task {task_id}")
                
                finally:
                    # Clear current task
                    self.current_task = None
            
            except Exception as e:
                logger.error(f"Error in task loop: {e}")
                
                # Clear current task
                self.current_task = None
