"""
Web3 Manager Module

This module provides Web3 integration for blockchain interactions.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
import json
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

        # Cache for loaded ABIs
        self._abi_cache = {}
        
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


    async def load_abi_async(self, contract_name: str) -> Dict[str, Any]:
        """
        Load a contract ABI asynchronously.
        
        Args:
            contract_name: Name of the contract ABI file (without .json extension)
            
        Returns:
            Contract ABI as a dictionary
        """
        # Check if already cached
        if contract_name in self._abi_cache:
            return self._abi_cache[contract_name]
            
        try:
            # Use an executor to read the file asynchronously
            loop = asyncio.get_event_loop()
            
            def _load_abi():
                import os
                # Attempt to find the ABI in the abi directory
                abi_path = os.path.join('abi', f'{contract_name}.json')
                
                if not os.path.exists(abi_path):
                    # Try looking in the project root
                    abi_path = os.path.join('arbitrage_bot', 'abi', f'{contract_name}.json')
                
                if not os.path.exists(abi_path):
                    raise FileNotFoundError(f"ABI file not found: {contract_name}.json")
                
                with open(abi_path, 'r') as f:
                    return json.load(f)
            
            abi = await loop.run_in_executor(None, _load_abi)
            
            # Cache the ABI
            self._abi_cache[contract_name] = abi
            return abi
            
        except Exception as e:
            logger.error(f"Error loading ABI {contract_name}: {e}")
            raise
    
    async def get_transaction_count_async(self, address: str) -> int:
        """
        Get the transaction count for an address asynchronously.
        
        Args:
            address: Ethereum address
            
        Returns:
            Transaction count (nonce)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.w3.eth.get_transaction_count(address)
        )
    
    async def send_raw_transaction_async(self, raw_transaction: bytes) -> bytes:
        """
        Send a raw transaction asynchronously.
        
        Args:
            raw_transaction: Signed transaction data
            
        Returns:
            Transaction hash
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.w3.eth.send_raw_transaction(raw_transaction)
        )
    
    async def wait_for_transaction_receipt_async(self, tx_hash: bytes, timeout: int = 120, poll_latency: float = 0.1) -> Dict[str, Any]:
        """
        Wait for a transaction receipt asynchronously.
        
        Args:
            tx_hash: Transaction hash
            timeout: Maximum time to wait in seconds
            poll_latency: Time between polling attempts in seconds
            
        Returns:
            Transaction receipt
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                return self.w3.eth.get_transaction_receipt(tx_hash)
            except Exception:
                await asyncio.sleep(poll_latency)
        
        raise TimeoutError(f"Transaction {tx_hash.hex()} timed out after {timeout} seconds")


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
