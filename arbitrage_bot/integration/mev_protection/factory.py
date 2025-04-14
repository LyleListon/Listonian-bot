"""Factory for creating MEV protection services."""

import logging
from typing import Dict, Any, Optional

from arbitrage_bot.integration.mev_protection.base_protection import BaseMEVProtection
from arbitrage_bot.integration.mev_protection.flashbots_protection import FlashbotsProtection
from arbitrage_bot.integration.blockchain.base_connector import BaseBlockchainConnector

logger = logging.getLogger(__name__)


def create_mev_protection(
    provider_name: str,
    config: Dict[str, Any],
    blockchain_connectors: Dict[str, BaseBlockchainConnector],
) -> Optional[BaseMEVProtection]:
    """Create a MEV protection service.
    
    Args:
        provider_name: Name of the protection service.
        config: Configuration dictionary.
        blockchain_connectors: Dictionary mapping network names to blockchain connectors.
        
    Returns:
        A MEV protection service, or None if the provider is not supported.
    """
    # Get blockchain connector for Ethereum
    # Most MEV protection services are on Ethereum
    blockchain_connector = blockchain_connectors.get("ethereum")
    if not blockchain_connector:
        # Try to find any blockchain connector
        if blockchain_connectors:
            blockchain_connector = next(iter(blockchain_connectors.values()))
        else:
            logger.error("No blockchain connectors available")
            return None
    
    # Create protection service based on name
    if provider_name.lower() in ["flashbots", "flashbot"]:
        return FlashbotsProtection("flashbots", config, blockchain_connector)
    elif provider_name.lower() in ["mev_blocker", "mevblocker"]:
        # TODO: Implement MEV Blocker protection
        logger.warning(f"MEV Blocker protection not implemented yet")
        return None
    else:
        logger.warning(f"Unsupported MEV protection provider: {provider_name}")
        return None


def create_mev_protection_service(
    config: Dict[str, Any],
    blockchain_connectors: Dict[str, BaseBlockchainConnector],
) -> Optional[BaseMEVProtection]:
    """Create a MEV protection service based on configuration.
    
    Args:
        config: Configuration dictionary.
        blockchain_connectors: Dictionary mapping network names to blockchain connectors.
        
    Returns:
        A MEV protection service, or None if disabled or not configured.
    """
    # Get MEV protection configuration
    mev_protection_config = config.get("mev_protection", {})
    
    # Skip if MEV protection is disabled
    if not mev_protection_config.get("enabled", True):
        logger.info("MEV protection is disabled")
        return None
    
    # Get provider name
    provider_name = mev_protection_config.get("provider")
    if not provider_name:
        logger.warning("No MEV protection provider specified")
        return None
    
    # Get provider-specific configuration
    provider_config = mev_protection_config.get(provider_name.lower(), {})
    
    # Create protection service
    protection = create_mev_protection(provider_name, provider_config, blockchain_connectors)
    
    if protection:
        logger.info(f"Created MEV protection service: {provider_name}")
    else:
        logger.warning(f"Failed to create MEV protection service: {provider_name}")
    
    return protection
