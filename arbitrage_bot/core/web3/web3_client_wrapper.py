"""
Web3 Client Wrapper Module

This module provides wrappers for web3.py functionality to ensure proper async/await handling.
"""

from typing import Any, Dict, Optional
from eth_typing import ChecksumAddress
from web3 import Web3

from .interfaces import Web3Client, Contract, ContractWrapper

class Web3ClientWrapper(Web3Client):
    """Wrapper for web3.py client to ensure proper async/await handling."""
    
    def __init__(self, w3: Web3):
        """
        Initialize wrapper.

        Args:
            w3: Web3.py client
        """
        self._w3 = w3

    @property
    def eth(self) -> Any:
        """
        Get eth module.

        Returns:
            Eth module
        """
        return self._w3.eth

    def contract(self, address: ChecksumAddress, abi: Dict[str, Any]) -> Contract:
        """
        Create contract instance.

        Args:
            address: Contract address
            abi: Contract ABI

        Returns:
            Wrapped contract instance
        """
        # Create contract using raw Web3 instance
        raw_contract = self._w3.eth.contract(address=address, abi=abi)
        # Wrap the contract
        return ContractWrapper(raw_contract)

    async def get_balance(self, address: ChecksumAddress) -> int:
        """
        Get ETH balance for address.

        Args:
            address: Address to check

        Returns:
            Balance in wei
        """
        return self._w3.eth.get_balance(address)

    async def get_transaction_count(self, address: ChecksumAddress) -> int:
        """
        Get transaction count (nonce) for address.

        Args:
            address: Address to check

        Returns:
            Transaction count
        """
        return self._w3.eth.get_transaction_count(address)

    async def get_block(self, block_identifier: Any) -> Dict[str, Any]:
        """
        Get block by number or hash.

        Args:
            block_identifier: Block number or hash

        Returns:
            Block data
        """
        return self._w3.eth.get_block(block_identifier)

    async def get_block_number(self) -> int:
        """
        Get current block number.

        Returns:
            Block number
        """
        return self._w3.eth.block_number

    async def get_gas_price(self) -> int:
        """
        Get current gas price.

        Returns:
            Gas price in wei
        """
        return self._w3.eth.gas_price

    async def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get transaction by hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction data
        """
        return self._w3.eth.get_transaction(tx_hash)

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get transaction receipt by hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction receipt
        """
        return self._w3.eth.get_transaction_receipt(tx_hash)

    async def wait_for_transaction_receipt(
        self,
        tx_hash: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Wait for transaction receipt.

        Args:
            tx_hash: Transaction hash
            timeout: Optional timeout in seconds

        Returns:
            Transaction receipt
        """
        return self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout)

    async def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """
        Estimate gas for transaction.

        Args:
            transaction: Transaction dict

        Returns:
            Gas estimate
        """
        return self._w3.eth.estimate_gas(transaction)

    async def send_raw_transaction(self, raw_transaction: bytes) -> str:
        """
        Send raw transaction.

        Args:
            raw_transaction: Raw transaction bytes

        Returns:
            Transaction hash
        """
        return self._w3.eth.send_raw_transaction(raw_transaction)

    async def send_transaction(self, transaction: Dict[str, Any]) -> str:
        """
        Send transaction.

        Args:
            transaction: Transaction dict

        Returns:
            Transaction hash
        """
        return self._w3.eth.send_transaction(transaction)

    async def call(self, transaction: Dict[str, Any]) -> bytes:
        """
        Call contract function.

        Args:
            transaction: Transaction dict

        Returns:
            Return data
        """
        return self._w3.eth.call(transaction)

    async def close(self):
        """Clean up resources."""
        if hasattr(self._w3.provider, "close"):
            await self._w3.provider.close()