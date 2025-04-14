"""MCP (Multi-Component Processing) server for distributed processing."""

import json
import logging
import threading
import time
import uuid
from typing import Dict, List, Any, Optional, Set
from queue import Queue, Empty
import socket
from socketserver import ThreadingTCPServer, BaseRequestHandler

logger = logging.getLogger(__name__)


class Task:
    """Task for distributed processing."""
    
    def __init__(
        self,
        task_id: str,
        task_type: str,
        data: Dict[str, Any],
        priority: int = 0,
    ):
        """Initialize a task.
        
        Args:
            task_id: Task ID.
            task_type: Task type.
            data: Task data.
            priority: Task priority (higher values have higher priority).
        """
        self.task_id = task_id
        self.task_type = task_type
        self.data = data
        self.priority = priority
        self.created_at = time.time()
        self.assigned_to = None
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.status = "pending"  # pending, assigned, running, completed, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary.
        
        Returns:
            Dictionary representation of the task.
        """
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "data": self.data,
            "priority": self.priority,
            "created_at": self.created_at,
            "assigned_to": self.assigned_to,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary.
        
        Args:
            data: Dictionary representation of the task.
            
        Returns:
            Task instance.
        """
        task = cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            data=data["data"],
            priority=data["priority"],
        )
        
        task.created_at = data.get("created_at", time.time())
        task.assigned_to = data.get("assigned_to")
        task.started_at = data.get("started_at")
        task.completed_at = data.get("completed_at")
        task.result = data.get("result")
        task.error = data.get("error")
        task.status = data.get("status", "pending")
        
        return task


