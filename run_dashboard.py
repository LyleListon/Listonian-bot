#!/usr/bin/env python
"""Dashboard server for the arbitrage bot."""

import argparse
import logging
import os
import signal
import sys
import time
from typing import Dict, Any, Optional

from arbitrage_bot.common.config.config_loader import load_config
from arbitrage_bot.common.logging.logger import setup_logger
from arbitrage_bot.dashboard.backend.server import DashboardServer
from run_bot import ArbitrageBot


class DashboardRunner:
    """Runner for the dashboard server."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the dashboard runner.

        Args:
            config: Configuration dictionary.
        """
        self.config = config
        self.logger = setup_logger(config, "arbitrage_bot.dashboard")
        self.running = False

        # Create bot instance
        self.bot = ArbitrageBot(config)

        # Create dashboard server
        self.dashboard_server = DashboardServer(self.bot, config)

        self.logger.info("Dashboard runner initialized")

    def start(self, block: bool = True) -> None:
        """Start the dashboard server.

        Args:
            block: Whether to block the main thread.
        """
        self.running = True
        self.logger.info("Starting dashboard server")

        # Start bot
        self.bot.start(block=False)

        # Start dashboard server
        self.dashboard_server.start()

        if block:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.stop()

    def stop(self) -> None:
        """Stop the dashboard server."""
        self.running = False
        self.logger.info("Stopping dashboard server")

        # Stop dashboard server
        self.dashboard_server.stop()

        # Stop bot
        self.bot.stop()

        self.logger.info("Dashboard server stopped")


def main():
    """Main entry point for the dashboard server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Arbitrage Bot Dashboard Server")
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Environment to use (development, production, test)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.env)

    # Override dashboard configuration if specified
    dashboard_config = config.get("dashboard", {})
    if args.host:
        dashboard_config["host"] = args.host
    if args.port:
        dashboard_config["port"] = args.port
    config["dashboard"] = dashboard_config

    # Set up logging
    logger = setup_logger(config, "arbitrage_bot.dashboard")

    # Create and start dashboard server
    dashboard_runner = DashboardRunner(config)

    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        dashboard_runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the server
    try:
        logger.info("Starting the dashboard server...")
        dashboard_runner.start()
        logger.info("Dashboard server started successfully")
    except Exception as e:
        logger.error(f"Error starting the dashboard server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
