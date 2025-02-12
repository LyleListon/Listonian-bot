"""Web3 manager for blockchain interactions."""

import os
import json
import logging
from typing import Optional, Union, Dict, Any, List, Callable
from web3 import Web3
from web3.types import (
    BlockIdentifier, 
    TxParams, 
    TxReceipt, 
    Wei, 
    BlockData,
    Nonce
)
from eth_account import Account
from eth_typing import HexStr
from web3.contract import Contract
import asyncio
from functools import partial, wraps

logger = logging.getLogger(__name__)

class AsyncContractFunction:
    """Wrapper for contract functions to make them async."""
    def __init__(self, fn):
        self._fn = fn

    async def __call__(self, *args, **kwargs):
        """Make async call to contract function."""
        loop = asyncio.get_event_loop()
        fn = self._fn(*args, **kwargs)
        return await loop.run_in_executor(None, fn.call)

class AsyncContractFunctions:
    """Wrapper for contract functions container."""
    def __init__(self, contract_functions):
        self._functions = contract_functions

    def __getattr__(self, name):
        fn = getattr(self._functions, name)  # Get the ContractFunction instance
        return AsyncContractFunction(fn)

class AsyncContract:
    """Wrapper for contract to make all functions async."""
    def __init__(self, contract: Contract):
        self._contract = contract
        self.functions = AsyncContractFunctions(contract.functions)
        self.address = contract.address

    def __getattr__(self, name):
        return getattr(self._contract, name)

class Web3Manager:
    """Manages Web3 connections and blockchain interactions."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Web3 manager."""
        self.config = config
        
        # Try to get provider URL from config or environment
        self.provider_url = config.get('network', {}).get('rpc_url') or os.getenv('BASE_RPC_URL')
        if not self.provider_url:
            raise ValueError("RPC URL not found in configuration or environment")

        # Initialize Web3 connection
        self.provider = Web3.HTTPProvider(self.provider_url)
        self._w3 = Web3(self.provider)

        # Load wallet
        self._load_wallet()

        if not self._w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.provider_url}")

        logger.info(f"Connected to network: {self._w3.eth.chain_id}")

    def _load_wallet(self) -> None:
        """Load wallet from configuration or environment."""
        try:
            # Try to get private key from config
            wallet_config = self.config.get('wallet', {})
            private_key = wallet_config.get('private_key')
            
            # If not in config, try environment variable
            if not private_key:
                private_key = os.getenv('PRIVATE_KEY')
                
            if not private_key:
                raise ValueError("Private key not found in configuration or environment")
            
            # Remove '0x' prefix if present
            if private_key.startswith('0x'):
                private_key = private_key[2:]
            
            self.account = Account.from_key(private_key)
            self.address = self._w3.to_checksum_address(self.account.address)
            self.wallet_address = self.address  # Add wallet_address alias
            logger.info(f"Loaded wallet: {self.address}")
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")
            raise

    def load_abi(self, name: str) -> List[Dict[str, Any]]:
        """Load ABI from file.
        
        Args:
            name: Name of the ABI file without .json extension
            
        Returns:
            ABI as a list of dictionaries
        """
        try:
            # Get absolute path from project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            # Try different ABI file patterns
            possible_paths = [
                os.path.join(project_root, 'abi', f'{name}.json'),
                os.path.join(project_root, 'abi', f'{name}_v3.json'),
                os.path.join(project_root, 'abi', f'{name}_v2.json'),
                os.path.join(project_root, 'abi', f'{name.replace("_v3", "")}.json'),  # Try without _v3 suffix
                os.path.join(project_root, 'abi', f'{name.replace("_v3_", "_")}.json')  # Try without v3 in middle
            ]
            
            logger.debug(f"Looking for ABI file {name} in paths: {possible_paths}")
            
            for abi_path in possible_paths:
                if os.path.exists(abi_path):
                    break
            else:
                raise FileNotFoundError(f"Could not find ABI file for {name}")
            with open(abi_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ABI {name}: {e}")
            raise

    @property
    def w3(self) -> Web3:
        """Get Web3 instance."""
        return self._w3

    @property
    def eth(self):
        """Get eth module."""
        return self._w3.eth

    def get_balance(self, address: str) -> Wei:
        """Get balance for address."""
        checksum_address = self._w3.to_checksum_address(address)
        return self._w3.eth.get_balance(checksum_address)

    async def get_eth_balance(self) -> Wei:
        """Get ETH balance for the current wallet."""
        try:
            loop = asyncio.get_event_loop()
            balance = await loop.run_in_executor(
                None,
                lambda: self._w3.eth.get_balance(self.wallet_address)
            )
            return balance
        except Exception as e:
            logger.error(f"Failed to get ETH balance: {e}")
            raise

    def get_block(self, block_identifier: BlockIdentifier = 'latest') -> BlockData:
        """Get block information."""
        return self._w3.eth.get_block(block_identifier)

    def get_transaction_count(self, address: str) -> Nonce:
        """Get transaction count for address."""
        checksum_address = self._w3.to_checksum_address(address)
        return self._w3.eth.get_transaction_count(checksum_address)

    def get_gas_price(self) -> Wei:
        """Get current gas price."""
        return self._w3.eth.gas_price

    def get_chain_id(self) -> int:
        """Get current chain ID."""
        return self._w3.eth.chain_id

    def is_connected(self) -> bool:
        """Check if connected to network."""
        return self._w3.is_connected()

    async def connect(self) -> None:
        """Connect to the network."""
        if not self.is_connected():
            raise ConnectionError(f"Failed to connect to {self.provider_url}")

    def send_transaction(self, transaction: TxParams) -> TxReceipt:
        """Send a transaction."""
        try:
            # Add necessary transaction fields
            if 'chainId' not in transaction:
                transaction['chainId'] = self.get_chain_id()
            if 'nonce' not in transaction:
                transaction['nonce'] = self.get_transaction_count(self.address)
            if 'gasPrice' not in transaction and 'maxFeePerGas' not in transaction:
                transaction['gasPrice'] = self.get_gas_price()

            # Sign transaction
            signed_txn = self._w3.eth.account.sign_transaction(transaction, self.account.key)
            
            # Send transaction
            tx_hash = self._w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for transaction receipt
            tx_receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return tx_receipt
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise

    def get_contract(self, address: str, abi: list) -> Contract:
        """Get contract instance."""
        checksum_address = self._w3.to_checksum_address(address)
        return self._w3.eth.contract(address=checksum_address, abi=abi)

    async def get_contract_async(self, address: str, abi: list) -> AsyncContract:
        """Get contract instance with async support.
        
        Args:
            address: Contract address
            abi: Contract ABI
            
        Returns:
            Contract instance with async call methods
        """
        contract = self.get_contract(address, abi)
        return AsyncContract(contract)

    def estimate_gas(self, transaction: TxParams) -> int:
        """Estimate gas for transaction."""
        return self._w3.eth.estimate_gas(transaction)

async def create_web3_manager(config: Dict[str, Any]) -> Web3Manager:
    """Create a new Web3Manager instance.
    
    Args:
        config: Configuration dictionary with settings
        
    Returns:
        Initialized Web3Manager instance
    """
    manager = Web3Manager(config)
    await manager.connect()
    return manager
