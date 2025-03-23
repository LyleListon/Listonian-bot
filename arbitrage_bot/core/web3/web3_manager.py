"""
Web3 Manager Implementation

This module provides Web3 functionality with proper async handling and
retry mechanisms.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from web3 import Web3, AsyncWeb3
from web3.types import RPCEndpoint, RPCResponse

logger = logging.getLogger(__name__)

class Web3Manager:
    """
    Manager for Web3 interactions.
    
    This class provides:
    - Async Web3 initialization
    - Connection management
    - Transaction handling
    - Gas price estimation
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Web3 manager.
        
        Args:
            config: Web3 configuration
        """
        self._config = config
        
        # Configuration
        self._rpc_url = config["rpc_url"]
        self._chain_id = config["chain_id"]
        self._retry_count = config.get("retry_count", 3)
        self._retry_delay = config.get("retry_delay", 1.0)
        self._timeout = config.get("timeout", 30)
        
        # State
        self._web3: Optional[AsyncWeb3] = None
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the Web3 manager."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing Web3 manager")
            
            try:
                # Create async Web3 instance
                self._web3 = AsyncWeb3(
                    AsyncWeb3.AsyncHTTPProvider(
                        self._rpc_url,
                        request_kwargs={"timeout": self._timeout}
                    )
                )
                
                # Add custom middleware for POA chains
                if self._chain_id in (56, 97, 137, 80001):  # BSC, Polygon
                    # Create custom POA middleware
                    async def poa_middleware(
                        make_request: Any,
                        web3: AsyncWeb3
                    ) -> Any:
                        async def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
                            # Add extraData field to block parameters
                            if method == "eth_getBlockByNumber":
                                response = await make_request(method, params)
                                if "result" in response and response["result"]:
                                    if "extraData" not in response["result"]:
                                        response["result"]["extraData"] = "0x"
                                return response
                            return await make_request(method, params)
                        return middleware
                    
                    # Add middleware
                    self._web3.middleware_onion.inject(
                        poa_middleware,
                        layer=0
                    )
                
                # Verify connection
                if not await self._web3.is_connected():
                    raise ConnectionError(f"Failed to connect to {self._rpc_url}")
                
                # Verify chain ID
                chain_id = await self._web3.eth.chain_id
                if chain_id != self._chain_id:
                    raise ValueError(
                        f"Wrong chain ID: expected {self._chain_id}, got {chain_id}"
                    )
                
                self._initialized = True
                logger.info(
                    f"Web3 manager initialized on chain {self._chain_id}"
                )
                
            except Exception as e:
                logger.error(f"Failed to initialize Web3 manager: {e}", exc_info=True)
                raise
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            if not self._initialized:
                return
            
            logger.info("Cleaning up Web3 manager")
            
            if self._web3:
                await self._web3.provider.close()
            
            self._initialized = False
    
    @property
    def web3(self) -> AsyncWeb3:
        """Get the Web3 instance."""
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        return self._web3
    
    async def get_gas_price(self) -> int:
        """
        Get current gas price.
        
        Returns:
            Gas price in wei
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        return await self._web3.eth.gas_price
    
    async def estimate_gas(
        self,
        transaction: Dict[str, Any]
    ) -> int:
        """
        Estimate gas for a transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            Gas estimate in wei
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        return await self._web3.eth.estimate_gas(transaction)
    
    async def send_transaction(
        self,
        transaction: Dict[str, Any]
    ) -> str:
        """
        Send a transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            Transaction hash
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        for attempt in range(self._retry_count):
            try:
                # Update gas price if not set
                if "gasPrice" not in transaction:
                    transaction["gasPrice"] = await self.get_gas_price()
                
                # Estimate gas if not set
                if "gas" not in transaction:
                    gas_estimate = await self.estimate_gas(transaction)
                    transaction["gas"] = int(gas_estimate * 1.1)  # 10% buffer
                
                # Send transaction
                tx_hash = await self._web3.eth.send_transaction(transaction)
                return tx_hash.hex()
                
            except Exception as e:
                if attempt == self._retry_count - 1:
                    logger.error(
                        f"Failed to send transaction after {self._retry_count} attempts: {e}",
                        exc_info=True
                    )
                    raise
                
                logger.warning(
                    f"Failed to send transaction (attempt {attempt + 1}): {e}"
                )
                await asyncio.sleep(self._retry_delay)
    
    async def get_transaction_receipt(
        self,
        tx_hash: str,
        timeout: float = None
    ) -> Dict[str, Any]:
        """
        Get transaction receipt.
        
        Args:
            tx_hash: Transaction hash
            timeout: Maximum time to wait in seconds
            
        Returns:
            Transaction receipt
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        timeout = timeout or self._timeout
        deadline = asyncio.get_event_loop().time() + timeout
        
        while True:
            try:
                receipt = await self._web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    return receipt
                
            except Exception as e:
                logger.warning(f"Error getting receipt: {e}")
            
            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError(
                    f"Timeout waiting for receipt of transaction {tx_hash}"
                )
            
            await asyncio.sleep(1)

async def create_web3_manager(config: Dict[str, Any]) -> Web3Manager:
    """
    Create and initialize a Web3 manager.
    
    Args:
        config: Web3 configuration
        
    Returns:
        Initialized Web3 manager
    """
    manager = Web3Manager(config)
    await manager.initialize()
    return manager
