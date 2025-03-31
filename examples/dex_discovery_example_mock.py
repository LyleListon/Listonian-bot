"""
DEX Discovery Example with Mock Web3 Manager (FOR TESTING ONLY)

This script demonstrates how to use the DEX discovery system to find and validate
DEXes on the Base network using a mock Web3 manager.

WARNING: This script is for testing and demonstration purposes only.
DO NOT use this in production as it creates mock data that could interfere
with real DEX discovery.
"""

import asyncio
import json
import logging
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arbitrage_bot.core.arbitrage.discovery import (
    DEXDiscoveryManager,
    create_dex_discovery_manager,
    DEXInfo,
    DEXProtocolType
)
from arbitrage_bot.utils.config_loader import load_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_mock_web3_manager():
    """Create a mock Web3 manager for testing."""
    mock = MagicMock()
    mock.w3 = MagicMock()
    mock.w3.is_address = lambda addr: True
    mock.w3.eth.get_code = AsyncMock(return_value=b'0x123456')
    
    # Create mock contract
    mock_contract = MagicMock()
    
    # Mock contract functions for validation
    mock_getPair = AsyncMock(return_value="0x1234567890123456789012345678901234567890")
    mock_allPairs = AsyncMock(return_value="0x1234567890123456789012345678901234567890")
    mock_allPairsLength = AsyncMock(return_value=10)
    mock_createPair = AsyncMock(return_value="0x1234567890123456789012345678901234567890")
    mock_swapExactTokensForTokens = AsyncMock(return_value="0x1234567890123456789012345678901234567890")
    mock_swapTokensForExactTokens = AsyncMock(return_value="0x1234567890123456789012345678901234567890")
    mock_addLiquidity = AsyncMock(return_value="0x1234567890123456789012345678901234567890")
    
    # Set up contract functions
    mock_contract.functions.getPair = MagicMock(return_value=MagicMock(call=mock_getPair))
    mock_contract.functions.allPairs = MagicMock(return_value=MagicMock(call=mock_allPairs))
    mock_contract.functions.allPairsLength = MagicMock(return_value=MagicMock(call=mock_allPairsLength))
    mock_contract.functions.createPair = MagicMock(return_value=MagicMock(call=mock_createPair))
    mock_contract.functions.swapExactTokensForTokens = MagicMock(return_value=MagicMock(call=mock_swapExactTokensForTokens))
    mock_contract.functions.swapTokensForExactTokens = MagicMock(return_value=MagicMock(call=mock_swapTokensForExactTokens))
    mock_contract.functions.addLiquidity = MagicMock(return_value=MagicMock(call=mock_addLiquidity))
    
    # Set up contract method
    mock.contract = MagicMock(return_value=mock_contract)
    
    # Set up initialize and close methods
    mock.initialize = AsyncMock(return_value=True)
    mock.close = AsyncMock()
    
    return mock


async def main():
    """Run the DEX discovery example."""
    # Load configuration
    config = load_config()
    
    # Create mock Web3 manager
    web3_manager = create_mock_web3_manager()
    
    # Create a temporary directory for testing
    temp_dir = "temp_test_data/dexes"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Create DEX discovery manager with temporary storage
    discovery_config = {
        "discovery_interval_seconds": 3600,  # 1 hour
        "auto_validate": True,
        "chain_id": 8453,  # Base chain ID
        "storage_dir": temp_dir,
        "storage_file": "test_dexes.json"
    }
    
    discovery_manager = await create_dex_discovery_manager(
        web3_manager=web3_manager,
        config=discovery_config
    )
    
    try:
        # Create a mock DEX
        mock_dex = DEXInfo(
            name="mock_dex",
            protocol_type=DEXProtocolType.UNISWAP_V2,
            version="v2",
            chain_id=8453,
            factory_address="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
            router_address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            source="mock"
        )
        
        # Add the mock DEX to the repository
        await discovery_manager.repository.add_dex(mock_dex)
        
        # Discover DEXes
        logger.info("Discovering DEXes...")
        dexes = await discovery_manager.discover_dexes()
        
        logger.info(f"Discovered {len(dexes)} DEXes")
        
        # Print DEX information
        for dex in dexes:
            logger.info(f"DEX: {dex.name}")
            logger.info(f"  Protocol: {dex.protocol_type.name}")
            logger.info(f"  Version: {dex.version}")
            logger.info(f"  Factory: {dex.factory_address}")
            logger.info(f"  Router: {dex.router_address}")
            logger.info(f"  Validated: {dex.validated}")
            if not dex.validated:
                logger.info(f"  Validation Errors: {dex.validation_errors}")
            logger.info("")
        
        # Get DEXes from repository
        repo_dexes = await discovery_manager.get_dexes()
        logger.info(f"Repository contains {len(repo_dexes)} DEXes")
        
        # Save DEX information to temporary file
        temp_output = os.path.join("temp_test_data", "discovered_dexes.json")
        os.makedirs(os.path.dirname(temp_output), exist_ok=True)
        with open(temp_output, "w") as f:
            json.dump([dex.to_dict() for dex in repo_dexes], f, indent=2)
        
        logger.info(f"DEX information saved to {temp_output}")
    
    finally:
        # Clean up resources
        await discovery_manager.cleanup()
        await web3_manager.close()
        
        # Clean up temporary files
        logger.info("Cleaning up temporary test files...")
        import shutil
        if os.path.exists("temp_test_data"):
            shutil.rmtree("temp_test_data")
        logger.info("Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())