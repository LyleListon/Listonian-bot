"""Type definitions for DEX interfaces."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import List, Optional

from web3.types import ChecksumAddress


class DEXType(Enum):
    """Type of DEX protocol."""
    BASESWAP = auto()
    SWAPBASED = auto()
    PANCAKESWAP_V3 = auto()


@dataclass
class Token:
    """Token information."""
    address: ChecksumAddress
    symbol: str
    name: str
    decimals: int


@dataclass
class TokenAmount:
    """Token amount."""
    token: Token
    amount: Decimal

    def to_wei(self) -> int:
        """Convert amount to wei.
        
        Returns:
            Amount in wei
        """
        return int(self.amount * Decimal(10 ** self.token.decimals))

    @classmethod
    def from_wei(cls, token: Token, amount_wei: int) -> 'TokenAmount':
        """Create from wei amount.
        
        Args:
            token: Token
            amount_wei: Amount in wei
            
        Returns:
            Token amount
        """
        return cls(
            token=token,
            amount=Decimal(amount_wei) / Decimal(10 ** token.decimals)
        )


@dataclass
class PriceImpact:
    """Price impact information."""
    percentage: Decimal
    base_price: Decimal
    actual_price: Decimal
    is_high: bool


@dataclass
class LiquidityInfo:
    """Pool liquidity information."""
    token0_reserve: TokenAmount
    token1_reserve: TokenAmount
    total_supply: int
    updated_at: int


@dataclass
class PoolInfo:
    """Pool information."""
    address: ChecksumAddress
    token0: Token
    token1: Token
    fee: Decimal
    liquidity: LiquidityInfo
    protocol: DEXType


@dataclass
class SwapQuote:
    """Swap quote information."""
    input_amount: TokenAmount
    output_amount: TokenAmount
    price_impact: Decimal
    path: List[ChecksumAddress]
    gas_estimate: int


@dataclass
class SwapParams:
    """Swap parameters."""
    quote: SwapQuote
    slippage: Decimal
    deadline: int
    recipient: ChecksumAddress

    def _calculate_min_out(self) -> int:
        """Calculate minimum output amount with slippage.
        
        Returns:
            Minimum output amount in wei
        """
        min_amount = self.quote.output_amount.amount * (
            Decimal(1) - self.slippage
        )
        return int(min_amount * Decimal(10 ** self.quote.output_amount.token.decimals))