"""
Test using PYTHONPATH environment variable.
"""

import os
import sys
import asyncio
import logging
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set PYTHONPATH
project_root = os.path.abspath(os.path.dirname(__file__))
core_path = os.path.join(project_root, 'arbitrage_bot', 'core')
os.environ['PYTHONPATH'] = f"{project_root}{os.pathsep}{core_path}"

logger.info(f"Project root: {project_root}")
logger.info(f"Core path: {core_path}")
logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
logger.info("Python path:")
for p in sys.path:
    logger.info(f"  {p}")

async def main():
    try:
        # Import modules
        from arbitrage_bot.core.web3.web3_manager import Web3Manager
        logger.info("Imported Web3Manager")
        
        from arbitrage_bot.core.distribution.manager import DistributionManager
        logger.info("Imported DistributionManager")

        # Create mock web3 manager
        web3_manager = Mock()
        web3_manager.get_balance = AsyncMock(return_value=Decimal('1.0'))
        web3_manager.wallet_address = "0x1234567890123456789012345678901234567890"
        web3_manager.w3 = Mock()
        web3_manager.w3.to_wei = lambda x, _: int(float(x) * 10**18)
        web3_manager.send_transaction = AsyncMock(return_value="0xmocked_tx_hash")
        logger.info("Created mock web3 manager")

        # Create distribution manager
        manager = DistributionManager(web3_manager)
        logger.info("Created distribution manager")

        # Initialize
        success = await manager.initialize()
        logger.info(f"Initialization {'succeeded' if success else 'failed'}")

        # Cleanup
        await manager.cleanup()
        logger.info("Cleanup completed")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())