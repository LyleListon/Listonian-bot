"""
DEX Discovery Integration

This module provides integration between the DEX discovery system and the
existing arbitrage system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from ..interfaces import OpportunityDiscoveryManager
from ...dex.dex_manager import DexManager
from ...web3.web3_manager import Web3Manager
from .sources.manager import DEXDiscoveryManager, create_dex_discovery_manager

logger = logging.getLogger(__name__)


async def integrate_dex_discovery(
    discovery_manager: OpportunityDiscoveryManager,
    dex_manager: DexManager,
    web3_manager: Web3Manager,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Integrate DEX discovery with the existing arbitrage system.

    This function discovers DEXes using the DEX discovery system and adds them
    to the existing DexManager.

    Args:
        discovery_manager: Opportunity discovery manager
        dex_manager: DEX manager
        web3_manager: Web3 manager
        config: Configuration dictionary
    """
    logger.info("Integrating DEX discovery with arbitrage system")

    # Create DEX discovery manager
    dex_discovery_config = config.get("dex_discovery", {})
    dex_discovery_manager = await create_dex_discovery_manager(
        web3_manager=web3_manager, config=dex_discovery_config
    )

    try:
        # Discover DEXes
        logger.info("Discovering DEXes...")
        dexes = await dex_discovery_manager.discover_dexes()

        logger.info(f"Discovered {len(dexes)} DEXes")

        # Add DEXes to DexManager
        added_count = 0
        for dex in dexes:
            # Skip invalid DEXes
            if not dex.validated:
                logger.warning(
                    f"Skipping invalid DEX {dex.name}: {dex.validation_errors}"
                )
                continue

            # Skip DEXes that are already in DexManager
            if dex.name in dex_manager.dexes:
                logger.debug(f"DEX {dex.name} already in DexManager")
                continue

            try:
                # Add DEX to DexManager
                dex_config = {
                    "factory": dex.factory_address,
                    "router": dex.router_address,
                    "fee_tiers": dex.fee_tiers,
                    "version": dex.version,
                }

                # Add quoter if available
                if dex.quoter_address:
                    dex_config["quoter"] = dex.quoter_address

                # Add DEX to DexManager
                await dex_manager.add_dex(dex.name, dex_config)
                added_count += 1

                logger.info(f"Added DEX {dex.name} to DexManager")

            except Exception as e:
                logger.error(f"Error adding DEX {dex.name} to DexManager: {e}")

        logger.info(f"Added {added_count} new DEXes to DexManager")

    finally:
        # Clean up resources
        await dex_discovery_manager.cleanup()


async def setup_dex_discovery(
    dex_manager: DexManager,
    web3_manager: Web3Manager,
    config: Optional[Dict[str, Any]] = None,
) -> DEXDiscoveryManager:
    """
    Set up DEX discovery.

    This function creates and initializes a DEX discovery manager and starts
    periodic discovery.

    Args:
        dex_manager: DEX manager
        web3_manager: Web3 manager
        config: Configuration dictionary

    Returns:
        Initialized DEX discovery manager
    """
    logger.info("Setting up DEX discovery")

    # Create DEX discovery manager
    dex_discovery_config = config.get("dex_discovery", {})
    dex_discovery_manager = await create_dex_discovery_manager(
        web3_manager=web3_manager, config=dex_discovery_config
    )

    # Start periodic discovery
    await dex_discovery_manager.start_discovery()

    # Set up callback to add new DEXes to DexManager
    async def on_discovery_complete(dexes: List[Any]) -> None:
        """Callback for when discovery completes."""
        # Add DEXes to DexManager
        added_count = 0
        for dex in dexes:
            # Skip invalid DEXes
            if not dex.validated:
                continue

            # Skip DEXes that are already in DexManager
            if dex.name in dex_manager.dexes:
                continue

            try:
                # Add DEX to DexManager
                dex_config = {
                    "factory": dex.factory_address,
                    "router": dex.router_address,
                    "fee_tiers": dex.fee_tiers,
                    "version": dex.version,
                }

                # Add quoter if available
                if dex.quoter_address:
                    dex_config["quoter"] = dex.quoter_address

                # Add DEX to DexManager
                await dex_manager.add_dex(dex.name, dex_config)
                added_count += 1

                logger.info(f"Added DEX {dex.name} to DexManager")

            except Exception as e:
                logger.error(f"Error adding DEX {dex.name} to DexManager: {e}")

        if added_count > 0:
            logger.info(f"Added {added_count} new DEXes to DexManager")

    # Register callback
    # Note: This is a placeholder since the current implementation doesn't have a callback mechanism
    # In a real implementation, we would register this callback with the discovery manager

    return dex_discovery_manager
