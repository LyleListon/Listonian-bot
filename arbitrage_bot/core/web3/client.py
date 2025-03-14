"""
Web3 Client Implementation

This module provides the Web3 client implementation for blockchain interactions.
"""

import logging
from typing import Dict, Any, Optional, Union
from decimal import Decimal
from eth_typing import ChecksumAddress
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

from .interfaces import Web3Client, Contract, ContractWrapper

logger = logging.getLogger(__name__)

class Web3ClientImpl(Web3Client):
    """Implementation of the Web3Client interface."""
    
    def __init__(
        self,
        rpc_endpoint: str,
        chain: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Web3 client.
        
        Args:
            rpc_endpoint: RPC endpoint URL
            chain: Chain identifier (e.g., "base_mainnet")
            config: Additional configuration
        """
        self.rpc_endpoint = rpc_endpoint
        self.chain = chain
        self.config = config or {}
        self.web3 = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the Web3 connection."""
        if self._initialized:
            return
            
        logger.info(f"Initializing Web3 client for {self.chain}")
        
        try:
            # Create Web3 instance
            self.web3 = Web3(HTTPProvider(self.rpc_endpoint))
            
            # Add PoA middleware for Base chain
            if self.chain in ["base_mainnet", "base_goerli"]:
                self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Test connection
            block = await self.get_block("latest")
            logger.info(f"Connected to {self.chain} at block {block['number']}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Web3 client: {e}")
            raise
    
    def contract(self, address: ChecksumAddress, abi: Dict[str, Any]) -> Contract:
        """Get contract instance."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")
            
        contract = self.web3.eth.contract(address=address, abi=abi)
        return ContractWrapper(contract)
    
    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")
            
        return self.web3.eth.gas_price
    
    async def get_block(self, block_identifier: Union[str, int]) -> Dict[str, Any]:
        """Get block by number or hash."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")
            
        return self.web3.eth.get_block(block_identifier)
    
    def to_wei(self, value: Union[int, float, str, Decimal], currency: str) -> int:
        """Convert currency value to wei."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")
            
        return self.web3.to_wei(value, currency)
    
    @property
    def eth(self) -> Any:
        """Get eth module."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")
            
        return self.web3.eth