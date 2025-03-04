"""
Ethereum Client Implementation

This module provides the EthClient implementation for interacting with
Ethereum networks through Web3.py.
"""

import asyncio
import json
import logging
import aiohttp
from typing import List, Dict, Any, Optional, Union, Tuple
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account

from ..interfaces import Web3Client, Transaction

logger = logging.getLogger(__name__)


class EthClient(Web3Client):
    """
    Ethereum client implementation using Web3.py.
    
    This class provides a concrete implementation of the Web3Client interface
    using the Web3.py library to interact with Ethereum networks.
    """
    
    def __init__(
        self,
        provider_url: str,
        private_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Ethereum client.
        
        Args:
            provider_url: URL of the Ethereum node to connect to
            private_key: Private key for signing transactions (without 0x prefix)
            config: Configuration parameters for the client
        """
        self.provider_url = provider_url
        self.private_key = private_key
        self.config = config or {}
        
        # Configuration
        self.chain_id = self.config.get("chain_id")
        
        # Set up Web3 instance
        self.web3 = None
        self.account = None
        if private_key:
            self.account = Account.from_key(private_key)
        
        # Session
        self._http_session = None
        
        # State
        self._is_connected = False
        self._connection_lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """
        Connect to the Ethereum network.
        
        Returns:
            True if the connection was successful, False otherwise
        """
        async with self._connection_lock:
            if self._is_connected:
                logger.debug("Already connected to Ethereum network")
                return True
            
            try:
                logger.info(f"Connecting to Ethereum network at {self.provider_url}")
                
                # Create HTTP session
                self._http_session = aiohttp.ClientSession()
                
                # Create Web3 instance
                self.web3 = Web3(Web3.HTTPProvider(self.provider_url))
                
                # Verify connection
                if not self.web3.is_connected():
                    logger.error("Failed to connect to Ethereum network")
                    return False
                
                # Get chain ID if not provided
                if not self.chain_id:
                    self.chain_id = self.web3.eth.chain_id
                    
                logger.info(f"Connected to Ethereum network (chain ID: {self.chain_id})")
                self._is_connected = True
                return True
                
            except Exception as e:
                logger.error(f"Failed to connect to Ethereum network: {e}")
                return False
    
    async def is_connected(self) -> bool:
        """
        Check if the client is connected to the Ethereum network.
        
        Returns:
            True if connected, False otherwise
        """
        return self._is_connected and self.web3 and self.web3.is_connected()
    
    async def get_accounts(self) -> List[str]:
        """
        Get the list of accounts controlled by the client.
        
        Returns:
            List of account addresses (checksummed)
        """
        await self._ensure_connected()
        
        accounts = []
        
        # Add the account from the private key if available
        if self.account:
            accounts.append(self.account.address)
        
        # Add accounts from the provider (unlocked accounts)
        try:
            provider_accounts = await asyncio.to_thread(
                self.web3.eth.accounts.__getattribute__, 
                '__iter__'
            )
            accounts.extend(provider_accounts)
        except Exception as e:
            logger.warning(f"Failed to get accounts from provider: {e}")
        
        # Remove duplicates and return
        return list(set(accounts))
    
    async def get_balance(self, address: str, block: str = "latest") -> int:
        """
        Get the balance of an address.
        
        Args:
            address: Address to get balance for (checksummed)
            block: Block number or hash, or "latest", "pending", "earliest"
            
        Returns:
            Balance in wei
        """
        await self._ensure_connected()
        
        try:
            balance = await asyncio.to_thread(
                self.web3.eth.get_balance,
                Web3.to_checksum_address(address),
                block
            )
            return balance
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise
    
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
        await self._ensure_connected()
        
        try:
            nonce = await asyncio.to_thread(
                self.web3.eth.get_transaction_count,
                Web3.to_checksum_address(address),
                block
            )
            return nonce
        except Exception as e:
            logger.error(f"Failed to get transaction count for {address}: {e}")
            raise
    
    async def get_block_number(self) -> int:
        """
        Get the latest block number.
        
        Returns:
            Latest block number
        """
        await self._ensure_connected()
        
        try:
            block_number = await asyncio.to_thread(self.web3.eth.block_number)
            return block_number
        except Exception as e:
            logger.error(f"Failed to get block number: {e}")
            raise
    
    async def get_gas_price(self) -> int:
        """
        Get the current gas price.
        
        Returns:
            Gas price in wei
        """
        await self._ensure_connected()
        
        try:
            gas_price = await asyncio.to_thread(self.web3.eth.gas_price)
            return gas_price
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            raise
    
    async def get_chain_id(self) -> int:
        """
        Get the chain ID.
        
        Returns:
            Chain ID
        """
        await self._ensure_connected()
        
        try:
            if self.chain_id:
                return self.chain_id
            
            chain_id = await asyncio.to_thread(lambda: self.web3.eth.chain_id)
            self.chain_id = chain_id
            return chain_id
        except Exception as e:
            logger.error(f"Failed to get chain ID: {e}")
            raise
    
    async def estimate_gas(self, transaction: Transaction) -> int:
        """
        Estimate the gas needed for a transaction.
        
        Args:
            transaction: Transaction to estimate gas for
            
        Returns:
            Estimated gas amount
        """
        await self._ensure_connected()
        
        try:
            # Convert to Web3 transaction format
            tx = {
                "from": Web3.to_checksum_address(transaction.from_address),
                "to": Web3.to_checksum_address(transaction.to_address),
                "value": transaction.value,
                "data": transaction.data,
            }
            
            # Add gas price if provided
            if transaction.gas_price is not None:
                tx["gasPrice"] = transaction.gas_price
            
            # Estimate gas
            gas = await asyncio.to_thread(self.web3.eth.estimate_gas, tx)
            return gas
        except Exception as e:
            logger.error(f"Failed to estimate gas for transaction: {e}")
            raise
    
    async def send_transaction(self, transaction: Transaction) -> str:
        """
        Send a transaction.
        
        Args:
            transaction: Transaction to send
            
        Returns:
            Transaction hash
        """
        await self._ensure_connected()
        
        try:
            # Convert to Web3 transaction format
            tx = {
                "from": Web3.to_checksum_address(transaction.from_address),
                "to": Web3.to_checksum_address(transaction.to_address),
                "value": transaction.value,
                "data": transaction.data,
            }
            
            # Add gas and gas price if provided
            if transaction.gas is not None:
                tx["gas"] = transaction.gas
            else:
                # Estimate gas if not provided
                tx["gas"] = await self.estimate_gas(transaction)
            
            if transaction.gas_price is not None:
                tx["gasPrice"] = transaction.gas_price
            
            # Add nonce if provided
            if transaction.nonce is not None:
                tx["nonce"] = transaction.nonce
            
            # If we have a private key, sign and send the transaction
            if self.private_key:
                # Add chain ID
                tx["chainId"] = await self.get_chain_id()
                
                # Get nonce if not provided
                if "nonce" not in tx:
                    tx["nonce"] = await self.get_transaction_count(
                        transaction.from_address,
                        "pending"
                    )
                
                # Sign transaction
                signed_tx = self.web3.eth.account.sign_transaction(
                    tx,
                    private_key=self.private_key
                )
                
                # Send signed transaction
                tx_hash = await asyncio.to_thread(
                    self.web3.eth.send_raw_transaction,
                    signed_tx.rawTransaction
                )
            else:
                # Otherwise, use the unlocked account on the provider
                tx_hash = await asyncio.to_thread(
                    self.web3.eth.send_transaction,
                    tx
                )
            
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Failed to send transaction: {e}")
            raise
    
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
        await self._ensure_connected()
        
        args = args or []
        
        try:
            # If contract address and ABI are provided, use Contract object
            if contract_address and contract_abi:
                contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=contract_abi
                )
                
                # Get contract method
                method = getattr(contract.functions, method_name)
                
                # Create method instance with arguments
                method_instance = method(*args)
                
                # If transaction parameters are provided, use them
                if transaction:
                    tx_params = {
                        "from": Web3.to_checksum_address(transaction.from_address)
                    }
                    
                    if transaction.gas is not None:
                        tx_params["gas"] = transaction.gas
                    
                    if transaction.gas_price is not None:
                        tx_params["gasPrice"] = transaction.gas_price
                    
                    if transaction.value is not None:
                        tx_params["value"] = transaction.value
                    
                    # Call method with transaction parameters
                    result = await asyncio.to_thread(
                        method_instance.call,
                        tx_params,
                        block_identifier=block
                    )
                else:
                    # Call method without transaction parameters
                    result = await asyncio.to_thread(
                        method_instance.call,
                        block_identifier=block
                    )
                
                return result
            else:
                # If no contract address or ABI, make a raw JSON-RPC call
                return await self.make_request(method_name, args)
        except ContractLogicError as e:
            logger.error(f"Contract logic error calling {method_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to call contract method {method_name}: {e}")
            raise
    
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
        if not self._http_session:
            await self.connect()
        
        params = params or []
        headers = headers or {}
        url = url or self.provider_url
        timeout = timeout or 30
        
        # Set basic headers
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        
        # Create request payload
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": int(asyncio.get_event_loop().time() * 1000)
        }
        
        try:
            # Send request
            async with self._http_session.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout
            ) as response:
                # Parse response
                response_data = await response.json()
                
                # Check for errors
                if "error" in response_data:
                    error = response_data["error"]
                    logger.error(f"RPC error: {error}")
                    return response_data
                
                return response_data
        except Exception as e:
            logger.error(f"Failed to make RPC request: {e}")
            return {"error": {"code": -32000, "message": str(e)}}
    
    async def close(self) -> None:
        """Close the client and clean up resources."""
        logger.info("Closing Ethereum client")
        
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
        
        self._is_connected = False
    
    async def _ensure_connected(self) -> None:
        """Ensure the client is connected to the Ethereum network."""
        if not self._is_connected:
            await self.connect()
            
            if not self._is_connected:
                raise ConnectionError("Not connected to Ethereum network")