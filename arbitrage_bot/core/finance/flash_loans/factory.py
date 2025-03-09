"""
Flash Loan Provider Factory

This module contains factory functions for creating flash loan provider instances
based on configuration parameters and implementing intelligent provider selection
to maximize profitability.
"""

import logging
from typing import Dict, List, Any, Optional, Type, cast
import asyncio

from ....core.web3.interfaces import Web3Client
from .interfaces import FlashLoanProvider, TokenAmount
from decimal import Decimal

logger = logging.getLogger(__name__)


async def create_flash_loan_provider(
    provider_type: str,
    web3_client: Web3Client,
    config: Optional[Dict[str, Any]] = None
) -> FlashLoanProvider:
    """
    Create a flash loan provider based on the given type.
    
    Args:
        provider_type: Type of flash loan provider to create
            (e.g. "balancer", "aave", etc.)
        web3_client: Web3 client to use for provider
        config: Configuration parameters for the provider
        
    Returns:
        Initialized flash loan provider
        
    Raises:
        ValueError: If the provider type is not supported
    """
    config = config or {}
    provider_type = provider_type.lower()
    
    logger.info(f"Creating flash loan provider of type: {provider_type}")
    
    # Import specific providers here to avoid circular imports
    if provider_type == "balancer":
        from .providers.balancer import BalancerFlashLoanProvider
        provider = BalancerFlashLoanProvider(web3_client, config)
    elif provider_type == "aave":
        from .providers.aave import AaveFlashLoanProvider
        provider = AaveFlashLoanProvider(web3_client, config)
    else:
        raise ValueError(f"Unsupported flash loan provider type: {provider_type}")
    
    # Initialize the provider
    await provider.initialize()
    
    return cast(FlashLoanProvider, provider)


async def get_all_provider_types() -> List[str]:
    """
    Get a list of all supported flash loan provider types.
    
    Returns:
        List of supported provider types
    """
    return ["balancer", "aave"]


async def get_best_provider(
    web3_client: Web3Client,
    token_address: str,
    amount: Decimal,
    config: Optional[Dict[str, Any]] = None
) -> FlashLoanProvider:
    """
    Get the best flash loan provider for the given token and amount.
    
    This function selects the optimal provider based on fees, liquidity,
    and availability. It prioritizes:
    1. Balancer (zero fees) if there's sufficient liquidity
    2. Aave as a fallback (higher liquidity but 0.09% fee)
    
    Args:
        web3_client: Web3 client to use for providers
        token_address: Address of the token to borrow
        amount: Amount to borrow
        config: Configuration for flash loan providers
        
    Returns:
        Best flash loan provider for the token
        
    Raises:
        ValueError: If no suitable provider is found
    """
    config = config or {}
    all_types = await get_all_provider_types()
    balancer_config = config.get("balancer", {})
    aave_config = config.get("aave", {})
    
    # Try Balancer first (zero fees = higher profits)
    try:
        logger.info(f"Attempting to use Balancer as primary flash loan provider for {token_address}")
        balancer = await create_flash_loan_provider("balancer", web3_client, balancer_config)
        
        # Check if token has enough liquidity in Balancer
        if await balancer.check_liquidity(token_address, amount):
            logger.info(f"Selected Balancer as flash loan provider for {token_address} (sufficient liquidity)")
            return balancer
        else:
            logger.warning(f"Balancer has insufficient liquidity for {token_address}, amount {amount}")
            # Don't close the provider yet, we may use it for other tokens
    except Exception as e:
        logger.warning(f"Failed to create or use Balancer provider: {e}")
    
    # Try Aave as fallback
    try:
        logger.info(f"Attempting to use Aave as fallback flash loan provider for {token_address}")
        aave = await create_flash_loan_provider("aave", web3_client, aave_config)
        
        # Check if token has enough liquidity in Aave
        if await aave.check_liquidity(token_address, amount):
            logger.info(f"Selected Aave as flash loan provider for {token_address} (sufficient liquidity)")
            return aave
        else:
            logger.warning(f"Aave has insufficient liquidity for {token_address}, amount {amount}")
    except Exception as e:
        logger.warning(f"Failed to create or use Aave provider: {e}")
    
    # No provider with sufficient liquidity found
    raise ValueError(f"No flash loan provider with sufficient liquidity for token {token_address}, amount {amount}")


