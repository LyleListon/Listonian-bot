"""
Optimized Web3 Manager with Resource Management

This module extends the Web3Manager with resource management optimizations
for better performance and resource utilization.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple

from web3 import Web3

from .web3_manager import Web3Manager
from arbitrage_bot.core.optimization.resource_manager import (
    ResourceManager,
    TaskPriority,
    ResourceType
)

logger = logging.getLogger(__name__)

class OptimizedWeb3Manager(Web3Manager):
    """
    Optimized Web3 manager with resource management.
    
    This class extends the base Web3Manager with:
    - Resource management for better performance
    - Task prioritization
    - Memory optimization
    - I/O optimization
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the optimized Web3 manager.
        
        Args:
            config: Web3 configuration
        """
        super().__init__(config)
        
        # Resource manager
        self._resource_manager = None
        
        # Resource management configuration
        self._resource_config = config.get("resource_management", {})
        self._num_workers = self._resource_config.get("num_workers", None)
        self._max_cpu_percent = self._resource_config.get("max_cpu_percent", 80.0)
        self._max_memory_percent = self._resource_config.get("max_memory_percent", 80.0)
        
        # Task priorities
        self._task_priorities = {
            "send_transaction": TaskPriority.CRITICAL,
            "get_transaction_receipt": TaskPriority.HIGH,
            "get_quote": TaskPriority.NORMAL,
            "estimate_gas": TaskPriority.NORMAL,
            "get_gas_price": TaskPriority.LOW,
            "get_pool_liquidity": TaskPriority.LOW
        }
    
    async def initialize(self) -> None:
        """Initialize the Web3 manager."""
        # Initialize base manager
        await super().initialize()
        
        # Initialize resource manager
        self._resource_manager = ResourceManager(
            num_workers=self._num_workers,
            max_cpu_percent=self._max_cpu_percent,
            max_memory_percent=self._max_memory_percent
        )
        await self._resource_manager.start()
        
        # Create connection pool
        await self._resource_manager.create_object_pool(
            "web3_connection",
            factory=self._create_web3_connection,
            max_size=10,
            ttl=300.0,  # 5 minutes
            validation_func=self._validate_web3_connection
        )
        
        logger.info("OptimizedWeb3Manager initialized with resource management")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        # Clean up resource manager
        if self._resource_manager:
            await self._resource_manager.stop()
        
        # Clean up base manager
        await super().cleanup()
    
    async def get_gas_price(self) -> int:
        """
        Get current gas price.
        
        Returns:
            Gas price in wei
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        # Use resource manager
        if self._resource_manager:
            return await self._resource_manager.submit_task(
                self._get_gas_price_internal,
                priority=self._task_priorities.get("get_gas_price", TaskPriority.LOW),
                resource_type=ResourceType.CPU,
                timeout=self._timeout
            )
        else:
            return await super().get_gas_price()
    
    async def _get_gas_price_internal(self) -> int:
        """Internal implementation of get_gas_price."""
        return await self._web3.eth.gas_price
    
    async def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """
        Estimate gas for a transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            Gas estimate in wei
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        # Use resource manager
        if self._resource_manager:
            return await self._resource_manager.submit_task(
                self._estimate_gas_internal,
                transaction,
                priority=self._task_priorities.get("estimate_gas", TaskPriority.NORMAL),
                resource_type=ResourceType.CPU,
                timeout=self._timeout
            )
        else:
            return await super().estimate_gas(transaction)
    
    async def _estimate_gas_internal(self, transaction: Dict[str, Any]) -> int:
        """Internal implementation of estimate_gas."""
        return await self._web3.eth.estimate_gas(transaction)
    
    async def send_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Send a transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            Transaction hash
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        # Use resource manager
        if self._resource_manager:
            return await self._resource_manager.submit_task(
                self._send_transaction_internal,
                transaction,
                priority=self._task_priorities.get("send_transaction", TaskPriority.CRITICAL),
                resource_type=ResourceType.CPU,
                timeout=self._timeout,
                retries=self._retry_count,
                retry_delay=self._retry_delay
            )
        else:
            return await super().send_transaction(transaction)
    
    async def _send_transaction_internal(self, transaction: Dict[str, Any]) -> str:
        """Internal implementation of send_transaction."""
        # Update gas price if not set
        if "gasPrice" not in transaction:
            transaction["gasPrice"] = await self._get_gas_price_internal()
        
        # Estimate gas if not set
        if "gas" not in transaction:
            gas_estimate = await self._estimate_gas_internal(transaction)
            transaction["gas"] = int(gas_estimate * 1.1)  # 10% buffer
        
        # Send transaction
        tx_hash = await self._web3.eth.send_transaction(transaction)
        return tx_hash.hex()
    
    async def get_transaction_receipt(self, tx_hash: str, timeout: float = None) -> Dict[str, Any]:
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
        
        # Use resource manager
        if self._resource_manager:
            return await self._resource_manager.submit_task(
                self._get_transaction_receipt_internal,
                tx_hash,
                timeout or self._timeout,
                priority=self._task_priorities.get("get_transaction_receipt", TaskPriority.HIGH),
                resource_type=ResourceType.CPU,
                timeout=timeout or self._timeout
            )
        else:
            return await super().get_transaction_receipt(tx_hash, timeout)
    
    async def _get_transaction_receipt_internal(self, tx_hash: str, timeout: float) -> Dict[str, Any]:
        """Internal implementation of get_transaction_receipt."""
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
    
    async def get_quote(
        self,
        factory: str,
        token_in: str,
        token_out: str,
        amount: str,
        version: str = 'v3'
    ) -> int:
        """
        Get quote from a DEX pool.
        
        Args:
            factory: Factory contract address
            token_in: Input token address
            token_out: Output token address
            amount: Amount of input token in wei
            version: DEX version ('v2' or 'v3')
            
        Returns:
            Quote amount in output token decimals
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        # Use resource manager
        if self._resource_manager:
            return await self._resource_manager.submit_task(
                self._get_quote_internal,
                factory,
                token_in,
                token_out,
                amount,
                version,
                priority=self._task_priorities.get("get_quote", TaskPriority.NORMAL),
                resource_type=ResourceType.CPU,
                timeout=self._timeout,
                retries=self._retry_count,
                retry_delay=self._retry_delay
            )
        else:
            return await super().get_quote(factory, token_in, token_out, amount, version)
    
    async def _get_quote_internal(
        self,
        factory: str,
        token_in: str,
        token_out: str,
        amount: str,
        version: str
    ) -> int:
        """Internal implementation of get_quote."""
        # This is a simplified implementation - in a real scenario, you would
        # copy the implementation from the parent class
        return await super().get_quote(factory, token_in, token_out, amount, version)
    
    async def get_pool_liquidity(
        self,
        factory: str,
        token0: str,
        token1: str
    ) -> float:
        """
        Get pool liquidity in USD.
        
        Args:
            factory: Factory contract address
            token0: First token address
            token1: Second token address
            
        Returns:
            Pool liquidity in USD
        """
        if not self._initialized:
            raise RuntimeError("Web3 manager not initialized")
        
        # Use resource manager
        if self._resource_manager:
            return await self._resource_manager.submit_task(
                self._get_pool_liquidity_internal,
                factory,
                token0,
                token1,
                priority=self._task_priorities.get("get_pool_liquidity", TaskPriority.LOW),
                resource_type=ResourceType.CPU,
                timeout=self._timeout
            )
        else:
            return await super().get_pool_liquidity(factory, token0, token1)
    
    async def _get_pool_liquidity_internal(
        self,
        factory: str,
        token0: str,
        token1: str
    ) -> float:
        """Internal implementation of get_pool_liquidity."""
        return await super().get_pool_liquidity(factory, token0, token1)
    
    def _create_web3_connection(self):
        """Create a new Web3 connection."""
        return Web3.AsyncHTTPProvider(
            self._rpc_url,
            request_kwargs={"timeout": self._timeout}
        )
    
    def _validate_web3_connection(self, connection) -> bool:
        """Validate a Web3 connection."""
        return True  # Simplified validation
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get resource statistics.
        
        Returns:
            Dictionary with resource statistics
        """
        if not self._resource_manager:
            return {}
        
        return self._resource_manager.get_stats()

async def create_optimized_web3_manager(config: Dict[str, Any]) -> OptimizedWeb3Manager:
    """
    Create and initialize an optimized Web3 manager.
    
    Args:
        config: Web3 configuration
        
    Returns:
        Initialized optimized Web3 manager
    """
    manager = OptimizedWeb3Manager(config)
    await manager.initialize()
    return manager