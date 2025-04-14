#!/usr/bin/env python
"""API server for the arbitrage bot."""

import argparse
import logging
import os
import signal
import sys
import time
from typing import Dict, Any, Optional

from arbitrage_bot.common.config.config_loader import load_config
from arbitrage_bot.common.logging.logger import setup_logger
from arbitrage_bot.api.server import APIServer
from run_bot import ArbitrageBot


class APIServerRunner:
    """Runner for the API server."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the API server runner.

        Args:
            config: Configuration dictionary.
        """
        self.config = config
        self.logger = setup_logger(config, "arbitrage_bot.api")
        self.running = False

        # Create bot instance
        self.bot = ArbitrageBot(config)

        # Create API server
        self.api_server = APIServer(self.bot, config)

        self.logger.info("API server runner initialized")

    def start(self, block: bool = True) -> None:
        """Start the API server.

        Args:
            block: Whether to block the main thread.
        """
        self.running = True
        self.logger.info("Starting API server")

        # Start bot
        self.bot.start(block=False)

        # Start API server
        self.api_server.start()

        if block:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.stop()

    def stop(self) -> None:
        """Stop the API server."""
        self.running = False
        self.logger.info("Stopping API server")

        # Stop API server
        self.api_server.stop()

        # Stop bot
        self.bot.stop()

        self.logger.info("API server stopped")


def main():
    """Main entry point for the API server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Arbitrage Bot API Server")
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

    # Override API configuration if specified
    api_config = config.get("api", {})
    if args.host:
        api_config["host"] = args.host
    if args.port:
        api_config["port"] = args.port
    config["api"] = api_config

    # Set up logging
    logger = setup_logger(config, "arbitrage_bot.api")

    # Create and start API server
    server_runner = APIServerRunner(config)

    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        server_runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the server
    try:
        logger.info("Starting the API server...")
        server_runner.start()
        logger.info("API server started successfully")
    except Exception as e:
        logger.error(f"Error starting the API server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
