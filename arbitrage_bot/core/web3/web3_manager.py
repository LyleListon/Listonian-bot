"""Web3 connection and interaction utilities with secure key management."""

import logging
import asyncio
import os
import json
import pathlib
from typing import Dict, Any, Optional, List
from web3 import AsyncWeb3
from web3.exceptions import TimeExhausted
from eth_account import Account
from ...utils.config_loader import load_config
from ...utils.secure_env import SecureEnvironment
from ...utils.mcp_client import use_mcp_tool as mcp_tool

logger = logging.getLogger(__name__)

class Web3ConnectionError(Exception):
    """Custom exception for Web3 connection errors."""
    pass

class Web3Manager:
    """Manages Web3 connection and interactions with secure key handling."""

    def __init__(self, provider_url: Optional[str] = None, chain_id: Optional[int] = None, testing: bool = False):
        """
        Initialize Web3 manager.

        Args:
            provider_url: Web3 provider URL
            chain_id: Chain ID
            testing: Whether running in test mode
        """
        self.provider_url = provider_url
        self.chain_id = chain_id
        self.testing = testing
        self._web3 = None
        self._account = None  # Store account without private key
        self.secure_env = SecureEnvironment()
        logger.info("Web3 manager initialized")

    async def connect(self):
        """Initialize Web3 connection with secure key handling."""
        try:
            if self.testing:
                logger.info("Running in test mode - using mock Web3 connection")
                self._web3 = AsyncWeb3(AsyncWeb3.AsyncEthereumTesterProvider())
                self.chain_id = 8453  # Base chain ID
                return

            # Get provider URL from environment
            if not self.provider_url:
                self.provider_url = os.getenv("NETWORK_RPC_URL")
                if not self.provider_url:
                    # Try backup URL
                    self.provider_url = os.getenv("BACKUP_RPC_URL")
                    if not self.provider_url:
                        raise ValueError("No RPC URL configured")

            # Create async Web3 instance with HTTP provider
            provider = AsyncWeb3.AsyncHTTPProvider(
                self.provider_url,
                request_kwargs={
                    "headers": {
                        "Content-Type": "application/json",
                        "User-Agent": "arbitrage_bot/1.0.0",
                    },
                    "timeout": 30,  # 30 second timeout
                },
            )
            self._web3 = AsyncWeb3(provider)

            # Test connection
            try:
                block_number = await self._web3.eth.block_number
                logger.debug(f"Successfully connected to network. Current block: {block_number}")

                if not self.chain_id:
                    self.chain_id = int(os.getenv("CHAIN_ID", "8453"))

                # Initialize account securely
                await self._init_account()

            except Exception as e:
                logger.error(f"Connection test failed: {str(e)}")
                raise Web3ConnectionError(f"Failed to connect to Web3 provider: {str(e)}")

            logger.info(f"Connected to Web3 provider: {self.provider_url}")
            logger.info(f"Chain ID: {self.chain_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            raise

    async def _init_account(self):
        """Initialize account using secure environment."""
        try:
            # Get private key from secure storage
            private_key = self.secure_env.secure_load("PRIVATE_KEY")
            if not private_key:
                raise ValueError("No private key found in secure storage")

            # Add 0x prefix if missing
            if not private_key.startswith("0x"):
                private_key = f"0x{private_key}"

            # Create account and immediately clear private key
            self._account = self._web3.eth.account.from_key(private_key)
            self._web3.eth.default_account = self._account.address
            
            # Clear private key from memory
            private_key = None
            
            logger.info(f"Account initialized: {self._account.address}")
        except Exception as e:
            logger.error("Failed to initialize account securely")
            raise

    @property
    def account_address(self) -> str:
        """Get account address safely."""
        if self._account:
            return self._account.address
        raise ValueError("Account not initialized")
        
    @property
    def wallet_address(self) -> str:
        """Get wallet address safely (alias for account_address)."""
        return self.account_address

    async def get_eth_balance(self, address: str = None) -> float:
        """Get ETH balance for an address."""
        try:
            if not address:
                address = self.account_address
            balance_wei = await self._web3.eth.get_balance(address)
            return float(self._web3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            logger.error(f"Failed to get ETH balance: {e}")
            raise

    async def get_token_balance(self, token_address: str, address: str = None) -> float:
        """Get token balance for an address."""
        try:
            if not address:
                address = self.account_address
            token_abi = self.load_abi('ERC20')
            token_contract = self._web3.eth.contract(address=token_address, abi=token_abi)
            balance = await token_contract.functions.balanceOf(address).call()
            decimals = await token_contract.functions.decimals().call()
            return float(balance) / (10 ** decimals)
        except Exception as e:
            logger.error(f"Failed to get token balance: {e}")
            raise

    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        try:
            return await self._web3.eth.gas_price
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            raise

    def load_abi(self, name: str) -> Dict[str, Any]:
        """Load ABI from file."""
        try:
            root_dir = pathlib.Path(os.getcwd())
            abi_path = root_dir / 'abi' / f'{name}.json'
            
            with open(abi_path) as f:
                abi = json.load(f)
            return abi
        except Exception as e:
            logger.error(f"Failed to load ABI {name}: {e}")
            raise

    async def sign_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Sign transaction securely.
        
        Args:
            transaction: Transaction to sign
            
        Returns:
            str: Signed transaction
        """
        try:
            # Get private key securely for signing
            private_key = self.secure_env.secure_load("PRIVATE_KEY")
            if not private_key:
                raise ValueError("No private key available for signing")

            if not private_key.startswith("0x"):
                private_key = f"0x{private_key}"

            # Sign transaction
            signed = self._web3.eth.account.sign_transaction(transaction, private_key)
            
            # Clear private key from memory
            private_key = None
            
            return signed.rawTransaction
        except Exception as e:
            logger.error("Failed to sign transaction securely")
            raise

    async def send_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Send transaction with secure signing.
        
        Args:
            transaction: Transaction to send
            
        Returns:
            str: Transaction hash
        """
        try:
            signed = await self.sign_transaction(transaction)
            tx_hash = await self._web3.eth.send_raw_transaction(signed)
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Failed to send transaction: {e}")
            raise

    @property
    def w3(self) -> AsyncWeb3:
        """Get Web3 instance."""
        return self._web3

async def create_web3_manager(testing: bool = False) -> Web3Manager:
    """Create Web3Manager instance using secure environment."""
    try:
        secure_env = SecureEnvironment()
        provider_url = secure_env.secure_load("NETWORK_RPC_URL")
        if not provider_url and not testing:
            raise ValueError("NETWORK_RPC_URL not found in secure storage")

        chain_id = int(secure_env.secure_load("NETWORK_CHAIN_ID") or "8453")
        
        manager = Web3Manager(
            provider_url=provider_url,
            chain_id=chain_id,
            testing=testing
        )
        
        try:
            await manager.connect()
            return manager
        except Exception as primary_error:
            if not testing:
                backup_url = secure_env.secure_load("BACKUP_RPC_URL")
                if backup_url:
                    logger.warning(f"Primary RPC failed: {primary_error}. Trying backup RPC...")
                    manager = Web3Manager(provider_url=backup_url, chain_id=chain_id)
                    await manager.connect()
                    return manager
            raise primary_error

    except Exception as e:
        logger.error(f"Failed to create Web3Manager: {e}")
        raise
