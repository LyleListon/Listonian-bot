#!/usr/bin/env python
"""
Run Test Dashboard for Listonian Arbitrage Bot

This script launches a test dashboard for the Listonian Arbitrage Bot
that simulates real-time data and provides a visual interface for monitoring
arbitrage operations.
"""

import os
import sys
import asyncio
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
TEST_SERVER_PORT = 9050
TEST_SERVER_HOST = "0.0.0.0"


async def ensure_directories_exist():
    """Ensure all necessary directories exist."""
    base_dir = Path(__file__).parent

    # Create test dashboard directories if they don't exist
    dirs = [
        base_dir / "tests" / "dashboard" / "templates",
        base_dir / "tests" / "dashboard" / "static",
    ]

    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")


def start_test_server():
    """Start the test server using the run_test_server.py script."""
    script_path = Path(__file__).parent / "run_test_server.py"

    if not script_path.exists():
        logger.error(f"Test server script not found at {script_path}")
        sys.exit(1)

    logger.info(f"Starting test server on http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}")

    # Make the script executable
    os.chmod(script_path, 0o755)

    # Start the server process
    try:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Print the startup message
        for line in process.stdout:
            print(line, end="")
            if "Application startup complete" in line:
                break

        return process
    except Exception as e:
        logger.error(f"Failed to start test server: {e}")
        sys.exit(1)


def open_browser():
    """Open the default web browser to the dashboard URL."""
    import webbrowser

    url = f"http://localhost:{TEST_SERVER_PORT}"
    logger.info(f"Opening dashboard in browser: {url}")

    # Open the URL in the default browser
    webbrowser.open(url)


async def main():
    """Main function to run the test dashboard."""
    # Ensure all necessary directories exist
    await ensure_directories_exist()

    # Start the test server
    server_process = start_test_server()

    try:
        # Open the browser
        open_browser()

        # Keep the script running until interrupted
        logger.info("Test dashboard is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping test dashboard...")
    finally:
        # Terminate the server process
        if server_process:
            server_process.terminate()
            logger.info("Test server stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test dashboard stopped by user.")
    except Exception as e:
        logger.error(f"Error running test dashboard: {e}")
        sys.exit(1)
