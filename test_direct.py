"""
Test using direct file paths.
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

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

logger.info(f"Current directory: {current_dir}")
logger.info(f"Python path: {sys.path}")

async def main():
    try:
        # Import using direct file paths
        sys.path.insert(0, os.path.join(current_dir, 'arbitrage_bot'))
        
        from core.web3.web3_manager import Web3Manager
        from core.distribution.manager import DistributionManager
        logger.info("Modules imported successfully")

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