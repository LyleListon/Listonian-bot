"""Script to run the dashboard with optimized settings."""

import uvicorn
import asyncio
import logging
from pathlib import Path
import socket
import contextlib

from new_dashboard.dashboard.core.logging import configure_logging
from new_dashboard.dashboard.app import app

# Configure logging
configure_logging()
logger = logging.getLogger("dashboard.runner")

def find_available_port(start_port: int = 9050, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No available ports found between {start_port} and {start_port + max_attempts}")

def main():
    """Run the dashboard application."""
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

        # Find available port
        port = find_available_port()
        logger.info(f"Using port: {port}")
        
        # Set up asyncio policy for Windows
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Run uvicorn directly with CLI options
        import sys
        sys.argv = ["uvicorn", "new_dashboard.app:app", "--host", "0.0.0.0", "--port", str(port), "--no-access-log"]
        logger.info(f"Dashboard ready at http://localhost:{port}")
        
        # Set up asyncio policy for Windows
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # Run the server
        uvicorn.main()

    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        raise

if __name__ == "__main__":
    main()