#!/usr/bin/env python
"""Start all components of the arbitrage bot."""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Dict, List, Any, Optional

from arbitrage_bot.common.config.config_loader import load_config
from arbitrage_bot.common.logging.logger import setup_logger


class ComponentStarter:
    """Starter for all components."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the component starter.

        Args:
            config: Configuration dictionary.
        """
        self.config = config
        self.logger = setup_logger(config, "arbitrage_bot.starter")

        # Initialize state
        self.processes = {}
        self.running = False

        self.logger.info("Component starter initialized")

    def start_all(self) -> None:
        """Start all components."""
        self.running = True
        self.logger.info("Starting all components")

        try:
            # Start MCP server
            self.start_component("mcp", ["python", "run_mcp_server.py"])

            # Wait for MCP server to start
            time.sleep(2)

            # Start bot
            self.start_component("bot", ["python", "run_bot.py"])

            # Wait for bot to start
            time.sleep(2)

            # Start API server
            self.start_component("api", ["python", "bot_api_server.py"])

            # Wait for API server to start
            time.sleep(2)

            # Start dashboard server
            self.start_component("dashboard", ["python", "run_dashboard.py"])

            self.logger.info("All components started")

            # Wait for interrupt
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.stop_all()

        except Exception as e:
            self.logger.error(f"Error starting components: {e}")
            self.stop_all()

    def stop_all(self) -> None:
        """Stop all components."""
        self.running = False
        self.logger.info("Stopping all components")

        # Stop components in reverse order
        for name in reversed(list(self.processes.keys())):
            self.stop_component(name)

        self.logger.info("All components stopped")

    def start_component(self, name: str, command: List[str]) -> None:
        """Start a component.

        Args:
            name: Component name.
            command: Command to run.
        """
        self.logger.info(f"Starting {name}")

        try:
            # Start process with visible console window
            process = subprocess.Popen(
                command,
                # Don't redirect stdout/stderr to allow console window to show
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

            # Store process
            self.processes[name] = process

            self.logger.info(f"{name} started with PID {process.pid}")

            # Check if process is still running after a short delay
            time.sleep(1)
            if process.poll() is not None:
                self.logger.error(f"{name} process terminated immediately with code {process.returncode}")
            else:
                self.logger.info(f"{name} process is running")

        except Exception as e:
            self.logger.error(f"Error starting {name}: {e}")

    def stop_component(self, name: str) -> None:
        """Stop a component.

        Args:
            name: Component name.
        """
        if name not in self.processes:
            return

        self.logger.info(f"Stopping {name}")

        try:
            # Get process
            process = self.processes[name]

            # Terminate process
            process.terminate()

            # Wait for process to terminate
            process.wait(timeout=5.0)

            # Remove process
            del self.processes[name]

            self.logger.info(f"{name} stopped")

        except Exception as e:
            self.logger.error(f"Error stopping {name}: {e}")

            # Try to kill process
            try:
                process = self.processes[name]
                process.kill()
                process.wait(timeout=5.0)
                del self.processes[name]
                self.logger.info(f"{name} killed")
            except Exception as e2:
                self.logger.error(f"Error killing {name}: {e2}")


def main():
    """Main entry point for the component starter."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Arbitrage Bot Component Starter")
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Environment to use (development, production, test)",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.env)

    # Create and start component starter
    starter = ComponentStarter(config)

    # Set up signal handlers
    def signal_handler(sig, frame):
        logger = logging.getLogger("arbitrage_bot.starter")
        logger.info(f"Received signal {sig}")
        starter.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start all components
    starter.start_all()


if __name__ == "__main__":
    main()
