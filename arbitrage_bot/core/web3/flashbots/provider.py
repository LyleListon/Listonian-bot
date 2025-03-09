"""
Flashbots Provider

This module contains the implementation of the Flashbots provider, which
handles interactions with the Flashbots RPC endpoint for bundle submission and tracking.
"""

import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, Union, cast
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr, URI
from web3 import Web3, HTTPProvider
from web3.types import RPCEndpoint, Wei

from ...web3.interfaces import Web3Client, Transaction
from .interfaces import (
    FlashbotsBundle, 
    BundleSimulationResult,
    BundleSubmissionResult,
    BundleStatsResult
)

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
        config: Optional[Dict[str, Any]] = None
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
                logger.info(f"Initializing Flashbots provider for network {self.network}")
                
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
        def build_flashbots_middleware(account: LocalAccount):
            async def middleware(method, params):
                # Only intercept Flashbots methods
                if method in [
                    self.SEND_BUNDLE, 
                    self.CALL_BUNDLE, 
                    self.SIMULATE_BUNDLE, 
                    self.GET_BUNDLE_STATS, 
                    self.GET_USER_STATS
                ]:
                    request = {"method": method, "params": params}
                    request_json = json.dumps(request)
                    
                    # Calculate signature
                    message = Web3.solidity_keccak(
                        ["string"], [request_json]
                    )
                    signed_message = account.sign_message(message)
                    
                    # Add headers
                    headers = {
                        "X-Flashbots-Signature": f"{account.address}:{signed_message.signature.hex()}",
                        "Content-Type": "application/json"
                    }
                    
                    # Make request directly
                    response = await self.web3_client.make_request(
                        method,
                        params,
                        url=self.relay_url,
                        headers=headers,
                        timeout=self.relay_timeout
                    )
                    
                    return response
                
                # For non-Flashbots methods, use regular provider
                return await self.web3_client.make_request(method, params)
            
            return middleware
        
        # Inject middleware
        self.flashbots_web3.middleware_onion.add(build_flashbots_middleware(self.signing_account))
    
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
    
    async def sign_bundle(
        self,
        bundle: FlashbotsBundle
    ) -> FlashbotsBundle:
        """
        Sign a Flashbots bundle.
        
        This method signs all transactions in the bundle using the provider's
        signing account.
        
        Args:
            bundle: Bundle to sign
            
        Returns:
            Signed bundle
        """
        if bundle.signed:
            logger.debug("Bundle already signed")
            return bundle
        
        signed_transactions = []
        
        for tx in bundle.transactions:
            # Clone tx to avoid modifying the original
            tx_dict = tx.__dict__.copy()
            
            # If gas price is not set, estimate it
            if tx_dict.get("gas_price") is None:
                gas_price = await self.web3_client.get_gas_price()
                tx_dict["gas_price"] = int(gas_price)
            
            # If nonce is not set, get it
            if tx_dict.get("nonce") is None:
                nonce = await self.web3_client.get_transaction_count(
                    tx_dict["from_address"],
                    'pending'
                )
                tx_dict["nonce"] = nonce
            
            # Create raw transaction
            raw_tx = {
                "from": tx_dict["from_address"],
                "to": tx_dict["to_address"],
                "value": tx_dict.get("value", 0),
                "gas": tx_dict.get("gas", 21000),
                "gasPrice": tx_dict.get("gas_price", 0),
                "nonce": tx_dict.get("nonce", 0),
                "data": tx_dict.get("data", "0x"),
                "chainId": self.chain_id
            }
            
            # Sign transaction
            signed_tx = self.signing_account.sign_transaction(raw_tx)
            signed_transactions.append(signed_tx.rawTransaction.hex())
        
        # Create a new bundle with signed transactions
        result = FlashbotsBundle(
            transactions=bundle.transactions,
            target_block_number=bundle.target_block_number,
            blocks_into_future=bundle.blocks_into_future,
            replacements=bundle.replacements,
            simulation_timestamp=bundle.simulation_timestamp,
            signed=True,
            signed_transactions=signed_transactions
        )
        
        return result
    
    async def simulate_bundle(
        self,
        bundle: FlashbotsBundle,
        block: Union[str, int] = "latest",
        state_block: Optional[Union[str, int]] = None,
        timestamp: Optional[int] = None
    ) -> BundleSimulationResult:
        """
        Simulate a Flashbots bundle.
        
        This method simulates the execution of a bundle using the Flashbots
        simulation endpoint, which allows calculating the profit and gas usage
        without actually submitting the transactions.
        
        Args:
            bundle: Bundle to simulate
            block: Block number or hash to simulate against
            state_block: Block to use for state, or None for same as block
            timestamp: Timestamp to use for simulation, or None for current time
            
        Returns:
            Simulation result
        """
        if not self._is_initialized:
            await self.initialize()
        
        # Ensure bundle is signed
        if not bundle.signed:
            bundle = await self.sign_bundle(bundle)
        
        # Default timestamp to current time if not provided
        if timestamp is None:
            timestamp = int(time.time())
        
        # Default state block to simulation block if not provided
        if state_block is None:
            state_block = block
        
        # Prepare simulation params
        params = [{
            "txs": bundle.signed_transactions,
            "blockNumber": block,
            "stateBlockNumber": state_block,
            "timestamp": timestamp
        }]
        
        try:
            # Call simulation endpoint
            response = await self.web3_client.make_request(
                self.SIMULATE_BUNDLE,
                params,
                url=self.relay_url,
                headers={
                    "X-Flashbots-Signature": f"{self.signing_account.address}:0x",
                    "Content-Type": "application/json"
                },
                timeout=self.relay_timeout
            )
            
            # Check for errors
            if "error" in response:
                logger.error(f"Simulation failed: {response['error']}")
                return BundleSimulationResult(
                    success=False,
                    error=str(response["error"])
                )
            
            # Parse result
            result = response.get("result", {})
            
            return BundleSimulationResult(
                success=True,
                state_changes=result.get("stateChanges", {}),
                gas_used=result.get("gasUsed", 0),
                gas_price=result.get("gasPrice", 0),
                eth_sent_to_coinbase=result.get("ethSentToCoinbase", 0),
                simulation_block=result.get("simulationBlock", 0),
                simulation_timestamp=result.get("simulationTimestamp", 0)
            )
            
        except Exception as e:
            logger.error(f"Simulation request failed: {e}")
            return BundleSimulationResult(
                success=False,
                error=str(e)
            )
    
    async def submit_bundle(
        self,
        bundle: FlashbotsBundle
    ) -> BundleSubmissionResult:
        """
        Submit a Flashbots bundle.
        
        This method submits a bundle to the Flashbots relay for inclusion
        in a future block, allowing for private transaction execution.
        
        Args:
            bundle: Bundle to submit
            
        Returns:
            Submission result
        """
        if not self._is_initialized:
            await self.initialize()
        
        # Ensure bundle is signed
        if not bundle.signed:
            bundle = await self.sign_bundle(bundle)
        
        # Determine target block number
        if bundle.target_block_number:
            target_block = bundle.target_block_number
        else:
            current_block = await self.web3_client.get_block_number()
            target_block = current_block + bundle.blocks_into_future
        
        # Prepare submission params
        params = [{
            "txs": bundle.signed_transactions,
            "blockNumber": hex(target_block),
            "minTimestamp": bundle.simulation_timestamp,
            "maxTimestamp": bundle.simulation_timestamp
        }]
        
        # Remove None values
        params[0] = {k: v for k, v in params[0].items() if v is not None}
        
        try:
            # Call submission endpoint
            response = await self.web3_client.make_request(
                self.SEND_BUNDLE,
                params,
                url=self.relay_url,
                headers={
                    "X-Flashbots-Signature": f"{self.signing_account.address}:0x",
                    "Content-Type": "application/json"
                },
                timeout=self.relay_timeout
            )
            
            # Check for errors
            if "error" in response:
                logger.error(f"Bundle submission failed: {response['error']}")
                return BundleSubmissionResult(
                    success=False,
                    error=str(response["error"]),
                    relay_response=response
                )
            
            # Parse result
            result = response.get("result", {})
            bundle_hash = result.get("bundleHash")
            
            if not bundle_hash:
                logger.error("Bundle submission failed: No bundle hash returned")
                return BundleSubmissionResult(
                    success=False,
                    error="No bundle hash returned",
                    relay_response=response
                )
            
            logger.info(f"Bundle submitted successfully: {bundle_hash}")
            return BundleSubmissionResult(
                success=True,
                bundle_hash=bundle_hash,
                relay_response=response
            )
            
        except Exception as e:
            logger.error(f"Bundle submission request failed: {e}")
            return BundleSubmissionResult(
                success=False,
                error=str(e),
                relay_response={}
            )
    
    async def get_bundle_stats(
        self,
        bundle_hash: str
    ) -> Optional[BundleStatsResult]:
        """
        Get statistics for a submitted bundle.
        
        This method retrieves information about a previously submitted bundle,
        including whether it was included in a block.
        
        Args:
            bundle_hash: Hash of the bundle to check
            
        Returns:
            Bundle statistics or None if not found
        """
        if not self._is_initialized:
            await self.initialize()
        
        params = [{"bundleHash": bundle_hash}]
        
        try:
            # Call stats endpoint
            response = await self.web3_client.make_request(
                self.GET_BUNDLE_STATS,
                params,
                url=self.relay_url,
                headers={
                    "X-Flashbots-Signature": f"{self.signing_account.address}:0x",
                    "Content-Type": "application/json"
                },
                timeout=self.relay_timeout
            )
            
            # Check for errors
            if "error" in response:
                logger.error(f"Get bundle stats failed: {response['error']}")
                return None
            
            # Parse result
            result = response.get("result", {})
            
            if not result:
                logger.warning(f"No stats returned for bundle: {bundle_hash}")
                return None
            
            # Create result object
            stats: BundleStatsResult = {
                "bundle_hash": bundle_hash,
                "is_included": result.get("isIncluded", False),
                "block_number": result.get("blockNumber"),
                "transaction_hash": result.get("transactionHash"),
                "miner": result.get("miner"),
                "gas_used": result.get("gasUsed"),
                "gas_price": result.get("gasPrice"),
                "eth_sent_to_coinbase": result.get("ethSentToCoinbase"),
                "bundle_stats": result.get("bundleStats", {})
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Get bundle stats request failed: {e}")
            return None
    
    async def wait_for_bundle_inclusion(
        self,
        bundle_hash: str,
        target_block: int,
        max_wait_blocks: int = 5,
        interval_seconds: int = 12
    ) -> Optional[BundleStatsResult]:
        """
        Wait for a bundle to be included in a block.
        
        This method polls the Flashbots API to check if a bundle has been
        included in a block, up to a maximum number of blocks.
        
        Args:
            bundle_hash: Hash of the bundle to check
            target_block: Target block number
            max_wait_blocks: Maximum number of blocks to wait
            interval_seconds: Interval between checks in seconds
            
        Returns:
            Bundle statistics if included, None otherwise
        """
        if not self._is_initialized:
            await self.initialize()
        
        final_block = target_block + max_wait_blocks
        current_block = await self.web3_client.get_block_number()
        
        logger.info(f"Waiting for bundle {bundle_hash} inclusion (target: {target_block}, max: {final_block})")
        
        # Wait for target block
        while current_block < final_block:
            # Check if the bundle was included
            stats = await self.get_bundle_stats(bundle_hash)
            
            if stats and stats.get("is_included"):
                logger.info(f"Bundle included in block {stats.get('block_number')}")
                return stats
            
            # Sleep for interval
            await asyncio.sleep(interval_seconds)
            
            # Update current block
            current_block = await self.web3_client.get_block_number()
        
        logger.warning(f"Bundle {bundle_hash} not included within {max_wait_blocks} blocks")
        return None
    
    async def close(self) -> None:
        """Close the Flashbots provider and clean up resources."""
        logger.info("Closing Flashbots provider")
        self._is_initialized = False