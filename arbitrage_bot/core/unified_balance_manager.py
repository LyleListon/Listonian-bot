"""
Unified Balance Manager Module

This module provides a consolidated solution for tracking balances and allocating 
trading amounts. It combines features from the BalanceManager and BalanceAllocator
into a single unified implementation.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple, List, Union
from decimal import Decimal
from web3 import Web3

logger = logging.getLogger(__name__)

class UnifiedBalanceManager:
    """
    Unified manager for tracking balances and allocating trading amounts.
    
    This class consolidates functionality from BalanceManager and BalanceAllocator
    into a single implementation that tracks token balances and determines
    appropriate trading sizes based on available funds.
    """
    
    _instance = None
    
    def __init__(
        self,
        web3_manager,
        dex_manager=None,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the UnifiedBalanceManager.
        
        Args:
            web3_manager: Web3Manager instance for blockchain interactions
            dex_manager: DexManager instance for DEX interactions (optional)
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.config = config or {}
        
        # Balance tracking
        self.balances = {}
        self.running = False
        self._tasks = set()  # Set of asyncio.Task
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()  # For thread safety
        
        # Allocation configuration
        allocation_config = self.config.get('dynamic_allocation', {})
        
        # Set allocation properties from config with sensible defaults
        self.allocation_enabled = allocation_config.get('enabled', True)
        self.min_percentage = allocation_config.get('min_percentage', 5)  # Default 5%
        self.max_percentage = allocation_config.get('max_percentage', 50)  # Default 50%
        self.absolute_min_eth = allocation_config.get('absolute_min_eth', 0.05)
        self.absolute_max_eth = allocation_config.get('absolute_max_eth', 10.0)
        self.concurrent_trades = allocation_config.get('concurrent_trades', 2)
        self.reserve_percentage = allocation_config.get('reserve_percentage', 10)  # Default 10%
        
        # Set update interval for balance tracking
        self.update_interval = self.config.get('balance_update_interval', 60)  # Default 60s
        
        # Cache of token contracts
        self._token_contracts = {}
        
        # Known token addresses (ETH/WETH)
        self.token_addresses = {}
        for token_symbol, token_data in self.config.get('tokens', {}).items():
            if isinstance(token_data, dict) and 'address' in token_data:
                self.token_addresses[token_symbol.lower()] = token_data['address'].lower()
        
        logger.info("UnifiedBalanceManager initialized")
        logger.info("Dynamic allocation enabled: %s", self.allocation_enabled)
    
    @classmethod
    async def get_instance(
        cls,
        web3_manager=None,
        dex_manager=None,
        config: Optional[Dict[str, Any]] = None
    ) -> 'UnifiedBalanceManager':
        """
        Get or create singleton instance.
        
        Args:
            web3_manager: Web3Manager instance
            dex_manager: DexManager instance
            config: Configuration dictionary
            
        Returns:
            Singleton UnifiedBalanceManager instance
        """
        async with asyncio.Lock():
            if not cls._instance:
                if not web3_manager:
                    raise ValueError("web3_manager is required")
                if not config:
                    # Import here to avoid circular imports
                    from ...utils.config_loader import load_config
                    config = load_config()
                
                cls._instance = cls(web3_manager, dex_manager, config)
                logger.info("UnifiedBalanceManager instance created successfully")
                # Start balance updates in a task to avoid blocking
                asyncio.create_task(cls._instance.start())
            return cls._instance
    
    @classmethod
    def get_instance_sync(
        cls,
        web3_manager=None,
        dex_manager=None,
        config: Optional[Dict[str, Any]] = None
    ) -> 'UnifiedBalanceManager':
        """
        Get or create singleton instance synchronously.
        
        Args:
            web3_manager: Web3Manager instance
            dex_manager: DexManager instance
            config: Configuration dictionary
            
        Returns:
            Singleton UnifiedBalanceManager instance
        """
        # Run the async method in the event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(cls.get_instance(web3_manager, dex_manager, config))
    
    # ======== Balance Tracking Methods ========
    
    async def start(self):
        """Start balance updates."""
        async with self._lock:
            if self.running:
                return
            
            self.running = True
            self._shutdown_event.clear()
            
            # Create update task
            update_task = asyncio.create_task(self._periodic_updates())
            self._tasks.add(update_task)
            update_task.add_done_callback(self._tasks.discard)
            
            logger.info("Balance tracking started")
    
    def start_sync(self):
        """Start balance updates synchronously."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.start())
    
    async def stop(self):
        """Stop balance updates."""
        async with self._lock:
            if not self.running:
                return
            
            # Signal shutdown
            self._shutdown_event.set()
            self.running = False
            
            # Cancel all tasks
            for task in self._tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
            
            logger.info("Balance tracking stopped")
    
    def stop_sync(self):
        """Stop balance updates synchronously."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.stop())
    
    async def _periodic_updates(self):
        """Periodically update balances."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    await self._update_balances()
                    
                    # Wait before next update
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.update_interval
                        )
                    except asyncio.TimeoutError:
                        continue
                    
                except Exception as e:
                    logger.error("Error in update loop: %s", str(e))
                    await asyncio.sleep(5)  # Wait before retry
                    
        except asyncio.CancelledError:
            logger.info("Update task cancelled")
        except Exception as e:
            logger.error("Fatal error in update task: %s", str(e))
    
    async def _update_balances(self):
        """Update token balances."""
        async with self._lock:
            try:
                # Update ETH balance
                eth_balance = await self.web3_manager.get_balance()
                self.balances['ETH'] = eth_balance
                
                # Update token balances
                for token_symbol, token_data in self.config.get('tokens', {}).items():
                    if isinstance(token_data, dict) and 'address' in token_data:
                        if token_symbol == 'ETH':
                            continue
                        
                        try:
                            token_address = Web3.to_checksum_address(token_data['address'])
                            token_contract = await self._get_token_contract(token_address)
                            
                            if token_contract:
                                try:
                                    balance = await self.web3_manager.call_contract_function(
                                        token_contract.functions.balanceOf,
                                        self.web3_manager.wallet_address
                                    )
                                    self.balances[token_symbol] = balance
                                except Exception as e:
                                    logger.error("Failed to call balanceOf for %s: %s", token_symbol, str(e))
                            else:
                                logger.warning("Failed to get contract for token %s", token_symbol)
                                
                        except Exception as e:
                            logger.error("Failed to update balance for %s: %s", token_symbol, str(e))
                
            except Exception as e:
                logger.error("Error updating balances: %s", str(e))
    
    async def _get_token_contract(self, token_address: str):
        """Get token contract instance with caching."""
        token_address = token_address.lower()
        if token_address not in self._token_contracts:
            try:
                contract = self.web3_manager.get_token_contract(token_address)
                self._token_contracts[token_address] = contract
                return contract
            except Exception as e:
                logger.error("Failed to get token contract for %s: %s", token_address, str(e))
                return None
        
        return self._token_contracts[token_address]
    
    async def get_balance(self, token_symbol: str) -> Optional[int]:
        """
        Get balance for a token.
        
        Args:
            token_symbol: Symbol of the token
            
        Returns:
            Balance in wei or None if not available
        """
        # Force update if no balance is available
        if token_symbol not in self.balances:
            await self._update_balances()
        
        return self.balances.get(token_symbol)
    
    def get_balance_sync(self, token_symbol: str) -> Optional[int]:
        """
        Get balance for a token synchronously.
        
        Args:
            token_symbol: Symbol of the token
            
        Returns:
            Balance in wei or None if not available
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_balance(token_symbol))
    
    async def get_all_balances(self) -> Dict[str, int]:
        """
        Get all token balances.
        
        Returns:
            Dictionary of token balances
        """
        return self.balances.copy()
    
    def get_all_balances_sync(self) -> Dict[str, int]:
        """
        Get all token balances synchronously.
        
        Returns:
            Dictionary of token balances
        """
        return self.balances.copy()
    
    async def check_balance(self, token_symbol: str, amount: int) -> bool:
        """
        Check if balance is sufficient for amount.
        
        Args:
            token_symbol: Symbol of the token
            amount: Amount to check in wei
            
        Returns:
            True if balance is sufficient
        """
        try:
            balance = await self.get_balance(token_symbol)
            if balance is None:
                return False
            return balance >= amount
        except Exception as e:
            logger.error("Failed to check balance: %s", str(e))
            return False
    
    def check_balance_sync(self, token_symbol: str, amount: int) -> bool:
        """
        Check if balance is sufficient for amount synchronously.
        
        Args:
            token_symbol: Symbol of the token
            amount: Amount to check in wei
            
        Returns:
            True if balance is sufficient
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.check_balance(token_symbol, amount))
    
    async def get_formatted_balance(self, token_symbol: str) -> Optional[Decimal]:
        """
        Get formatted balance with decimals.
        
        Args:
            token_symbol: Symbol of the token
            
        Returns:
            Decimal balance or None if not available
        """
        try:
            balance = await self.get_balance(token_symbol)
            if balance is None:
                return None
            
            token_data = self.config.get('tokens', {}).get(token_symbol)
            if not token_data:
                return None
            
            decimals = token_data.get('decimals', 18)
            return Decimal(balance) / Decimal(10 ** decimals)
            
        except Exception as e:
            logger.error("Failed to get formatted balance: %s", str(e))
            return None
    
    def get_formatted_balance_sync(self, token_symbol: str) -> Optional[Decimal]:
        """
        Get formatted balance with decimals synchronously.
        
        Args:
            token_symbol: Symbol of the token
            
        Returns:
            Decimal balance or None if not available
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_formatted_balance(token_symbol))
    
    # ======== Allocation Methods ========
    
    async def get_allocation_range(self, token_address: str) -> Tuple[int, int]:
        """
        Get the minimum and maximum allocation amounts for a token based on current balance.
        
        Args:
            token_address: Address of the token to allocate
            
        Returns:
            Tuple of (min_amount, max_amount) in wei
        """
        if not self.allocation_enabled:
            # Return default values if dynamic allocation is disabled
            return (
                self.web3_manager.w3.to_wei(self.absolute_min_eth, 'ether'),
                self.web3_manager.w3.to_wei(self.absolute_max_eth, 'ether')
            )
        
        # Check if token is ETH/WETH or other token
        is_eth = False
        for symbol, address in self.token_addresses.items():
            if symbol in ['eth', 'weth'] and token_address.lower() == address:
                is_eth = True
                break
        
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
            # For other tokens, use the token balance
            # Find token symbol from address
            token_symbol = None
            for symbol, address in self.token_addresses.items():
                if token_address.lower() == address:
                    for config_symbol, token_data in self.config.get('tokens', {}).items():
                        if isinstance(token_data, dict) and 'address' in token_data and token_data['address'].lower() == address:
                            token_symbol = config_symbol
                            break
                    break
            
            if not token_symbol:
                # Return default values if token not found
                return (
                    self.web3_manager.w3.to_wei(self.absolute_min_eth, 'ether'),
                    self.web3_manager.w3.to_wei(self.absolute_max_eth, 'ether')
                )
            
            # Get token balance
            balance = await self.get_balance(token_symbol)
            if balance is None:
                # Return default values if balance not available
                return (
                    self.web3_manager.w3.to_wei(self.absolute_min_eth, 'ether'),
                    self.web3_manager.w3.to_wei(self.absolute_max_eth, 'ether')
                )
            
            # Get token decimals
            token_data = self.config.get('tokens', {}).get(token_symbol)
            if not token_data:
                # Return default values if token data not available
                return (
                    self.web3_manager.w3.to_wei(self.absolute_min_eth, 'ether'),
                    self.web3_manager.w3.to_wei(self.absolute_max_eth, 'ether')
                )
            
            # Calculate available balance (after reserve)
            available_balance = Decimal(balance) * (100 - self.reserve_percentage) / 100
            
            # Calculate min and max allocations as percentages of available balance
            min_amount = max(
                available_balance * self.min_percentage / 100,
                Decimal('0')  # Ensure at least 0
            )
            
            # Max amount considers concurrent trades
            max_amount = min(
                available_balance * self.max_percentage / 100 / self.concurrent_trades,
                available_balance  # Ensure at most available balance
            )
            
            logger.info("Dynamic allocation range: %s to %s tokens", min_amount, max_amount)
            
            return (int(min_amount), int(max_amount))
    
    def get_allocation_range_sync(self, token_address: str) -> Tuple[int, int]:
        """
        Get the minimum and maximum allocation amounts for a token based on current balance synchronously.
        
        Args:
            token_address: Address of the token to allocate
            
        Returns:
            Tuple of (min_amount, max_amount) in wei
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_allocation_range(token_address))
    
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
    
    def adjust_amount_to_limits_sync(self, token_address: str, amount: int) -> int:
        """
        Adjust an amount to be within the current allocation limits synchronously.
        
        Args:
            token_address: Address of the token
            amount: Proposed amount in wei
            
        Returns:
            Adjusted amount in wei within allocation limits
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.adjust_amount_to_limits(token_address, amount))


# Factory functions

async def create_unified_balance_manager(
    web3_manager,
    dex_manager=None,
    config: Optional[Dict[str, Any]] = None
) -> UnifiedBalanceManager:
    """
    Create and initialize a UnifiedBalanceManager instance asynchronously.
    
    Args:
        web3_manager: Web3Manager instance
        dex_manager: DexManager instance (optional)
        config: Configuration dictionary (optional)
        
    Returns:
        Initialized UnifiedBalanceManager instance
    """
    return await UnifiedBalanceManager.get_instance(web3_manager, dex_manager, config)

def create_unified_balance_manager_sync(
    web3_manager,
    dex_manager=None,
    config: Optional[Dict[str, Any]] = None
) -> UnifiedBalanceManager:
    """
    Create and initialize a UnifiedBalanceManager instance synchronously.
    
    Args:
        web3_manager: Web3Manager instance
        dex_manager: DexManager instance (optional)
        config: Configuration dictionary (optional)
        
    Returns:
        Initialized UnifiedBalanceManager instance
    """
    return UnifiedBalanceManager.get_instance_sync(web3_manager, dex_manager, config)