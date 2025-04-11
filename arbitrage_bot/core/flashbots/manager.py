"""
Flashbots manager module.

This module provides the core functionality for interacting with Flashbots RPC,
including private transaction submission and MEV protection.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from web3 import Web3
from web3.types import TxParams, HexStr
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress

logger = logging.getLogger(__name__)


class FlashbotsManager:
    """
    Manages Flashbots RPC interactions and MEV protection.

    This class handles:
    - Private transaction routing
    - Bundle submission
    - Front-running protection
    - Sandwich attack prevention
    """

    def __init__(
        self,
        web3: Web3,
        flashbots_endpoint: str,
        private_key: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize the Flashbots manager.

        Args:
            web3: Web3 instance
            flashbots_endpoint: Flashbots RPC endpoint URL
            private_key: Private key for signing bundles
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.web3 = web3
        self.flashbots_endpoint = flashbots_endpoint
        self.account = self.web3.eth.account.from_key(private_key)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._lock = asyncio.Lock()
        self._initialized = False

        # Validate address checksum
        if not Web3.is_checksum_address(self.account.address):
            raise ValueError("Account address must be checksummed")

        logger.info(f"Initialized FlashbotsManager with account {self.account.address}")

    async def initialize(self) -> bool:
        """
        Initialize Flashbots connection and authentication.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            async with self._lock:
                if self._initialized:
                    return True

                # Set up Flashbots provider
                await self._setup_flashbots_provider()

                # Test connection
                await self._test_connection()

                self._initialized = True
                logger.info("FlashbotsManager initialized successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize FlashbotsManager: {e}")
            return False

    async def _setup_flashbots_provider(self) -> None:
        """Set up Flashbots RPC provider with authentication."""
        try:
            # Sign Flashbots auth message
            auth_msg = f"Flashbots {self.account.address}"
            signature = self.account.sign_message(auth_msg).signature.hex()

            # Configure provider headers
            self.headers = {
                "X-Flashbots-Signature": f"{self.account.address}:{signature}"
            }

            logger.debug("Flashbots provider configured")

        except Exception as e:
            logger.error(f"Failed to setup Flashbots provider: {e}")
            raise

    async def _test_connection(self) -> None:
        """Test Flashbots RPC connection."""
        try:
            # Send test request
            await self._make_request("flashbots_status")
            logger.debug("Flashbots connection test successful")

        except Exception as e:
            logger.error(f"Flashbots connection test failed: {e}")
            raise

    async def _make_request(
        self, method: str, params: Optional[list] = None, retries: int = 0
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Flashbots RPC.

        Args:
            method: RPC method name
            params: RPC method parameters
            retries: Current retry attempt number

        Returns:
            Dict[str, Any]: RPC response

        Raises:
            Exception: If request fails after max retries
        """
        try:
            # Build request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or [],
            }

            # Send request
            response = await self.web3.eth.request_blocking(
                method, params or [], request_kwargs={"headers": self.headers}
            )

            return response

        except Exception as e:
            if retries < self.max_retries:
                logger.warning(
                    f"Flashbots request failed, retrying ({retries + 1}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(self.retry_delay)
                return await self._make_request(method, params, retries + 1)
            else:
                logger.error(
                    f"Flashbots request failed after {self.max_retries} retries: {e}"
                )
                raise

    async def submit_private_transaction(
        self, transaction: TxParams, block_number: Optional[int] = None
    ) -> HexStr:
        """
        Submit a private transaction through Flashbots.

        Args:
            transaction: Transaction parameters
            block_number: Target block number (optional)

        Returns:
            HexStr: Transaction hash

        Raises:
            Exception: If transaction submission fails
        """
        if not self._initialized:
            raise RuntimeError("FlashbotsManager not initialized")

        try:
            # Sign transaction
            signed_tx = self.account.sign_transaction(transaction)

            # Prepare submission params
            params = [
                {
                    "signed_transaction": signed_tx.rawTransaction.hex(),
                    "block_number": block_number or "latest",
                }
            ]

            # Submit transaction
            response = await self._make_request("eth_sendPrivateTransaction", params)

            tx_hash = response["result"]
            logger.info(f"Successfully submitted private transaction: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Failed to submit private transaction: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            async with self._lock:
                self._initialized = False
                logger.info("FlashbotsManager cleaned up")

        except Exception as e:
            logger.error(f"Error during FlashbotsManager cleanup: {e}")
            raise
