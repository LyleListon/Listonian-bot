"""
Core Interfaces Module

This module provides common interfaces and data structures used across the arbitrage system:
- Transaction types
- Token pair structures
- Liquidity data types
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from decimal import Decimal
from eth_typing import ChecksumAddress


@dataclass
class Transaction:
    """Represents a blockchain transaction."""

    to: ChecksumAddress
    from_: Optional[ChecksumAddress] = None
    value: int = 0
    gas: int = 0
    gas_price: int = 0
    nonce: Optional[int] = None
    data: str = "0x"
    chain_id: Optional[int] = None
    hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary format."""
        return {
            "to": self.to,
            "from": self.from_,
            "value": hex(self.value) if self.value else "0x0",
            "gas": hex(self.gas) if self.gas else "0x0",
            "gasPrice": hex(self.gas_price) if self.gas_price else "0x0",
            "nonce": hex(self.nonce) if self.nonce is not None else None,
            "data": self.data,
            "chainId": hex(self.chain_id) if self.chain_id is not None else None,
        }


@dataclass
class TokenPair:
    """Represents a trading pair of tokens."""

    token0: ChecksumAddress
    token1: ChecksumAddress
    fee: Optional[int] = None

    def __str__(self) -> str:
        """String representation of token pair."""
        return f"{self.token0}/{self.token1}"


@dataclass
class LiquidityData:
    """Represents pool liquidity information."""

    liquidity: Decimal
    fee: int
    token0_reserve: Decimal
    token1_reserve: Decimal
    last_update_timestamp: int

    @property
    def total_value_locked(self) -> Decimal:
        """Calculate total value locked in the pool."""
        return self.token0_reserve + self.token1_reserve


@dataclass
class PriceData:
    """Represents token price information."""

    price: Decimal
    timestamp: int
    source: str
    confidence: float = 1.0


@dataclass
class ExecutionResult:
    """Represents the result of an arbitrage execution."""

    success: bool
    profit: int
    gas_used: int
    execution_time: float
    error: Optional[str] = None
