"""
Cross-DEX Arbitrage Detector

This module contains the implementation of the CrossDexDetector,
which identifies arbitrage opportunities across different decentralized exchanges.
"""

import asyncio
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Any, Optional, Set, Tuple, cast # Import Any

from arbitrage_bot.dex.base_dex import BaseDEX
from ...interfaces import OpportunityDetector, MarketDataProvider
# Import only the models that actually exist and are used
from ...models import (
    ArbitrageOpportunity,
    TokenAmount,
    StrategyType,
    # Removed ArbitrageRoute, ArbitrageStep, TokenPair, DEXPair, MarketCondition, OpportunityStatus
)
# Import MarketCondition from the correct location if needed elsewhere, or handle differently.
# Assuming MarketCondition might be passed in kwargs or handled by the caller.
# Import TokenPair if needed for type hinting elsewhere, assuming it exists somewhere.
# For now, removing imports that cause errors.
from datetime import datetime # Added import for datetime

logger = logging.getLogger(__name__)


class CrossDexDetector(OpportunityDetector):
    """
    Detector for cross-DEX arbitrage opportunities.

    This detector identifies price discrepancies for the same token pair
    across different DEXs and calculates potential arbitrage profits.
    """

    def __init__(self, dexes: List[BaseDEX], config: Dict[str, Any] = None):
        """
        Initialize the cross-DEX detector.

        Args:
            dexes: List of DEXs to monitor
            config: Configuration dictionary
        """
        self.dexes = dexes
        self.config = config or {}

        # Configuration
        self.min_profit_percentage = Decimal(
            self.config.get("min_profit_percentage", "0.05")
        )  # 0.05%
        self.max_slippage = Decimal(self.config.get("max_slippage", "0.5"))  # 0.5%
        self.min_liquidity_usd = Decimal(
            self.config.get("min_liquidity_usd", "10000")
        )  # $10,000
        self.gas_cost_buffer_percentage = Decimal(
            self.config.get("gas_cost_buffer_percentage", "50")
        )  # 50%
        self.batch_size = int(self.config.get("batch_size", 50))
        self.max_pairs_per_dex = int(self.config.get("max_pairs_per_dex", 200))
        self.confidence_threshold = Decimal(
            self.config.get("confidence_threshold", "0.7")
        )  # 70% confidence

        # Cache for token pairs with timestamps
        self._token_pair_cache: Dict[str, Tuple[List[Any], float]] = {} # Use Any
        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._cache_ttl = float(self.config.get("cache_ttl_seconds", 5.0))

        # Locks
        self._cache_lock = asyncio.Lock()

        logger.info(f"CrossDexDetector initialized with {len(dexes)} DEXs")

    async def detect_opportunities(
        self, market_condition: Dict[str, Any], max_results: int = 10, **kwargs # Use Dict type hint
    ) -> List[ArbitrageOpportunity]:
        """
        Detect cross-DEX arbitrage opportunities.

        Args:
            market_condition: Current market condition
            max_results: Maximum number of opportunities to return
            **kwargs: Additional parameters

        Returns:
            List of arbitrage opportunities
        """
        logger.info("Detecting cross-DEX arbitrage opportunities")

        # Extract parameters from kwargs or use defaults
        token_filter = kwargs.get("token_filter")
        dex_filter = kwargs.get("dex_filter")
        min_profit_wei = int(
            kwargs.get("min_profit_wei", self.config.get("min_profit_wei", 0))
        )
        # Get all token pairs from DEXs
        try:
            token_pairs_by_dex = await self._get_token_pairs_by_dex(
                token_filter=token_filter, dex_filter=dex_filter
            )

            # Group token pairs by address pair
            grouped_pairs = self._group_token_pairs(token_pairs_by_dex)

            # Find arbitrage opportunities
            raw_opportunities = await self._find_arbitrage_opportunities(
                grouped_pairs=grouped_pairs,
                market_condition=market_condition,
                min_profit_wei=min_profit_wei,
            )
        except Exception as e:
            logger.error(f"Error finding arbitrage opportunities: {e}")
            raw_opportunities = []

        # Sort opportunities by expected profit and limit to max_results
        sorted_opportunities = sorted(
            raw_opportunities, key=lambda o: o.expected_profit_wei, reverse=True # Use expected_profit_wei
        )

        return sorted_opportunities[:max_results]

    async def _get_token_pairs_by_dex(
        self,
        token_filter: Optional[Set[str]] = None,
        dex_filter: Optional[Set[str]] = None,
    ) -> Dict[BaseDEX, List[Any]]: # Use Any
        """
        Get token pairs from each DEX with caching.

        Args:
            token_filter: Optional set of token addresses to filter by
            dex_filter: Optional set of DEX IDs to filter by

        Returns:
            Dictionary mapping DEXs to their token pairs
        """
        result: Dict[BaseDEX, List[Any]] = {} # Use Any

        # Filter DEXs if dex_filter is provided
        dexes_to_use = []
        if dex_filter:
            dexes_to_use = [dex for dex in self.dexes if dex.id in dex_filter]
        else:
            dexes_to_use = self.dexes

        # Get token pairs from each DEX with caching
        tasks = []
        for dex in dexes_to_use:
            task = asyncio.create_task(
                self._get_token_pairs_from_dex(dex=dex, token_filter=token_filter)
            )
            tasks.append((dex, task))

        # Wait for all tasks to complete
        for dex, task in tasks:
            try:
                token_pairs = await task
                if token_pairs:
                    result[dex] = token_pairs
            except Exception as e:
                logger.error(f"Error getting token pairs from {dex.id}: {e}")

        return result

    async def _get_token_pairs_from_dex(
        self, dex: BaseDEX, token_filter: Optional[Set[str]] = None
    ) -> List[Any]: # Use Any
        """
        Get token pairs from a single DEX with caching.

        Args:
            dex: DEX to get token pairs from
            token_filter: Optional set of token addresses to filter by

        Returns:
            List of token pairs from the DEX
        """
        cache_key = (
            f"{dex.id}_{hash(frozenset(token_filter)) if token_filter else 'all'}"
        )

        # Check cache
        async with self._cache_lock:
            cached = self._token_pair_cache.get(cache_key)
            current_time = time.time()

            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]

        # Get token pairs from DEX
        try:
            # Ensure DEX is price source
            if not isinstance(dex, BaseDEX):
                logger.warning(f"DEX {dex.id} is not a BaseDEX, skipping")
                return []

            # Get all pairs from DEX
            # Try different methods to get token pairs
            if hasattr(dex, 'get_token_pairs'):
                # Use get_token_pairs if available
                token_pairs = await dex.get_token_pairs(
                    max_pairs=self.max_pairs_per_dex
                )
            elif hasattr(dex, 'get_supported_tokens'):
                # If get_token_pairs is not available, try to build pairs from supported tokens
                logger.info(f"Using get_supported_tokens for {dex.id} instead of get_token_pairs")
                token_pairs = await self._build_token_pairs_from_supported_tokens(dex)
            elif hasattr(dex, 'get_pools'):
                # If get_pools is available, try to use that
                logger.info(f"Using get_pools for {dex.id} instead of get_token_pairs")
                token_pairs = await self._build_token_pairs_from_pools(dex)
            else:
                # No suitable method found
                logger.warning(f"DEX {dex.id} does not have get_token_pairs or alternative methods.")
                return []

            # Filter by tokens if specified
            if token_filter:
                token_pairs = [
                    pair
                    for pair in token_pairs
                    if pair.token0_address in token_filter
                    or pair.token1_address in token_filter
                ]

            # Update cache
            async with self._cache_lock:
                self._token_pair_cache[cache_key] = (token_pairs, time.time())

            return token_pairs

        except Exception as e:
            logger.error(f"Error getting token pairs from {dex.id}: {e}")
            return []

    def _group_token_pairs(
        self, token_pairs_by_dex: Dict[BaseDEX, List[Any]]
    ) -> Dict[str, Dict[BaseDEX, Any]]: # Use Any
        """
        Group token pairs by token address pair.

        Args:
            token_pairs_by_dex: Dictionary mapping DEXs to their token pairs

        Returns:
            Dictionary mapping token address pairs to DEXs and token pairs
        """
        grouped_pairs: Dict[str, Dict[BaseDEX, Any]] = {} # Use Any

        for dex, token_pairs in token_pairs_by_dex.items():
            for token_pair in token_pairs:
                # Create a unique key for the token pair
                # Ensure token0 is always the "smaller" address to make consistent keys
                if (
                    token_pair.token0_address.lower()
                    < token_pair.token1_address.lower()
                ):
                    key = f"{token_pair.token0_address.lower()}_{token_pair.token1_address.lower()}"
                else:
                    key = f"{token_pair.token1_address.lower()}_{token_pair.token0_address.lower()}"

                # Add to grouped pairs
                if key not in grouped_pairs:
                    grouped_pairs[key] = {}

                grouped_pairs[key][dex] = token_pair

        return grouped_pairs

    async def _find_arbitrage_opportunities(
        self,
        grouped_pairs: Dict[str, Dict[BaseDEX, Any]], # Use Any
        market_condition: Dict[str, Any],
        min_profit_wei: int,
    ) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities from grouped token pairs.

        Args:
            grouped_pairs: Dictionary mapping token address pairs to DEXs and token pairs
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei

        Returns:
            List of arbitrage opportunities
        """
        opportunities: List[ArbitrageOpportunity] = []

        # Process token pairs in batches
        keys = list(grouped_pairs.keys())
        batches = [
            keys[i : i + self.batch_size] for i in range(0, len(keys), self.batch_size)
        ]

        # Iterate through batches
        for batch in batches:
            batch_tasks = []
            for key in batch:
                dex_token_pairs = grouped_pairs[key]
                # Only process pairs available on at least 2 DEXs
                if len(dex_token_pairs) < 2:
                    continue

                task = asyncio.create_task(
                    self._process_token_pair_group(
                        key=key,
                        dex_token_pairs=dex_token_pairs,
                        market_condition=market_condition,
                        min_profit_wei=min_profit_wei,
                    )
                )
                batch_tasks.append(task)

            # Wait for batch to complete
            if batch_tasks:
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing token pair group: {result}")
                    elif result:
                        opportunities.extend(result)

        return opportunities

    async def _process_token_pair_group(
        self,
        key: str,
        dex_token_pairs: Dict[BaseDEX, Any], # Use Any
        market_condition: Dict[str, Any], # Use Dict type hint
        min_profit_wei: int,
    ) -> List[ArbitrageOpportunity]:
        """
        Process a group of token pairs on different DEXs to find arbitrage opportunities.

        Args:
            key: Token pair key
            dex_token_pairs: Dictionary mapping DEXs to token pairs
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei

        Returns:
            List of arbitrage opportunities
        """
        # Get prices from all DEXs for this token pair
        dex_prices: Dict[BaseDEX, Tuple[Decimal, Decimal]] = {}
        dex_list = list(dex_token_pairs.keys())

        for dex in dex_list:
            token_pair = dex_token_pairs[dex]

            try:
                # Get prices from DEX
                if not isinstance(dex, BaseDEX):
                    continue

                # Get price of token0 in terms of token1, and token1 in terms of token0
                token0_price, token1_price = await self._get_token_pair_prices(
                    dex=dex, token_pair=token_pair
                )

                dex_prices[dex] = (token0_price, token1_price)

            except Exception as e:
                logger.error(f"Error getting prices from {dex.id} for pair {key}: {e}")

        # Need at least 2 DEXs with valid prices
        if len(dex_prices) < 2:
            return []

        # Find arbitrage opportunities
        opportunities = []

        # Compare each DEX pair to find arbitrage opportunities
        for i, dex_a in enumerate(dex_list):
            if dex_a not in dex_prices:
                continue

            for dex_b in dex_list[i + 1 :]:
                if dex_b not in dex_prices:
                    continue

                token_pair_a = dex_token_pairs[dex_a]
                token_pair_b = dex_token_pairs[dex_b]

                price_a_0, price_a_1 = dex_prices[dex_a]
                price_b_0, price_b_1 = dex_prices[dex_b]

                # Check for profitable opportunities, token0 -> token1 direction
                if price_a_0 > price_b_0:
                    # Buy on dex_b, sell on dex_a
                    opportunity = await self._create_opportunity(
                        dex_buy=dex_b,
                        dex_sell=dex_a,
                        token_pair_buy=token_pair_b,
                        token_pair_sell=token_pair_a,
                        buy_price=price_b_0,
                        sell_price=price_a_0,
                        direction="0_to_1",
                        market_condition=market_condition,
                        min_profit_wei=min_profit_wei,
                    )
                    if opportunity:
                        opportunities.append(opportunity)

                # Check for profitable opportunities, token1 -> token0 direction
                if price_a_1 > price_b_1:
                    # Buy on dex_b, sell on dex_a
                    opportunity = await self._create_opportunity(
                        dex_buy=dex_b,
                        dex_sell=dex_a,
                        token_pair_buy=token_pair_b,
                        token_pair_sell=token_pair_a,
                        buy_price=price_b_1,
                        sell_price=price_a_1,
                        direction="1_to_0",
                        market_condition=market_condition,
                        min_profit_wei=min_profit_wei,
                    )
                    if opportunity:
                        opportunities.append(opportunity)

        return opportunities

    async def _build_token_pairs_from_supported_tokens(self, dex: BaseDEX) -> List[Any]:
        """
        Build token pairs from supported tokens.

        Args:
            dex: DEX to get token pairs from

        Returns:
            List of token pairs
        """
        from dataclasses import dataclass

        @dataclass
        class TokenPair:
            token0_address: str
            token1_address: str
            pool_address: str
            reserve0: Decimal
            reserve1: Decimal
            fee: Decimal
            dex_id: str
            token0_decimals: int = 18
            token1_decimals: int = 18

        try:
            # Get supported tokens
            supported_tokens = await dex.get_supported_tokens()
            if not supported_tokens:
                logger.warning(f"No supported tokens found for {dex.id}")
                return []

            # Create pairs from supported tokens
            pairs = []
            for i, token0 in enumerate(supported_tokens):
                for token1 in supported_tokens[i+1:]:
                    try:
                        # Check if pool exists
                        try:
                            pool_address = await dex.get_pool_address(token0, token1)
                        except (ValueError, AttributeError):
                            # Try with fee parameter if available
                            try:
                                if hasattr(dex, 'fee'):
                                    pool_address = await dex.get_pool_address(token0, token1, fee=dex.fee)
                                else:
                                    # No pool exists for this pair
                                    continue
                            except Exception:
                                # No pool exists for this pair
                                continue

                        if not pool_address or pool_address == "0x0000000000000000000000000000000000000000":
                            continue

                        # Get token decimals
                        token0_decimals = 18
                        token1_decimals = 18
                        try:
                            if hasattr(dex, 'get_token_decimals'):
                                token0_decimals = await dex.get_token_decimals(token0)
                                token1_decimals = await dex.get_token_decimals(token1)
                        except Exception as e:
                            logger.debug(f"Error getting token decimals: {e}")

                        # Get reserves
                        reserve0 = Decimal(0)
                        reserve1 = Decimal(0)
                        fee = Decimal("0.003")  # Default fee

                        try:
                            if hasattr(dex, 'get_reserves'):
                                reserves = await dex.get_reserves(pool_address)
                                if isinstance(reserves, tuple) and len(reserves) == 2:
                                    reserve0, reserve1 = reserves
                            elif hasattr(dex, 'get_pool_info'):
                                pool_info = await dex.get_pool_info(pool_address)
                                if pool_info:
                                    # Extract reserves from pool info
                                    if 'reserve0' in pool_info and 'reserve1' in pool_info:
                                        reserve0 = Decimal(str(pool_info['reserve0']))
                                        reserve1 = Decimal(str(pool_info['reserve1']))
                                    # Extract fee from pool info
                                    if 'fee' in pool_info:
                                        fee = Decimal(str(pool_info['fee'])) / Decimal("1000000")
                        except Exception as e:
                            logger.debug(f"Error getting reserves: {e}")
                            continue

                        # Create token pair
                        pair = TokenPair(
                            token0_address=token0,
                            token1_address=token1,
                            pool_address=pool_address,
                            reserve0=reserve0,
                            reserve1=reserve1,
                            fee=fee,
                            dex_id=dex.id,
                            token0_decimals=token0_decimals,
                            token1_decimals=token1_decimals
                        )
                        pairs.append(pair)

                        # Limit the number of pairs
                        if len(pairs) >= self.max_pairs_per_dex:
                            return pairs
                    except Exception as e:
                        logger.debug(f"Error creating pair {token0}/{token1}: {e}")
                        continue

            return pairs
        except Exception as e:
            logger.error(f"Error building token pairs from supported tokens for {dex.id}: {e}")
            return []

    async def _build_token_pairs_from_pools(self, dex: BaseDEX) -> List[Any]:
        """
        Build token pairs from pools.

        Args:
            dex: DEX to get token pairs from

        Returns:
            List of token pairs
        """
        from dataclasses import dataclass

        @dataclass
        class TokenPair:
            token0_address: str
            token1_address: str
            pool_address: str
            reserve0: Decimal
            reserve1: Decimal
            fee: Decimal
            dex_id: str
            token0_decimals: int = 18
            token1_decimals: int = 18

        try:
            # Get pools
            pools = await dex.get_pools()
            if not pools:
                logger.warning(f"No pools found for {dex.id}")
                return []

            # Create pairs from pools
            pairs = []
            for pool in pools:
                try:
                    # Extract pool data
                    pool_address = pool.get('address')
                    token0 = pool.get('token0')
                    token1 = pool.get('token1')

                    if not pool_address or not token0 or not token1:
                        continue

                    # Get token decimals
                    token0_decimals = 18
                    token1_decimals = 18
                    try:
                        if hasattr(dex, 'get_token_decimals'):
                            token0_decimals = await dex.get_token_decimals(token0)
                            token1_decimals = await dex.get_token_decimals(token1)
                    except Exception as e:
                        logger.debug(f"Error getting token decimals: {e}")

                    # Get reserves
                    reserve0 = pool.get('reserve0', Decimal(0))
                    reserve1 = pool.get('reserve1', Decimal(0))
                    fee = pool.get('fee', Decimal("0.003"))  # Default fee

                    # Create token pair
                    pair = TokenPair(
                        token0_address=token0,
                        token1_address=token1,
                        pool_address=pool_address,
                        reserve0=Decimal(str(reserve0)),
                        reserve1=Decimal(str(reserve1)),
                        fee=Decimal(str(fee)),
                        dex_id=dex.id,
                        token0_decimals=token0_decimals,
                        token1_decimals=token1_decimals
                    )
                    pairs.append(pair)

                    # Limit the number of pairs
                    if len(pairs) >= self.max_pairs_per_dex:
                        return pairs
                except Exception as e:
                    logger.debug(f"Error creating pair from pool: {e}")
                    continue

            return pairs
        except Exception as e:
            logger.error(f"Error building token pairs from pools for {dex.id}: {e}")
            return []

    async def _get_token_pair_prices(
        self, dex: BaseDEX, token_pair: Any
    ) -> Tuple[Decimal, Decimal]:
        """
        Get prices for a token pair from a DEX using get_amounts_out.

        Args:
            dex: DEX instance
            token_pair: Object containing token0_address, token1_address, etc.

        Returns:
            Tuple of (token0_price, token1_price) where:
            - token0_price: Price of token0 in terms of token1 (e.g., ETH/USDC)
            - token1_price: Price of token1 in terms of token0 (e.g., USDC/ETH)
        """
        token0_address = token_pair.token0_address
        token1_address = token_pair.token1_address
        cache_key_0 = f"{dex.id}_{token0_address}_{token1_address}"
        cache_key_1 = f"{dex.id}_{token1_address}_{token0_address}"
        current_time = time.time()

        # Check cache first
        async with self._cache_lock:
            cached_0 = self._price_cache.get(cache_key_0)
            if cached_0 and (current_time - cached_0[1] < self._cache_ttl):
                token0_price = cached_0[0]
            else:
                token0_price = None

            cached_1 = self._price_cache.get(cache_key_1)
            if cached_1 and (current_time - cached_1[1] < self._cache_ttl):
                token1_price = cached_1[0]
            else:
                token1_price = None

        # Fetch prices if not cached or expired
        if token0_price is None or token1_price is None:
            try:
                # Get decimals (assuming BaseDEX provides this or we can fetch it)
                # Fallback to 18 if method doesn't exist
                decimals0 = getattr(token_pair, 'token0_decimals', 18)
                decimals1 = getattr(token_pair, 'token1_decimals', 18)
                if not isinstance(decimals0, int): # Fetch if not available on pair object
                     decimals0 = await dex.get_token_decimals(token0_address)
                if not isinstance(decimals1, int):
                     decimals1 = await dex.get_token_decimals(token1_address)

                # --- Calculate price of token0 in terms of token1 ---
                # Get how much token1 we get for 1 unit of token0
                amount_in_0 = Decimal(10**decimals0) # 1 unit of token0 in wei
                path_0_to_1 = [token0_address, token1_address]
                amounts_out_0 = await dex.get_amounts_out(amount_in_0 / Decimal(10**decimals0), path_0_to_1) # Pass human-readable amount
                if len(amounts_out_0) > 1:
                    token0_price = amounts_out_0[1] # Amount of token1 received for 1 token0
                    async with self._cache_lock:
                        self._price_cache[cache_key_0] = (token0_price, current_time)
                else:
                    token0_price = Decimal("0") # Failed quote

                # --- Calculate price of token1 in terms of token0 ---
                # Get how much token0 we get for 1 unit of token1
                amount_in_1 = Decimal(10**decimals1) # 1 unit of token1 in wei
                path_1_to_0 = [token1_address, token0_address]
                amounts_out_1 = await dex.get_amounts_out(amount_in_1 / Decimal(10**decimals1), path_1_to_0) # Pass human-readable amount
                if len(amounts_out_1) > 1:
                    token1_price = amounts_out_1[1] # Amount of token0 received for 1 token1
                    async with self._cache_lock:
                        self._price_cache[cache_key_1] = (token1_price, current_time)
                else:
                    token1_price = Decimal("0") # Failed quote

            except Exception as e:
                logger.error(f"Error getting prices via get_amounts_out for {dex.id}: {e}")
                token0_price = token0_price if token0_price is not None else Decimal("0")
                token1_price = token1_price if token1_price is not None else Decimal("0")

        return token0_price, token1_price

    async def _create_opportunity(
        self,
        dex_buy: BaseDEX,
        dex_sell: BaseDEX,
        token_pair_buy: Any, # Use Any
        token_pair_sell: Any, # Use Any
        buy_price: Decimal,
        sell_price: Decimal,
        direction: str,
        market_condition: Dict[str, Any], # Use Dict type hint
        min_profit_wei: int,
    ) -> Optional[ArbitrageOpportunity]:
        """
        Create an arbitrage opportunity if it's profitable.

        Args:
            dex_buy: DEX to buy on
            dex_sell: DEX to sell on
            token_pair_buy: Token pair on buy DEX
            token_pair_sell: Token pair on sell DEX
            buy_price: Price on buy DEX
            sell_price: Price on sell DEX
            direction: Trading direction (0_to_1 or 1_to_0)
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei

        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        # Determine token addresses based on direction
        if direction == "0_to_1":
            # token0 -> token1 (buy token1 with token0, then sell token1 for token0)
            input_token_address = token_pair_buy.token0_address
            output_token_address = token_pair_buy.token0_address
            intermediate_token_address = token_pair_buy.token1_address
        else:
            # token1 -> token0 (buy token0 with token1, then sell token0 for token1)
            input_token_address = token_pair_buy.token1_address
            output_token_address = token_pair_buy.token1_address
            intermediate_token_address = token_pair_buy.token0_address

        # Calculate price difference and potential profit
        price_diff_percentage = (sell_price - buy_price) / buy_price * Decimal("100")

        # Skip if price difference is too small
        if price_diff_percentage < self.min_profit_percentage:
            return None

        # Estimate gas costs
        # Use average gas costs from market condition or default values
        gas_price = (
            market_condition.get('gas_price', 50 * 10**9) # Use .get()
        )  # 50 gwei default
        priority_fee = (
            market_condition.get('priority_fee', 1.5 * 10**9) # Use .get()
        )  # 1.5 gwei default

        # Estimate gas usage - these would be more accurate with actual execution data
        estimated_gas_buy = 150000  # Approximate gas for swap
        estimated_gas_sell = 150000  # Approximate gas for swap
        total_gas_estimate = estimated_gas_buy + estimated_gas_sell

        # Calculate gas cost
        gas_cost_wei = total_gas_estimate * (gas_price + priority_fee)

        # Add buffer for potential increases
        gas_cost_with_buffer = (
            gas_cost_wei
            * (Decimal("100") + self.gas_cost_buffer_percentage)
            / Decimal("100")
        )

        # Calculate token amounts for a sample trade to estimate profit
        # This uses a simplified approach - actual implementation would account for price impact
        input_amount_wei = 1 * 10**18  # 1 token as sample size
        intermediate_amount_wei = input_amount_wei * buy_price
        output_amount_wei = intermediate_amount_wei * sell_price
        expected_profit_wei = output_amount_wei - input_amount_wei

        # Check if profit exceeds gas costs and minimum profit threshold
        if (
            expected_profit_wei <= gas_cost_with_buffer
            or expected_profit_wei < min_profit_wei
        ):
            return None

        # Create path as list of dictionaries
        path_list = [
            { # Step 1: Buy intermediate token on dex_buy
                "dex_id": dex_buy.id,
                "dex_name": getattr(dex_buy, 'name', dex_buy.id), # Use name if available, else id
                "input_token_address": input_token_address,
                "input_token_symbol": (
                    getattr(token_pair_buy, 'token0_symbol', 'TOKEN0') # Use symbol if available
                    if direction == "0_to_1"
                    else getattr(token_pair_buy, 'token1_symbol', 'TOKEN1')
                ),
                "input_amount_wei": input_amount_wei,
                "output_token_address": intermediate_token_address,
                "output_token_symbol": (
                     getattr(token_pair_buy, 'token1_symbol', 'TOKEN1') # Use symbol if available
                    if direction == "0_to_1"
                    else getattr(token_pair_buy, 'token0_symbol', 'TOKEN0')
                ),
                "output_amount_wei": int(intermediate_amount_wei), # Approximate, ensure int
                "action": "swap",
                "gas_estimate": estimated_gas_buy,
            },
            { # Step 2: Sell intermediate token on dex_sell
                "dex_id": dex_sell.id,
                "dex_name": getattr(dex_sell, 'name', dex_sell.id), # Use name if available, else id
                "input_token_address": intermediate_token_address,
                "input_token_symbol": (
                    getattr(token_pair_sell, 'token1_symbol', 'TOKEN1') # Use symbol if available
                    if direction == "0_to_1"
                    else getattr(token_pair_sell, 'token0_symbol', 'TOKEN0')
                ),
                "input_amount_wei": int(intermediate_amount_wei), # Approximate, ensure int
                "output_token_address": output_token_address,
                "output_token_symbol": (
                    getattr(token_pair_sell, 'token0_symbol', 'TOKEN0') # Use symbol if available
                    if direction == "0_to_1"
                    else getattr(token_pair_sell, 'token1_symbol', 'TOKEN1')
                ),
                "output_amount_wei": int(output_amount_wei), # Approximate, ensure int
                "action": "swap",
                "gas_estimate": estimated_gas_sell,
            },
        ]

        # Calculate profit margin as percentage
        profit_margin_percentage = (
            Decimal("100") * (output_amount_wei - input_amount_wei) / input_amount_wei
        )

        # Calculate profit after gas costs
        profit_after_gas = expected_profit_wei - gas_cost_wei

        # Create opportunity using the structure from models.py
        opportunity = ArbitrageOpportunity(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(), # Use current time
            token_in=input_token_address,
            token_out=output_token_address, # This should be same as input for arbitrage
            amount_in_wei=int(input_amount_wei),
            path=path_list,
            dexes=[dex_buy.id, dex_sell.id],
            # Placeholder values - these require external price feeds or further calculation
            input_price_usd=0.0,
            output_price_usd=0.0,
            expected_profit_wei=int(expected_profit_wei),
            expected_profit_usd=0.0, # Placeholder
            gas_cost_wei=int(gas_cost_wei),
            gas_cost_usd=0.0, # Placeholder
            net_profit_usd=0.0, # Placeholder
            confidence_score=float(self._calculate_confidence_score( # Ensure float
                price_diff_percentage=price_diff_percentage,
                market_condition=market_condition,
                token_pair_buy=token_pair_buy,
                token_pair_sell=token_pair_sell,
            )),
            # Placeholder values for risk/validation/execution details
            risk_factors={},
            price_validated=False, # Assume not validated yet
            liquidity_validated=False, # Assume not validated yet
            execution_deadline=datetime.fromtimestamp(int(time.time()) + 300), # Default 5 min deadline
            max_slippage=float(self.max_slippage), # Use configured slippage
            flashloan_required=False, # Assume no flashloan needed for simple cross-dex
            # Removed fields not in models.py: expected_profit_after_gas, profit_margin_percentage, gas_estimate, gas_price, priority_fee, strategy_type, status, creation_timestamp, metadata
        )

        return opportunity

    def _calculate_confidence_score(
        self,
        price_diff_percentage: Decimal,
        market_condition: Dict[str, Any],
        token_pair_buy: Any,
        token_pair_sell: Any,
    ) -> Decimal:
        """
        Calculate confidence score for an arbitrage opportunity.

        Args:
            price_diff_percentage: Price difference percentage
            market_condition: Current market condition
            token_pair_buy: Token pair on buy DEX
            token_pair_sell: Token pair on sell DEX

        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from price difference
        # Higher price difference = higher confidence
        base_confidence = min(price_diff_percentage / Decimal("5"), Decimal("1"))

        # Adjust for market volatility
        volatility_factor = Decimal("1")
        # Access dict keys using .get() with a default value
        market_volatility = market_condition.get('market_volatility', 0.0)
        if market_volatility:
            # Higher volatility = lower confidence
            volatility_factor = max(
                Decimal("1") - Decimal(str(market_volatility)) / Decimal("100"), # Use the variable
                Decimal("0.2"),
            )

        # Adjust for liquidity
        liquidity_factor = Decimal("1")
        # Use getattr for potentially missing attributes on token_pair objects
        liquidity_buy = getattr(token_pair_buy, 'liquidity_usd', None)
        liquidity_sell = getattr(token_pair_sell, 'liquidity_usd', None)
        if liquidity_buy and liquidity_sell:
            # Higher liquidity = higher confidence
            buy_liquidity = min(
                Decimal(str(liquidity_buy)) / self.min_liquidity_usd, Decimal("1") # Use variable
            )
            sell_liquidity = min(
                Decimal(str(liquidity_sell)) / self.min_liquidity_usd, Decimal("1") # Use variable
            )
            liquidity_factor = (buy_liquidity + sell_liquidity) / Decimal("2")

        # Adjust for network congestion
        congestion_factor = Decimal("1")
        network_congestion = market_condition.get('network_congestion', 0.0)
        if network_congestion:
            # Higher congestion = lower confidence
            congestion_factor = max(
                Decimal("1") - Decimal(str(network_congestion)) / Decimal("100"), # Use variable
                Decimal("0.2"),
            )

        # Calculate final confidence score
        confidence = (
            base_confidence * volatility_factor * liquidity_factor * congestion_factor
        )

        # Ensure score is between 0 and 1
        return max(min(confidence, Decimal("1")), Decimal("0"))


async def create_cross_dex_detector(
    dexes: List[BaseDEX], config: Dict[str, Any] = None # Use BaseDEX
) -> CrossDexDetector:
    """
    Factory function to create a cross-DEX detector.

    Args:
        dexes: List of DEXs to monitor
        config: Configuration dictionary

    Returns:
        Initialized cross-DEX detector
    """
    return CrossDexDetector(dexes=dexes, config=config)
