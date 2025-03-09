"""
Simple test script for DistributionManager.
"""

import os
import sys
import asyncio
import logging
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def create_mock_web3_manager():
    """Create a mock Web3Manager instance."""
    web3_manager = Mock()
    web3_manager.get_balance = AsyncMock(return_value=Decimal('1.0'))
    web3_manager.wallet_address = "0x1234567890123456789012345678901234567890"
    web3_manager.w3 = Mock()
    web3_manager.w3.to_wei = lambda x, _: int(float(x) * 10**18)
    web3_manager.send_transaction = AsyncMock(return_value="0xmocked_tx_hash")
    return web3_manager

async def main():
    try:
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Python path: {sys.path}")
        
        logger.info("Importing modules...")
        from arbitrage_bot.core.web3.web3_manager import Web3Manager
        logger.info("Successfully imported Web3Manager")
        
        from arbitrage_bot.core.distribution.manager import DistributionManager
        logger.info("Successfully imported DistributionManager")

        # Create mock web3 manager
        web3_manager = create_mock_web3_manager()
        logger.info("Created mock web3 manager")

        # Create distribution manager
        config = {
            'wallet': {'profit_recipient': '0x9876543210987654321098765432109876543210'},
            'min_balance': 0.1,
            'gas_buffer': 0.05
        }
        manager = DistributionManager(web3_manager, config)
        logger.info("Created distribution manager")

        # Initialize
        success = await manager.initialize()
        logger.info(f"Initialization {'succeeded' if success else 'failed'}")

        if success:
            # Test balance check
            balance = await manager.get_balance()
            logger.info(f"Current balance: {balance}")

            # Test profit distribution
            amount = Decimal('0.5')
            distribution_success = await manager.distribute_profits(amount)
            logger.info(f"Distribution {'succeeded' if distribution_success else 'failed'}")

        # Cleanup
        await manager.cleanup()
        logger.info("Cleanup completed")

    except ImportError as e:
        logger.error(f"Import error: {e}")
        if hasattr(e, 'path'):
            logger.error(f"Failed module path: {e.path}")
        if hasattr(e, 'name'):
            logger.error(f"Failed module name: {e.name}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)