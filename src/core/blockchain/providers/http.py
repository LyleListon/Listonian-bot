"""HTTP provider implementation with retry logic."""

import asyncio
import logging
from typing import Any, Dict, Optional, Union

from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.types import RPCEndpoint, RPCResponse
from web3.exceptions import Web3Exception

from .base import BaseProvider

logger = logging.getLogger(__name__)

class HttpProvider(BaseProvider):
    """HTTP provider implementation with retry and error handling."""

    async def connect(self) -> None:
        """Connect to the blockchain network.
        
        Implements retry logic and middleware setup for HTTP connections.
        
        Raises:
            ConnectionError: If connection fails after retries
        """
        try:
            provider = AsyncHTTPProvider(self.url)
            self._web3 = AsyncWeb3(provider)

            # Add retry middleware
            def retry_middleware(make_request, w3):
                async def middleware(method, params):
                    for attempt in range(self.retry_count):
                        try:
                            return await make_request(method, params)
                        except Exception as e:
                            if attempt == self.retry_count - 1:
                                raise
                            delay = 0.5 * (2 ** attempt)
                            logger.warning(
                                f"Request failed, retrying in {delay}s "
                                f"(attempt {attempt + 1}/{self.retry_count}): {e}"
                            )
                            await asyncio.sleep(delay)
                return middleware

            self._web3.middleware_onion.inject(retry_middleware, layer=0)

            # Verify connection
            chain_id = await self._web3.eth.chain_id
            if chain_id != self.chain_id:
                raise ConnectionError(
                    f"Chain ID mismatch. Expected {self.chain_id}, got {chain_id}"
                )

            logger.info(
                f"Connected to network {self.chain_id} at {self.url}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to {self.url}: {e}")
            raise ConnectionError(f"Failed to connect: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the blockchain network."""
        if self._web3:
            await self._web3.provider.disconnect()
            self._web3 = None
            logger.info("Disconnected from network")

    async def is_connected(self) -> bool:
        """Check if provider is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self._web3:
            return False
        try:
            await self._web3.eth.get_block_number()
            return True
        except Exception:
            return False

    async def make_request(
        self,
        method: Union[RPCEndpoint, str],
        params: Optional[Any] = None
    ) -> RPCResponse:
        """Make an RPC request with retry logic.
        
        Args:
            method: RPC method to call
            params: Parameters for the RPC call
            
        Returns:
            RPCResponse: Response from the RPC call
            
        Raises:
            Web3Error: If request fails after retries
        """
        try:
            return await self.web3.provider.make_request(method, params)
        except Web3Exception as e:
            logger.error(f"RPC request failed: {e}")
            raise

    async def get_block_number(self) -> int:
        """Get current block number.
        
        Returns:
            int: Current block number
            
        Raises:
            Web3Error: If request fails
        """
        try:
            return await self.web3.eth.block_number
        except Web3Exception as e:
            logger.error(f"Failed to get block number: {e}")
            raise

    async def get_gas_price(self) -> int:
        """Get current gas price.
        
        Returns:
            int: Current gas price in wei
            
        Raises:
            Web3Error: If request fails
        """
        try:
            return await self.web3.eth.gas_price
        except Web3Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            raise

    async def estimate_gas(
        self,
        transaction: Dict[str, Any]
    ) -> int:
        """Estimate gas for transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            int: Estimated gas cost
            
        Raises:
            Web3Error: If estimation fails
        """
        try:
            return await self.web3.eth.estimate_gas(transaction)
        except Web3Exception as e:
            logger.error(f"Failed to estimate gas: {e}")
            raise