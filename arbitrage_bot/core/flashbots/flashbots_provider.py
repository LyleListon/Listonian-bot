"""
Flashbots Provider Implementation

This module provides functionality for interacting with Flashbots to protect
against MEV and submit bundles.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.types import TxParams, HexStr
from web3.exceptions import TransactionNotFound
from eth_typing import ChecksumAddress

logger = logging.getLogger(__name__)

class FlashbotsProvider:
    """
    Provider for Flashbots interactions.
    
    This class provides:
    - Bundle submission
    - MEV protection
    - Transaction simulation
    - Block monitoring
    """
    
    def __init__(
        self,
        web3: Web3,
        config: Dict[str, Any],
        account: LocalAccount,
        max_retries: int = 3
    ):
        """
        Initialize the Flashbots provider.
        
        Args:
            web3: Web3 instance
            config: Flashbots configuration
            account: Account for signing bundles
            max_retries: Maximum number of retry attempts
        """
        self._web3 = web3
        self._config = config
        self._account = account
        self._max_retries = max_retries
        
        # Configuration
        self._relay_url = config["relay_url"]
        self._bundle_timeout = config.get("bundle_timeout", 30)
        self._max_blocks = config.get("max_blocks_to_search", 25)
        self._chain_id = config.get("chain_id", 1)  # Default to Ethereum mainnet
        
        # State
        self._lock = asyncio.Lock()
        self._initialized = False
        self._flashbots_auth_header = None
        self._provider = None
        self._nonce = None
    
    async def initialize(self) -> None:
        """Initialize the Flashbots provider."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing Flashbots provider")
            
            try:
                # Create Flashbots auth header
                auth_msg = f"flashbots {self._account.address}"
                signed_msg = self._account.sign_message(text=auth_msg)
                signature = signed_msg.signature.hex()
                
                self._flashbots_auth_header = {
                    "X-Flashbots-Signature": f"{self._account.address}:{signature}"
                }
                
                logger.debug(f"Created Flashbots auth header for {self._account.address}")
                
                # Add account to sign transactions
                self._web3.eth.default_account = self._account.address
                
                # Set Flashbots RPC endpoint
                from web3.providers.rpc import HTTPProvider
                
                self._provider = HTTPProvider(
                    endpoint_uri=self._relay_url,
                    request_kwargs={"headers": self._flashbots_auth_header}
                )
                
                # Keep original provider for non-Flashbots operations
                self._original_provider = self._web3.provider
                
                self._initialized = True
                logger.info("Flashbots provider initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize Flashbots provider: {e}", exc_info=True)
                raise
                
    async def is_initialized(self) -> bool:
        """Check if the provider is initialized."""
        return self._initialized
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            self._initialized = False
            self._provider = None
            self._flashbots_auth_header = None
    
    async def _get_nonce(self) -> int:
        """Get the current nonce for the account."""
        if self._nonce is None:
            self._nonce = await self._web3.eth.get_transaction_count(
                self._account.address, 'pending'
            )
        else:
            self._nonce += 1
        return self._nonce
    
    async def simulate_bundle(
        self,
        transactions: List[TxParams],
        block_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simulate a bundle of transactions.
        
        Args:
            transactions: List of transactions to simulate
            block_number: Block number to simulate at
            
        Returns:
            Simulation results
        """
        if not self._initialized:
            raise RuntimeError("Flashbots provider not initialized")
        
        try:
            # Get target block
            if not block_number:
                block_number = await self._web3.eth.block_number
            
            # Simulate bundle
            signed_txs = []
            for tx in transactions:
                # If transaction is not signed, sign it
                if isinstance(tx, dict) and 'rawTransaction' not in tx:
                    # Add nonce if not present
                    if 'nonce' not in tx:
                        tx['nonce'] = await self._get_nonce()
                    
                    # Add chain ID if not present
                    if 'chainId' not in tx:
                        tx['chainId'] = self._chain_id
                    
                    # Sign transaction
                    signed_tx = self._account.sign_transaction(tx)
                    signed_txs.append(signed_tx.rawTransaction.hex())
                else:
                    # Already signed
                    signed_txs.append(tx.rawTransaction.hex() if hasattr(tx, 'rawTransaction') else tx)
            
            # Prepare simulation request
            params = [{
                "txs": signed_txs,
                "blockNumber": hex(block_number),
                "stateBlockNumber": "latest"
            }]
            
            result = await self._make_request(
                "eth_callBundle", params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error simulating bundle: {e}", exc_info=True)
            raise

    async def _make_request(
        self,
        method: str,
        params: List[Any],
        retries: int = 0
    ) -> Dict[str, Any]:
        """
        Make a request to the Flashbots RPC endpoint.
        
        Args:
            method: RPC method
            params: RPC parameters
            retries: Current retry count
            
        Returns:
            Response from Flashbots
        """
        if not self._initialized:
            raise RuntimeError("Flashbots provider not initialized")
        
        try:
            # Create JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            
            # Send request
            response = await self._web3.provider.make_request(
                method,
                params
            )
            
            # Check for errors
            if "error" in response:
                error = response["error"]
                logger.error(f"Flashbots RPC error: {error}")
                raise ValueError(f"Flashbots RPC error: {error}")
            
            return response
            
        except Exception as e:
            if retries < self._max_retries:
                logger.warning(f"Retrying Flashbots request ({retries+1}/{self._max_retries}): {e}")
                await asyncio.sleep(0.5 * (retries + 1))  # Exponential backoff
                return await self._make_request(method, params, retries + 1)
            else:
                raise
    
    async def send_bundle(
        self,
        transactions: List[TxParams],
        target_block_number: Optional[int] = None
    ) -> str:
        """
        Send a bundle of transactions.
        
        Args:
            transactions: List of transactions to send
            target_block_number: Target block number
            
        Returns:
            Bundle hash
        """
        if not self._initialized:
            raise RuntimeError("Flashbots provider not initialized")
        
        try:
            # Determine target block
            if not target_block_number:
                target_block_number = await self._web3.eth.block_number + 1
            
            # Sign transactions if needed
            signed_txs = []
            for tx in transactions:
                # If transaction is not signed, sign it
                if isinstance(tx, dict) and 'rawTransaction' not in tx:
                    # Add nonce if not present
                    if 'nonce' not in tx:
                        tx['nonce'] = await self._get_nonce()
                    
                    # Add chain ID if not present
                    if 'chainId' not in tx:
                        tx['chainId'] = self._chain_id
                    
                    # Sign transaction
                    signed_tx = self._account.sign_transaction(tx)
                    signed_txs.append(signed_tx.rawTransaction.hex())
                else:
                    # Already signed
                    signed_txs.append(tx.rawTransaction.hex() if hasattr(tx, 'rawTransaction') else tx)
            
            # Prepare bundle request
            params = [{
                "txs": signed_txs,
                "blockNumber": hex(target_block_number)
            }]
            
            # Send bundle request
            response = await self._make_request(
                "eth_sendBundle", params
            )
            
            # Extract bundle hash
            if "result" in response and "bundleHash" in response["result"]:
                bundle_hash = response["result"]["bundleHash"]
                logger.info(f"Bundle submitted with hash: {bundle_hash}")
                return bundle_hash
            else:
                raise ValueError(f"Invalid response from Flashbots: {response}")
            
        except Exception as e:
            logger.error(f"Error sending bundle: {e}", exc_info=True)
            raise
    
    async def get_bundle_stats(
        self,
        bundle_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a bundle.
        
        Args:
            bundle_hash: Hash of bundle to check
            
        Returns:
            Bundle statistics
        """
        if not self._initialized:
            raise RuntimeError("Flashbots provider not initialized")
        
        try:
            # Prepare request
            params = [{
                "bundleHash": bundle_hash
            }]
            
            # Send request
            response = await self._make_request(
                "flashbots_getBundleStats", params
            )
            
            # Return stats
            if "result" in response:
                return response["result"]
            
        except Exception as e:
            logger.error(f"Error getting bundle stats: {e}", exc_info=True)
            raise
    
    async def wait_for_bundle(
        self,
        bundle_hash: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Wait for a bundle to be included.
        
        Args:
            bundle_hash: Hash of bundle to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Bundle inclusion details
        """
        if not self._initialized:
            raise RuntimeError("Flashbots provider not initialized")
        
        timeout = timeout or self._bundle_timeout
        deadline = asyncio.get_event_loop().time() + timeout
        current_block = await self._web3.eth.block_number
        target_block = current_block + self._max_blocks
        
        while current_block <= target_block:
            try:
                # Check if bundle was included
                stats = await self.get_bundle_stats(bundle_hash)
                if stats and stats.get("included"):
                    return stats
                
                # Check timeout
                if asyncio.get_event_loop().time() > deadline:
                    raise TimeoutError(
                        f"Timeout waiting for bundle {bundle_hash}"
                    )
                
                # Wait for next block
                await asyncio.sleep(1)
                current_block = await self._web3.eth.block_number
                
            except Exception as e:
                logger.error(f"Error waiting for bundle: {e}", exc_info=True)
                raise
        
        raise TimeoutError(
            f"Bundle {bundle_hash} not included within {self._max_blocks} blocks"
        )

    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics from Flashbots.
        
        Returns:
            User statistics
        """
        if not self._initialized:
            raise RuntimeError("Flashbots provider not initialized")
        
        try:
            # Send request
            response = await self._make_request(
                "flashbots_getUserStats", [{}]
            )
            
            # Return stats
            if "result" in response:
                return response["result"]
            else:
                return {}
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}", exc_info=True)
            return {}

    async def get_block_number(self) -> int:
        """
        Get the current block number.
        
        Returns:
            Current block number
        """
        try:
            return await self._web3.eth.block_number
        except Exception as e:
            logger.error(f"Error getting block number: {e}", exc_info=True)
            raise

    async def get_gas_price(self) -> int:
        """
        Get the current gas price.
        
        Returns:
            Current gas price in wei
        """
        try:
            return await self._web3.eth.gas_price
        except Exception as e:
            logger.error(f"Error getting gas price: {e}", exc_info=True)
            raise

    async def close(self) -> None:
        """
        Close the provider and clean up resources.
        
        This method should be called when the provider is no longer needed.
        """
        try:
            await self.cleanup()
        except Exception as e:
            logger.error(f"Error closing Flashbots provider: {e}", exc_info=True)

async def create_flashbots_provider(
    web3: Web3,
    config: Dict[str, Any]
) -> FlashbotsProvider:
    """
    Create and initialize a Flashbots provider.
    
    Args:
        web3: Web3 instance
        config: Flashbots configuration
        
    Returns:
        Initialized Flashbots provider
    """
    try:
        # Create signing account
        private_key = config.get("private_key")
        if not private_key:
            raise ValueError("Private key not provided in config")
            
        account = web3.eth.account.from_key(private_key)
        provider = FlashbotsProvider(web3, config, account)
        await provider.initialize()
        return provider
    except Exception as e:
        logger.error(f"Failed to create Flashbots provider: {e}", exc_info=True)
        raise