#!/usr/bin/env python3
"""
Command-line script to run path finder tests in production environments.

This script tests the path finding algorithm with real-world data to validate
performance, gas estimation accuracy, and success rates.

Example usage:
    python test_path_finder.py --max-tests 50 --output-dir data/test_results
"""

import asyncio
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("path_finder_test")

async def main():
    """Run the path finder tests."""
    try:
        # Add project root to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        # Import the testing module
        from arbitrage_bot.testing.path_finder_tester import run_path_finder_tests
        
        # Run tests
        await run_path_finder_tests()
        
    except Exception as e:
        logger.error(f"Error running path finder tests: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Check Python version
    if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)