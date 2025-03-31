#!/usr/bin/env python3
"""
Run Performance Optimization Example

This script runs the performance optimization example to demonstrate:
- Memory-Mapped Files
- WebSocket Optimization
- Resource Management
"""

import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run the performance optimization example."""
    try:
        # Import the example module
        from examples.performance_optimization_example import main as example_main
        
        # Run the example
        logger.info("Starting performance optimization example...")
        await example_main()
        logger.info("Performance optimization example completed successfully")
        
    except Exception as e:
        logger.error(f"Error running performance optimization example: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())