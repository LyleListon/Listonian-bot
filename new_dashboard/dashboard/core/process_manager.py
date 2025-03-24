"""Process Manager for Dashboard.

This module implements a process manager that handles process lifecycle,
cleanup, and monitoring to ensure proper isolation and resource management.
"""

import asyncio
import logging
import os
import psutil
import signal
import subprocess
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto

from .logging import get_logger

logger = get_logger(__name__)

class ProcessState(Enum):
    """Process lifecycle states."""
    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    ERROR = auto()
    STOPPING = auto()

@dataclass
class ProcessInfo:
    """Information about a managed process."""
    name: str
    command: List[str]
    state: ProcessState
    pid: Optional[int] = None
    start_time: Optional[datetime] = None
    error: Optional[Exception] = None
    restart_count: int = 0
    max_restarts: int = 3
    backoff_factor: float = 1.5

class ProcessManager:
    """Manages process lifecycle and monitoring."""

    def __init__(self, base_path: Path):
        self._base_path = Path(base_path)
        self._processes: Dict[str, ProcessInfo] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._logger = logger
        self._monitor_interval = 10  # seconds
        self._monitor_task: Optional[asyncio.Task] = None
        self._cleanup_on_exit = True

    async def initialize(self) -> None:
        """Initialize the process manager."""
        async with self._lock:
            if self._initialized:
                return

            self._logger.info("Initializing process manager")

            try:
                # Register signal handlers
                self._setup_signal_handlers()

                # Start monitoring task
                self._monitor_task = asyncio.create_task(
                    self._monitoring_loop()
                )

                self._initialized = True
                self._logger.info("Process manager initialized successfully")

            except Exception as e:
                error_msg = f"Failed to initialize process manager: {e}"
                self._logger.error(error_msg, exc_info=True)
                await self.cleanup()
                raise RuntimeError(error_msg)

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def handle_shutdown(signum, frame):
            if self._cleanup_on_exit:
                asyncio.create_task(self.cleanup())

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

    async def register_process(
        self,
        name: str,
        command: List[str],
        max_restarts: int = 3
    ) -> None:
        """Register a process for management.

        Args:
            name: Process name
            command: Command list to execute
            max_restarts: Maximum number of restart attempts
        """
        async with self._lock:
            if name in self._processes:
                raise ValueError(f"Process {name} already registered")

            self._processes[name] = ProcessInfo(
                name=name,
                command=command,
                state=ProcessState.STOPPED,
                max_restarts=max_restarts
            )
            self._logger.info(f"Registered process: {name}")

    async def start_process(self, name: str) -> None:
        """Start a registered process."""
        process = self._processes.get(name)
        if not process:
            raise ValueError(f"Unknown process: {name}")

        if process.state != ProcessState.STOPPED:
            raise RuntimeError(
                f"Process {name} not stopped (state: {process.state.name})"
            )

        process.state = ProcessState.STARTING
        try:
            # Clean up any existing processes first
            await self._cleanup_existing_processes(process.command)

            # Start the process
            proc = subprocess.Popen(
                process.command,
                cwd=str(self._base_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            process.pid = proc.pid
            process.start_time = datetime.utcnow()
            process.state = ProcessState.RUNNING
            self._logger.info(f"Started process {name} (PID: {proc.pid})")

        except Exception as e:
            process.state = ProcessState.ERROR
            process.error = e
            raise

    async def _cleanup_existing_processes(self, command: List[str]) -> None:
        """Clean up any existing processes matching the command."""
        try:
            # Find processes matching the command
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if proc.info['cmdline'] and all(
                        cmd in ' '.join(proc.info['cmdline'])
                        for cmd in command
                    ):
                        # Terminate process
                        proc_obj = psutil.Process(proc.info['pid'])
                        proc_obj.terminate()
                        try:
                            proc_obj.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc_obj.kill()
                        self._logger.info(
                            f"Terminated existing process: {proc.info['pid']}"
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self._logger.error(f"Error cleaning up existing processes: {e}")
            raise

    async def stop_process(self, name: str, timeout: int = 5) -> None:
        """Stop a running process.

        Args:
            name: Process name
            timeout: Seconds to wait for graceful termination
        """
        process = self._processes.get(name)
        if not process:
            raise ValueError(f"Unknown process: {name}")

        if process.state not in (ProcessState.RUNNING, ProcessState.ERROR):
            return

        process.state = ProcessState.STOPPING
        try:
            if process.pid:
                proc = psutil.Process(process.pid)
                # Try graceful termination first
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except psutil.TimeoutExpired:
                    # Force kill if timeout
                    proc.kill()
                    proc.wait(timeout=1)

            process.pid = None
            process.start_time = None
            process.state = ProcessState.STOPPED
            self._logger.info(f"Stopped process {name}")

        except psutil.NoSuchProcess:
            process.pid = None
            process.start_time = None
            process.state = ProcessState.STOPPED
        except Exception as e:
            process.state = ProcessState.ERROR
            process.error = e
            raise

    async def _monitoring_loop(self) -> None:
        """Monitor running processes."""
        while True:
            try:
                for name, process in self._processes.items():
                    if process.state == ProcessState.RUNNING and process.pid:
                        try:
                            # Check if process is still running
                            proc = psutil.Process(process.pid)
                            if proc.status() == psutil.STATUS_ZOMBIE:
                                raise psutil.NoSuchProcess(process.pid)
                        except psutil.NoSuchProcess:
                            self._logger.warning(
                                f"Process {name} (PID: {process.pid}) died"
                            )
                            await self._handle_process_failure(name)

                await asyncio.sleep(self._monitor_interval)

            except asyncio.CancelledError:
                self._logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                self._logger.error(
                    f"Error in monitoring loop: {e}",
                    exc_info=True
                )
                await asyncio.sleep(self._monitor_interval)

    async def _handle_process_failure(self, name: str) -> None:
        """Handle process failure with restart logic."""
        process = self._processes[name]
        process.state = ProcessState.ERROR

        if process.restart_count < process.max_restarts:
            backoff = process.backoff_factor ** process.restart_count
            self._logger.info(
                f"Restarting {name} in {backoff:.1f}s "
                f"(attempt {process.restart_count + 1})"
            )
            await asyncio.sleep(backoff)
            process.restart_count += 1
            try:
                await self.start_process(name)
            except Exception as e:
                self._logger.error(
                    f"Failed to restart {name}: {e}",
                    exc_info=True
                )
        else:
            self._logger.error(
                f"Max restarts ({process.max_restarts}) reached for {name}"
            )

    async def get_process_status(self) -> Dict[str, Dict]:
        """Get status of all managed processes."""
        status = {}
        for name, process in self._processes.items():
            info = {
                "state": process.state.name,
                "pid": process.pid,
                "restart_count": process.restart_count,
                "max_restarts": process.max_restarts,
                "error": str(process.error) if process.error else None
            }
            if process.start_time:
                info["uptime"] = str(
                    datetime.utcnow() - process.start_time
                ).split('.')[0]
            status[name] = info
        return status

    async def cleanup(self) -> None:
        """Clean up all managed processes."""
        async with self._lock:
            if not self._initialized:
                return

            self._logger.info("Cleaning up processes")

            # Cancel monitoring task
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            # Stop all processes
            for name in list(self._processes.keys()):
                try:
                    await self.stop_process(name)
                except Exception as e:
                    self._logger.error(
                        f"Error stopping process {name}: {e}",
                        exc_info=True
                    )

            self._initialized = False
            self._logger.info("Process cleanup completed")