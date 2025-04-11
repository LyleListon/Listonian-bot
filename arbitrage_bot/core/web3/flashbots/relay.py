"""
Flashbots Relay Module

This module provides functionality for:
- Flashbots RPC connection
- Authentication
- Request signing
- Response validation
"""

# import asyncio # Unused
import logging
import json
from typing import Any, Dict, Optional
from eth_account import Account
# from eth_account.signers.local import LocalAccount # Unused
from eth_typing import HexStr
from web3 import Web3
from web3.types import RPCEndpoint

from ....utils.async_manager import with_retry, AsyncLock

logger = logging.getLogger(__name__)


class FlashbotsRelay:
    """Manages Flashbots relay connection and authentication."""

    def __init__(
        self,
        w3: Web3,
        relay_url: str,
        auth_key: Optional[str] = None,
        chain_id: int = 8453,  # Base mainnet
    ):
        """
        Initialize Flashbots relay.

        Args:
            w3: Web3 instance
            relay_url: Flashbots relay URL
            auth_key: Optional authentication key
            chain_id: Chain ID
        """
        self.w3 = w3
        self.relay_url = relay_url
        self.chain_id = chain_id

        # Set up authentication
        self.auth_signer = None
        if auth_key:
            self.auth_signer = Account.from_key(auth_key)

        # Initialize locks
        self._request_lock = AsyncLock()

        logger.info(
            f"Flashbots relay initialized for chain {chain_id} "
            f"with auth signer {self.auth_signer.address if self.auth_signer else 'None'}"
        )

    def _sign_request(self, method: RPCEndpoint, params: Any) -> HexStr:
        """
        Sign RPC request.

        Args:
            method: RPC method
            params: Request parameters

        Returns:
            Request signature

        Raises:
            ValueError: If no auth signer configured
        """
        if not self.auth_signer:
            raise ValueError("No auth signer configured")

        # Create message
        message = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        message_hash = self.w3.keccak(text=json.dumps(message, sort_keys=True))

        # Sign message
        signature = self.auth_signer.sign_message(message_hash)
        return HexStr(signature.signature.hex())

    @with_retry(retries=3, delay=1.0)
    async def send_request(self, method: RPCEndpoint, params: Any) -> Dict[str, Any]:
        """
        Send authenticated request to Flashbots relay.

        Args:
            method: RPC method
            params: Request parameters

        Returns:
            Response data
        """
        async with self._request_lock:
            try:
                # Sign request
                signature = self._sign_request(method, params)

                # Add authentication headers
                headers = {
                    "X-Flashbots-Signature": signature,
                    "X-Flashbots-Chain-Id": str(self.chain_id),
                }

                # Make RPC call
                response = await self.w3.eth.call(
                    {
                        "to": self.relay_url,
                        "data": self.w3.eth.abi.encode_abi(
                            ["tuple(string method, bytes params, bytes signature)"],
                            [
                                {
                                    "method": method,
                                    "params": self.w3.eth.abi.encode_abi(
                                        ["tuple(bytes)"], [params]
                                    ),
                                    "signature": signature,
                                }
                            ],
                        ),
                    }
                )

                # Parse response
                result = self.w3.eth.abi.decode_abi(
                    ["tuple(bool success, bytes result)"], response
                )[0]

                if not result[0]:
                    error = json.loads(result[1])
                    raise ValueError(
                        f"RPC request failed: {error.get('error', 'Unknown error')}"
                    )

                return json.loads(result[1])

            except Exception as e:
                logger.error(f"Failed to send request to Flashbots relay: {e}")
                raise

    @with_retry(retries=3, delay=1.0)
    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics from Flashbots relay.

        Returns:
            User statistics
        """
        try:
            response = await self.send_request(
                method="flashbots_getUserStats", params=[]
            )
            return response

        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {"success": False, "error": str(e)}

    @with_retry(retries=3, delay=1.0)
    async def get_bundle_stats(self, bundle_hash: HexStr) -> Dict[str, Any]:
        """
        Get bundle statistics from Flashbots relay.

        Args:
            bundle_hash: Bundle hash

        Returns:
            Bundle statistics
        """
        try:
            response = await self.send_request(
                method="flashbots_getBundleStats", params=[bundle_hash]
            )
            return response

        except Exception as e:
            logger.error(f"Failed to get bundle stats: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Clean up resources."""
        pass


async def create_flashbots_relay(
    w3: Web3, relay_url: str, auth_key: Optional[str] = None, chain_id: int = 8453
) -> FlashbotsRelay:
    """
    Create a new Flashbots relay instance.

    Args:
        w3: Web3 instance
        relay_url: Flashbots relay URL
        auth_key: Optional authentication key
        chain_id: Chain ID

    Returns:
        FlashbotsRelay instance
    """
    return FlashbotsRelay(
        w3=w3, relay_url=relay_url, auth_key=auth_key, chain_id=chain_id
    )
