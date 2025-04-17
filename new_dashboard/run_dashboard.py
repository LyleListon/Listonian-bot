"""Script to run the dashboard with optimized settings."""

import uvicorn
import asyncio
import logging
import argparse
from pathlib import Path
import socket
import contextlib
import sys
import os

from new_dashboard.dashboard.core.logging import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger("dashboard.runner")


def find_available_port(start_port: int = 9050, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with contextlib.closing(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ) as sock:
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"No available ports found between {start_port} and {start_port + max_attempts}"
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the dashboard application")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9050,
        help="Port to run the dashboard on"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--find-port",
        action="store_true",
        help="Find an available port automatically"
    )
    return parser.parse_args()


def main():
    """Run the dashboard application."""
    args = parse_args()

    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Create memory-bank directory if it doesn't exist
        memory_bank_dir = Path("memory-bank")
        memory_bank_dir.mkdir(exist_ok=True)

        logger.info("Starting dashboard...")
        logger.info(f"Logs directory: {logs_dir.absolute()}")
        logger.info(f"Memory bank directory: {memory_bank_dir.absolute()}")

        # Find available port if requested
        port = args.port
        if args.find_port:
            port = find_available_port(start_port=args.port)

        logger.info(f"Using port: {port}")

        # Set up asyncio policy for Windows
        if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # Set environment variables
        os.environ["DASHBOARD_HOST"] = args.host
        os.environ["DASHBOARD_PORT"] = str(port)
        os.environ["DASHBOARD_DEBUG"] = "1" if args.debug else "0"

        # Log configuration
        logger.info("Dashboard configuration:")
        logger.info(f"  Host: {args.host}")
        logger.info(f"  Port: {port}")
        logger.info(f"  Reload: {args.reload}")
        logger.info(f"  Debug: {args.debug}")

        logger.info(f"Dashboard will be available at http://localhost:{port}")
        logger.info(f"WebSocket test page will be available at http://localhost:{port}/websocket-test")

        # Run the dashboard
        uvicorn.run(
            "new_dashboard.dashboard.app:create_app",
            factory=True,
            host=args.host,
            port=port,
            reload=args.reload,
            log_level="debug" if args.debug else "info",
            access_log=True,
            lifespan="on",
        )

    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        raise


if __name__ == "__main__":
    main()
