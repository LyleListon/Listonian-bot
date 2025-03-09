"""Pool management for PancakeSwap V3."""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from web3.types import ChecksumAddress

from ...utils import get_contract
from .constants import (
    DEFAULT_FEE_TIER,
    ERRORS,
    FEE_AMOUNTS,
    TICK_SPACINGS,
)
from .math import (
    get_sqrt_ratio_at_tick,
    get_tick_at_sqrt_ratio,
    price_to_sqrt_price_x96,
    price_to_tick,
    sqrt_price_x96_to_price,
    tick_to_price,
)
from .types import (
    FeeTier,
    PoolCache,
    PoolImmutables,
    PoolKey,
    PoolState,
    PriceObservation,
    Slot0,
    TickData,
    Token,
)
from .validation import (
    validate_fee_tier,
    validate_pool_state,
    validate_price_limits,
    validate_tick,
)

logger = logging.getLogger(__name__)


class PoolManager:
    """Manager for PancakeSwap V3 pools."""

    def __init__(self, web3_manager):
        """Initialize pool manager.
        
        Args:
            web3_manager: Web3 manager instance
        """
        self.web3 = web3_manager
        self.cache = PoolCache()

    async def get_pool(
        self,
        token0: Token,
        token1: Token,
        fee: FeeTier = DEFAULT_FEE_TIER
    ) -> Optional[PoolState]:
        """Get pool state.
        
        Args:
            token0: First token
            token1: Second token
            fee: Fee tier
            
        Returns:
            Pool state if exists
        """
        # Validate fee tier
        valid, error = validate_fee_tier(fee)
        if not valid:
            raise ValueError(error)

        # Sort tokens
        if token0.address > token1.address:
            token0, token1 = token1, token0

        # Check cache
        key = self.cache.get_pool_key(token0.address, token1.address, fee)
        pool = self.cache.get_pool(key)
        if pool:
            return pool

        try:
            # Get pool address
            factory = get_contract(
                self.web3,
                self.factory_address,
                'pancakeswap_factory'
            )
            pool_address = await factory.functions.getPool(
                token0.address,
                token1.address,
                FEE_AMOUNTS[fee]
            ).call()

            if pool_address == "0x0000000000000000000000000000000000000000":
                return None

            # Get pool contract
            pool_contract = get_contract(
                self.web3,
                pool_address,
                'pancakeswap_pool'
            )

            # Get immutables if not cached
            immutables = self.cache.get_immutables(key)
            if not immutables:
                immutables = await self._get_pool_immutables(
                    pool_contract,
                    token0,
                    token1,
                    fee
                )
                self.cache.set_immutables(key, immutables)

            # Get current state
            slot0: Slot0 = await pool_contract.functions.slot0().call()
            liquidity = await pool_contract.functions.liquidity().call()

            # Create pool state
            state = PoolState(
                liquidity=liquidity,
                sqrt_price_x96=slot0.sqrt_price_x96,
                tick=slot0.tick,
                tick_spacing=TICK_SPACINGS[fee],
                fee=fee,
                token0=token0,
                token1=token1,
                observation_index=slot0.observation_index,
                observation_cardinality=slot0.observation_cardinality,
                observation_cardinality_next=slot0.observation_cardinality_next,
                fee_protocol=slot0.fee_protocol,
                unlocked=slot0.unlocked
            )

            # Validate state
            valid, error = validate_pool_state(state)
            if not valid:
                logger.warning(f"Invalid pool state: {error}")
                return None

            # Cache state
            self.cache.set_pool(key, state)
            return state

        except Exception as e:
            logger.error(f"Failed to get pool: {e}")
            return None

    async def get_pool_price(
        self,
        pool: PoolState
    ) -> Decimal:
        """Get current pool price.
        
        Args:
            pool: Pool state
            
        Returns:
            Current price
        """
        return sqrt_price_x96_to_price(pool.sqrt_price_x96)

    async def get_ticks(
        self,
        pool: PoolState,
        tick_lower: Optional[int] = None,
        tick_upper: Optional[int] = None
    ) -> Dict[int, TickData]:
        """Get tick data for range.
        
        Args:
            pool: Pool state
            tick_lower: Optional lower tick bound
            tick_upper: Optional upper tick bound
            
        Returns:
            Dictionary of tick data
        """
        key = self.cache.get_pool_key(
            pool.token0.address,
            pool.token1.address,
            pool.fee
        )

        # Get cached ticks
        cached_ticks = self.cache.get_ticks(key)

        # If no bounds specified, return all cached ticks
        if tick_lower is None and tick_upper is None:
            return cached_ticks

        # Validate bounds
        if tick_lower is not None:
            valid, error = validate_tick(tick_lower)
            if not valid:
                raise ValueError(error)

        if tick_upper is not None:
            valid, error = validate_tick(tick_upper)
            if not valid:
                raise ValueError(error)

        # Filter ticks by range
        filtered_ticks = {}
        for tick, data in cached_ticks.items():
            if (tick_lower is None or tick >= tick_lower) and \
               (tick_upper is None or tick <= tick_upper):
                filtered_ticks[tick] = data

        return filtered_ticks

    async def get_observations(
        self,
        pool: PoolState,
        count: int = 1
    ) -> List[PriceObservation]:
        """Get recent price observations.
        
        Args:
            pool: Pool state
            count: Number of observations to get
            
        Returns:
            List of price observations
        """
        key = self.cache.get_pool_key(
            pool.token0.address,
            pool.token1.address,
            pool.fee
        )
        return self.cache.get_observations(key)[-count:]

    async def _get_pool_immutables(
        self,
        pool_contract,
        token0: Token,
        token1: Token,
        fee: FeeTier
    ) -> PoolImmutables:
        """Get pool immutable parameters.
        
        Args:
            pool_contract: Pool contract
            token0: First token
            token1: Second token
            fee: Fee tier
            
        Returns:
            Pool immutables
        """
        return PoolImmutables(
            factory=await pool_contract.functions.factory().call(),
            token0=token0,
            token1=token1,
            fee=fee,
            tick_spacing=TICK_SPACINGS[fee],
            max_liquidity_per_tick=await pool_contract.functions.maxLiquidityPerTick().call()
        )