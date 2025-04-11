"""RPC provider management with rotation and rate limiting."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable, TypeVar, Awaitable
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.exceptions import TimeExhausted, Web3Exception

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RPCEndpoint:
    """RPC endpoint configuration and state tracking."""

    url: str
    request_count: int = 0
    last_request: float = 0
    last_error: float = 0
    consecutive_errors: int = 0
    is_active: bool = True


class RPCProviderManager:
    """Manages multiple RPC providers with rotation and rate limiting."""

    def __init__(self, endpoints: List[str], min_request_interval: float = 0.1):
        """
        Initialize RPC provider manager.

        Args:
            endpoints: List of RPC endpoint URLs
            min_request_interval: Minimum time between requests in seconds
        """
        if not endpoints:
            raise ValueError("At least one RPC endpoint is required")

        self.endpoints = [RPCEndpoint(url=url) for url in endpoints]
        self.min_request_interval = min_request_interval
        self.current_index = 0
        self.request_queue = asyncio.Queue()
        self.lock = asyncio.Lock()

        # Default headers
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "User-Agent": "arbitrage_bot/1.0.0",
        }

    def _get_next_endpoint(self) -> RPCEndpoint:
        """Get next available endpoint using round-robin."""
        with_retries = 0
        while with_retries < len(self.endpoints):
            endpoint = self.endpoints[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.endpoints)

            if endpoint.is_active:
                # Check if endpoint has recovered from errors
                if endpoint.consecutive_errors > 0:
                    backoff_time = min(60, 2**endpoint.consecutive_errors)
                    if time.time() - endpoint.last_error > backoff_time:
                        endpoint.consecutive_errors = 0
                        endpoint.is_active = True
                        return endpoint
                else:
                    return endpoint

            with_retries += 1

        raise Web3Exception("No healthy RPC endpoints available")

    async def get_provider(self) -> AsyncHTTPProvider:
        """Get Web3 provider with rate limiting and rotation."""
        async with self.lock:
            endpoint = self._get_next_endpoint()

            # Apply rate limiting
            if endpoint.last_request:
                time_since_last = time.time() - endpoint.last_request
                if time_since_last < self.min_request_interval:
                    await asyncio.sleep(self.min_request_interval - time_since_last)

            # Update endpoint state
            endpoint.last_request = time.time()
            endpoint.request_count += 1

            return AsyncHTTPProvider(
                endpoint.url, request_kwargs={"headers": self.headers}
            )

    def handle_success(self, provider: AsyncHTTPProvider) -> None:
        """Handle successful requests and update endpoint state."""
        if not provider or not provider.endpoint_uri:
            return

        endpoint_url = str(provider.endpoint_uri)
        for endpoint in self.endpoints:
            if endpoint.url == endpoint_url:
                endpoint.consecutive_errors = 0
                endpoint.is_active = True
                break

    def handle_error(self, provider: AsyncHTTPProvider, error: Exception) -> None:
        """Handle provider errors and update endpoint state."""
        if not provider or not provider.endpoint_uri:
            return

        endpoint_url = str(provider.endpoint_uri)
        for endpoint in self.endpoints:
            if endpoint.url == endpoint_url:
                endpoint.last_error = time.time()
                endpoint.consecutive_errors += 1

                # Disable endpoint temporarily if too many consecutive errors
                if endpoint.consecutive_errors >= 3:
                    endpoint.is_active = False
                    logger.warning(
                        f"Temporarily disabled RPC endpoint {endpoint_url} due to consecutive errors"
                    )

                # Special handling for rate limit errors
                if isinstance(error, Exception) and "429" in str(error):
                    logger.warning(
                        f"Rate limit hit for {endpoint_url}, backing off exponentially"
                    )
                break

    async def execute_with_retry(
        self,
        operation: Callable[[AsyncHTTPProvider], Awaitable[T]],
        max_retries: int = 3,
    ) -> T:
        """
        Execute operation with automatic retries and provider rotation.

        Args:
            operation: Async function that takes a provider and returns a result
            max_retries: Maximum number of retry attempts

        Returns:
            Result of the operation

        Raises:
            Web3Exception: If all retries fail
        """
        last_error: Optional[Exception] = None
        provider: Optional[AsyncHTTPProvider] = None

        for attempt in range(max_retries):
            try:
                provider = await self.get_provider()
                result = await operation(provider)
                self.handle_success(provider)
                return result

            except Exception as e:
                last_error = e
                if provider:
                    self.handle_error(provider, e)

                if attempt < max_retries - 1:
                    backoff_time = 2**attempt
                    logger.warning(
                        f"Request failed, retrying in {backoff_time}s: {str(e)}"
                    )
                    await asyncio.sleep(backoff_time)

        raise Web3Exception(f"All retries failed: {str(last_error)}") from last_error

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get current statistics for all endpoints."""
        return {
            endpoint.url: {
                "requests": endpoint.request_count,
                "errors": endpoint.consecutive_errors,
                "active": endpoint.is_active,
                "last_request": endpoint.last_request,
                "last_error": endpoint.last_error,
            }
            for endpoint in self.endpoints
        }
