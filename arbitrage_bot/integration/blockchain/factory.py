"""Factory for creating blockchain connectors."""

import logging
from typing import Dict, Any, Optional

from arbitrage_bot.integration.blockchain.base_connector import BaseBlockchainConnector
from arbitrage_bot.integration.blockchain.ethereum_connector import EthereumConnector

logger = logging.getLogger(__name__)


def create_blockchain_connector(
    network_name: str, config: Dict[str, Any]
) -> Optional[BaseBlockchainConnector]:
    """Create a blockchain connector.
    
    Args:
        network_name: Name of the blockchain network.
        config: Configuration dictionary.
        
    Returns:
        A blockchain connector, or None if the network is not supported.
    """
    # Get network configuration
    network_config = None
    
    # Check if network_name is a direct config
    if isinstance(config, dict):
        network_config = config
    else:
        # Look for network in blockchain.networks
        blockchain_config = config.get("blockchain", {})
        networks = blockchain_config.get("networks", [])
        
        for network in networks:
            if network.get("name") == network_name:
                network_config = network
                break
    
    if not network_config:
        logger.error(f"No configuration found for network {network_name}")
        return None
    
    # Check if network is enabled
    if not network_config.get("enabled", True):
        logger.warning(f"Network {network_name} is disabled")
        return None
    
    # Create connector based on network name
    if network_name.lower() in ["ethereum", "eth", "mainnet"]:
        return EthereumConnector("ethereum", network_config)
    elif network_name.lower() in ["bsc", "binance", "binance_smart_chain"]:
        return EthereumConnector("bsc", network_config)
    elif network_name.lower() in ["base"]:
        return EthereumConnector("base", network_config)
    elif network_name.lower() in ["polygon", "matic"]:
        return EthereumConnector("polygon", network_config)
    elif network_name.lower() in ["arbitrum", "arbitrum_one"]:
        return EthereumConnector("arbitrum", network_config)
    elif network_name.lower() in ["optimism"]:
        return EthereumConnector("optimism", network_config)
    elif network_name.lower() in ["avalanche", "avax"]:
        return EthereumConnector("avalanche", network_config)
    else:
        logger.warning(f"Unsupported network: {network_name}")
        return None


def create_all_blockchain_connectors(
    config: Dict[str, Any]
) -> Dict[str, BaseBlockchainConnector]:
    """Create all enabled blockchain connectors.
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        Dictionary mapping network names to blockchain connectors.
    """
    connectors = {}
    
    # Get blockchain configuration
    blockchain_config = config.get("blockchain", {})
    networks = blockchain_config.get("networks", [])
    
    for network in networks:
        network_name = network.get("name")
        if not network_name:
            continue
        
        # Skip disabled networks
        if not network.get("enabled", True):
            logger.info(f"Skipping disabled network: {network_name}")
            continue
        
        # Create connector
        connector = create_blockchain_connector(network_name, network)
        if connector:
            connectors[network_name] = connector
    
    logger.info(f"Created {len(connectors)} blockchain connectors")
    return connectors
