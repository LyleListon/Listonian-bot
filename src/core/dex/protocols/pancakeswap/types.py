"""Type definitions for PancakeSwap V3."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from web3.types import ChecksumAddress

from ...interfaces.types import Token


class FeeTier(Enum):
    """Available fee tiers."""
    LOWEST = 100   # 0.01%
    LOW = 500      # 0.05%
    MEDIUM = 3000  # 0.3%
    HIGH = 10000   # 1%


@dataclass
class TickData:
    """Data for a single tick."""
    tick_idx: int
    liquidity_net: int
    liquidity_gross: int
    fee_growth_outside0: int
    fee_growth_outside1: int
    initialized: bool = False


@dataclass
class PoolState:
    """Current state of a pool."""
    liquidity: int
    sqrt_price_x96: int
    tick: int
    tick_spacing: int
    fee: FeeTier
    token0: Token
    token1: Token
    observation_index: int
    observation_cardinality: int
    observation_cardinality_next: int
    fee_protocol: int
    unlocked: bool


@dataclass
class Slot0:
    """Slot0 data from pool contract."""
    sqrt_price_x96: int
    tick: int
    observation_index: int
    observation_cardinality: int
    observation_cardinality_next: int
    fee_protocol: int
    unlocked: bool


@dataclass
class PoolKey:
    """Key for identifying a pool."""
    token0: ChecksumAddress
    token1: ChecksumAddress
    fee: FeeTier


@dataclass
class PoolImmutables:
    """Immutable pool parameters."""
    factory: ChecksumAddress
    token0: Token
    token1: Token
    fee: FeeTier
    tick_spacing: int
    max_liquidity_per_tick: int


@dataclass
class SwapCache:
    """Cache for swap calculations."""
    liquidity_start: int
    block_timestamp: int
    fee_protocol: int
    seconds_per_liquidity_cumulative: int
    tick_cumulative: int
    computed_latest_observation: bool


@dataclass
class StepComputations:
    """Results of a single swap step."""
    sqrt_price_start_x96: int
    tick_next: int
    initialized: bool
    sqrt_price_next_x96: int
    amount_in: int
    amount_out: int
    fee_amount: int


@dataclass
class SwapState:
    """Current state during swap."""
    amount_specified_remaining: int
    amount_calculated: int
    sqrt_price_x96: int
    tick: int
    liquidity: int
    fee_growth_global: int


@dataclass
class PriceObservation:
    """Price observation at a point in time."""
    block_timestamp: int
    tick_cumulative: int
    seconds_per_liquidity_cumulative: int
    initialized: bool


class PoolCache:
    """Cache for pool data."""
    def __init__(self):
        self.pools: Dict[str, PoolState] = {}
        self.immutables: Dict[str, PoolImmutables] = {}
        self.observations: Dict[str, List[PriceObservation]] = {}
        self.ticks: Dict[str, Dict[int, TickData]] = {}

    def get_pool_key(self, token0: ChecksumAddress, token1: ChecksumAddress, fee: FeeTier) -> str:
        """Get cache key for pool.
        
        Args:
            token0: First token address
            token1: Second token address
            fee: Fee tier
            
        Returns:
            Cache key string
        """
        return f"{token0}-{token1}-{fee.value}"

    def get_pool(self, key: str) -> Optional[PoolState]:
        """Get cached pool state.
        
        Args:
            key: Cache key
            
        Returns:
            Pool state if exists
        """
        return self.pools.get(key)

    def set_pool(self, key: str, state: PoolState) -> None:
        """Cache pool state.
        
        Args:
            key: Cache key
            state: Pool state
        """
        self.pools[key] = state

    def get_immutables(self, key: str) -> Optional[PoolImmutables]:
        """Get cached pool immutables.
        
        Args:
            key: Cache key
            
        Returns:
            Pool immutables if exists
        """
        return self.immutables.get(key)

    def set_immutables(self, key: str, immutables: PoolImmutables) -> None:
        """Cache pool immutables.
        
        Args:
            key: Cache key
            immutables: Pool immutables
        """
        self.immutables[key] = immutables

    def get_observations(self, key: str) -> List[PriceObservation]:
        """Get cached price observations.
        
        Args:
            key: Cache key
            
        Returns:
            List of price observations
        """
        return self.observations.get(key, [])

    def set_observations(self, key: str, observations: List[PriceObservation]) -> None:
        """Cache price observations.
        
        Args:
            key: Cache key
            observations: Price observations
        """
        self.observations[key] = observations

    def get_ticks(self, key: str) -> Dict[int, TickData]:
        """Get cached ticks.
        
        Args:
            key: Cache key
            
        Returns:
            Dictionary of tick data
        """
        return self.ticks.get(key, {})

    def set_ticks(self, key: str, ticks: Dict[int, TickData]) -> None:
        """Cache ticks.
        
        Args:
            key: Cache key
            ticks: Tick data
        """
        self.ticks[key] = ticks