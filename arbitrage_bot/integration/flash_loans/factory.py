"""Factory for creating flash loan providers."""

import logging
from typing import Dict, Any, List, Optional

from arbitrage_bot.integration.flash_loans.base_provider import BaseFlashLoanProvider
from arbitrage_bot.integration.flash_loans.aave_provider import AaveFlashLoanProvider
from arbitrage_bot.integration.blockchain.base_connector import BaseBlockchainConnector

logger = logging.getLogger(__name__)


def create_flash_loan_provider(
    provider_name: str,
    network: str,
    config: Dict[str, Any],
    blockchain_connectors: Dict[str, BaseBlockchainConnector],
) -> Optional[BaseFlashLoanProvider]:
    """Create a flash loan provider.
    
    Args:
        provider_name: Name of the provider.
        network: Network the provider is on.
        config: Configuration dictionary.
        blockchain_connectors: Dictionary mapping network names to blockchain connectors.
        
    Returns:
        A flash loan provider, or None if the provider is not supported.
    """
    # Get blockchain connector for the network
    blockchain_connector = blockchain_connectors.get(network)
    if not blockchain_connector:
        logger.error(f"No blockchain connector found for network {network}")
        return None
    
    # Create provider based on name
    if provider_name.lower() in ["aave", "aave_v3"]:
        return AaveFlashLoanProvider("aave", network, config, blockchain_connector)
    elif provider_name.lower() in ["dydx", "dydx_solo"]:
        # TODO: Implement dYdX provider
        logger.warning(f"dYdX flash loan provider not implemented yet")
        return None
    else:
        logger.warning(f"Unsupported flash loan provider: {provider_name}")
        return None


def create_all_flash_loan_providers(
    config: Dict[str, Any],
    blockchain_connectors: Dict[str, BaseBlockchainConnector],
) -> Dict[str, BaseFlashLoanProvider]:
    """Create all enabled flash loan providers.
    
    Args:
        config: Configuration dictionary.
        blockchain_connectors: Dictionary mapping network names to blockchain connectors.
        
    Returns:
        Dictionary mapping provider names to flash loan providers.
    """
    providers = {}
    
    # Get flash loan configuration
    flash_loans_config = config.get("flash_loans", {})
    
    # Skip if flash loans are disabled
    if not flash_loans_config.get("enabled", True):
        logger.info("Flash loans are disabled")
        return providers
    
    # Create providers
    provider_configs = flash_loans_config.get("providers", [])
    
    for provider_config in provider_configs:
        provider_name = provider_config.get("name")
        network = provider_config.get("network")
        
        if not provider_name or not network:
            continue
        
        # Skip disabled providers
        if not provider_config.get("enabled", True):
            logger.info(f"Skipping disabled flash loan provider: {provider_name} on {network}")
            continue
        
        # Create provider
        provider = create_flash_loan_provider(
            provider_name, network, provider_config, blockchain_connectors
        )
        if provider:
            providers[provider_name] = provider
    
    logger.info(f"Created {len(providers)} flash loan providers")
    return providers
