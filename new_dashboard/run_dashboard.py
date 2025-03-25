"""Script to run the dashboard with optimized settings."""

import uvicorn
import asyncio
import logging
from pathlib import Path
import socket
import contextlib

from new_dashboard.dashboard.core.logging import configure_logging
from new_dashboard.dashboard.app import create_app

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

        # Create and run the application
        app = create_app()
        
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            reload=True,
            workers=1,  # Single worker for WebSocket support
            loop="asyncio",
            log_config=None,  # Use our custom logging config
            ws_ping_interval=5,  # WebSocket ping every 5 seconds
            ws_ping_timeout=10,  # WebSocket timeout after 10 seconds
            timeout_keep_alive=30,  # Keep-alive timeout
            access_log=True
        )
        
        server = uvicorn.Server(config)
        logger.info(f"Dashboard ready at http://localhost:{port}")
        
        # Set up asyncio policy for Windows
        if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # Run the server
        server.run()

    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        raise

if __name__ == "__main__":
    main()