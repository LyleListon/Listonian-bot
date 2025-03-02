"""
Flashbots Provider

This module contains the FlashbotsProvider implementation for interacting
with the Flashbots RPC service to enable MEV protection for transactions.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple, cast, Union
import secrets
import eth_account
from eth_account.signers.local import LocalAccount
from eth_typing import HexStr, BlockNumber
from web3.types import RPCEndpoint, Wei

from ..interfaces import Web3Client, Transaction, TransactionReceipt

logger = logging.getLogger(__name__)

# Flashbots specific constants
FLASHBOTS_ENDPOINT = "https://relay.flashbots.net"
FLASHBOTS_HEADERS_PREFIX = "X-Flashbots"


class FlashbotsProvider:
    """
    Provider for interacting with Flashbots RPC service.
    
    This provider enables:
    1. Private transaction submission to avoid frontrunning
    2. Bundle creation and submission for atomic execution
    3. Bundle simulation for profit validation
    4. Block builder integration for transaction privacy
    """
    
    def __init__(
        self,
        web3_client: Web3Client,
        auth_signer_key: Optional[str] = None,
        flashbots_endpoint: str = FLASHBOTS_ENDPOINT,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the flashbots provider.
        
        Args:
            web3_client: Base web3 client for standard blockchain interactions
            auth_signer_key: Private key for signing Flashbots authentication
            flashbots_endpoint: Flashbots RPC endpoint URL
            config: Additional configuration parameters
        """
        self.web3_client = web3_client
        self.flashbots_endpoint = flashbots_endpoint
        self.config = config or {}
        
        # Authentication
        self.auth_signer: Optional[LocalAccount] = None
        if auth_signer_key:
            self.auth_signer = eth_account.Account.from_key(auth_signer_key)
        else:
            # Generate ephemeral account for signing if none provided
            # This is not recommended for production but allows for testing
            random_key = secrets.token_hex(32)
            self.auth_signer = eth_account.Account.from_key(random_key)
            logger.warning(
                "Using ephemeral auth signer for Flashbots. "
                "For production, provide a permanent key."
            )
        
        # Configuration
        self.max_retries = int(self.config.get("max_retries", 3))
        self.retry_delay = float(self.config.get("retry_delay", 1.0))
        self.simulation_block = self.config.get("simulation_block", "latest")
        self.fast_mode = bool(self.config.get("fast_mode", False))
        
        # State
        self._request_lock = asyncio.Lock()
        self._last_request_time = 0
        self._min_request_interval = float(self.config.get("min_request_interval", 0.1))
        
        logger.info("FlashbotsProvider initialized")
    
    async def send_private_transaction(
        self,
        transaction: Transaction
    ) -> Optional[str]:
        """
        Send a private transaction through Flashbots.
        
        Args:
            transaction: Transaction object to send
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        logger.info("Preparing private transaction for Flashbots submission")
        
        # Ensure transaction is fully formed
        if not transaction.from_address:
            transaction.from_address = self.web3_client.get_default_account()
        
        if transaction.nonce is None:
            nonce = await self.web3_client.get_transaction_count(transaction.from_address)
            transaction.nonce = nonce
        
        # Get gas parameters if not set
        if not transaction.gas:
            try:
                gas_estimate = await self.web3_client.estimate_gas(transaction)
                transaction.gas = gas_estimate
            except Exception as e:
                logger.error(f"Error estimating gas for transaction: {e}")
                return None
        
        # Get gas price if not set
        if not transaction.gas_price and not (transaction.max_fee_per_gas and transaction.max_priority_fee_per_gas):
            gas_price = await self.web3_client.get_gas_price()
            transaction.gas_price = gas_price
        
        # Build a bundle with just this transaction
        bundle = await self._build_single_tx_bundle(transaction)
        
        # Submit the bundle
        bundle_hash = await self.send_bundle(bundle)
        
        # Return the first transaction's hash in the bundle
        if bundle_hash and bundle:
            tx_hash = bundle[0].get("hash")
            logger.info(f"Transaction submitted via Flashbots: {tx_hash}")
            return tx_hash
        
        logger.warning("Failed to submit transaction via Flashbots")
        return None
    
    async def send_bundle(
        self,
        bundle: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Send a bundle of transactions to Flashbots.
        
        Args:
            bundle: List of signed transaction objects in bundle
            
        Returns:
            Bundle hash if successful, None otherwise
        """
        logger.info(f"Sending bundle with {len(bundle)} transactions to Flashbots")
        
        # Get the current block to target bundle inclusion
        try:
            current_block = await self.web3_client.get_block_number()
            target_block = current_block + 1
        except Exception as e:
            logger.error(f"Error getting current block: {e}")
            return None
        
        # Prepare the bundle request
        params = {
            "txs": [tx.get("raw") for tx in bundle if tx.get("raw")],
            "blockNumber": hex(target_block),
            "minTimestamp": 0,
            "maxTimestamp": int(time.time()) + 120,  # 2 minutes in the future
            "revertingTxHashes": []
        }
        
        # Submit the bundle with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                bundle_hash = await self._send_flashbots_request("eth_sendBundle", params)
                if bundle_hash:
                    logger.info(f"Bundle submitted successfully: {bundle_hash}")
                    return bundle_hash
                else:
                    logger.warning(f"Bundle submission returned no hash (attempt {attempt})")
            except Exception as e:
                logger.error(f"Error submitting bundle (attempt {attempt}): {e}")
            
            # Retry with delay
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay)
        
        logger.error("Bundle submission failed after all retries")
        return None
    
    async def simulate_bundle(
        self,
        bundle: List[Dict[str, Any]],
        block_number: Optional[Union[int, str]] = None,
        state_block_number: Optional[Union[int, str]] = None,
        timestamp: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Simulate a bundle to validate its execution and profit.
        
        Args:
            bundle: List of transaction objects to simulate
            block_number: Block number to simulate on
            state_block_number: Block to use for state 
            timestamp: Timestamp for simulation
            
        Returns:
            Simulation result if successful, None otherwise
        """
        logger.info(f"Simulating bundle with {len(bundle)} transactions")
        
        # Set default block number if not provided
        if not block_number:
            try:
                current_block = await self.web3_client.get_block_number()
                block_number = current_block
            except Exception as e:
                logger.error(f"Error getting current block for simulation: {e}")
                return None
        
        # Convert block number to hex
        if isinstance(block_number, int):
            block_number_hex = hex(block_number)
        else:
            block_number_hex = block_number
        
        # Set default state block if not provided
        if not state_block_number:
            state_block_number = block_number_hex
        elif isinstance(state_block_number, int):
            state_block_number = hex(state_block_number)
        
        # Set default timestamp if not provided
        if not timestamp:
            timestamp = int(time.time())
        
        # Prepare simulation params
        params = {
            "txs": [tx.get("raw") for tx in bundle if tx.get("raw")],
            "blockNumber": block_number_hex,
            "stateBlockNumber": state_block_number,
            "timestamp": timestamp
        }
        
        # Send simulation request
        try:
            simulation_result = await self._send_flashbots_request("eth_callBundle", params)
            
            if simulation_result:
                logger.info("Bundle simulation completed successfully")
                return simulation_result
            else:
                logger.warning("Bundle simulation returned no result")
                return None
                
        except Exception as e:
            logger.error(f"Error simulating bundle: {e}")
            return None
    
    async def get_bundle_stats(
        self,
        bundle_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a submitted bundle.
        
        Args:
            bundle_hash: Hash of the bundle
            
        Returns:
            Bundle statistics if available, None otherwise
        """
        logger.info(f"Getting stats for bundle: {bundle_hash}")
        
        params = {"bundleHash": bundle_hash}
        
        try:
            stats = await self._send_flashbots_request("flashbots_getBundleStats", params)
            return stats
        except Exception as e:
            logger.error(f"Error getting bundle stats: {e}")
            return None
    
    async def get_user_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get statistics for the current user.
        
        Returns:
            User statistics if available, None otherwise
        """
        logger.info("Getting user stats from Flashbots")
        
        try:
            stats = await self._send_flashbots_request("flashbots_getUserStats", {})
            return stats
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    async def cancel_bundle(
        self,
        bundle_hash: str
    ) -> bool:
        """
        Cancel a previously submitted bundle.
        
        Args:
            bundle_hash: Hash of the bundle to cancel
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        logger.info(f"Cancelling bundle: {bundle_hash}")
        
        params = {"bundleHash": bundle_hash}
        
        try:
            result = await self._send_flashbots_request("flashbots_cancelBundle", params)
            return bool(result)
        except Exception as e:
            logger.error(f"Error cancelling bundle: {e}")
            return False
    
    async def _build_single_tx_bundle(
        self,
        transaction: Transaction
    ) -> List[Dict[str, Any]]:
        """
        Build a bundle containing a single transaction.
        
        Args:
            transaction: Transaction to include in the bundle
            
        Returns:
            Bundle with the transaction
        """
        # Sign the transaction
        try:
            signed_tx = await self.web3_client.sign_transaction(transaction)
            
            if not signed_tx:
                logger.error("Failed to sign transaction for bundle")
                return []
                
            # Create the bundle entry
            return [{
                "hash": signed_tx.hash,
                "raw": signed_tx.raw_transaction.hex(),
                "tx": transaction
            }]
            
        except Exception as e:
            logger.error(f"Error building single transaction bundle: {e}")
            return []
    
    async def _send_flashbots_request(
        self,
        method: str,
        params: Dict[str, Any]
    ) -> Any:
        """
        Send a request to the Flashbots RPC endpoint.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            Response from Flashbots
        """
        # Ensure we don't flood the API
        async with self._request_lock:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self._min_request_interval:
                await asyncio.sleep(self._min_request_interval - time_since_last)
            
            self._last_request_time = time.time()
            
            # Prepare request data
            request_id = secrets.randbits(32)
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": [params]
            }
            
            # Generate Flashbots signature for authentication
            message = json.dumps(payload)
            signature = self._generate_auth_signature(message)
            
            # Prepare headers with Flashbots authentication
            headers = {
                "Content-Type": "application/json",
                f"{FLASHBOTS_HEADERS_PREFIX}-Signature": signature
            }
            
            # Send the request
            try:
                response = await self.web3_client.make_request(
                    method=method,
                    params=params,
                    endpoint=self.flashbots_endpoint,
                    headers=headers
                )
                
                # Check for errors
                if "error" in response:
                    error = response["error"]
                    logger.error(f"Flashbots request error: {error}")
                    raise Exception(f"Flashbots request failed: {error}")
                
                # Return the result
                if "result" in response:
                    return response["result"]
                    
                return None
                
            except Exception as e:
                logger.error(f"Error sending Flashbots request: {e}")
                raise
    
    def _generate_auth_signature(self, message: str) -> str:
        """
        Generate Flashbots authentication signature.
        
        Args:
            message: Message to sign
            
        Returns:
            Signature for authentication
        """
        if not self.auth_signer:
            raise ValueError("No authentication signer available")
        
        # Sign the message
        signature = self.auth_signer.sign_message(
            eth_account.messages.encode_defunct(text=message)
        )
        
        # Return the signature as hex string
        return f"{self.auth_signer.address}:{signature.signature.hex()}"
    
    async def close(self) -> None:
        """Close the provider and release resources."""
        logger.info("Closing FlashbotsProvider")
        # Nothing to clean up for now


async def create_flashbots_provider(
    web3_client: Web3Client,
    auth_signer_key: Optional[str] = None,
    flashbots_endpoint: str = FLASHBOTS_ENDPOINT,
    config: Dict[str, Any] = None
) -> FlashbotsProvider:
    """
    Factory function to create a Flashbots provider.
    
    Args:
        web3_client: Base web3 client for standard blockchain interactions
        auth_signer_key: Private key for signing Flashbots authentication
        flashbots_endpoint: Flashbots RPC endpoint URL
        config: Additional configuration parameters
        
    Returns:
        Initialized Flashbots provider
    """
    return FlashbotsProvider(
        web3_client=web3_client,
        auth_signer_key=auth_signer_key,
        flashbots_endpoint=flashbots_endpoint,
        config=config
    )