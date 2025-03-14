"""
Start the dashboard application.

This script starts the aiohttp-based dashboard that provides:
- Real-time arbitrage opportunity tracking
- Balance and allocation monitoring
- Historical trade performance analytics
- DEX pricing and liquidity analysis
- System status and health monitoring
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to sys.path to allow absolute imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from arbitrage_bot.dashboard.run import run_async

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'dashboard.log'))
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Get port from environment or use default
        port = int(os.environ.get('DASHBOARD_PORT', 8080))
        host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')

        logger.info(f"Starting dashboard on {host}:{port}")
        
        # Run the async application
        asyncio.run(run_async())

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Dashboard failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()