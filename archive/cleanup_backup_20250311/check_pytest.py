"""
Check pytest installation and configuration.
"""

import sys
import pytest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Python version: {sys.version}")
logger.info(f"Pytest version: {pytest.__version__}")
logger.info(f"Python path: {sys.path}")

try:
    import arbitrage_bot
    logger.info("Successfully imported arbitrage_bot package")
except ImportError as e:
    logger.error(f"Failed to import arbitrage_bot: {e}")

try:
    from arbitrage_bot.core.distribution.manager import DistributionManager
    logger.info("Successfully imported DistributionManager")
except ImportError as e:
    logger.error(f"Failed to import DistributionManager: {e}")