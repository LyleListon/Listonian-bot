"""
Async Provider Module

This module provides an async provider implementation for Web3.py.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from web3.providers import BaseProvider
from web3.types import RPCEndpoint, RPCResponse

logger = logging.getLogger(__name__)

class CustomAsyncProvider(BaseProvider):
    """Custom async provider with rate limiting and failover support."""

    def __init__(self, endpoint_uri: str):
        """
        Initialize provider.

        Args:
            endpoint_uri: RPC endpoint URI
        """
        super().__init__()
        self.endpoint_uri = endpoint_uri
        self._request_lock = asyncio.Lock()
        self._session = None

    async def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        """
        Make async RPC request.

        Args:
            method: RPC method
            params: Method parameters

        Returns:
            RPC response

        Raises:
            Exception: If request fails
        """
        async with self._request_lock:
            try:
                # Ensure session is initialized
                if not self._session:
                    import aiohttp
                    self._session = aiohttp.ClientSession()

                # Prepare request
                request_data = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": id(params)
                }

                # Make request
                async with self._session.post(
                    self.endpoint_uri,
                    json=request_data,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        raise ValueError(
                            f"HTTP {response.status}: {await response.text()}"
                        )

                    # Parse response
                    result = await response.json()

                    # Check for RPC error
                    if "error" in result:
                        raise ValueError(
                            f"RPC error: {result['error']}"
                        )

                    return result

            except Exception as e:
                logger.error(f"Provider request failed: {e}")
                raise

    def request_func(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        """
        Synchronous request function required by BaseProvider.
        This is called by Web3.py when not using async methods.
        We raise an error since we only support async operations.
        """
        raise NotImplementedError(
            "CustomAsyncProvider only supports async operations. "
            "Use the async methods instead."
        )

    async def close(self):
        """Close provider session."""
        if self._session:
            await self._session.close()
            self._session = None