"""Web3 manager for handling blockchain interactions."""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List, Union
from web3 import Web3, AsyncWeb3
from web3.contract import Contract
from web3.exceptions import ContractLogicError
from web3.types import TxReceipt
import json
import os
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

class Web3ConnectionError(Exception):
    """Error raised when Web3 connection fails."""
    pass

class Web3Manager:
    """Manages Web3 interactions and contract operations."""

    def __init__(
        self,
        provider_url: str,
        chain_id: int,
        private_key: Optional[str] = None,
        wallet_address: Optional[str] = None
    ):
        """Initialize Web3 manager."""
        self.provider_url = provider_url
        self.chain_id = chain_id
        self.private_key = private_key
        self.wallet_address = wallet_address
        self.w3 = None
        self._contract_cache = {}
        self._abi_cache = {}
        self._connected = False
        
        # Increase recursion limit for complex operations
        sys.setrecursionlimit(10000)
        
        logger.info("==================================================")
        logger.info("WALLET CONFIGURATION")
        logger.info("==================================================")
        logger.info("Using wallet address: %s", wallet_address)
        
        # Validate and checksum wallet address
        if wallet_address:
            try:
                self.wallet_address = Web3.to_checksum_address(wallet_address)
                logger.info("Address checksum: %s", self.wallet_address)
            except ValueError as e:
                raise ValueError("Invalid wallet address: %s" % str(e))

        logger.info("Initialized Web3 manager with account: %s", self.wallet_address)

    async def connect(self):
        """Connect to Web3 provider."""
        try:
            logger.info("Connecting Web3Manager...")
            
            # Create Web3 instance with SSL verification disabled
            self.w3 = Web3(
                Web3.HTTPProvider(
                    self.provider_url,
                    request_kwargs={
                        'verify': False,  # Disable SSL verification
                        'timeout': 30  # 30 second timeout
                    }
                )
            )
            
            # Test connection
            try:
                block_number = self.w3.eth.block_number
                logger.info("Successfully connected to network. Current block: %d", block_number)
            except Exception as e:
                logger.error("Connection test failed: %s", str(e))
                raise Web3ConnectionError("Failed to connect to Web3 provider: %s" % str(e))

            # Get account balance
            if self.wallet_address:
                balance = await self.w3.eth.get_balance(self.wallet_address)
                logger.info(
                    "Account %s balance: %f ETH",
                    self.wallet_address,
                    balance / 10**18
                )

            logger.info("Connected to Web3 provider: %s", self.provider_url)
            logger.info("Using account: %s", self.wallet_address)
            logger.info("Chain ID: %d", self.chain_id)
            
            self._connected = True

        except Exception as e:
            logger.error("Failed to initialize Web3: %s", str(e))
            raise Web3ConnectionError("Failed to connect to Web3 provider: %s" % str(e))

    def get_contract(self, address: str, abi_name: str) -> Optional[Contract]:
        """Get contract instance with caching."""
        try:
            # Return cached contract if available
            cache_key = f"{address}:{abi_name}"
            if cache_key in self._contract_cache:
                return self._contract_cache[cache_key]

            # Load ABI
            abi = self._load_abi(abi_name)
            if not abi:
                return None

            # Create and cache contract
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi
            )
            self._contract_cache[cache_key] = contract
            return contract

        except Exception as e:
            logger.error("Failed to get contract %s: %s", abi_name, str(e))
            return None

    def get_token_contract(self, token_address: str) -> Optional[Contract]:
        """Get token contract instance."""
        try:
            return self.get_contract(
                address=Web3.to_checksum_address(token_address),
                abi_name="ERC20"
            )
        except Exception as e:
            logger.error("Failed to get token contract: %s", str(e))
            return None

    def _load_abi(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """Load ABI from cache or file."""
        try:
            # Return cached ABI if available
            if name in self._abi_cache:
                return self._abi_cache[name]

            # Load ABI from file
            abi_path = os.path.join('abi', f"{name}.json")
            if not os.path.exists(abi_path):
                logger.error("ABI file not found: %s", abi_path)
                return None

            with open(abi_path, 'r') as f:
                abi = json.load(f)

            # Cache and return ABI
            self._abi_cache[name] = abi
            return abi

        except Exception as e:
            logger.error("Failed to load ABI %s: %s", name, str(e))
            return None

    async def call_contract_function(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Call contract function with retries."""
        retries = 3
        delay = 1.0
        
        for i in range(retries):
            try:
                return await func(*args, **kwargs).call()
            except Exception as e:
                if i == retries - 1:
                    raise
                await asyncio.sleep(delay * (2 ** i))

    async def build_and_send_transaction(
        self,
        contract: Contract,
        method: str,
        *args,
        tx_params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Build and send a contract transaction."""
        try:
            # Get contract function
            contract_func = getattr(contract.functions, method)
            if not contract_func:
                raise ValueError(f"Method {method} not found on contract")

            # Build transaction
            if tx_params is None:
                tx_params = {}
            
            # Add from address if not provided
            if 'from' not in tx_params and self.wallet_address:
                tx_params['from'] = self.wallet_address

            # Build transaction
            tx = contract_func(*args, **kwargs).build_transaction(tx_params)

            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                private_key=self.private_key
            )
            
            # Send transaction
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return tx_hash

        except Exception as e:
            logger.error("Failed to build and send transaction: %s", str(e))
            raise

    async def wait_for_transaction(
        self,
        tx_hash: Union[str, bytes],
        timeout: int = 180,
        poll_interval: float = 0.1
    ) -> TxReceipt:
        """Wait for transaction receipt."""
        if isinstance(tx_hash, str):
            tx_hash = bytes.fromhex(tx_hash.replace('0x', ''))

        start_time = asyncio.get_event_loop().time()
        while True:
            try:
                receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    return receipt
            except Exception:
                pass

            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(
                    f"Transaction {tx_hash.hex()} not mined after {timeout} seconds"
                )

            await asyncio.sleep(poll_interval)

    async def estimate_gas(
        self,
        contract: Contract,
        method: str,
        *args,
        **kwargs
    ) -> int:
        """Estimate gas for a contract call."""
        try:
            contract_func = getattr(contract.functions, method)
            if not contract_func:
                raise ValueError(f"Method {method} not found on contract")

            return await contract_func(*args, **kwargs).estimate_gas()

        except ContractLogicError as e:
            logger.error("Contract logic error in gas estimation: %s", str(e))
            raise
        except Exception as e:
            logger.error("Failed to estimate gas: %s", str(e))
            raise

async def create_web3_manager(
    provider_url: str,
    chain_id: int,
    private_key: Optional[str] = None,
    wallet_address: Optional[str] = None
) -> Web3Manager:
    """Create and initialize Web3 manager."""
    primary_error = None
    retries = 3
    
    for i in range(retries):
        try:
            manager = Web3Manager(
                provider_url=provider_url,
                chain_id=chain_id,
                private_key=private_key,
                wallet_address=wallet_address
            )
            
            # Ensure connection is established
            await manager.connect()
            
            return manager
            
        except Exception as e:
            primary_error = e
            if i < retries - 1:
                await asyncio.sleep(1 * (2 ** i))
                continue
            
    raise primary_error
