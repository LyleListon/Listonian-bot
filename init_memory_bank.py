#!/usr/bin/env python
"""Memory Bank Initialization Script.

This script initializes or updates the memory bank system, ensuring all required
components are in place and properly configured.
"""

import asyncio
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

from arbitrage_bot.utils.memory_bank import initialize_memory_bank

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main() -> int:
    """Initialize the memory bank system."""
    parser = ArgumentParser(description="Initialize or update the memory bank system")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("memory-bank"),
        help="Path to memory bank directory (default: memory-bank)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset memory bank (WARNING: this will delete existing data)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        logger.info(f"Initializing memory bank at: {args.path}")
        status = await initialize_memory_bank(
            args.path,
            preserve_data=not args.reset
        )

        if status.status == "healthy":
            logger.info("Memory bank initialization completed successfully")
            logger.info("System Status:")
            logger.info(f"  Health: {status.status}")
            logger.info(f"  Message: {status.message}")
            for key, value in status.metrics.items():
                logger.info(f"  {key}: {value}")
            return 0
        else:
            logger.error(f"Memory bank initialization completed with status: {status.status}")
            logger.error(f"Error message: {status.message}")
            return 1

    except Exception as e:
        logger.error(f"Failed to initialize memory bank: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("Initialization cancelled by user")
        sys.exit(130)