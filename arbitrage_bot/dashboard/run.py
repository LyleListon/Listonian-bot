"""Run the dashboard application."""

import os
import sys
import asyncio
import logging
import signal
from pathlib import Path
from aiohttp import web
from typing import Optional, Tuple, Any

# Add parent directory to sys.path to allow absolute imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from arbitrage_bot.dashboard.app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardRunner:
    """Manages the dashboard application lifecycle."""

    def __init__(self):
        """Initialize the dashboard runner."""
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.ws_server = None
        self.shutdown_event = asyncio.Event()

    async def setup(self) -> Tuple[web.Application, Any]:
        """Set up the dashboard application."""
        try:
            # Create application
            self.app, self.ws_server = await create_app()
            
            # Set up runner
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Configure port
            port = int(os.environ.get('DASHBOARD_PORT', 5000))
            self.site = web.TCPSite(self.runner, '0.0.0.0', port)
            
            return self.app, self.ws_server

        except Exception as e:
            logger.error(f"Failed to set up dashboard: {e}")
            await self.cleanup()
            raise

    async def start(self):
        """Start the dashboard server."""
        try:
            if not self.site:
                raise RuntimeError("Dashboard not set up. Call setup() first.")
            
            # Start the site
            await self.site.start()
            logger.info(f"Dashboard running on http://0.0.0.0:{self.site._port}")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()

        except Exception as e:
            logger.error(f"Error running dashboard: {e}")
            raise

        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        try:
            # Stop WebSocket server
            if self.ws_server:
                await self.ws_server.stop()
                logger.info("WebSocket server stopped")

            # Clean up site and runner
            if self.site:
                await self.site.stop()
                logger.info("Site stopped")

            if self.runner:
                await self.runner.cleanup()
                logger.info("Runner cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def signal_handler(self, signame: str):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signame}, initiating shutdown...")
        self.shutdown_event.set()

async def run_async():
    """Run the async application."""
    runner = DashboardRunner()
    
    # Set up signal handlers
    for signame in ('SIGINT', 'SIGTERM'):
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            getattr(signal, signame),
            lambda s=signame: runner.signal_handler(s)
        )

    try:
        # Set up and start the dashboard
        await runner.setup()
        await runner.start()
        
    except Exception as e:
        logger.error(f"Dashboard failed to start: {e}")
        await runner.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(run_async())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)
