"""Factory for creating DEX connectors."""

import logging
from typing import Dict, Any, List, Optional

from arbitrage_bot.integration.dex.base_connector import BaseDEXConnector
from arbitrage_bot.integration.dex.uniswap_v3_connector import UniswapV3Connector
from arbitrage_bot.integration.blockchain.base_connector import BaseBlockchainConnector

logger = logging.getLogger(__name__)


def create_dex_connector(
    dex_name: str,
    network: str,
    config: Dict[str, Any],
    blockchain_connectors: Dict[str, BaseBlockchainConnector],
) -> Optional[BaseDEXConnector]:
    """Create a DEX connector.
    
    Args:
        dex_name: Name of the DEX.
        network: Network the DEX is on.
        config: Configuration dictionary.
        blockchain_connectors: Dictionary mapping network names to blockchain connectors.
        
    Returns:
        A DEX connector, or None if the DEX is not supported.
    """
    # Get blockchain connector for the network
    blockchain_connector = blockchain_connectors.get(network)
    if not blockchain_connector:
        logger.error(f"No blockchain connector found for network {network}")
        return None
    
    # Create connector based on DEX name
    if dex_name.lower() in ["uniswap_v3", "uniswap", "uni_v3"]:
        return UniswapV3Connector("uniswap_v3", network, config, blockchain_connector)
    elif dex_name.lower() in ["pancakeswap", "pancake", "cake"]:
        # TODO: Implement PancakeSwap connector
        logger.warning(f"PancakeSwap connector not implemented yet")
        return None
    elif dex_name.lower() in ["sushiswap", "sushi"]:
        # TODO: Implement SushiSwap connector
        logger.warning(f"SushiSwap connector not implemented yet")
        return None
    else:
        logger.warning(f"Unsupported DEX: {dex_name}")
        return None


def create_all_dex_connectors(
    config: Dict[str, Any],
    blockchain_connectors: Dict[str, BaseBlockchainConnector],
) -> List[BaseDEXConnector]:
    """Create all enabled DEX connectors.
    
    Args:
        config: Configuration dictionary.
        blockchain_connectors: Dictionary mapping network names to blockchain connectors.
        
    Returns:
        List of DEX connectors.
    """
    connectors = []
    
    # Get DEX configuration
    dexes = config.get("dexes", [])
    
    for dex_config in dexes:
        dex_name = dex_config.get("name")
        network = dex_config.get("network")
        
        if not dex_name or not network:
            continue
        
        # Skip disabled DEXes
        if not dex_config.get("enabled", True):
            logger.info(f"Skipping disabled DEX: {dex_name} on {network}")
            continue
        
        # Create connector
        connector = create_dex_connector(dex_name, network, dex_config, blockchain_connectors)
        if connector:
            connectors.append(connector)
    
    logger.info(f"Created {len(connectors)} DEX connectors")
    return connectors
