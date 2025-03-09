"""
Simple test script for distribution manager.
"""

import asyncio
import logging
import sys
from decimal import Decimal
from arbitrage_bot.core.distribution.manager import DistributionManager
from unittest.mock import AsyncMock, Mock

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main():
    try:
        logger.info("Starting test...")
        
        # Create mock web3 manager
        web3_manager = Mock()
        web3_manager.get_balance = AsyncMock(return_value=1.0)
        web3_manager.wallet_address = "0x1234567890123456789012345678901234567890"
        web3_manager.w3 = Mock()
        web3_manager.w3.to_wei = lambda x, _: int(float(x) * 10**18)
        web3_manager.send_transaction = AsyncMock(return_value="0xmocked_tx_hash")
        
        logger.info("Created mock web3 manager")
        
        # Create and initialize distribution manager
        config = {
            'wallet': {'profit_recipient': '0x9876543210987654321098765432109876543210'},
            'min_balance': 0.1,
            'gas_buffer': 0.05
        }
        
        logger.info("Creating distribution manager...")
        manager = DistributionManager(web3_manager, config)
        
        logger.info("Initializing distribution manager...")
        success = await manager.initialize()
        logger.info(f"Initialization {'succeeded' if success else 'failed'}")
        
        if success:
            # Test balance check
            logger.info("Testing balance check...")
            balance = await manager.get_balance()
            logger.info(f"Current balance: {balance}")
            
            # Test profit distribution
            amount = Decimal('0.5')
            logger.info(f"Testing profit distribution of {amount} ETH...")
            distribution_success = await manager.distribute_profits(amount)
            logger.info(f"Distribution {'succeeded' if distribution_success else 'failed'}")
            
            # Cleanup
            logger.info("Cleaning up...")
            await manager.cleanup()
            logger.info("Cleanup completed")
        else:
            logger.error("Failed to initialize distribution manager")

    except Exception as e:
        logger.exception("Test failed with error:")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.exception("Test failed with error:")
        sys.exit(1)