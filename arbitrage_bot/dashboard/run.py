"""
Dashboard runner script.

This module:
1. Loads environment variables
2. Initializes core components
3. Starts the FastAPI application
4. Handles graceful shutdown
"""

import os
import sys
import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

import uvicorn
from web3 import Web3

from ..core import (
    get_cache,
    get_ws_manager,
    get_metrics_collector,
    get_web3_manager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DashboardRunner:
    """Manages the dashboard lifecycle."""
    
    def __init__(self):
        """Initialize the dashboard runner."""
        self.should_exit = False
        self._setup_signal_handlers()
        
        # Load environment variables
        env_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        # Validate environment variables
        required_vars = [
            'RPC_URL',
            'CHAIN_ID',
            'DASHBOARD_HOST',
            'DASHBOARD_PORT'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
            
        # Validate RPC URL format
        rpc_url = os.getenv('RPC_URL')
        if not rpc_url.startswith(('http://', 'https://')):
            logger.error(f"Invalid RPC URL format: {rpc_url}")
            sys.exit(1)
            
        # Log configuration
        logger.info(f"Using RPC URL: {rpc_url}")
        logger.info(f"Using Chain ID: {os.getenv('CHAIN_ID')}")
        
        # Core components
        self.cache = get_cache()
        self.ws_manager = get_ws_manager()
        self.metrics_collector = get_metrics_collector()
        self.web3 = get_web3_manager()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_signal)
    
    def _handle_signal(self, signum: int, frame: Optional[object]) -> None:
        """Handle termination signals."""
        logger.info(f"Received signal {signum}")
        self.should_exit = True
    
    async def initialize(self) -> None:
        """Initialize core components."""
        try:
            # Start cache cleanup task
            await self.cache.start_cleanup_task()
            
            # Start WebSocket manager
            await self.ws_manager.start()
            
            # Start metrics collector
            await self.metrics_collector.start()
            
            logger.info("Core components initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Stop metrics collector
            await self.metrics_collector.stop()
            
            # Stop WebSocket manager
            await self.ws_manager.stop()
            
            # Stop cache cleanup
            await self.cache.stop_cleanup_task()
            
            logger.info("Core components stopped")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise

async def main() -> None:
    """Main entry point."""
    try:
        # Initialize runner
        runner = DashboardRunner()
        await runner.initialize()
        
        # Configure uvicorn
        config = uvicorn.Config(
            "arbitrage_bot.dashboard.app:app",
            host=os.getenv('DASHBOARD_HOST', '127.0.0.1'),
            port=int(os.getenv('DASHBOARD_PORT', '8000')),
            reload=False,
            log_level="info"
        )
        
        # Start server
        server = uvicorn.Server(config)
        
        # Run until signal received
        await server.serve()
        
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")
        raise
    finally:
        if 'runner' in locals():
            await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
