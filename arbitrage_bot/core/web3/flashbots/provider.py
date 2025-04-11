"""
Flashbots Provider

This module contains the implementation of the Flashbots provider, which
handles interactions with the Flashbots RPC endpoint for bundle submission and tracking.
"""

import asyncio
import json
import logging
# import time # Unused
# from decimal import Decimal # Unused
from typing import Dict, Any, Optional, Callable # Removed List, Tuple, Union, cast
from eth_account import Account
from eth_account.signers.local import LocalAccount
# from eth_typing import HexStr, URI # Unused
from web3 import Web3, HTTPProvider
from web3.types import RPCEndpoint # Removed Wei

from ...web3.interfaces import Web3Client # Removed Transaction
# from .interfaces import ( # All unused
#     FlashbotsBundle,
#     BundleSimulationResult,
#     BundleSubmissionResult,
#     BundleStatsResult,
# )

logger = logging.getLogger(__name__)


class FlashbotsProvider:
    """
    Provider for interacting with Flashbots.

    This provider enables private transaction submission to miners through
    the Flashbots relay, protecting transactions from front-running and
    other MEV attacks.
    """

    # Flashbots relay endpoints
    MAINNET_RELAY_URL = "https://relay.flashbots.net"
    GOERLI_RELAY_URL = "https://relay-goerli.flashbots.net"
    SEPOLIA_RELAY_URL = "https://relay-sepolia.flashbots.net"

    # RPC methods
    SEND_BUNDLE = RPCEndpoint("eth_sendBundle")
    CALL_BUNDLE = RPCEndpoint("eth_callBundle")
    SIMULATE_BUNDLE = RPCEndpoint("eth_simulateBundle")
    GET_BUNDLE_STATS = RPCEndpoint("flashbots_getBundleStats")
    GET_USER_STATS = RPCEndpoint("flashbots_getUserStats")

    def __init__(
        self,
        web3_client: Web3Client,
        signing_key: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Flashbots provider.

        Args:
            web3_client: Web3 client for blockchain interactions
            signing_key: Private key for signing bundles (without 0x prefix)
            config: Configuration parameters for the provider
        """
        self.web3_client = web3_client
        self.config = config or {}

        # Configuration
        self.network = self.config.get("network", "mainnet").lower()
        self.max_block_priority_fee = self.config.get("max_block_priority_fee", 2.5)
        self.blocks_into_future = self.config.get("blocks_into_future", 2)
        self.relay_timeout = self.config.get("relay_timeout", 30)  # seconds

        # Set up relay URL based on network
        if self.network == "goerli":
            self.relay_url = self.GOERLI_RELAY_URL
        elif self.network == "sepolia":
            self.relay_url = self.SEPOLIA_RELAY_URL
        else:  # mainnet
            self.relay_url = self.MAINNET_RELAY_URL

        # Override relay URL if provided in config
        self.relay_url = self.config.get("relay_url", self.relay_url)

        # Set up signing account
        self.signing_account = Account.from_key(signing_key)

        # Get chain ID
        self.chain_id = self.config.get("chain_id", None)

        # Set up relay provider
        self.flashbots_web3 = None

        # State
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """
        Initialize the Flashbots provider.

        This method sets up the connection to the Flashbots relay and
        ensures the provider is ready for use.

        Returns:
            True if initialization succeeds, False otherwise
        """
        async with self._initialization_lock:
            if self._is_initialized:
                logger.debug("Flashbots provider already initialized")
                return True

            try:
                logger.info(
                    f"Initializing Flashbots provider for network {self.network}"
                )

                # Get chain ID if not provided
                if not self.chain_id:
                    self.chain_id = await self.web3_client.get_chain_id()

                # Create a new web3 instance for Flashbots
                self.flashbots_web3 = Web3(HTTPProvider(self.relay_url))

                # Inject Flashbots middleware
                self._inject_flashbots_middleware()

                # Verify connection
                if not await self.is_operational():
                    logger.warning("Failed to verify Flashbots connection")
                    return False

                self._is_initialized = True
                logger.info("Flashbots provider initialized successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to initialize Flashbots provider: {e}")
                return False

    def _inject_flashbots_middleware(self) -> None:
        """
        Inject Flashbots middleware into the Web3 instance.

        This method adds the necessary authentication headers to RPC requests.
        """

        class FlashbotsMiddleware:
            """Middleware for Flashbots request signing."""

            def __init__(self, account: LocalAccount, provider: "FlashbotsProvider"):
                self.account = account
                self.provider = provider
                self.w3 = None

            def __call__(self, w3: Web3) -> "FlashbotsMiddleware":
                """
                Called when middleware is added to web3 instance.

                Args:
                    w3: Web3 instance

                Returns:
                    Self for middleware registration
                """
                self.w3 = w3
                return self

            def wrap_make_request(
                self, make_request: Callable[[str, list], Any]
            ) -> Callable[[str, list], Any]:
                """
                Wrap the make_request function with Flashbots signing functionality.

                Args:
                    make_request: Original make_request function to wrap

                Returns:
                    Wrapped make_request function
                """

                def middleware(method: str, params: list) -> Any:
                    # Only intercept Flashbots methods
                    if method in [
                        self.provider.SEND_BUNDLE,
                        self.provider.CALL_BUNDLE,
                        self.provider.SIMULATE_BUNDLE,
                        self.provider.GET_BUNDLE_STATS,
                        self.provider.GET_USER_STATS,
                    ]:
                        request = {"method": method, "params": params}
                        request_json = json.dumps(request)

                        # Calculate signature
                        message = Web3.solidity_keccak(["string"], [request_json])
                        signed_message = self.account.sign_message(message)

                        # Add headers
                        headers = {
                            "X-Flashbots-Signature": f"{self.account.address}:{signed_message.signature.hex()}",
                            "Content-Type": "application/json",
                        }

                        # Make request directly
                        return make_request(method, params)

                    # For non-Flashbots methods, use regular provider
                    return make_request(method, params)

                return middleware

        # Inject middleware
        middleware = FlashbotsMiddleware(self.signing_account, self)
        self.flashbots_web3.middleware_onion.add(middleware, name="flashbots")

    async def is_operational(self) -> bool:
        """
        Check if the Flashbots provider is operational.

        Returns:
            True if the provider is operational, False otherwise
        """
        try:
            # Try to get block number as a simple check
            block_number = await self.web3_client.get_block_number()
            return block_number > 0
        except Exception as e:
            logger.error(f"Flashbots provider operational check failed: {e}")
            return False
