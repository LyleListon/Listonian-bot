"""
Test using sys.path manipulation.
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

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add core directory to Python path
core_path = os.path.join(project_root, 'arbitrage_bot', 'core')
if core_path not in sys.path:
    sys.path.insert(0, core_path)

logger.info(f"Project root: {project_root}")
logger.info(f"Core path: {core_path}")
logger.info("Python path:")
for p in sys.path:
    logger.info(f"  {p}")

async def main():
    try:
        # Import modules
        from web3.web3_manager import Web3Manager
        logger.info("Imported Web3Manager")
        
        from distribution.manager import DistributionManager
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