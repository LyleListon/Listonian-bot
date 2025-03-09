"""
Minimal test script for imports.
"""

import asyncio
import logging
import sys

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    try:
        logger.info("Importing Web3Manager...")
        from arbitrage_bot.core.web3.web3_manager import Web3Manager
        logger.info("Web3Manager imported successfully")
        
        logger.info("Importing DistributionManager...")
        from arbitrage_bot.core.distribution.manager import DistributionManager
        logger.info("DistributionManager imported successfully")
        
        # Create instances
        web3_manager = Web3Manager()
        dist_manager = DistributionManager(web3_manager)
        
        # Test initialization
        success = await dist_manager.initialize()
        logger.info(f"Initialization {'succeeded' if success else 'failed'}")
        
        # Cleanup
        await dist_manager.cleanup()
        logger.info("Cleanup completed")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())