async def create_providers_for_token_amounts(
    web3_client: Web3Client,
    token_amounts: List[TokenAmount],
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, FlashLoanProvider]:
    """
    Create optimal flash loan providers for a list of token amounts.
    
    This function analyzes which provider is best for each token and returns
    a mapping of token addresses to the most suitable providers.
    
    Args:
        web3_client: Web3 client to use
        token_amounts: List of token amounts to borrow
        config: Provider configurations
        
    Returns:
        Dictionary mapping token addresses to providers
    """
    providers = {}
    config = config or {}
    
    for token_amount in token_amounts:
        token_address = token_amount.token_address
        amount = token_amount.amount
        
        if token_address not in providers:
            try:
                provider = await get_best_provider(web3_client, token_address, amount, config)
                providers[token_address] = provider
            except ValueError as e:
                logger.error(f"No suitable provider for {token_address}: {e}")
                # Continue with other tokens
    
    return providers


async def get_optimal_multi_token_provider(
    web3_client: Web3Client,
    token_amounts: List[TokenAmount],
    config: Optional[Dict[str, Any]] = None
) -> Optional[FlashLoanProvider]:
    """
    Find the optimal provider for a multi-token flash loan.
    
    When borrowing multiple tokens in a single flash loan, we need a provider
    that supports all tokens with sufficient liquidity. This function tries to
    find the best provider that can handle all tokens.
    
    Priority:
    1. Balancer (if it supports all tokens with sufficient liquidity)
    2. Aave (if Balancer doesn't support all tokens)
    
    Args:
        web3_client: Web3 client to use
        token_amounts: List of token amounts to borrow
        config: Provider configurations
        
    Returns:
        Optimal provider for all tokens or None if no single provider works
    """
    config = config or {}
    balancer_config = config.get("balancer", {})
    aave_config = config.get("aave", {})
    
    # Try Balancer first (zero fees)
    try:
        balancer = await create_flash_loan_provider("balancer", web3_client, balancer_config)
        all_supported = True
        
        # Check all tokens
        for token_amount in token_amounts:
            if not await balancer.check_liquidity(token_amount.token_address, token_amount.amount):
                all_supported = False
                logger.info(f"Balancer cannot provide {token_amount.token_address} "
                           f"with amount {token_amount.amount}")
                break
        
        if all_supported:
            logger.info("Balancer can support all requested tokens - using as primary provider")
            return balancer
        else:
            await balancer.close()
    except Exception as e:
        logger.warning(f"Failed to create or use Balancer provider: {e}")
    
    # Try Aave as fallback
    try:
        aave = await create_flash_loan_provider("aave", web3_client, aave_config)
        all_supported = True
        
        # Check all tokens
        for token_amount in token_amounts:
            if not await aave.check_liquidity(token_amount.token_address, token_amount.amount):
                all_supported = False
                logger.info(f"Aave cannot provide {token_amount.token_address} "
                           f"with amount {token_amount.amount}")
                break
        
        if all_supported:
            logger.info("Aave can support all requested tokens - using as fallback provider")
            return aave
        else:
            await aave.close()
    except Exception as e:
        logger.warning(f"Failed to create or use Aave provider: {e}")
    
    logger.error("No single provider can support all requested tokens")
    return None


async def estimate_flash_loan_cost(
    web3_client: Web3Client,
    token_address: str,
    amount: Decimal,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Decimal]:
    """
    Estimate the cost of a flash loan across different providers.
    
    This function calculates the fee cost for borrowing the specified
    token and amount across all available providers, to help with
    provider selection and profit calculation.
    
    Args:
        web3_client: Web3 client to use
        token_address: Address of the token to borrow
        amount: Amount to borrow
        config: Configuration for providers
        
    Returns:
        Dictionary mapping provider names to fee costs
    """
    config = config or {}
    costs = {}
    provider_types = await get_all_provider_types()
    
    for provider_type in provider_types:
        try:
            provider_config = config.get(provider_type, {})
            provider = await create_flash_loan_provider(provider_type, web3_client, provider_config)
            
            # Get fee percentage
            fee_pct = await provider.get_flash_loan_fee(token_address, amount)
            
            # Calculate fee cost
            fee_cost = amount * fee_pct
            
            # Add to costs dictionary
            costs[provider.name] = fee_cost
            
            # Close provider
            await provider.close()
            
        except Exception as e:
            logger.warning(f"Failed to estimate cost for {provider_type}: {e}")
    
    return costs