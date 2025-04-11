"""Flashbots provider implementation for MEV protection."""

import logging
import json
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from eth_account.account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

logger = logging.getLogger(__name__)


class FlashbotsError(Exception):
    """Base exception for Flashbots related errors."""

    pass


class FlashbotsProvider:
    """Provider for Flashbots API interaction."""

    def __init__(self, w3, auth_signer, relay_url):
        """Initialize Flashbots provider."""
        self.w3 = w3
        self.auth_signer = auth_signer
        self.relay_url = relay_url
        self.session = None
        self._session_lock = asyncio.Lock()
        self._closed = False
        logger.info("Initialized Flashbots provider with relay URL: %s", relay_url)

    async def __aenter__(self):
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure proper cleanup when used as context manager."""
        await self.close()
        return False  # Don't suppress exceptions

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._closed:
            raise FlashbotsError("Cannot use closed Flashbots provider")

        async with self._session_lock:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),  # 30 second timeout
                    raise_for_status=True,
                )
                logger.debug("Created new aiohttp session for Flashbots provider")
        return self.session

    def is_closed(self):
        """Check if provider is closed."""
        return self._closed

    async def close(self):
        """Close the aiohttp session and cleanup resources."""
        if self._closed:
            return

        async with self._session_lock:
            if self.session:
                try:
                    await self.session.close()
                    logger.debug("Closed aiohttp session for Flashbots provider")
                except Exception as e:
                    logger.warning("Error closing Flashbots session: %s", str(e))
                self.session = None
            self._closed = True

    async def _sign_request(self, endpoint, params):
        """Sign request for Flashbots authentication using the auth signer."""
        message = encode_defunct(text=json.dumps(params))
        signature = self.auth_signer.sign_message(message)
        headers = {
            "X-Flashbots-Signature": "{}:{}".format(
                self.auth_signer.address, signature.signature.hex()
            ),
            "Content-Type": "application/json",
        }
        return headers

    async def simulate(
        self, txs: List[Dict[str, Any]], block_tag: str = "latest"
    ) -> Dict[str, Any]:
        """Simulate a bundle of transactions."""
        if self._closed:
            raise FlashbotsError("Cannot use closed Flashbots provider")
        try:
            session = await self._get_session()

            # Prepare simulation params
            params = {
                "txs": txs,
                "blockNumber": block_tag,
                "stateBlockNumber": "latest",
            }

            # Sign request
            headers = await self._sign_request("/simulate", params)

            # Send simulation request
            async with session.post(
                self.relay_url + "/simulate", headers=headers, json=params
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise FlashbotsError(f"Simulation failed: {error}")

                result = await response.json()
                logger.debug("Bundle simulation completed successfully")
                return result
        except Exception as e:
            logger.error("Failed to simulate bundle: %s", str(e))
            raise

    async def send_bundle(
        self, txs: List[Dict[str, Any]], target_block_number: int
    ) -> Dict[str, Any]:
        """Send a bundle to Flashbots."""
        if self._closed:
            raise FlashbotsError("Cannot use closed Flashbots provider")
        try:
            session = await self._get_session()

            # Prepare bundle params
            params = {"txs": txs, "blockNumber": str(target_block_number)}

            # Sign request
            headers = await self._sign_request("/bundle", params)

            # Send bundle request
            async with session.post(
                self.relay_url + "/bundle", headers=headers, json=params
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise FlashbotsError(f"Bundle submission failed: {error}")

                result = await response.json()
                logger.debug("Bundle submitted successfully to Flashbots relay")
                return result
        except Exception as e:
            logger.error("Failed to send bundle: %s", str(e))
            raise

    async def get_bundle_stats(self, bundle_id: str) -> Dict[str, Any]:
        """Get statistics for a bundle."""
        if self._closed:
            raise FlashbotsError("Cannot use closed Flashbots provider")
        try:
            session = await self._get_session()

            # Prepare stats params
            params = {"bundleId": bundle_id}

            # Sign request
            headers = await self._sign_request("/bundle/stats", params)

            # Get bundle stats
            async with session.get(
                self.relay_url + "/bundle/stats", headers=headers, params=params
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise FlashbotsError(f"Failed to get bundle stats: {error}")

                result = await response.json()
                logger.debug("Retrieved bundle stats successfully")
                return result
        except Exception as e:
            logger.error("Failed to get bundle stats: %s", str(e))
            raise

    async def get_user_stats(self) -> Dict[str, Any]:
        """Get statistics for the current user."""
        if self._closed:
            raise FlashbotsError("Cannot use closed Flashbots provider")
        try:
            session = await self._get_session()

            # Sign request
            headers = await self._sign_request("/stats", {})

            # Get user stats
            async with session.get(
                self.relay_url + "/stats", headers=headers
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise FlashbotsError(f"Failed to get user stats: {error}")

                result = await response.json()
                logger.debug("Retrieved user stats successfully")
                return result
        except Exception as e:
            logger.error("Failed to get user stats: %s", str(e))
            raise
