"""
Unified Balance Manager

Manages token balances and approvals across multiple DEXs.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from web3 import Web3

from .web3.web3_manager import Web3Manager
from .dex.dex_manager import DexManager

logger = logging.getLogger(__name__)

class UnifiedBalanceManager:
    """Manages token balances and approvals."""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __init__(
        self,
        web3_manager: Web3Manager,
        dex_manager: DexManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the balance manager.
        
        Args:
            web3_manager: Web3 manager instance
            dex_manager: DEX manager instance
            config: Optional configuration
        """
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.config = config or {}
        self.initialized = False
        
        # Cache for token balances and allowances
        self._balance_cache = {}
        self._allowance_cache = {}
        
        # Cache TTL in seconds
        self.cache_ttl = int(self.config.get('balance_cache_ttl', 30))
        
        # Approval settings
        self.max_approval_amount = Web3.to_wei(
            self.config.get('max_approval_amount', 1000000), 'ether'
        )
        self.min_approval_amount = Web3.to_wei(
            self.config.get('min_approval_amount', 1000), 'ether'
        )
        
        # Lock for balance updates
        self.balance_lock = asyncio.Lock()
        
    @classmethod
    async def get_instance(
        cls,
        web3_manager: Web3Manager,
        dex_manager: DexManager,
        config: Optional[Dict[str, Any]] = None
    ) -> 'UnifiedBalanceManager':
        """
        Get or create singleton instance.
        
        Args:
            web3_manager: Web3 manager instance
            dex_manager: DEX manager instance
            config: Optional configuration
            
        Returns:
            UnifiedBalanceManager instance
        """
        async with cls._lock:
            if not cls._instance:
                cls._instance = cls(web3_manager, dex_manager, config)
                await cls._instance.initialize()
            return cls._instance
            
    async def initialize(self) -> bool:
        """
        Initialize the balance manager.
        
        Returns:
            True if initialization successful
        """
        try:
            # Load ERC20 ABI
            self.erc20_abi = await self.web3_manager.load_abi_async('ERC20')
            
            # Initialize caches
            self._balance_cache = {}
            self._allowance_cache = {}
            
            self.initialized = True
            logger.info("Balance manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize balance manager: {e}")
            return False
            
    async def get_balance(
        self,
        token_address: str,
        wallet_address: Optional[str] = None,
        force_refresh: bool = False
    ) -> int:
        """
        Get token balance for an address.
        
        Args:
            token_address: Token contract address
            wallet_address: Optional wallet address (defaults to current wallet)
            force_refresh: Force cache refresh
            
        Returns:
            Token balance in smallest units
        """
        if not self.initialized:
            raise RuntimeError("Balance manager not initialized")
            
        wallet_address = wallet_address or self.web3_manager.wallet_address
        cache_key = f"{token_address}:{wallet_address}"
        
        async with self.balance_lock:
            # Check cache
            if not force_refresh and cache_key in self._balance_cache:
                timestamp, balance = self._balance_cache[cache_key]
                if asyncio.get_event_loop().time() - timestamp < self.cache_ttl:
                    return balance
            
            try:
                # Get balance
                if token_address == '0x0000000000000000000000000000000000000000':
                    # ETH balance
                    balance = await self.web3_manager.get_balance(wallet_address)
                else:
                    # ERC20 balance
                    contract = self.web3_manager.eth.contract(
                        address=token_address,
                        abi=self.erc20_abi
                    )
                    balance = await contract.functions.balanceOf(wallet_address).call()
                
                # Update cache
                self._balance_cache[cache_key] = (
                    asyncio.get_event_loop().time(),
                    balance
                )
                
                return balance
                
            except Exception as e:
                logger.error(f"Failed to get balance for {token_address}: {e}")
                raise
                
    async def get_allowance(
        self,
        token_address: str,
        spender_address: str,
        wallet_address: Optional[str] = None,
        force_refresh: bool = False
    ) -> int:
        """
        Get token allowance for a spender.
        
        Args:
            token_address: Token contract address
            spender_address: Spender contract address
            wallet_address: Optional wallet address (defaults to current wallet)
            force_refresh: Force cache refresh
            
        Returns:
            Allowance amount in smallest units
        """
        if not self.initialized:
            raise RuntimeError("Balance manager not initialized")
            
        wallet_address = wallet_address or self.web3_manager.wallet_address
        cache_key = f"{token_address}:{wallet_address}:{spender_address}"
        
        async with self.balance_lock:
            # Check cache
            if not force_refresh and cache_key in self._allowance_cache:
                timestamp, allowance = self._allowance_cache[cache_key]
                if asyncio.get_event_loop().time() - timestamp < self.cache_ttl:
                    return allowance
            
            try:
                # Get allowance
                contract = self.web3_manager.eth.contract(
                    address=token_address,
                    abi=self.erc20_abi
                )
                allowance = await contract.functions.allowance(
                    wallet_address,
                    spender_address
                ).call()
                
                # Update cache
                self._allowance_cache[cache_key] = (
                    asyncio.get_event_loop().time(),
                    allowance
                )
                
                return allowance
                
            except Exception as e:
                logger.error(f"Failed to get allowance for {token_address}: {e}")
                raise
                
    async def approve_token(
        self,
        token_address: str,
        spender_address: str,
        amount: Optional[int] = None
    ) -> bool:
        """
        Approve token spending.
        
        Args:
            token_address: Token contract address
            spender_address: Spender contract address
            amount: Optional approval amount (defaults to max_approval_amount)
            
        Returns:
            True if successful
        """
        if not self.initialized:
            raise RuntimeError("Balance manager not initialized")
            
        amount = amount or self.max_approval_amount
        
        try:
            # Get current allowance
            current_allowance = await self.get_allowance(
                token_address,
                spender_address,
                force_refresh=True
            )
            
            # Check if approval needed
            if current_allowance >= amount:
                logger.debug(f"Sufficient allowance for {token_address}")
                return True
            
            # Approve
            contract = self.web3_manager.eth.contract(
                address=token_address,
                abi=self.erc20_abi
            )
            
            tx = await contract.functions.approve(
                spender_address,
                amount
            ).build_transaction({
                'from': self.web3_manager.wallet_address,
                'gas': 100000,
                'nonce': await self.web3_manager.get_transaction_count_async(
                    self.web3_manager.wallet_address
                )
            })
            
            # Sign and send transaction
            tx_hash = await self.web3_manager.send_transaction(tx)
            
            # Wait for receipt
            receipt = await self.web3_manager.wait_for_transaction_receipt_async(tx_hash)
            
            success = receipt['status'] == 1
            if success:
                # Invalidate cache
                cache_key = f"{token_address}:{self.web3_manager.wallet_address}:{spender_address}"
                self._allowance_cache.pop(cache_key, None)
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to approve {token_address}: {e}")
            return False
            
    async def check_and_approve(
        self,
        token_address: str,
        spender_address: str,
        amount: int
    ) -> bool:
        """
        Check allowance and approve if needed.
        
        Args:
            token_address: Token contract address
            spender_address: Spender contract address
            amount: Required amount
            
        Returns:
            True if sufficient allowance exists or approval successful
        """
        try:
            # Get current allowance
            allowance = await self.get_allowance(token_address, spender_address)
            
            # Check if approval needed
            if allowance >= amount:
                return True
                
            # Approve
            return await self.approve_token(
                token_address,
                spender_address,
                max(amount, self.min_approval_amount)
            )
            
        except Exception as e:
            logger.error(f"Failed to check and approve {token_address}: {e}")
            return False