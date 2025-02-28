"""
Balance Allocator Module

This module dynamically allocates trading amounts based on available wallet balance.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

class BalanceAllocator:
    """Dynamically allocates trading amounts based on available wallet balance."""
    
    def __init__(self, web3_manager, config: Dict[str, Any]):
        """
        Initialize the BalanceAllocator.
        
        Args:
            web3_manager: Web3Manager instance for checking balances
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        
        # Get allocation config
        allocation_config = config.get('dynamic_allocation', {})
        
        # Set properties from config with sensible defaults
        self.enabled = allocation_config.get('enabled', True)
        
        # Minimum trade size as percentage of available balance
        self.min_percentage = allocation_config.get('min_percentage', 5)  # Default 5%
        
        # Maximum trade size as percentage of available balance
        self.max_percentage = allocation_config.get('max_percentage', 50)  # Default 50%
        
        # Absolute minimum trade size in ETH to ensure profitability (gas costs)
        self.absolute_min_eth = allocation_config.get('absolute_min_eth', 0.05)
        
        # Absolute maximum trade size in ETH to limit risk
        self.absolute_max_eth = allocation_config.get('absolute_max_eth', 10.0)
        
        # How many concurrent trades to allow (divides max allocation)
        self.concurrent_trades = allocation_config.get('concurrent_trades', 2)
        
        # Reserve percentage to keep in wallet (e.g., for gas)
        self.reserve_percentage = allocation_config.get('reserve_percentage', 10)  # Default 10%
        
        logger.info("BalanceAllocator initialized")
        logger.info("Dynamic allocation enabled: %s", self.enabled)
    
    async def get_allocation_range(self, token_address: str) -> Tuple[int, int]:
        """
        Get the minimum and maximum allocation amounts for a token based on current balance.
        
        Args:
            token_address: Address of the token to allocate
            
        Returns:
            Tuple of (min_amount, max_amount) in wei
        """
        if not self.enabled:
            # Return default values if dynamic allocation is disabled
            return (
                self.web3_manager.w3.to_wei(self.absolute_min_eth, 'ether'),
                self.web3_manager.w3.to_wei(self.absolute_max_eth, 'ether')
            )
        
        # Check if token is ETH/WETH or other token
        # For simplicity, we'll focus on ETH/WETH here
        is_eth = token_address.lower() in [
            '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'.lower(),  # WETH mainnet
            '0x4200000000000000000000000000000000000006'.lower()   # WETH optimism
        ]
        
        if is_eth:
            # Get ETH balance
            balance_wei = await self.web3_manager.get_balance()
            logger.info("Current ETH balance: %s wei", balance_wei)
            
            # Convert to Decimal for precise calculations
            balance_eth = Decimal(self.web3_manager.w3.from_wei(balance_wei, 'ether'))
            
            # Calculate available balance (after reserve)
            available_eth = balance_eth * (100 - self.reserve_percentage) / 100
            
            # Calculate min and max allocations as percentages of available balance
            min_eth = max(
                available_eth * self.min_percentage / 100,
                Decimal(self.absolute_min_eth)  # Ensure at least absolute minimum
            )
            
            # Max amount considers concurrent trades
            max_eth = min(
                available_eth * self.max_percentage / 100 / self.concurrent_trades,
                Decimal(self.absolute_max_eth)  # Ensure at most absolute maximum
            )
            
            logger.info("Dynamic allocation range: %.6f ETH to %.6f ETH", min_eth, max_eth)
            
            # Convert back to wei
            min_wei = self.web3_manager.w3.to_wei(min_eth, 'ether')
            max_wei = self.web3_manager.w3.to_wei(max_eth, 'ether')
            
            return (min_wei, max_wei)
        else:
            # For other tokens, we'd need to check ERC20 balances
            # For now, return default values
            return (
                self.web3_manager.w3.to_wei(self.absolute_min_eth, 'ether'),
                self.web3_manager.w3.to_wei(self.absolute_max_eth, 'ether')
            )
    
    async def adjust_amount_to_limits(self, token_address: str, amount: int) -> int:
        """
        Adjust an amount to be within the current allocation limits.
        
        Args:
            token_address: Address of the token
            amount: Proposed amount in wei
            
        Returns:
            Adjusted amount in wei within allocation limits
        """
        min_amount, max_amount = await self.get_allocation_range(token_address)
        
        if amount < min_amount:
            logger.info("Adjusting amount up to minimum: %s wei", min_amount)
            return min_amount
        
        if amount > max_amount:
            logger.info("Adjusting amount down to maximum: %s wei", max_amount)
            return max_amount
        
        return amount


async def create_balance_allocator(web3_manager, config: Dict[str, Any]) -> BalanceAllocator:
    """
    Create and initialize a BalanceAllocator instance.
    
    Args:
        web3_manager: Web3Manager instance
        config: Configuration dictionary
        
    Returns:
        Initialized BalanceAllocator instance
    """
    # Create BalanceAllocator
    allocator = BalanceAllocator(web3_manager, config)
    
    return allocator