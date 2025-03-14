"""
Web3 Manager Module

Manages Web3 interactions with enhanced Alchemy support for:
- Token price fetching
- WebSocket subscriptions
- Mempool monitoring
- Gas predictions
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from web3 import Web3, AsyncWeb3
from web3.types import RPCEndpoint, RPCResponse
from decimal import Decimal

from .async_provider import CustomAsyncProvider
from .alchemy_provider import AlchemyProvider
from arbitrage_bot.utils.async_manager import AsyncLock

logger = logging.getLogger(__name__)

class Web3Manager:
    """Manages Web3 interactions with enhanced Alchemy support."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Web3 manager.

        Args:
            config: Configuration dictionary containing:
                - RPC endpoints
                - API keys
                - WebSocket URIs
                - Chain settings
        """
        self.config = config
        self._provider_lock = AsyncLock()
        self._price_cache = {}
        self._price_cache_ttl = 30  # seconds
        self._last_gas_prediction = None
        self._gas_prediction_ttl = 60  # seconds
        
        # Initialize wallet
        self.wallet_key = config['web3']['wallet_key']
        self.wallet_address = Web3.to_checksum_address(Web3().eth.account.from_key(self.wallet_key).address)
        
        # Store chain ID
        self.chain_id = config['web3']['chain_id']

        # Initialize Web3 instance
        self.w3 = AsyncWeb3()
        
        # Providers will be set up during initialize()
        self.primary_provider = None
        self.backup_providers = []

    async def _setup_providers(self):
        """Set up primary and backup providers."""
        providers = self.config['web3']['providers']
        
        if 'alchemy' in providers:
            self.primary_provider = AlchemyProvider(
                endpoint_uri=providers['alchemy']['http'],
                api_key=providers['alchemy']['api_key'],
                websocket_uri=providers['alchemy'].get('ws')
            )
        else:
            self.primary_provider = CustomAsyncProvider(
                providers['primary']
            )

        # Set up backup providers
        self.backup_providers = [
            CustomAsyncProvider(uri)
            for uri in providers.get('backup', [])
        ]

        # Set initial provider
        self.w3.provider = self.primary_provider

    async def initialize(self) -> bool:
        """Initialize Web3 manager and providers."""
        try:
            # Set up providers
            await self._setup_providers()
            
            # Initialize primary provider
            if isinstance(self.primary_provider, AlchemyProvider):
                await self.primary_provider.initialize()

            # Test connection
            chain_id = await self.w3.eth.chain_id
            logger.info(f"Web3 manager initialized successfully with chain ID: {chain_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Web3 manager: {e}")
            raise  # Raise the exception instead of returning False

    @staticmethod
    def to_wei(value: Union[int, float, str, Decimal], unit: str = 'ether') -> int:
        """Convert value to wei."""
        return Web3.to_wei(value, unit)

    async def get_block_number(self) -> int:
        """Get current block number."""
        try:
            return await self.w3.eth.block_number
        except Exception as e:
            logger.error(f"Failed to get block number: {e}")
            raise

    async def get_token_prices(
        self,
        token_addresses: List[str],
        force_refresh: bool = False
    ) -> Dict[str, Decimal]:
        """
        Get current prices for multiple tokens.

        Args:
            token_addresses: List of token addresses
            force_refresh: Force cache refresh

        Returns:
            Dict mapping token addresses to prices
        """
        now = time.monotonic()  # Use monotonic time instead of event loop time
        
        # Check cache first
        if not force_refresh:
            cached = {
                addr: price for addr, (price, timestamp) in self._price_cache.items()
                if addr in token_addresses and (now - timestamp) < self._price_cache_ttl
            }
            if len(cached) == len(token_addresses):
                return cached

        # Use Alchemy Token API if available
        if isinstance(self.primary_provider, AlchemyProvider):
            prices = await self.primary_provider.get_token_prices(token_addresses)
            
            # Update cache
            for addr, price in prices.items():
                self._price_cache[addr] = (price, now)
            
            return prices

        # Fallback to on-chain price fetching
        return await self._fetch_onchain_prices(token_addresses)

    async def subscribe_to_price_updates(
        self,
        token_address: str,
        callback: callable
    ):
        """
        Subscribe to real-time price updates.

        Args:
            token_address: Token address to monitor
            callback: Async callback function for price updates
        """
        if isinstance(self.primary_provider, AlchemyProvider):
            await self.primary_provider.subscribe_to_price_updates(
                token_address,
                callback
            )
        else:
            raise NotImplementedError(
                "Price subscriptions require Alchemy provider"
            )

    async def get_gas_price_prediction(
        self,
        force_refresh: bool = False
    ) -> Dict[str, int]:
        """
        Get gas price predictions.

        Args:
            force_refresh: Force cache refresh

        Returns:
            Dict containing gas price predictions
        """
        now = time.monotonic()  # Use monotonic time instead of event loop time
        
        # Check cache
        if not force_refresh and self._last_gas_prediction:
            prediction, timestamp = self._last_gas_prediction
            if (now - timestamp) < self._gas_prediction_ttl:
                return prediction

        # Use Alchemy if available
        if isinstance(self.primary_provider, AlchemyProvider):
            prediction = await self.primary_provider.get_gas_price_prediction()
            self._last_gas_prediction = (prediction, now)
            return prediction

        # Fallback to basic gas price
        gas_price = await self.w3.eth.gas_price
        return {
            "safe_low": gas_price,
            "standard": int(gas_price * 1.1),
            "fast": int(gas_price * 1.2),
            "fastest": int(gas_price * 1.3)
        }

    async def simulate_transaction(
        self,
        tx_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate transaction with asset changes.

        Args:
            tx_params: Transaction parameters

        Returns:
            Simulation results
        """
        if isinstance(self.primary_provider, AlchemyProvider):
            return await self.primary_provider.simulate_asset_changes(tx_params)
        else:
            # Fallback to eth_call
            return await self.w3.eth.call(tx_params)

    async def monitor_mempool(
        self,
        filter_criteria: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Monitor mempool for pending transactions.

        Args:
            filter_criteria: Optional criteria to filter transactions

        Returns:
            List of pending transactions
        """
        if isinstance(self.primary_provider, AlchemyProvider):
            return await self.primary_provider.get_pending_transactions(
                filter_criteria
            )
        else:
            # Fallback to eth_getBlockByNumber
            block = await self.w3.eth.get_block('pending', True)
            return block.transactions

    async def _fetch_onchain_prices(
        self,
        token_addresses: List[str]
    ) -> Dict[str, Decimal]:
        """Fallback method to fetch prices from on-chain sources."""
        # Implementation would use DEX pools or price feeds
        pass

    async def close(self):
        """Close all connections."""
        await self.primary_provider.close()
        for provider in self.backup_providers:
            await provider.close()

async def create_web3_manager(config: Dict[str, Any]) -> Web3Manager:
    """
    Create and initialize a Web3Manager instance.

    Args:
        config: Configuration dictionary

    Returns:
        Initialized Web3Manager instance
    """
    manager = Web3Manager(config)
    await manager.initialize()
    return manager
