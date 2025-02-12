"""Web3 manager for blockchain interactions."""

import logging
from typing import Dict, Optional, Type, Union

from web3.types import Wei
from web3.exceptions import Web3Exception

from .providers.base import BaseProvider
from .providers.http import HttpProvider

logger = logging.getLogger(__name__)

class Web3Manager:
    """Manages Web3 connections and blockchain interactions."""

    def __init__(
        self,
        url: str,
        chain_id: int,
        retry_count: int = 3,
        provider_class: Type[BaseProvider] = HttpProvider
    ):
        """Initialize the Web3 manager.
        
        Args:
            url: RPC endpoint URL
            chain_id: Network chain ID
            retry_count: Number of retry attempts
            provider_class: Provider implementation to use
        """
        self._provider: Optional[BaseProvider] = None
        self._url = url
        self._chain_id = chain_id
        self._retry_count = retry_count
        self._provider_class = provider_class

    @property
    def provider(self) -> BaseProvider:
        """Get the current provider.
        
        Returns:
            BaseProvider: The initialized provider
            
        Raises:
            RuntimeError: If not connected
        """
        if not self._provider:
            raise RuntimeError("Not connected to blockchain")
        return self._provider

    async def connect(self) -> None:
        """Connect to the blockchain network.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self._provider = self._provider_class(
                url=self._url,
                chain_id=self._chain_id,
                retry_count=self._retry_count
            )
            await self._provider.connect()
            logger.info(
                f"Connected to chain {self._chain_id} at {self._url}"
            )
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self._provider = None
            raise ConnectionError(f"Failed to connect: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the blockchain network."""
        if self._provider:
            await self._provider.disconnect()
            self._provider = None
            logger.info("Disconnected from blockchain")

    async def is_connected(self) -> bool:
        """Check if connected to blockchain.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return (
            self._provider is not None and 
            await self._provider.is_connected()
        )

    async def get_block_number(self) -> int:
        """Get current block number.
        
        Returns:
            int: Current block number
            
        Raises:
            Web3Error: If request fails
        """
        return await self.provider.get_block_number()

    async def get_gas_price(self) -> Wei:
        """Get current gas price.
        
        Returns:
            Wei: Current gas price in wei
            
        Raises:
            Web3Error: If request fails
        """
        return await self.provider.get_gas_price()

    async def estimate_gas(
        self,
        transaction: Dict[str, Union[str, int]]
    ) -> int:
        """Estimate gas for transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            int: Estimated gas cost
            
        Raises:
            Web3Error: If estimation fails
        """
        return await self.provider.estimate_gas(transaction)

    async def send_transaction(
        self,
        transaction: Dict[str, Union[str, int]]
    ) -> str:
        """Send a transaction.
        
        Args:
            transaction: Transaction parameters
            
        Returns:
            str: Transaction hash
            
        Raises:
            Web3Error: If transaction fails
        """
        try:
            # Estimate gas if not provided
            if 'gas' not in transaction:
                gas = await self.estimate_gas(transaction)
                transaction['gas'] = int(gas * 1.1)  # Add 10% buffer

            # Get gas price if not provided
            if 'gasPrice' not in transaction:
                transaction['gasPrice'] = await self.get_gas_price()

            # Send transaction
            tx_hash = await self.provider.web3.eth.send_transaction(transaction)
            logger.info(f"Transaction sent: {tx_hash.hex()}")
            return tx_hash.hex()

        except Web3Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise

    async def wait_for_transaction(
        self,
        tx_hash: str,
        timeout: int = 120,
        poll_interval: int = 2
    ) -> Dict[str, any]:
        """Wait for transaction to be mined.
        
        Args:
            tx_hash: Transaction hash
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds
            
        Returns:
            Dict: Transaction receipt
            
        Raises:
            TimeoutError: If transaction not mined within timeout
            Web3Error: If transaction fails
        """
        try:
            receipt = await self.provider.web3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=timeout,
                poll_latency=poll_interval
            )
            logger.info(
                f"Transaction {tx_hash} mined in block {receipt['blockNumber']}"
            )
            return receipt

        except Web3Exception as e:
            logger.error(f"Failed to get transaction receipt: {e}")
            raise