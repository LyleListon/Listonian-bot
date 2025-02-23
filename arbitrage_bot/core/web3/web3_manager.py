"""Web3 manager for handling blockchain interactions."""

import logging
import asyncio
import ssl
from typing import Dict, Any, Optional, Callable, List, Union, Tuple
from web3 import Web3, AsyncWeb3
from web3.contract import Contract, AsyncContract
from web3.exceptions import ContractLogicError
from web3.types import TxReceipt, BlockData
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
            
            # Create AsyncWeb3 instance with SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.w3 = AsyncWeb3(
                AsyncWeb3.AsyncHTTPProvider(
                    self.provider_url,
                    request_kwargs={
                        'ssl': ssl_context,
                        'timeout': 30  # 30 second timeout
                    }
                )
            )
            
            # Test connection
            try:
                block_number = await self.w3.eth.block_number
                retries = 3
                for i in range(retries):
                    try:
                        block_number = await self.w3.eth.block_number
                        logger.info("Successfully connected to network. Current block: %d", block_number)
                        break
                    except Exception as e:
                        if i == retries - 1:
                            raise
                        await asyncio.sleep(1 * (2 ** i))
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

    async def get_block(self, block_identifier: Union[str, int] = 'latest') -> BlockData:
        """Get block data."""
        try:
            return await self.w3.eth.get_block(block_identifier)
        except Exception as e:
            logger.error("Failed to get block: %s", str(e))
            raise

    async def get_contract(self, address: str, abi_name: str) -> Optional[AsyncContract]:
        """Get contract instance with caching."""
        try:
            # Return cached contract if available
            cache_key = str(address) + "-" + str(abi_name)
            if cache_key in self._contract_cache:
                return self._contract_cache[cache_key]

            # Load ABI
            abi = await self._load_abi(abi_name)
            if not abi:
                return None

            # Validate contract deployment
            code = await self.w3.eth.get_code(Web3.to_checksum_address(address))
            if code == b'' or code == '0x':
                logger.error(
                    "Contract not deployed at address %s",
                    address
                )
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

    async def get_token_contract(self, token_address: str) -> Optional[AsyncContract]:
        """Get token contract instance."""
        try:
            return await self.get_contract(
                address=Web3.to_checksum_address(token_address),
                abi_name="ERC20"
            )
        except Exception as e:
            logger.error("Failed to get token contract: %s", str(e))
            return None

    async def _load_abi(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """Load ABI from cache or file."""
        try:
            # Return cached ABI if available
            if name in self._abi_cache:
                return self._abi_cache[name]

            # Try loading from project root first
            abi_paths = [
                os.path.join('abi', name + ".json"),
                os.path.join('arbitrage_bot', 'abi', name + ".json"),
                os.path.join(os.path.dirname(__file__), '..', '..', 'abi', name + ".json")
            ]

            for abi_path in abi_paths:
                if os.path.exists(abi_path):
                    with open(abi_path, 'r') as f:
                        abi = json.load(f)
                        self._abi_cache[name] = abi
                        return abi

            logger.error("ABI file not found in any location: %s", name)
            return None

        except Exception as e:
            logger.error("Failed to load ABI %s: %s", name, str(e))
            return None

    async def _convert_to_string(self, value: Any) -> Any:
        """Convert numeric values to strings."""
        try:
            if isinstance(value, (int, float)):
                return str(value)
            elif isinstance(value, (list, tuple)):
                return tuple(await self._convert_to_string(item) for item in value)
            elif isinstance(value, dict):
                return {key: await self._convert_to_string(val) for key, val in value.items()}
            elif asyncio.iscoroutine(value):
                result = await value
                return await self._convert_to_string(result)
            return value
        except Exception as e:
            logger.error("Failed to convert value to string: %s", str(e))
            return value

    async def _call_contract_function_with_retry(
        self,
        func: Any,  # Changed from AsyncContractFunction to Any
        retries: int = 3,
        delay: float = 1.0
    ) -> Any:
        """Call contract function with retries."""
        last_error = None
        for i in range(retries):
            try:
                # Call the function and await the result
                result = await func.call()
                if asyncio.iscoroutine(result):
                    result = await result

                # Convert the result to string if it's a number
                if isinstance(result, (int, float)):
                    return str(result)
                elif isinstance(result, (list, tuple)):
                    return tuple(str(item) if isinstance(item, (int, float)) else item for item in result)
                elif isinstance(result, dict):
                    return {key: str(val) if isinstance(val, (int, float)) else val for key, val in result.items()}
                
                return result
                
            except Exception as e:
                last_error = e
                if i < retries - 1:
                    await asyncio.sleep(delay * (2 ** i))
                    continue
        
        raise last_error

    async def call_contract_function(
        self,
        func: Union[Any, Callable],  # Changed from AsyncContractFunction to Any
        *args,
        **kwargs
    ) -> Any:
        """Call contract function with retries."""
        try:
            # Case 1: Function builder (e.g., contract.functions.someFunction)
            if callable(func):
                contract_func = func(*args, **kwargs)
                if hasattr(contract_func, 'call'):
                    # Add retry logic for API calls
                    retries = 3
                    for i in range(retries):
                        try:
                            result = await asyncio.wait_for(contract_func.call()
, timeout=30)
                            await asyncio.sleep(1 * (2 ** i))  # Exponential backoff
                            break
                        except Exception as e:
                            if i == retries - 1:
                                raise
                    if asyncio.iscoroutine(result):
                        result = await result
                    return self._convert_numeric_to_string(result)
                return contract_func

            # Case 2: Already built contract function
            if hasattr(func, 'call'):
                # Add retry logic for API calls
                retries = 3
                for i in range(retries):
                    try:
                        result = await asyncio.wait_for(func.call(), timeout=30)
                        await asyncio.sleep(1 * (2 ** i))  # Exponential backoff
                        break
                    except Exception as e:
                        if i == retries - 1:
                            raise
                if asyncio.iscoroutine(result):
  
                  result = await result
                return self._convert_numeric_to_string(result)

            raise ValueError("Invalid contract function")

            '''
            # If it's a function builder, build and call it
            contract_func = func(*args, **kwargs)
            
            if hasattr(contract_func, 'call'):  # Check if it's a contract function
                result = await self._call_contract_function_with_retry(contract_func)
                if asyncio.iscoroutine(result):
                    result = await result
                if isinstance(result, (int, float)):
                    return str(result)
                elif isinstance(result, (list, tuple)):
                    return tuple(str(item) if isinstance(item, (int, float)) else item for item in result)
                elif isinstance(result, dict):
                    return {key: str(val) if isinstance(val, (int, float)) else val for key, val in result.items()}
                return result
            
            elif asyncio.iscoroutine(contract_func):
                # If it's a coroutine, await it and convert result
                result = await contract_func
                if isinstance(result, (int, float)):
                    return str(result)
                elif isinstance(result, (list, tuple)):
                    return tuple(str(item) if isinstance(item, (int, float)) else item for item in result)
                elif isinstance(result, dict):
                    return {key: str(val) if isinstance(val, (int, float)) else val for key, val in result.items()}
                return result
            
            else:
                # If it's a regular function, call it and convert result
                result = contract_func
                if isinstance(result, (int, float)):
                    return str(result)
                elif isinstance(result, (list, tuple)):
                    return tuple(str(item) if isinstance(item, (int, float)) else item for item in result)
                elif isinstance(result, dict):
                    return {key: str(val) if isinstance(val, (int, float)) else val for key, val in result.items()}
                return result
            '''

        except Exception as e:
            logger.error("Failed to call contract function: %s", str(e))
            raise

    def _convert_numeric_to_string(self, value: Any) -> Any:
        """Convert numeric values to strings recursively."""
        if isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, (list, tuple)):
            return tuple(self._convert_numeric_to_string(item) for item in value)
        elif isinstance(value, dict):
            return {key: self._convert_numeric_to_string(val) for key, val in value.items()}
        return value

    async def build_and_send_transaction(
        self,
        contract: AsyncContract,
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
                raise ValueError("Method %s not found on contract" % method)

            # Build transaction
            if tx_params is None:
                tx_params = {}
            
            # Add from address if not provided
            if 'from' not in tx_params and self.wallet_address:
                tx_params['from'] = self.wallet_address

            # Build transaction
            tx = await contract_func(*args, **kwargs).build_transaction(tx_params)

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
                    "Transaction %s not mined after %d seconds" % (tx_hash.hex(), timeout)
                )

            await asyncio.sleep(poll_interval)

    async def estimate_gas(
        self,
        contract: AsyncContract,
        method: str,
        *args,
        **kwargs
    ) -> int:
        """Estimate gas for a contract call."""
        try:
            contract_func = getattr(contract.functions, method)
            if not contract_func:
                raise ValueError("Method %s not found on contract" % method)

            result = await contract_func(*args, **kwargs).estimate_gas()
            if asyncio.iscoroutine(result):
                result = await result
            if isinstance(result, (int, float)):
                return int(str(result))
            return result

        except ContractLogicError as e:
            logger.error("Contract logic error in gas estimation: %s", str(e))
            raise
        except Exception as e:
            logger.error("Failed to estimate gas: %s", str(e))
            raise

    async def get_token_price(self, token_address: str) -> Optional[float]:
        """Get token price."""
        try:
            token = await self.get_token_contract(token_address)
            if not token:
                return None
            return await self._get_token_price_from_chain(token)
        except Exception as e:
            logger.error("Failed to get token price: %s", str(e))
            return None

    async def get_eth_balance(self, address: str = None) -> float:
        """Get ETH balance for an address."""
        try:
            address = address or self.wallet_address
            balance = await self.w3.eth.get_balance(Web3.to_checksum_address(address))
            return float(balance) / 10**18
        except Exception as e:
            logger.error("Failed to get ETH balance: %s", str(e))
            return 0.0

            
    async def _get_token_price_from_chain(self, token: AsyncContract) -> Optional[float]:
        """Get token price from chain."""
        try:
            # Get token decimals
            decimals = await self.call_contract_function(token.functions.decimals())
            decimals = int(decimals)
            
            # Return price in ETH
            return 1.0 / (10 ** decimals)
        except Exception as e:
            logger.error("Failed to get token price from chain: %s", str(e))
            return None


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
