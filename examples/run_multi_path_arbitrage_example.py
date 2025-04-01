#!/usr/bin/env python3
"""
Run Multi-Path Arbitrage Example

This script runs the multi-path arbitrage example to demonstrate
the multi-path arbitrage optimization components.
"""

import asyncio
import logging
import os
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/multi_path_arbitrage_example.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)

def ensure_log_directory():
    """Ensure the logs directory exists."""
    os.makedirs('logs', exist_ok=True)

async def main():
    """Run the multi-path arbitrage example."""
    try:
        ensure_log_directory()
        
        logger.info("Starting Multi-Path Arbitrage Example")
        start_time = time.time()
        
        # Import and run the example
        from examples.multi_path_arbitrage_example import main as run_example
        await run_example()
        
        end_time = time.time()
        logger.info(f"Multi-Path Arbitrage Example completed in {end_time - start_time:.2f} seconds")
    
    except Exception as e:
        logger.error(f"Error running Multi-Path Arbitrage Example: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())