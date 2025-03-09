"""
Web3 Interfaces Module

This module provides interfaces for:
- Transaction types
- Web3 client interactions
- Contract interactions
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
from eth_typing import ChecksumAddress, HexStr

@dataclass
class Transaction:
    """Transaction data structure."""

    to: ChecksumAddress
    value: int = 0
    data: bytes = b""
    nonce: Optional[int] = None
    gas: Optional[int] = None
    maxFeePerGas: Optional[int] = None
    maxPriorityFeePerGas: Optional[int] = None
    chainId: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        tx_dict = {
            "to": self.to,
            "value": self.value,
            "data": self.data
        }

        if self.nonce is not None:
            tx_dict["nonce"] = self.nonce
        if self.gas is not None:
            tx_dict["gas"] = self.gas
        if self.maxFeePerGas is not None:
            tx_dict["maxFeePerGas"] = self.maxFeePerGas
        if self.maxPriorityFeePerGas is not None:
            tx_dict["maxPriorityFeePerGas"] = self.maxPriorityFeePerGas
        if self.chainId is not None:
            tx_dict["chainId"] = self.chainId

        return tx_dict

@dataclass
class TransactionReceipt:
    """Transaction receipt data structure."""

    transactionHash: HexStr
    blockHash: HexStr
    blockNumber: int
    from_: ChecksumAddress
    to: Optional[ChecksumAddress]
    status: int
    gasUsed: int
    effectiveGasPrice: int
    logs: List[Dict[str, Any]]

    @classmethod
    def from_dict(cls, receipt: Dict[str, Any]) -> "TransactionReceipt":
        """Create from dictionary format."""
        return cls(
            transactionHash=receipt["transactionHash"].hex(),
            blockHash=receipt["blockHash"].hex(),
            blockNumber=receipt["blockNumber"],
            from_=receipt["from"],
            to=receipt.get("to"),
            status=receipt["status"],
            gasUsed=receipt["gasUsed"],
            effectiveGasPrice=receipt["effectiveGasPrice"],
            logs=receipt["logs"]
        )

class Web3Client(Protocol):
    """Protocol for Web3 client interface."""

    async def get_balance(
        self,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get ETH balance for address.

        Args:
            address: Optional address to check

        Returns:
            Balance in wei
        """
        ...

    async def get_token_balance(
        self,
        token_address: ChecksumAddress,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get token balance for address.

        Args:
            token_address: Token contract address
            address: Optional address to check

        Returns:
            Token balance
        """
        ...

    async def get_nonce(
        self,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get next nonce for address.

        Args:
            address: Optional address to check

        Returns:
            Next nonce
        """
        ...

    async def close(self):
        """Clean up resources."""
        ...
