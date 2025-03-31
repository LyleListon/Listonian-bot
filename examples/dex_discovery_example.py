"""
DEX Discovery Example

This script demonstrates how to use the DEX discovery system to find and validate
DEXes on the Base network.
"""

import asyncio
import json
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arbitrage_bot.core.arbitrage.discovery import (
    DEXDiscoveryManager,
    create_dex_discovery_manager,
    DEXInfo,
    DEXProtocolType
)
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.utils.config_loader import load_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run the DEX discovery example."""
    # Load configuration
    config = load_config()
    
    # Create Web3 manager
    web3_manager = await create_web3_manager(config["web3"])
    
    # Create DEX discovery manager
    discovery_config = {
        "discovery_interval_seconds": 3600,  # 1 hour
        "auto_validate": True,
        "chain_id": 8453,  # Base chain ID
        "storage_dir": "data/dexes",
        "storage_file": "dexes.json"
    }
    
    discovery_manager = await create_dex_discovery_manager(
        web3_manager=web3_manager,
        config=discovery_config
    )
    
    try:
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
        
        # Save DEX information to file
        os.makedirs("data", exist_ok=True)
        with open("data/discovered_dexes.json", "w") as f:
            json.dump([dex.to_dict() for dex in dexes], f, indent=2)
        
        logger.info("DEX information saved to data/discovered_dexes.json")
    
    finally:
        # Clean up resources
        await discovery_manager.cleanup()
        await web3_manager.close()


if __name__ == "__main__":
    asyncio.run(main())