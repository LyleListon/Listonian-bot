"""Run the dashboard application."""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from hypercorn.config import Config
from hypercorn.asyncio import serve
from quart import Quart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)7s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Load dashboard configuration."""
    try:
        from ..utils.config_loader import load_config as load_main_config
        return load_main_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def find_available_port(start_port: int, max_attempts: int = 10) -> Optional[int]:
    """Find an available port starting from start_port."""
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return None

async def main():
    """Run the dashboard application."""
    try:
        logger.info("Starting dashboard application")

        # Load configuration
        config = load_config()

        # Create Quart app
        from .app import create_app
        app = create_app()

        # Configure Hypercorn
        hypercorn_config = Config()
        hypercorn_config.bind = ["0.0.0.0:5001"]  # Default port
        hypercorn_config.use_reloader = True
        hypercorn_config.accesslog = "-"

        # Set up WebSocket port
        base_ws_port = int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
        available_ws_port = find_available_port(base_ws_port)
        if not available_ws_port:
            raise RuntimeError(f"No available ports found in range {base_ws_port}-{base_ws_port + 9}")
        
        os.environ['DASHBOARD_WEBSOCKET_PORT'] = str(available_ws_port)
        logger.info(f"Selected WebSocket port: {available_ws_port}")

        # Find available HTTP port
        base_http_port = 5001
        available_http_port = find_available_port(base_http_port)
        if not available_http_port:
            raise RuntimeError(f"No available ports found in range {base_http_port}-{base_http_port + 9}")
        
        hypercorn_config.bind = [f"0.0.0.0:{available_http_port}"]
        logger.info(f"Starting Hypercorn server on 0.0.0.0:{available_http_port}")

        # Start server
        try:
            await serve(app, hypercorn_config)
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            raise

    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        raise

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
