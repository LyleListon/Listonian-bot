"""
Test using importlib for dynamic imports.
"""

import os
import sys
import asyncio
import logging
import importlib.util
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def import_module(module_path, module_name):
    """Import a module from file path."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            raise ImportError(f"Could not find module spec for {module_path}")
            
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            raise ImportError(f"Could not find module loader for {module_path}")
            
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Failed to import {module_path}: {e}")
        raise

async def main():
    try:
        # Import modules using importlib
        base_path = os.path.join(os.path.dirname(__file__), 'arbitrage_bot', 'core')
        
        web3_path = os.path.join(base_path, 'web3', 'web3_manager.py')
        web3_module = import_module(web3_path, 'web3_manager')
        Web3Manager = web3_module.Web3Manager
        logger.info("Imported Web3Manager")
        
        dist_path = os.path.join(base_path, 'distribution', 'manager.py')
        dist_module = import_module(dist_path, 'distribution_manager')
        DistributionManager = dist_module.DistributionManager
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