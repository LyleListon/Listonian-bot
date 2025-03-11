"""
Enhanced Alchemy Provider

This module provides an enhanced Alchemy provider that leverages Alchemy's specialized APIs for:
- Token price fetching
- WebSocket subscriptions
- Mempool monitoring
- Gas predictions
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Union
from web3 import Web3
from web3.types import RPCEndpoint, RPCResponse
from decimal import Decimal

from .async_provider import CustomAsyncProvider
from ..utils.async_manager import AsyncLock

logger = logging.getLogger(__name__)

class AlchemyProvider(CustomAsyncProvider):
    """Enhanced Alchemy provider with specialized API support."""

    def __init__(
        self,
        endpoint_uri: str,
        api_key: str,
        websocket_uri: Optional[str] = None
    ):
        """
        Initialize Alchemy provider.

        Args:
            endpoint_uri: HTTP RPC endpoint
            api_key: Alchemy API key
            websocket_uri: Optional WebSocket endpoint
        """
        super().__init__(endpoint_uri)
        self.api_key = api_key
        self.websocket_uri = websocket_uri
        self._ws = None
        self._price_subscriptions = {}
        self._mempool_subscriptions = set()
        self._subscription_lock = AsyncLock()
        self.base_api_url = "https://base-mainnet.g.alchemy.com/v2/"

    async def initialize(self):
        """Initialize provider and establish WebSocket connection."""
        if self.websocket_uri:
            try:
                import websockets
                self._ws = await websockets.connect(self.websocket_uri)
                logger.info("WebSocket connection established")
            except Exception as e:
                logger.error(f"Failed to establish WebSocket connection: {e}")

    async def get_token_prices(
        self,
        token_addresses: List[str],
        quote_currency: str = "USD"
    ) -> Dict[str, Decimal]:
        """
        Get current prices for multiple tokens using Alchemy Token API.

        Args:
            token_addresses: List of token addresses
            quote_currency: Quote currency (default: USD)

        Returns:
            Dict mapping token addresses to prices
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_api_url}{self.api_key}/token-api/getTokenPrices"
                params = {
                    "tokens": token_addresses,
                    "quote": quote_currency
                }
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise ValueError(f"HTTP {response.status}: {await response.text()}")
                    
                    data = await response.json()
                    return {
                        token: Decimal(str(price_data["price"]))
                        for token, price_data in data["prices"].items()
                    }

        except Exception as e:
            logger.error(f"Failed to fetch token prices: {e}")
            return {}

    async def subscribe_to_price_updates(
        self,
        token_address: str,
        callback: callable
    ):
        """
        Subscribe to real-time price updates for a token.

        Args:
            token_address: Token address to monitor
            callback: Async callback function for price updates
        """
        if not self._ws:
            raise ValueError("WebSocket connection not established")

        async with self._subscription_lock:
            subscription_id = f"price_{token_address}"
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "alchemy_tokenPriceUpdates",
                    {"token": token_address}
                ]
            }
            await self._ws.send(message)
            self._price_subscriptions[subscription_id] = callback

    async def get_pending_transactions(
        self,
        filter_criteria: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Get pending transactions from mempool with optional filtering.

        Args:
            filter_criteria: Optional criteria to filter transactions

        Returns:
            List of pending transactions
        """
        try:
            params = ["pending"]
            if filter_criteria:
                params.append(filter_criteria)

            result = await self.make_request(
                RPCEndpoint("eth_getBlockByNumber"),
                params
            )
            return result.get("transactions", [])

        except Exception as e:
            logger.error(f"Failed to get pending transactions: {e}")
            return []

    async def get_gas_price_prediction(self) -> Dict[str, int]:
        """
        Get gas price predictions using Alchemy's gas estimator.

        Returns:
            Dict containing:
                - safe_low: Safe low gas price
                - standard: Standard gas price
                - fast: Fast gas price
                - fastest: Fastest gas price
        """
        try:
            url = f"{self.base_api_url}{self.api_key}/gas-api/getPrices"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"HTTP {response.status}: {await response.text()}")
                    
                    data = await response.json()
                    return {
                        "safe_low": int(data["safeLow"]),
                        "standard": int(data["standard"]),
                        "fast": int(data["fast"]),
                        "fastest": int(data["fastest"])
                    }

        except Exception as e:
            logger.error(f"Failed to get gas price prediction: {e}")
            return {
                "safe_low": 0,
                "standard": 0,
                "fast": 0,
                "fastest": 0
            }

    async def simulate_asset_changes(
        self,
        tx_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate asset changes from a transaction using Alchemy Simulator.

        Args:
            tx_params: Transaction parameters

        Returns:
            Dict containing asset changes and gas estimates
        """
        try:
            url = f"{self.base_api_url}{self.api_key}/simulator/simulate"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=tx_params) as response:
                    if response.status != 200:
                        raise ValueError(f"HTTP {response.status}: {await response.text()}")
                    
                    return await response.json()

        except Exception as e:
            logger.error(f"Failed to simulate asset changes: {e}")
            return {}

    async def _handle_websocket_messages(self):
        """Handle incoming WebSocket messages."""
        if not self._ws:
            return

        try:
            while True:
                message = await self._ws.recv()
                data = Web3.json.loads(message)
                
                if "method" in data:
                    subscription_id = data["params"]["subscription"]
                    if subscription_id in self._price_subscriptions:
                        await self._price_subscriptions[subscription_id](data["params"]["result"])

        except Exception as e:
            logger.error(f"WebSocket message handling error: {e}")

    async def close(self):
        """Close provider connections."""
        await super().close()
        if self._ws:
            await self._ws.close()
            self._ws = None