"""
Web3 Manager Module

This module provides functionality for:
- Managing Web3 connections
- Contract interactions
- Transaction management
"""

import logging
from typing import Any, Dict, Optional, Callable
from web3 import Web3
from eth_account import Account
from eth_typing import ChecksumAddress

from ...utils.async_manager import with_retry
from .web3_client_wrapper import Web3ClientWrapper
from .interfaces import Web3Client, Contract, ContractWrapper

logger = logging.getLogger(__name__)

class SignerMiddleware:
    """Middleware for signing transactions."""

    def __init__(self, w3: Web3, account: Account):
        self.w3 = w3
        self.account = account

    def __call__(self, w3: Web3) -> "SignerMiddleware":
        """
        Called when middleware is added to web3 instance.

        Args:
            w3: Web3 instance

        Returns:
            Self for middleware registration
        """
        self.w3 = w3
        return self

    def wrap_make_request(self, make_request: Callable[[str, list], Any]) -> Callable[[str, list], Any]:
        """
        Wrap the make_request function with signing functionality.

        Args:
            make_request: Original make_request function

        Returns:
            Wrapped make_request function
        """
        def middleware(method: str, params: list) -> Any:
            if method == 'eth_sendRawTransaction':
                transaction_dict = params[0]
                signed = self.account.sign_transaction(transaction_dict)
                return make_request(method, [signed.rawTransaction])
            
            # For non-transaction methods, pass through
            return make_request(method, params)
            
        return middleware

class Web3Manager(Web3Client):
    """Manages Web3 connections and interactions."""

    def __init__(
        self,
        provider_url: str,
        private_key: Optional[str] = None,
        chain_id: int = 8453,  # Base mainnet
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Web3 manager.

        Args:
            provider_url: Web3 provider URL
            private_key: Optional private key for transactions
            chain_id: Chain ID
            config: Optional configuration dictionary
        """
        self.provider_url = provider_url
        self.chain_id = chain_id
        self.config = config or {}

        # Initialize Web3
        self._raw_w3 = Web3(Web3.HTTPProvider(provider_url))
        
        # Configure for PoA chains
        self._raw_w3.eth.default_block = "latest"

        # Set up account if private key provided
        self.private_key = private_key
        self.account = None
        self.wallet_address = None

        if private_key:
            self.account = Account.from_key(private_key)
            self.wallet_address = self.account.address

            # Add middleware for signing transactions
            signer = SignerMiddleware(self._raw_w3, self.account)
            self._raw_w3.middleware_onion.add(signer, name='signer')

        # Create wrapped Web3 instance
        self.w3 = Web3ClientWrapper(self._raw_w3)
        
        # Initialize eth module
        self._eth = self.w3.eth

        logger.info(
            f"Web3 manager initialized for chain {chain_id} "
            f"with account {self.wallet_address or 'None'}"
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
        return await self.eth.get_balance(address)

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
        balance = await token_contract.functions.balanceOf(address).call()
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
        return await self.eth.get_transaction_count(address)

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
    if not web3_config.get('rpc_url'):
        logger.error("Web3 RPC URL not configured")
        raise ValueError("Web3 RPC URL not configured")

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
        provider_url=web3_config['rpc_url'],
        private_key=web3_config.get('wallet_key'),
        chain_id=web3_config['chain_id'],
        config=config
    )

    logger.info("Web3 manager created successfully")
    return manager
