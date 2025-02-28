"""
Web3 Manager Module

This module provides Web3 integration for blockchain interactions.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from web3 import Web3, HTTPProvider

logger = logging.getLogger(__name__)

class Web3Manager:
    """Manages Web3 connections and interactions."""
    
    def __init__(self, provider_url: str, chain_id: int = None, private_key: str = None):
        """
        Initialize the Web3Manager.
        
        Args:
            provider_url: Ethereum node URL
            chain_id: Blockchain network ID
            private_key: Private key for transaction signing (without 0x prefix)
        """
        self.provider_url = provider_url
        self.chain_id = chain_id
        self.private_key = private_key
        
        # Initialize Web3
        self.w3 = Web3(HTTPProvider(provider_url))
        
        # Set up account if private key provided
        if private_key:
            self.account = self.w3.eth.account.from_key(private_key)
            self.wallet_address = self.account.address
        else:
            self.account = None
            self.wallet_address = None
        
        logger.info("Web3Manager initialized with provider %s", provider_url)
        if self.wallet_address:
            logger.info("Using wallet address %s", self.wallet_address)
    
    async def get_gas_price(self) -> int:
        """
        Get current gas price.
        
        Returns:
            Gas price in wei
        """
        return self.w3.eth.gas_price
    
    async def get_balance(self, address: str = None) -> int:
        """
        Get balance of an address.
        
        Args:
            address: Ethereum address to check (defaults to wallet address)
            
        Returns:
            Balance in wei
        """
        address = address or self.wallet_address
        return self.w3.eth.get_balance(address)
    
    async def sign_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Sign a transaction.
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Signed transaction hex string
        """
        if not self.account:
            raise ValueError("No private key provided for transaction signing")
        
        # Add necessary transaction params if not present
        if 'chainId' not in transaction and self.chain_id:
            transaction['chainId'] = self.chain_id
        
        if 'nonce' not in transaction:
            transaction['nonce'] = self.w3.eth.get_transaction_count(self.wallet_address)
        
        if 'gasPrice' not in transaction and 'maxFeePerGas' not in transaction:
            transaction['gasPrice'] = await self.get_gas_price()
        
        # Sign transaction
        signed_tx = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        return signed_tx.rawTransaction.hex()
    
    async def send_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Sign and send a transaction.
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Transaction hash
        """
        signed_tx = await self.sign_transaction(transaction)
        tx_hash = self.w3.eth.send_raw_transaction(bytes.fromhex(signed_tx[2:] if signed_tx.startswith('0x') else signed_tx))
        return tx_hash.hex()


async def create_web3_manager(provider_url: str = None, chain_id: int = None, private_key: str = None, config: Dict[str, Any] = None) -> Web3Manager:
    """
    Create and initialize a Web3Manager instance.
    
    Args:
        provider_url: Ethereum node URL
        chain_id: Blockchain network ID
        private_key: Private key for transaction signing
        config: Configuration dictionary
        
    Returns:
        Initialized Web3Manager instance
    """
    # Load config if provided
    if config:
        provider_url = provider_url or config.get('provider_url')
        chain_id = chain_id or config.get('chain_id')
        private_key = private_key or config.get('private_key')
    
    if not provider_url:
        raise ValueError("Provider URL is required")
    
    # Create Web3Manager
    web3_manager = Web3Manager(provider_url, chain_id, private_key)
    
    return web3_manager
