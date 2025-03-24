#!/usr/bin/env python3
"""
Launch script for the Arbitrage Bot Dashboard.
Starts both the dashboard server and monitor in separate processes with proper cleanup.
"""

import os
import sys
import subprocess
import time
import psutil
import signal
import logging
import socket
import json
import asyncio
from pathlib import Path
from typing import Dict, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dashboard configuration
DASHBOARD_PORT = 9095
MAX_STARTUP_ATTEMPTS = 3
STARTUP_RETRY_DELAY = 2
PROCESS_TIMEOUT = 10

class DashboardManager:
    """Manages dashboard processes and lifecycle."""

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.base_path = Path(__file__).parent
        self.config_path = self.base_path / 'configs' / 'config.json'

    def load_config(self) -> bool:
        """Load and validate configuration."""
        try:
            if not self.config_path.exists():
                logger.error(f"Configuration file not found: {self.config_path}")
                return False

            with open(self.config_path) as f:
                config = json.load(f)

            required_keys = ['provider_url', 'dexes', 'tokens']
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                logger.error(f"Missing required config keys: {missing_keys}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False

    def check_dependencies(self) -> bool:
        """Check and install required dependencies."""
        required_packages = [
            'aiohttp',
            'python-socketio',
            'psutil',
            'web3'
        ]

        try:
            import pkg_resources
            installed = {pkg.key for pkg in pkg_resources.working_set}
            missing = [pkg for pkg in required_packages if pkg.lower() not in installed]

            if missing:
                logger.info("Installing missing dependencies...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
                logger.info("Dependencies installed successfully")

            return True

        except Exception as e:
            logger.error(f"Error checking/installing dependencies: {e}")
            return False

    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def wait_for_port_release(self, port: int, timeout: int = 30) -> bool:
        """Wait for a port to be released."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_port_in_use(port):
                return True
            time.sleep(0.5)
        return False

    def kill_process_by_port(self, port: int) -> bool:
        """Kill any process using the specified port."""
        try:
            if not self.is_port_in_use(port):
                return True

            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    connections = proc.connections()
                    if any(conn.laddr.port == port for conn in connections):
                        process = psutil.Process(proc.pid)
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            process.kill()
                        logger.info(f"Terminated process using port {port}")
                        return self.wait_for_port_release(port)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return False

        except Exception as e:
            logger.error(f"Error killing process on port {port}: {e}")
            return False

    def start_process(self, script_name: str, process_name: str) -> Optional[subprocess.Popen]:
        """Start a Python script as a separate process."""
        try:
            script_path = self.base_path / script_name
            if not script_path.exists():
                logger.error(f"Script not found: {script_path}")
                return None

            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,  # Line buffered
                cwd=str(self.base_path)
            )

            self.processes[process_name] = process
            return process

        except Exception as e:
            logger.error(f"Error starting {script_name}: {e}")
            return None

    def monitor_process_output(self, process: subprocess.Popen, name: str):
        """Monitor and log process output."""
        try:
            if process.stdout:
                line = process.stdout.readline()
                if line.strip():
                    logger.info(f"[{name}] {line.strip()}")
            if process.stderr:
                line = process.stderr.readline()
                if line.strip():
                    logger.error(f"[{name}] {line.strip()}")
        except Exception as e:
            logger.error(f"Error reading {name} output: {e}")

    def cleanup_processes(self):
        """Clean up all running processes."""
        for name, process in self.processes.items():
            if process and process.poll() is None:
                logger.info(f"Stopping {name}...")
                process.terminate()
                try:
                    process.wait(timeout=PROCESS_TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        self.processes.clear()
        self.kill_process_by_port(DASHBOARD_PORT)

    def run(self):
        """Run the dashboard system."""
        try:
            # Initial setup
            if not self.check_dependencies() or not self.load_config():
                return False

            # Ensure clean state
            self.cleanup_processes()
            if not self.kill_process_by_port(DASHBOARD_PORT):
                logger.error("Failed to clear dashboard port")
                return False

            # Start dashboard
            logger.info("Starting dashboard server...")
            dashboard_process = self.start_process('final_dashboard.py', 'dashboard')
            if not dashboard_process:
                return False

            # Wait for dashboard to start
            time.sleep(2)
            attempts = 0
            while attempts < MAX_STARTUP_ATTEMPTS:
                if self.is_port_in_use(DASHBOARD_PORT):
                    break
                attempts += 1
                time.sleep(STARTUP_RETRY_DELAY)
            else:
                logger.error("Dashboard failed to start")
                self.cleanup_processes()
                return False

            # Start monitor
            logger.info("Starting dashboard monitor...")
            monitor_process = self.start_process('dashboard_monitor.py', 'monitor')
            if not monitor_process:
                self.cleanup_processes()
                return False

            logger.info(f"\nDashboard system is running!")
            logger.info(f"Open http://localhost:{DASHBOARD_PORT} in your browser")
            logger.info("Press Ctrl+C to stop")

            # Monitor processes
            while True:
                for name, process in self.processes.items():
                    if process.poll() is not None:
                        logger.error(f"{name} process has terminated unexpectedly")
                        self.cleanup_processes()
                        return False
                    self.monitor_process_output(process, name)
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        except Exception as e:
            logger.error(f"Error running dashboard: {e}")
        finally:
            self.cleanup_processes()

def main():
    """Main entry point."""
    manager = DashboardManager()
    manager.run()

if __name__ == "__main__":
    main()