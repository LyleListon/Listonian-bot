#!/usr/bin/env python
"""MCP server for distributed processing."""

import argparse
import logging
import signal
import sys
import time
from typing import Dict, Any, Optional

from arbitrage_bot.common.config.config_loader import load_config
from arbitrage_bot.common.logging.logger import setup_logger
from arbitrage_bot.mcp.server import MCPServer


class MCPServerRunner:
    """Runner for the MCP server."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the MCP server runner.

        Args:
            config: Configuration dictionary.
        """
        self.config = config
        self.logger = setup_logger(config, "arbitrage_bot.mcp")
        self.running = False

        # Create MCP server
        self.mcp_server = MCPServer(config)

        self.logger.info("MCP server runner initialized")

    def start(self, block: bool = True) -> None:
        """Start the MCP server.

        Args:
            block: Whether to block the main thread.
        """
        self.running = True
        self.logger.info("Starting MCP server")

        # Start MCP server
        self.mcp_server.start()

        if block:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                self.stop()

    def stop(self) -> None:
        """Stop the MCP server."""
        self.running = False
        self.logger.info("Stopping MCP server")

        # Stop MCP server
        self.mcp_server.stop()

        self.logger.info("MCP server stopped")


def main():
    """Main entry point for the MCP server."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Arbitrage Bot MCP Server")
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

    # Override MCP configuration if specified
    mcp_config = config.get("mcp", {})
    if args.host:
        mcp_config["host"] = args.host
    if args.port:
        mcp_config["port"] = args.port
    config["mcp"] = mcp_config

    # Set up logging
    logger = setup_logger(config, "arbitrage_bot.mcp")

    # Create and start MCP server
    server_runner = MCPServerRunner(config)

    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        server_runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the server
    try:
        logger.info("Starting the MCP server...")
        server_runner.start()
        logger.info("MCP server started successfully")
    except Exception as e:
        logger.error(f"Error starting the MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
