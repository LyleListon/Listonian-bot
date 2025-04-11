"""Process management for multiple bot instances."""

import time
import os
import sys
import json
import logging
import asyncio
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProcessState:
    """Process state information."""

    pid: int
    start_time: float
    memory_usage: float
    cpu_usage: float
    status: str
    last_heartbeat: float
    instance_id: str


class ProcessManager:
    """Manages multiple bot instances and their resources."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize process manager."""
        self.config = config
        self.processes: Dict[str, ProcessState] = {}
        self.state_file = Path("data/process_state.json")
        self.state_file.parent.mkdir(exist_ok=True)

        # Load existing state
        self._load_state()

        # Monitoring settings
        self.max_instances = config.get("process", {}).get("max_instances", 3)
        self.max_memory_per_instance = config.get("process", {}).get(
            "max_memory_mb", 1024
        )  # MB
        self.max_cpu_per_instance = config.get("process", {}).get(
            "max_cpu_percent", 50
        )  # %
        self.heartbeat_timeout = config.get("process", {}).get(
            "heartbeat_timeout", 30
        )  # seconds

        # Resource allocation
        self.port_ranges = {"dashboard": (5000, 5010), "websocket": (8771, 8780)}
        self.allocated_ports: Dict[str, Dict[str, int]] = {}

    def _load_state(self):
        """Load process state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    for instance_id, state in data.items():
                        self.processes[instance_id] = ProcessState(**state)
                logger.info(f"Loaded state for {len(self.processes)} processes")
        except Exception as e:
            logger.error(f"Failed to load process state: {e}")

    def _save_state(self):
        """Save process state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(
                    {
                        id: {
                            "pid": state.pid,
                            "start_time": state.start_time,
                            "memory_usage": state.memory_usage,
                            "cpu_usage": state.cpu_usage,
                            "status": state.status,
                            "last_heartbeat": state.last_heartbeat,
                            "instance_id": state.instance_id,
                        }
                        for id, state in self.processes.items()
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save process state: {e}")

    def _allocate_ports(self, instance_id: str) -> Dict[str, int]:
        """Allocate ports for a new instance."""
        allocated = {}
        for service, (start, end) in self.port_ranges.items():
            # Get currently used ports
            used_ports = set()
            for ports in self.allocated_ports.values():
                if service in ports:
                    used_ports.add(ports[service])

            # Find available port
            for port in range(start, end + 1):
                if port not in used_ports:
                    allocated[service] = port
                    break
            else:
                raise RuntimeError(f"No available ports for {service}")

        self.allocated_ports[instance_id] = allocated
        return allocated

    def _release_ports(self, instance_id: str):
        """Release ports allocated to an instance."""
        if instance_id in self.allocated_ports:
            del self.allocated_ports[instance_id]

    async def start_instance(self, instance_id: str) -> bool:
        """Start a new bot instance."""
        try:
            # Check if instance already exists
            if instance_id in self.processes:
                logger.warning(f"Instance {instance_id} already exists")
                return False

            # Check resource limits
            if len(self.processes) >= self.max_instances:
                logger.error("Maximum number of instances reached")
                return False

            # Allocate ports
            ports = self._allocate_ports(instance_id)

            # Set environment variables
            env = os.environ.copy()
            env["INSTANCE_ID"] = instance_id
            env["DASHBOARD_PORT"] = str(ports["dashboard"])
            env["DASHBOARD_WEBSOCKET_PORT"] = str(ports["websocket"])

            # Start process
            process = await asyncio.create_subprocess_exec(
                sys.executable, "production.py", env=env
            )

            # Record state
            self.processes[instance_id] = ProcessState(
                pid=process.pid,
                start_time=time.time(),
                memory_usage=0.0,
                cpu_usage=0.0,
                status="starting",
                last_heartbeat=time.time(),
                instance_id=instance_id,
            )

            self._save_state()
            logger.info(f"Started instance {instance_id} with PID {process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start instance {instance_id}: {e}")
            self._release_ports(instance_id)
            return False

    async def stop_instance(self, instance_id: str) -> bool:
        """Stop a bot instance."""
        try:
            if instance_id not in self.processes:
                logger.warning(f"Instance {instance_id} not found")
                return False

            state = self.processes[instance_id]

            # Stop process
            process = psutil.Process(state.pid)
            process.terminate()
            try:
                process.wait(timeout=10)
            except psutil.TimeoutExpired:
                process.kill()

            # Cleanup
            self._release_ports(instance_id)
            del self.processes[instance_id]
            self._save_state()

            logger.info(f"Stopped instance {instance_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop instance {instance_id}: {e}")
            return False

    async def monitor_instances(self):
        """Monitor running instances."""
        while True:
            try:
                current_time = time.time()

                # Check each instance
                for instance_id, state in list(self.processes.items()):
                    try:
                        process = psutil.Process(state.pid)

                        # Update metrics
                        with process.oneshot():
                            cpu_percent = process.cpu_percent()
                            memory_info = process.memory_info()
                            memory_mb = memory_info.rss / (1024 * 1024)

                        # Check resource limits
                        if memory_mb > self.max_memory_per_instance:
                            logger.warning(
                                f"Instance {instance_id} exceeded memory limit"
                            )
                            await self.stop_instance(instance_id)
                            continue

                        if cpu_percent > self.max_cpu_per_instance:
                            logger.warning(f"Instance {instance_id} exceeded CPU limit")
                            await self.stop_instance(instance_id)
                            continue

                        # Check heartbeat
                        if current_time - state.last_heartbeat > self.heartbeat_timeout:
                            logger.warning(f"Instance {instance_id} heartbeat timeout")
                            await self.stop_instance(instance_id)
                            continue

                        # Update state
                        state.memory_usage = memory_mb
                        state.cpu_usage = cpu_percent
                        state.status = "running"

                    except psutil.NoSuchProcess:
                        logger.warning(f"Instance {instance_id} process not found")
                        self._release_ports(instance_id)
                        del self.processes[instance_id]

                    except Exception as e:
                        logger.error(f"Error monitoring instance {instance_id}: {e}")

                self._save_state()

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            await asyncio.sleep(5)  # Check every 5 seconds

    async def heartbeat(self, instance_id: str) -> bool:
        """Update instance heartbeat."""
        try:
            if instance_id not in self.processes:
                return False

            self.processes[instance_id].last_heartbeat = time.time()
            return True

        except Exception as e:
            logger.error(f"Failed to update heartbeat for {instance_id}: {e}")
            return False

    def get_instance_info(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an instance."""
        try:
            if instance_id not in self.processes:
                return None

            state = self.processes[instance_id]
            return {
                "pid": state.pid,
                "uptime": time.time() - state.start_time,
                "memory_mb": state.memory_usage,
                "cpu_percent": state.cpu_usage,
                "status": state.status,
                "ports": self.allocated_ports.get(instance_id, {}),
            }

        except Exception as e:
            logger.error(f"Failed to get info for {instance_id}: {e}")
            return None

    def list_instances(self) -> List[Dict[str, Any]]:
        """List all running instances."""
        return [
            {
                "instance_id": id,
                "pid": state.pid,
                "uptime": time.time() - state.start_time,
                "memory_mb": state.memory_usage,
                "cpu_percent": state.cpu_usage,
                "status": state.status,
                "ports": self.allocated_ports.get(id, {}),
            }
            for id, state in self.processes.items()
        ]