class Worker:
    """Worker for distributed processing."""
    
    def __init__(
        self,
        worker_id: str,
        capabilities: List[str],
        address: str,
    ):
        """Initialize a worker.
        
        Args:
            worker_id: Worker ID.
            capabilities: List of task types the worker can handle.
            address: Worker address (host:port).
        """
        self.worker_id = worker_id
        self.capabilities = set(capabilities)
        self.address = address
        self.registered_at = time.time()
        self.last_heartbeat = time.time()
        self.status = "idle"  # idle, busy
        self.current_task_id = None
        self.completed_tasks = 0
        self.failed_tasks = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert worker to dictionary.
        
        Returns:
            Dictionary representation of the worker.
        """
        return {
            "worker_id": self.worker_id,
            "capabilities": list(self.capabilities),
            "address": self.address,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "status": self.status,
            "current_task_id": self.current_task_id,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Worker":
        """Create worker from dictionary.
        
        Args:
            data: Dictionary representation of the worker.
            
        Returns:
            Worker instance.
        """
        worker = cls(
            worker_id=data["worker_id"],
            capabilities=data["capabilities"],
            address=data["address"],
        )
        
        worker.registered_at = data.get("registered_at", time.time())
        worker.last_heartbeat = data.get("last_heartbeat", time.time())
        worker.status = data.get("status", "idle")
        worker.current_task_id = data.get("current_task_id")
        worker.completed_tasks = data.get("completed_tasks", 0)
        worker.failed_tasks = data.get("failed_tasks", 0)
        
        return worker


class MCPServer:
    """MCP server for distributed processing."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the MCP server.
        
        Args:
            config: Configuration dictionary.
        """
        self.config = config
        
        # Get MCP configuration
        mcp_config = config.get("mcp", {})
        self.host = mcp_config.get("host", "127.0.0.1")
        self.port = mcp_config.get("port", 9000)
        self.heartbeat_timeout = mcp_config.get("heartbeat_timeout", 30)
        self.task_timeout = mcp_config.get("task_timeout", 300)
        
        # Initialize state
        self.tasks: Dict[str, Task] = {}
        self.workers: Dict[str, Worker] = {}
        self.task_queue: Queue = Queue()
        self.running = False
        self.server = None
        self.server_thread = None
        self.scheduler_thread = None
        self.cleanup_thread = None
        
        # Initialize locks
        self.tasks_lock = threading.Lock()
        self.workers_lock = threading.Lock()
        
        logger.info("MCP server initialized")
    
    def start(self) -> None:
        """Start the MCP server."""
        if self.running:
            logger.warning("MCP server already running")
            return
        
        self.running = True
        logger.info("Starting MCP server")
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
        
        # Start TCP server
        self.server = ThreadingTCPServer((self.host, self.port), MCPRequestHandler)
        self.server.mcp_server = self
        
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info(f"MCP server started on {self.host}:{self.port}")
    
    def stop(self) -> None:
        """Stop the MCP server."""
        if not self.running:
            logger.warning("MCP server not running")
            return
        
        self.running = False
        logger.info("Stopping MCP server")
        
        # Stop TCP server
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        
        # Wait for threads to stop
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
            self.server_thread = None
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5.0)
            self.scheduler_thread = None
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)
            self.cleanup_thread = None
        
        logger.info("MCP server stopped")
    
    def add_task(self, task_type: str, data: Dict[str, Any], priority: int = 0) -> str:
        """Add a task to the queue.
        
        Args:
            task_type: Task type.
            data: Task data.
            priority: Task priority (higher values have higher priority).
            
        Returns:
            Task ID.
        """
        # Create task
        task_id = str(uuid.uuid4())
        task = Task(task_id, task_type, data, priority)
        
        # Add to tasks dictionary
        with self.tasks_lock:
            self.tasks[task_id] = task
        
        # Add to queue
        self.task_queue.put((priority, task_id))
        
        logger.info(f"Added task {task_id} of type {task_type}")
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID.
        
        Args:
            task_id: Task ID.
            
        Returns:
            Task dictionary, or None if not found.
        """
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            
            if task:
                return task.to_dict()
            
            return None
    
    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks.
        
        Args:
            status: Filter by status.
            
        Returns:
            List of task dictionaries.
        """
        with self.tasks_lock:
            if status:
                tasks = [task for task in self.tasks.values() if task.status == status]
            else:
                tasks = list(self.tasks.values())
            
            return [task.to_dict() for task in tasks]
    
    def register_worker(
        self, worker_id: str, capabilities: List[str], address: str
    ) -> Dict[str, Any]:
        """Register a worker.
        
        Args:
            worker_id: Worker ID.
            capabilities: List of task types the worker can handle.
            address: Worker address (host:port).
            
        Returns:
            Worker dictionary.
        """
        with self.workers_lock:
            # Check if worker already exists
            if worker_id in self.workers:
                # Update existing worker
                worker = self.workers[worker_id]
                worker.capabilities = set(capabilities)
                worker.address = address
                worker.last_heartbeat = time.time()
            else:
                # Create new worker
                worker = Worker(worker_id, capabilities, address)
                self.workers[worker_id] = worker
            
            logger.info(f"Registered worker {worker_id} with capabilities {capabilities}")
            
            return worker.to_dict()
    
    def unregister_worker(self, worker_id: str) -> bool:
        """Unregister a worker.
        
        Args:
            worker_id: Worker ID.
            
        Returns:
            True if worker was unregistered, False otherwise.
        """
        with self.workers_lock:
            if worker_id in self.workers:
                # Remove worker
                del self.workers[worker_id]
                
                logger.info(f"Unregistered worker {worker_id}")
                
                return True
            
            return False
    
    def heartbeat(self, worker_id: str) -> bool:
        """Update worker heartbeat.
        
        Args:
            worker_id: Worker ID.
            
        Returns:
            True if heartbeat was updated, False otherwise.
        """
        with self.workers_lock:
            if worker_id in self.workers:
                # Update heartbeat
                self.workers[worker_id].last_heartbeat = time.time()
                
                return True
            
            return False
    
    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get a worker by ID.
        
        Args:
            worker_id: Worker ID.
            
        Returns:
            Worker dictionary, or None if not found.
        """
        with self.workers_lock:
            worker = self.workers.get(worker_id)
            
            if worker:
                return worker.to_dict()
            
            return None
    
    def get_workers(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all workers.
        
        Args:
            status: Filter by status.
            
        Returns:
            List of worker dictionaries.
        """
        with self.workers_lock:
            if status:
                workers = [worker for worker in self.workers.values() if worker.status == status]
            else:
                workers = list(self.workers.values())
            
            return [worker.to_dict() for worker in workers]
    
    def request_task(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Request a task for a worker.
        
        Args:
            worker_id: Worker ID.
            
        Returns:
            Task dictionary, or None if no task is available.
        """
        with self.workers_lock:
            # Check if worker exists
            if worker_id not in self.workers:
                logger.warning(f"Worker {worker_id} not found")
                return None
            
            # Get worker
            worker = self.workers[worker_id]
            
            # Check if worker is already busy
            if worker.status == "busy":
                logger.warning(f"Worker {worker_id} is already busy")
                return None
            
            # Get worker capabilities
            capabilities = worker.capabilities
        
        # Find a task that matches worker capabilities
        task_id = None
        
        # Try to get a task from the queue
        try:
            # Get all tasks from the queue
            tasks = []
            while not self.task_queue.empty():
                try:
                    priority, tid = self.task_queue.get_nowait()
                    tasks.append((priority, tid))
                except Empty:
                    break
            
            # Sort tasks by priority (highest first)
            tasks.sort(reverse=True)
            
            # Find a task that matches worker capabilities
            for priority, tid in tasks:
                with self.tasks_lock:
                    task = self.tasks.get(tid)
                    
                    if not task:
                        continue
                    
                    if task.status != "pending":
                        continue
                    
                    if task.task_type in capabilities:
                        task_id = tid
                        break
            
            # Put back tasks that weren't assigned
            for priority, tid in tasks:
                if tid != task_id:
                    self.task_queue.put((priority, tid))
        
        except Empty:
            pass
        
        if not task_id:
            return None
        
        # Assign task to worker
        with self.tasks_lock, self.workers_lock:
            task = self.tasks.get(task_id)
            
            if not task:
                return None
            
            # Update task
            task.assigned_to = worker_id
            task.status = "assigned"
            
            # Update worker
            worker = self.workers.get(worker_id)
            
            if worker:
                worker.status = "busy"
                worker.current_task_id = task_id
            
            logger.info(f"Assigned task {task_id} to worker {worker_id}")
            
            return task.to_dict()
    
    def start_task(self, worker_id: str, task_id: str) -> bool:
        """Start a task.
        
        Args:
            worker_id: Worker ID.
            task_id: Task ID.
            
        Returns:
            True if task was started, False otherwise.
        """
        with self.tasks_lock:
            # Check if task exists
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Get task
            task = self.tasks[task_id]
            
            # Check if task is assigned to worker
            if task.assigned_to != worker_id:
                logger.warning(f"Task {task_id} is not assigned to worker {worker_id}")
                return False
            
            # Check if task is in the correct state
            if task.status != "assigned":
                logger.warning(f"Task {task_id} is not in assigned state")
                return False
            
            # Update task
            task.status = "running"
            task.started_at = time.time()
            
            logger.info(f"Started task {task_id} on worker {worker_id}")
            
            return True
    
    def complete_task(
        self, worker_id: str, task_id: str, result: Dict[str, Any]
    ) -> bool:
        """Complete a task.
        
        Args:
            worker_id: Worker ID.
            task_id: Task ID.
            result: Task result.
            
        Returns:
            True if task was completed, False otherwise.
        """
        with self.tasks_lock, self.workers_lock:
            # Check if task exists
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Get task
            task = self.tasks[task_id]
            
            # Check if task is assigned to worker
            if task.assigned_to != worker_id:
                logger.warning(f"Task {task_id} is not assigned to worker {worker_id}")
                return False
            
            # Check if task is in the correct state
            if task.status != "running":
                logger.warning(f"Task {task_id} is not in running state")
                return False
            
            # Update task
            task.status = "completed"
            task.completed_at = time.time()
            task.result = result
            
            # Update worker
            worker = self.workers.get(worker_id)
            
            if worker:
                worker.status = "idle"
                worker.current_task_id = None
                worker.completed_tasks += 1
            
            logger.info(f"Completed task {task_id} on worker {worker_id}")
            
            return True
    
    def fail_task(self, worker_id: str, task_id: str, error: str) -> bool:
        """Fail a task.
        
        Args:
            worker_id: Worker ID.
            task_id: Task ID.
            error: Error message.
            
        Returns:
            True if task was failed, False otherwise.
        """
        with self.tasks_lock, self.workers_lock:
            # Check if task exists
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Get task
            task = self.tasks[task_id]
            
            # Check if task is assigned to worker
            if task.assigned_to != worker_id:
                logger.warning(f"Task {task_id} is not assigned to worker {worker_id}")
                return False
            
            # Check if task is in the correct state
            if task.status not in ["assigned", "running"]:
                logger.warning(f"Task {task_id} is not in assigned or running state")
                return False
            
            # Update task
            task.status = "failed"
            task.completed_at = time.time()
            task.error = error
            
            # Update worker
            worker = self.workers.get(worker_id)
            
            if worker:
                worker.status = "idle"
                worker.current_task_id = None
                worker.failed_tasks += 1
            
            logger.info(f"Failed task {task_id} on worker {worker_id}: {error}")
            
            return True
    
    def _scheduler_loop(self) -> None:
        """Scheduler loop."""
        while self.running:
            try:
                # Check for timed out tasks
                self._check_task_timeouts()
                
                # Sleep for a bit
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
    
    def _cleanup_loop(self) -> None:
        """Cleanup loop."""
        while self.running:
            try:
                # Check for inactive workers
                self._check_worker_timeouts()
                
                # Sleep for a bit
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _check_task_timeouts(self) -> None:
        """Check for timed out tasks."""
        now = time.time()
        
        with self.tasks_lock, self.workers_lock:
            for task_id, task in list(self.tasks.items()):
                # Check if task is running
                if task.status == "running":
                    # Check if task has timed out
                    if task.started_at and now - task.started_at > self.task_timeout:
                        # Get worker
                        worker_id = task.assigned_to
                        worker = self.workers.get(worker_id)
                        
                        # Update task
                        task.status = "failed"
                        task.completed_at = now
                        task.error = "Task timed out"
                        
                        # Update worker
                        if worker:
                            worker.status = "idle"
                            worker.current_task_id = None
                            worker.failed_tasks += 1
                        
                        logger.warning(f"Task {task_id} timed out on worker {worker_id}")
    
    def _check_worker_timeouts(self) -> None:
        """Check for inactive workers."""
        now = time.time()
        
        with self.workers_lock:
            for worker_id, worker in list(self.workers.items()):
                # Check if worker has timed out
                if now - worker.last_heartbeat > self.heartbeat_timeout:
                    # Remove worker
                    del self.workers[worker_id]
                    
                    logger.warning(f"Worker {worker_id} timed out")
                    
                    # Check if worker had an assigned task
                    if worker.current_task_id:
                        # Requeue task
                        self._requeue_task(worker.current_task_id)
    
    def _requeue_task(self, task_id: str) -> None:
        """Requeue a task.
        
        Args:
            task_id: Task ID.
        """
        with self.tasks_lock:
            # Check if task exists
            if task_id not in self.tasks:
                return
            
            # Get task
            task = self.tasks[task_id]
            
            # Check if task is in a state that can be requeued
            if task.status in ["assigned", "running"]:
                # Update task
                task.status = "pending"
                task.assigned_to = None
                task.started_at = None
                
                # Add to queue
                self.task_queue.put((task.priority, task_id))
                
                logger.info(f"Requeued task {task_id}")


class MCPRequestHandler(BaseRequestHandler):
    """Request handler for MCP server."""
    
    def handle(self) -> None:
        """Handle a request."""
        # Get MCP server
        mcp_server = self.server.mcp_server
        
        # Get client address
        client_address = f"{self.client_address[0]}:{self.client_address[1]}"
        
        try:
            # Receive data
            data = self.request.recv(4096).decode("utf-8")
            
            # Parse JSON
            request = json.loads(data)
            
            # Get request type
            request_type = request.get("type")
            
            # Handle request
            if request_type == "register":
                # Register worker
                worker_id = request.get("worker_id")
                capabilities = request.get("capabilities", [])
                address = request.get("address", client_address)
                
                response = {
                    "success": True,
                    "data": mcp_server.register_worker(worker_id, capabilities, address),
                }
            
            elif request_type == "unregister":
                # Unregister worker
                worker_id = request.get("worker_id")
                
                response = {
                    "success": mcp_server.unregister_worker(worker_id),
                }
            
            elif request_type == "heartbeat":
                # Update worker heartbeat
                worker_id = request.get("worker_id")
                
                response = {
                    "success": mcp_server.heartbeat(worker_id),
                }
            
            elif request_type == "request_task":
                # Request a task
                worker_id = request.get("worker_id")
                
                task = mcp_server.request_task(worker_id)
                
                response = {
                    "success": task is not None,
                    "data": task,
                }
            
            elif request_type == "start_task":
                # Start a task
                worker_id = request.get("worker_id")
                task_id = request.get("task_id")
                
                response = {
                    "success": mcp_server.start_task(worker_id, task_id),
                }
            
            elif request_type == "complete_task":
                # Complete a task
                worker_id = request.get("worker_id")
                task_id = request.get("task_id")
                result = request.get("result", {})
                
                response = {
                    "success": mcp_server.complete_task(worker_id, task_id, result),
                }
            
            elif request_type == "fail_task":
                # Fail a task
                worker_id = request.get("worker_id")
                task_id = request.get("task_id")
                error = request.get("error", "Unknown error")
                
                response = {
                    "success": mcp_server.fail_task(worker_id, task_id, error),
                }
            
            elif request_type == "add_task":
                # Add a task
                task_type = request.get("task_type")
                data = request.get("data", {})
                priority = request.get("priority", 0)
                
                task_id = mcp_server.add_task(task_type, data, priority)
                
                response = {
                    "success": True,
                    "data": {"task_id": task_id},
                }
            
            elif request_type == "get_task":
                # Get a task
                task_id = request.get("task_id")
                
                task = mcp_server.get_task(task_id)
                
                response = {
                    "success": task is not None,
                    "data": task,
                }
            
            elif request_type == "get_tasks":
                # Get all tasks
                status = request.get("status")
                
                tasks = mcp_server.get_tasks(status)
                
                response = {
                    "success": True,
                    "data": {"tasks": tasks},
                }
            
            elif request_type == "get_worker":
                # Get a worker
                worker_id = request.get("worker_id")
                
                worker = mcp_server.get_worker(worker_id)
                
                response = {
                    "success": worker is not None,
                    "data": worker,
                }
            
            elif request_type == "get_workers":
                # Get all workers
                status = request.get("status")
                
                workers = mcp_server.get_workers(status)
                
                response = {
                    "success": True,
                    "data": {"workers": workers},
                }
            
            else:
                # Unknown request type
                response = {
                    "success": False,
                    "error": f"Unknown request type: {request_type}",
                }
            
            # Send response
            self.request.sendall(json.dumps(response).encode("utf-8"))
        
        except Exception as e:
            logger.error(f"Error handling request from {client_address}: {e}")
            
            # Send error response
            response = {
                "success": False,
                "error": str(e),
            }
            
            try:
                self.request.sendall(json.dumps(response).encode("utf-8"))
            except Exception:
                pass
