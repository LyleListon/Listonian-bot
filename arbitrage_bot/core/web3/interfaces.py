"""
Web3 Interface Definitions

This module defines the core interfaces for Web3 interactions, including the
Web3Client interface and the Transaction data structure.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union


@dataclass
class Transaction:
    """
    Represents an Ethereum transaction.
    
    This class encapsulates all the data needed to construct and send
    a transaction on the Ethereum network.
    """
    
    from_address: str
    """The address sending the transaction (checksummed)."""
    
    to_address: str
    """The address receiving the transaction (checksummed)."""
    
    data: str = "0x"
    """The transaction data (hex-encoded)."""
    
    value: int = 0
    """The amount of ETH to send in wei."""
    
    gas: Optional[int] = None
    """Gas limit for the transaction."""
    
    gas_price: Optional[int] = None
    """Gas price for the transaction in wei."""
    
    nonce: Optional[int] = None
    """Transaction nonce."""


class Web3Client:
    """
    Interface for interacting with the Ethereum blockchain.
    
    This class defines the methods that any Web3 client implementation
    must provide for interacting with the Ethereum network.
    """
    
    async def connect(self) -> bool:
        """
        Connect to the Ethereum network.
        
        Returns:
            True if the connection was successful, False otherwise
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def is_connected(self) -> bool:
        """
        Check if the client is connected to the Ethereum network.
        
        Returns:
            True if connected, False otherwise
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def get_accounts(self) -> List[str]:
        """
        Get the list of accounts controlled by the client.
        
        Returns:
            List of account addresses (checksummed)
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def get_balance(self, address: str, block: str = "latest") -> int:
        """
        Get the balance of an address.
        
        Args:
            address: Address to get balance for (checksummed)
            block: Block number or hash, or "latest", "pending", "earliest"
            
        Returns:
            Balance in wei
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def get_transaction_count(
        self,
        address: str,
        block: str = "latest"
    ) -> int:
        """
        Get the transaction count (nonce) for an address.
        
        Args:
            address: Address to get nonce for (checksummed)
            block: Block number or hash, or "latest", "pending", "earliest"
            
        Returns:
            Transaction count (nonce)
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def get_block_number(self) -> int:
        """
        Get the latest block number.
        
        Returns:
            Latest block number
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def get_gas_price(self) -> int:
        """
        Get the current gas price.
        
        Returns:
            Gas price in wei
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def get_chain_id(self) -> int:
        """
        Get the chain ID.
        
        Returns:
            Chain ID
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def estimate_gas(self, transaction: Transaction) -> int:
        """
        Estimate the gas needed for a transaction.
        
        Args:
            transaction: Transaction to estimate gas for
            
        Returns:
            Estimated gas amount
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def send_transaction(self, transaction: Transaction) -> str:
        """
        Send a transaction.
        
        Args:
            transaction: Transaction to send
            
        Returns:
            Transaction hash
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def call_contract_method(
        self,
        method_name: str,
        args: List[Any] = None,
        contract_address: Optional[str] = None,
        contract_abi: Optional[List[Dict[str, Any]]] = None,
        transaction: Optional[Transaction] = None,
        block: str = "latest"
    ) -> Any:
        """
        Call a contract method.
        
        Args:
            method_name: Name of the method to call
            args: Arguments to pass to the method
            contract_address: Address of the contract (checksummed)
            contract_abi: ABI of the contract
            transaction: Transaction parameters
            block: Block number or hash, or "latest", "pending", "earliest"
            
        Returns:
            Result of the method call
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def make_request(
        self,
        method: str,
        params: List[Any] = None,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make a raw JSON-RPC request.
        
        Args:
            method: JSON-RPC method
            params: Parameters for the method
            url: URL to send the request to (overrides default URL)
            headers: Headers to include in the request
            timeout: Request timeout in seconds
            
        Returns:
            Response from the JSON-RPC server
        """
        raise NotImplementedError("Method must be implemented by subclass")
    
    async def close(self) -> None:
        """Close the client and clean up resources."""
        raise NotImplementedError("Method must be implemented by subclass")