#!/usr/bin/env python3
"""Runner script for the real-time metrics example.

This script provides a convenient way to run the real-time metrics example.
"""

import os
import sys
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Import and run the example
        from examples.real_time_metrics_example import main
        main()
    except KeyboardInterrupt:
        logger.info("Example stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running example: {str(e)}")
        sys.exit(1)