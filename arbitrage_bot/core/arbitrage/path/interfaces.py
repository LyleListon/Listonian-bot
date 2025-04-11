"""
Interfaces for the path module.

This module defines the interfaces used by the path finding and optimization
components of the arbitrage bot.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Union


@dataclass
class Pool:
    """
    Represents a liquidity pool.

    Attributes:
        address: Pool contract address
        token0: Address of the first token in the pool
        token1: Address of the second token in the pool
        reserves0: Reserves of token0
        reserves1: Reserves of token1
        fee: Fee in basis points (e.g., 3000 = 0.3%)
        pool_type: Type of pool (e.g., "constant_product", "stable", "weighted")
        dex: DEX name (e.g., "uniswap_v2", "uniswap_v3", "sushiswap")
    """

    address: str
    token0: str
    token1: str
    reserves0: Optional[Decimal] = None
    reserves1: Optional[Decimal] = None
    fee: int = 3000  # 0.3% default
    pool_type: str = "constant_product"
    dex: str = "unknown"

    def __post_init__(self):
        """Validate pool attributes."""
        # Ensure token addresses are checksummed
        if self.token0 and not self.token0.startswith("0x"):
            raise ValueError(f"Token0 address must be checksummed: {self.token0}")
        if self.token1 and not self.token1.startswith("0x"):
            raise ValueError(f"Token1 address must be checksummed: {self.token1}")


@dataclass
class ArbitragePath:
    """
    Represents an arbitrage path.

    Attributes:
        tokens: List of token addresses in the path
        pools: List of pools in the path
        dexes: List of DEX names for each hop
        swap_data: Optional swap data for each hop
        optimal_amount: Optimal input amount for maximum profit
        expected_output: Expected output amount
        path_yield: Yield of the path (output/input)
        profit: Profit amount (expected_output - optimal_amount)
        confidence: Confidence level (0.0-1.0)
        estimated_gas: Estimated gas usage
        estimated_gas_cost: Estimated gas cost in ETH
        execution_priority: Priority for execution (lower is higher priority)
    """

    tokens: List[str]
    pools: List[Pool]
    dexes: List[str]
    swap_data: Optional[List[Dict[str, Any]]] = None
    optimal_amount: Optional[Decimal] = None
    expected_output: Optional[Decimal] = None
    path_yield: Optional[Decimal] = None
    confidence: float = 0.5
    estimated_gas: int = 0
    estimated_gas_cost: Optional[Decimal] = None
    execution_priority: int = 0

    def __post_init__(self):
        """Calculate derived attributes."""
        # Calculate profit if optimal_amount and expected_output are set
        if self.optimal_amount is not None and self.expected_output is not None:
            self.profit = self.expected_output - self.optimal_amount
        else:
            self.profit = None

        # Calculate path yield if optimal_amount and expected_output are set
        if (
            self.optimal_amount is not None
            and self.expected_output is not None
            and self.optimal_amount > 0
        ):
            self.path_yield = self.expected_output / self.optimal_amount
        else:
            self.path_yield = None

    @property
    def is_cyclic(self) -> bool:
        """Check if the path is cyclic (starts and ends with the same token)."""
        return len(self.tokens) >= 2 and self.tokens[0] == self.tokens[-1]

    @property
    def start_token(self) -> str:
        """Get the start token of the path."""
        return self.tokens[0] if self.tokens else ""

    @property
    def end_token(self) -> str:
        """Get the end token of the path."""
        return self.tokens[-1] if self.tokens else ""

    @property
    def is_valid(self) -> bool:
        """Check if the path is valid."""
        # Check if tokens and pools are non-empty
        if not self.tokens or not self.pools:
            return False

        # Check if the path is cyclic
        if not self.is_cyclic:
            return False

        # Check if the number of pools is correct
        if len(self.pools) != len(self.tokens) - 1:
            return False

        # Check if the number of dexes is correct
        if len(self.dexes) != len(self.pools):
            return False

        # Check if the path is profitable
        if self.profit is None or self.profit <= 0:
            return False

        return True


@dataclass
class MultiPathOpportunity:
    """
    Represents a multi-path arbitrage opportunity.

    Attributes:
        paths: List of arbitrage paths
        start_token: Start token address
        required_amount: Total required amount
        expected_profit: Expected profit
        allocations: List of allocated amounts for each path
        confidence_level: Overall confidence level
        created_at: Creation timestamp
        expiration: Expiration timestamp
    """

    paths: List[ArbitragePath]
    start_token: str
    required_amount: Decimal
    expected_profit: Decimal
    allocations: List[Decimal]
    confidence_level: float
    created_at: int
    expiration: Optional[int] = None

    @property
    def is_valid(self) -> bool:
        """Check if the opportunity is valid."""
        # Check if paths and allocations are non-empty
        if not self.paths or not self.allocations:
            return False

        # Check if the number of paths and allocations match
        if len(self.paths) != len(self.allocations):
            return False

        # Check if all paths are valid
        if not all(path.is_valid for path in self.paths):
            return False

        # Check if all paths have the same start token
        if not all(path.start_token == self.start_token for path in self.paths):
            return False

        # Check if the opportunity is profitable
        if self.expected_profit <= 0:
            return False

        # Check if the opportunity has expired
        if self.expiration is not None and self.expiration < self.created_at:
            return False

        return True
