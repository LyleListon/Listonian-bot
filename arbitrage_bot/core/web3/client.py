"""
Web3 Client Implementation

This module provides the Web3 client implementation for blockchain interactions.
"""

import logging
# import aiohttp # Imported locally in make_request
import asyncio
from typing import Dict, Any, Optional, Union
from decimal import Decimal
from eth_typing import ChecksumAddress
from web3 import Web3, AsyncWeb3
from web3.providers import AsyncHTTPProvider
from web3.types import RPCEndpoint # Removed RPCResponse

from .interfaces import Web3Client, Contract, ContractWrapper

logger = logging.getLogger(__name__)


class Web3ClientImpl(Web3Client):
    """Implementation of the Web3Client interface."""

    def __init__(
        self, rpc_endpoint: str, chain: str, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Web3 client.

        Args:
            rpc_endpoint: RPC endpoint URL
            chain: Chain identifier (e.g., "base_mainnet")
            config: Additional configuration
        """
        self.rpc_endpoint = rpc_endpoint
        self.chain = chain
        self.config = config or {}
        self.web3 = None
        self._initialized = False
        self._initialization_lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the Web3 connection."""
        if self._initialized:
            logger.debug("Web3 client already initialized")
            return

        async with self._initialization_lock:
            if self._initialized:  # Double check under lock
                return

            logger.info(f"Initializing Web3 client for {self.chain}")
            logger.debug(f"Using RPC endpoint: {self.rpc_endpoint}")

            try:
                # Create provider with custom request timeout
                provider = AsyncHTTPProvider(
                    self.rpc_endpoint,
                    request_kwargs={
                        "timeout": 30,  # 30 second timeout
                        "headers": {
                            "Content-Type": "application/json",
                        },
                    },
                )

                # Create Web3 instance
                self.web3 = AsyncWeb3(provider)
                logger.debug("Created AsyncWeb3 instance")

                # Test connection with retries
                max_retries = 3
                retry_delay = 2  # seconds

                for attempt in range(max_retries):
                    try:
                        logger.debug(
                            f"Testing connection (attempt {attempt + 1}/{max_retries})"
                        )

                        # Make direct RPC calls to test connection
                        # Get chain ID
                        response = await provider.make_request(
                            RPCEndpoint("eth_chainId"), []
                        )
                        if "error" in response:
                            raise ValueError(f"RPC error: {response['error']}")
                        chain_id = int(response["result"], 16)
                        logger.debug(f"Connected to chain ID: {chain_id}")

                        # Get block number
                        response = await provider.make_request(
                            RPCEndpoint("eth_blockNumber"), []
                        )
                        if "error" in response:
                            raise ValueError(f"RPC error: {response['error']}")
                        block_number = int(response["result"], 16)
                        logger.info(
                            f"Connected to {self.chain} at block {block_number}"
                        )

                        # Test gas price retrieval
                        response = await provider.make_request(
                            RPCEndpoint("eth_gasPrice"), []
                        )
                        if "error" in response:
                            raise ValueError(f"RPC error: {response['error']}")
                        gas_price = int(response["result"], 16)
                        logger.debug(f"Current gas price: {gas_price / 10**9} gwei")

                        self._initialized = True
                        logger.info("Web3 client initialization completed successfully")
                        return

                    except asyncio.TimeoutError:
                        logger.warning(f"Connection attempt {attempt + 1} timed out")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                        else:
                            raise
                    except Exception as e:
                        logger.error(f"Error during attempt {attempt + 1}: {str(e)}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                        else:
                            raise

            except Exception as e:
                logger.error(
                    f"Failed to initialize Web3 client: {str(e)}", exc_info=True
                )
                raise

    def contract(self, address: ChecksumAddress, abi: Dict[str, Any]) -> Contract:
        """Get contract instance."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")

        contract = self.web3.eth.contract(address=address, abi=abi)
        return ContractWrapper(contract)

    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")

        try:
            response = await self.web3.provider.make_request(
                RPCEndpoint("eth_gasPrice"), []
            )
            if "error" in response:
                raise ValueError(f"RPC error: {response['error']}")
            return int(response["result"], 16)
        except Exception as e:
            logger.error(f"Error getting gas price: {str(e)}")
            raise

    async def get_block(self, block_identifier: Union[str, int]) -> Dict[str, Any]:
        """Get block by number or hash."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")

        try:
            # Convert block identifier to hex if it's a number
            if isinstance(block_identifier, int):
                block_identifier = hex(block_identifier)
            elif block_identifier == "latest":
                block_identifier = "latest"

            response = await self.web3.provider.make_request(
                RPCEndpoint("eth_getBlockByNumber"), [block_identifier, False]
            )
            if "error" in response:
                raise ValueError(f"RPC error: {response['error']}")

            block = response["result"]
            # Convert hex values to integers
            for key in ["number", "timestamp", "gasLimit", "gasUsed"]:
                if key in block and block[key]:
                    block[key] = int(block[key], 16)
            return block

        except Exception as e:
            logger.error(f"Error getting block: {str(e)}")
            raise

    def to_wei(self, value: Union[int, float, str, Decimal], currency: str) -> int:
        """Convert currency value to wei."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")

        return Web3.to_wei(value, currency)  # Use static method from Web3

    @property
    def eth(self) -> Any:
        """Get eth module."""
        if not self._initialized:
            raise RuntimeError("Web3 client not initialized")

        return self.web3.eth

    async def close(self):
        """Close the Web3 client and cleanup resources."""
        logger.debug("Closing Web3 client")
        self._initialized = False
        self.web3 = None
        logger.info("Web3 client closed")
