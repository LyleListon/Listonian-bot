"""
Web3 Manager Module

This module provides functionality for:
- Managing Web3 connections
- Contract interactions
- Transaction management
"""

import logging
import asyncio
import time
from typing import Any, Dict, Optional, Union, List, TypeVar, Tuple, Callable
import decimal
from web3 import Web3
from eth_account import Account
from eth_typing import ChecksumAddress

from ...utils.async_manager import with_retry
from .web3_client_wrapper import Web3ClientWrapper
from .interfaces import Web3Client, Contract, ContractWrapper
from .async_provider import CustomAsyncProvider
from .errors import Web3Error

logger = logging.getLogger(__name__)

T = TypeVar('T')

def _parse_hex(value: Union[str, int]) -> int:
    """Parse hex value to integer."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if value.startswith('0x'):
            return int(value, 16)
        return int(value)
    raise ValueError(f"Cannot parse value: {value}")

class ProviderManager:
    """Manages multiple providers with failover."""
    
    def __init__(self, providers: Dict[str, Union[str, List[str]]], rate_limits: Dict[str, Any]):
        self.primary = providers['primary']
        self.backup = providers.get('backup', [])
        self.current_provider = self.primary
        self.failed_providers = set()
        self.last_switch = 0
        self.switch_cooldown = 60  # Wait 60s before switching back to failed provider
        
        # Configure rate limits
        self.requests_per_second = rate_limits.get('requests_per_second', 5)
        self.max_backoff = rate_limits.get('max_backoff', 60.0)
        self.batch_size = rate_limits.get('batch_size', 10)
        self.cache_ttl = rate_limits.get('cache_ttl', 30)
        
        self._lock = asyncio.Lock()
    
    async def get_provider(self) -> str:
        """Get current working provider URL."""
        async with self._lock:
            return self.current_provider
            
    async def mark_provider_failed(self, provider: str):
        """Mark a provider as failed and switch to backup if available."""
        async with self._lock:
            now = time.time()
            self.failed_providers.add(provider)
            
            # Try to switch to a working provider
            available = [p for p in [self.primary] + self.backup 
                       if p not in self.failed_providers]
            
            if available:
                self.current_provider = available[0]
                self.last_switch = now

class RequestBatcher:
    """Batches similar requests together."""
    
    def __init__(self, web3_manager: 'Web3Manager'):
        self.web3_manager = web3_manager
        self._lock = asyncio.Lock()
        self._request_times = []
        self._current_backoff = 1.0
    
    async def _check_rate_limit(self):
        """Apply rate limiting with exponential backoff."""
        now = time.time()
        self._request_times = [t for t in self._request_times if now - t < 1.0]
        if len(self._request_times) >= self.web3_manager.provider_manager.requests_per_second:
            await asyncio.sleep(self._current_backoff)

    async def batch_requests(
        self, 
        requests: List[Tuple[str, List[Any]]]
    ) -> List[Any]:
        """
        Execute multiple requests in a batch.
        
        Args:
            requests: List of (method, params) tuples
            
        Returns:
            List of results in same order as requests
        """
        async with self._lock:
            try:
                await self._check_rate_limit()
                
                # Split into batches based on configured size
                batch_size = self.web3_manager.provider_manager.batch_size
                results = []
                
                for i in range(0, len(requests), batch_size):
                    batch = requests[i:i + batch_size]
                    
                    try:
                        response = await self.web3_manager._raw_w3.provider.make_request(
                            "eth_batchRequest", 
                            batch
                        )
                        batch_results = [r.get('result') for r in response.get('result', [])]
                        results.extend(batch_results)
                        
                        # Success - reduce backoff
                        self._current_backoff = max(1.0, self._current_backoff * 0.5)
                        
                    except Exception as e:
                        # Failure - increase backoff
                        self._current_backoff = min(
                            self.web3_manager.provider_manager.max_backoff,
                            self._current_backoff * 2
                        )
                        raise Web3Error(str(e), "batch_request_error", {
                            "batch": batch,
                            "backoff": self._current_backoff
                        })
                
                return results
                
            except Exception as e:
                logger.error(f"Error in batch_requests: {e}")
                raise Web3Error(str(e), "batch_request_error", {
                    "requests": requests,
                    "backoff": self._current_backoff
                })

class AsyncMiddleware:
    """Middleware for handling async requests."""

    def __init__(self, w3: Web3, account: Optional[Account] = None):
        self.w3 = w3
        self.account = account

    def __call__(self, w3: Web3) -> "AsyncMiddleware":
        """
        Called when middleware is added to web3 instance.

        Args:
            w3: Web3 instance

        Returns:
            Self for middleware registration
        """
        self.w3 = w3
        return self

    def wrap_make_request(self, make_request: Callable) -> Callable:
        """
        Make request with signing if needed.

        Args:
            method: RPC method
            params: Method parameters

        Returns:
            Response from provider
        """
        async def middleware(method: str, params: list) -> Any:
            try:
                if method == 'eth_sendRawTransaction' and self.account:
                    transaction_dict = params[0]
                    signed = self.account.sign_transaction(transaction_dict)
                    response = await make_request(method, [signed.rawTransaction])
                    return response
                
                # For non-transaction methods, pass through
                response = await make_request(method, params)
                return response
            except Exception as e:
                raise Web3Error(
                    str(e), 
                    "middleware_error",
                    {"method": method, "params": params}
                )
        return middleware

class Web3Manager(Web3Client):
    """Manages Web3 connections and interactions."""

    def __init__(
        self,
        providers: Dict[str, Union[str, List[str]]],
        private_key: Optional[str] = None,
        chain_id: int = 8453,  # Base mainnet
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Web3 manager.

        Args:
            providers: Dictionary with primary and backup provider URLs
            private_key: Optional private key for transactions
            chain_id: Chain ID
            config: Optional configuration dictionary
        """
        self.chain_id = chain_id
        self.config = config or {}
        
        # Initialize provider manager
        rate_limits = config.get('rate_limits', {})
        self.provider_manager = ProviderManager(providers, rate_limits)

        # Initialize Web3 with CustomAsyncProvider
        initial_provider = CustomAsyncProvider(providers['primary'])
        self._raw_w3 = Web3(initial_provider)
        
        # Configure for PoA chains
        self._raw_w3.eth.default_block = "latest"

        # Set up account if private key provided
        self.private_key = private_key
        self.account = None
        self.wallet_address = None

        if private_key:
            self.account = Account.from_key(private_key)
            self.wallet_address = self.account.address

        # Add async middleware
        async_middleware = AsyncMiddleware(self._raw_w3, self.account)
        self._raw_w3.middleware_onion.add(async_middleware, name='async_middleware')

        # Create wrapped Web3 instance
        self.w3 = Web3ClientWrapper(self._raw_w3)
        
        # Initialize eth module
        self._eth = self.w3.eth

        # Initialize request batcher
        self.request_batcher = RequestBatcher(self)

        logger.info(
            f"Web3 manager initialized for chain {chain_id} "
            f"with account {self.wallet_address or 'None'} and {len(providers.get('backup', [])) + 1} providers"
        )

    @property
    def eth(self) -> Any:
        """
        Get eth module.

        Returns:
            Eth module
        """
        return self._eth

    @property
    def is_connected(self) -> bool:
        """Check if connected to node."""
        return self._raw_w3.is_connected()

    def contract(self, address: ChecksumAddress, abi: Dict[str, Any]) -> Contract:
        """
        Create contract instance.

        Args:
            address: Contract address
            abi: Contract ABI

        Returns:
            Contract instance
        """
        # Create contract using raw Web3 instance
        raw_contract = self._raw_w3.eth.contract(address=address, abi=abi)
        # Wrap the contract
        return ContractWrapper(raw_contract)

    @with_retry(retries=3, delay=1.0)
    async def get_balance(
        self,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get ETH balance for address.

        Args:
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            Balance in wei

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        if not address and not self.wallet_address:
            raise ValueError("No address provided and no wallet configured")

        address = address or self.wallet_address
        try:
            response = await self.w3.get_balance(address)
        except Exception as e:
            raise Web3Error(
                str(e),
                "balance_error",
                {
                    "address": address,
                }
            )
        return response

    @with_retry(retries=3, delay=1.0)
    async def get_gas_price(self) -> int:
        """
        Get current gas price.

        Returns:
            Gas price in wei
        """
        try:
            # Get both base fee and priority fee
            latest_block = await self.get_block('latest')
            base_fee = _parse_hex(latest_block.get('baseFeePerGas', '0x0'))
            
            # Add priority fee buffer
            priority_fee = int(2e9)  # 2 Gwei default priority fee
            
            response = base_fee + priority_fee
        except Exception as e:
            raise Web3Error(
                str(e),
                "gas_price_error",
                {"latest_block": latest_block if 'latest_block' in locals() else None}
            )
        return response

    @with_retry(retries=3, delay=1.0)
    async def get_block(self, block_identifier: Union[str, int], full_transactions: bool = False) -> Dict[str, Any]:
        """
        Get block by number or hash.

        Args:
            block_identifier: Block number, hash, or 'latest'
            full_transactions: If True, return full transaction objects instead of hashes

        Returns:
            Block data as a dictionary
        """
        try:
            response = await self.w3.get_block(block_identifier, full_transactions)
        except Exception as e:
            raise Web3Error(
                str(e),
                "block_error",
                {
                    "block_identifier": block_identifier
                }
            )
        return response

    @with_retry(retries=3, delay=1.0)
    async def get_block_number(self) -> int:
        """
        Get current block number.

        Returns:
            Block number
        """
        try:
            response = await self.w3.get_block_number()
        except Exception as e:
            raise Web3Error(
                str(e), "block_number_error", {}
            )
        return response

    @with_retry(retries=3, delay=1.0)
    async def get_token_balance(
        self,
        token_address: ChecksumAddress,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get token balance for address.

        Args:
            token_address: Token contract address
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            Token balance

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        if not address and not self.wallet_address:
            raise ValueError("No address provided and no wallet configured")

        address = address or self.wallet_address

        # Create ERC20 contract
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        token_contract = self.contract(token_address, erc20_abi)

        # Call balanceOf
        try:
            balance = await token_contract.functions.balanceOf(address).call()
        except Exception as e:
            raise Web3Error(
                str(e),
                "token_balance_error",
                {
                    "token_address": token_address,
                    "address": address,
                    "contract": token_contract.address
                }
            )

        return balance

    @with_retry(retries=3, delay=1.0)
    async def get_nonce(
        self,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get next nonce for address.

        Args:
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            Next nonce

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        if not address and not self.wallet_address:
            raise ValueError("No address provided and no wallet configured")

        address = address or self.wallet_address
        try:
            response = await self.w3.get_transaction_count(address)
        except Exception as e:
            raise Web3Error(
                str(e),
                "nonce_error",
                {
                    "address": address
                }
            )
        return response

    def to_wei(self, value: Union[int, float, str, decimal.Decimal], currency: str) -> int:
        """
        Convert currency value to wei.

        Args:
            value: Value to convert
            currency: Currency unit (e.g., 'ether', 'gwei')

        Returns:
            Value in wei

        Example:
            to_wei(1, 'ether') -> 1000000000000000000
        """
        return self._raw_w3.to_wei(value, currency)

    async def batch_call(self, contract_calls: List[Tuple[Contract, str, List[Any]]]) -> List[Any]:
        """
        Execute multiple contract calls in a batch.
        
        Args:
            contract_calls: List of (contract, method_name, args) tuples
        """
        requests = [(c.address, c.functions[m].encode_input(*a)) for c, m, a in contract_calls]
        return await self.request_batcher.batch_requests(requests)

    async def close(self):
        """Clean up resources."""
        if hasattr(self._raw_w3.provider, "close"):
            await self._raw_w3.provider.close()

async def create_web3_manager(
    config: Dict[str, Any]
) -> Web3Manager:
    """
    Create a new Web3 manager.

    Args:
        config: Configuration dictionary

    Returns:
        Web3Manager instance

    Raises:
        ValueError: If required web3 configuration is missing or invalid
    """
    # Validate web3 config
    if not config.get('web3'):
        logger.error("Web3 configuration missing in config")
        raise ValueError("Web3 configuration missing")

    web3_config = config['web3']

    # Validate required fields
    if not web3_config.get('providers'):
        logger.error("Web3 providers not configured")
        raise ValueError("Web3 providers not configured")

    if not web3_config.get('chain_id'):
        logger.error("Chain ID not configured")
        raise ValueError("Chain ID not configured")

    # Validate wallet key if provided
    wallet_key = web3_config.get('wallet_key')
    if wallet_key:
        if not wallet_key.startswith('0x') or len(wallet_key) != 66:
            logger.error("Invalid wallet key format provided")
            raise ValueError("Invalid wallet key format - must be 32 bytes hex")

    logger.info(f"Creating Web3 manager for chain {web3_config['chain_id']}")

    manager = Web3Manager(
        providers=web3_config['providers'],
        private_key=web3_config.get('wallet_key'),
        chain_id=web3_config['chain_id'],
        config=config
    )

    logger.info("Web3 manager created successfully")
    return manager
