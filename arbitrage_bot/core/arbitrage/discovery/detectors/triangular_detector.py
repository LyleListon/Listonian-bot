"""
Triangular Arbitrage Detector

This module contains the implementation of the TriangularDetector,
which identifies triangular arbitrage opportunities within a single DEX.
"""

import asyncio
import logging
import time
import uuid
from decimal import Decimal
from typing import Dict, List, Any, Optional, Set, Tuple, cast, DefaultDict # Import Any
from collections import defaultdict

from arbitrage_bot.dex.base_dex import BaseDEX # Corrected import
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


class TriangularDetector(OpportunityDetector):
    """
    Detector for triangular arbitrage opportunities.

    This detector identifies price discrepancies within a single DEX by trading
    through multiple tokens in a cycle and calculating the potential profit.
    """

    def __init__(self, dexes: List[BaseDEX], config: Dict[str, Any] = None): # Use BaseDEX
        """
        Initialize the triangular detector.

        Args:
            dexes: List of DEXs to monitor
            config: Configuration dictionary
        """
        self.dexes = dexes
        self.config = config or {}

        # Configuration
        self.min_profit_percentage = Decimal(
            self.config.get("min_profit_percentage", "0.1")
        )  # 0.1%
        self.max_slippage = Decimal(self.config.get("max_slippage", "0.5"))  # 0.5%
        self.min_liquidity_usd = Decimal(
            self.config.get("min_liquidity_usd", "10000")
        )  # $10,000
        self.gas_cost_buffer_percentage = Decimal(
            self.config.get("gas_cost_buffer_percentage", "50")
        )  # 50%
        self.batch_size = int(self.config.get("batch_size", 20))
        self.max_path_length = int(
            self.config.get("max_path_length", 3)
        )  # Maximum tokens in a path (typically 3 for triangular)
        self.confidence_threshold = Decimal(
            self.config.get("confidence_threshold", "0.7")
        )  # 70% confidence
        self.base_tokens = set(
            self.config.get("base_tokens", [])
        )  # List of base tokens to use as starting points

        # Cache for token pairs and prices with timestamps
        self._token_pair_cache: Dict[str, Tuple[List[Any], float]] = {} # Use Any
        self._price_cache: Dict[str, Tuple[Decimal, float]] = {}
        self._token_graph_cache: Dict[
            str, Tuple[DefaultDict[str, List[Tuple[str, Any]]], float] # Use Any
        ] = {}
        self._cache_ttl = float(self.config.get("cache_ttl_seconds", 5.0))

        # Locks
        self._cache_lock = asyncio.Lock()

        logger.info(f"TriangularDetector initialized with {len(dexes)} DEXs")

    async def detect_opportunities(
        self, market_condition: Dict[str, Any], max_results: int = 10, **kwargs # Use Dict
    ) -> List[ArbitrageOpportunity]:
        """
        Detect triangular arbitrage opportunities.

        Args:
            market_condition: Current market condition
            max_results: Maximum number of opportunities to return
            **kwargs: Additional parameters

        Returns:
            List of arbitrage opportunities
        """
        logger.info("Detecting triangular arbitrage opportunities")

        # Extract parameters from kwargs or use defaults
        token_filter = kwargs.get("token_filter")
        dex_filter = kwargs.get("dex_filter")
        min_profit_wei = int(
            kwargs.get("min_profit_wei", self.config.get("min_profit_wei", 0))
        )
        base_tokens = kwargs.get("base_tokens", self.base_tokens)

        # Process each DEX separately
        all_opportunities = []

        # Filter DEXs if dex_filter is provided
        dexes_to_use = []
        if dex_filter:
            dexes_to_use = [dex for dex in self.dexes if dex.id in dex_filter]
        else:
            dexes_to_use = self.dexes

        # Process each DEX in parallel
        tasks = []
        for dex in dexes_to_use:
            task = asyncio.create_task(
                self._process_single_dex(
                    dex=dex,
                    token_filter=token_filter,
                    base_tokens=base_tokens,
                    market_condition=market_condition,
                    min_profit_wei=min_profit_wei,
                )
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error processing DEX: {result}")
            elif result:
                all_opportunities.extend(result)

        # Sort opportunities by expected profit and limit to max_results
        sorted_opportunities = sorted(
            all_opportunities, key=lambda o: o.expected_profit_wei, reverse=True # Use expected_profit_wei
        )

        return sorted_opportunities[:max_results]

    async def _process_single_dex(
        self,
        dex: BaseDEX, # Use BaseDEX
        token_filter: Optional[Set[str]],
        base_tokens: Optional[Set[str]],
        market_condition: Dict[str, Any], # Use Dict
        min_profit_wei: int,
    ) -> List[ArbitrageOpportunity]:
        """
        Process a single DEX to find triangular arbitrage opportunities.

        Args:
            dex: DEX to process
            token_filter: Optional set of token addresses to filter by
            base_tokens: Optional set of base tokens to use as starting points
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei

        Returns:
            List of arbitrage opportunities
        """
        # Ensure DEX is a price source
        if not isinstance(dex, BaseDEX): # Use BaseDEX
            logger.warning(f"DEX {dex.id} is not a BaseDEX, skipping")
            return []

        # Get token pairs and build token graph
        token_graph = await self._build_token_graph(dex, token_filter) # Pass dex

        # If no base tokens specified, use tokens with the most connections
        actual_base_tokens = base_tokens or await self._get_most_connected_tokens(
            token_graph, 5
        )

        # Find triangular opportunities
        opportunities = []

        # Process base tokens in batches
        base_token_list = list(actual_base_tokens)
        batches = [
            base_token_list[i : i + self.batch_size]
            for i in range(0, len(base_token_list), self.batch_size)
        ]

        for batch in batches:
            batch_tasks = []
            for base_token in batch:
                task = asyncio.create_task(
                    self._find_triangular_paths(
                        dex=dex, # Pass dex
                        token_graph=token_graph,
                        base_token=base_token,
                        market_condition=market_condition,
                        min_profit_wei=min_profit_wei,
                    )
                )
                batch_tasks.append(task)

            if batch_tasks:
                batch_results = await asyncio.gather(
                    *batch_tasks, return_exceptions=True
                )
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error finding triangular paths: {result}")
                    elif result:
                        opportunities.extend(result)

        return opportunities

    async def _build_token_graph(
        self, dex: BaseDEX, token_filter: Optional[Set[str]] # Use BaseDEX
    ) -> DefaultDict[str, List[Tuple[str, Any]]]: # Use Any
        """
        Build a graph of tokens connected by trading pairs.

        Args:
            dex: DEX to get token pairs from
            token_filter: Optional set of token addresses to filter by

        Returns:
            Graph of tokens as adjacency list
        """
        cache_key = f"{dex.id}_graph_{hash(frozenset(token_filter)) if token_filter else 'all'}"

        # Check cache
        async with self._cache_lock:
            cached = self._token_graph_cache.get(cache_key)
            current_time = time.time()

            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]

        # Get token pairs
        token_pairs = await self._get_token_pairs_from_dex(dex, token_filter) # Pass dex

        # Build graph
        graph: DefaultDict[str, List[Tuple[str, Any]]] = defaultdict(list) # Use Any

        for pair in token_pairs:
            token0 = pair.token0_address.lower()
            token1 = pair.token1_address.lower()

            # Add edges in both directions
            graph[token0].append((token1, pair))
            graph[token1].append((token0, pair))

        # Update cache
        async with self._cache_lock:
            self._token_graph_cache[cache_key] = (graph, time.time())

        return graph

    async def _get_token_pairs_from_dex(
        self, dex: BaseDEX, token_filter: Optional[Set[str]] # Use BaseDEX
    ) -> List[Any]: # Use Any
        """
        Get token pairs from a single DEX with caching.

        Args:
            dex: DEX to get token pairs from
            token_filter: Optional set of token addresses to filter by

        Returns:
            List of token pairs from the DEX
        """
        cache_key = f"{dex.id}_pairs_{hash(frozenset(token_filter)) if token_filter else 'all'}"

        # Check cache
        async with self._cache_lock:
            cached = self._token_pair_cache.get(cache_key)
            current_time = time.time()

            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]

        # Get token pairs from DEX
        try:
            # Call get_token_pairs directly on dex if it exists, otherwise handle error
            if hasattr(dex, 'get_token_pairs'):
                 token_pairs = await dex.get_token_pairs(max_pairs=1000)
            else:
                 logger.warning(f"DEX {dex.id} does not have get_token_pairs method.")
                 return [] # Return empty list if method doesn't exist

            # Filter by tokens if specified
            if token_filter:
                token_pairs = [
                    pair
                    for pair in token_pairs
                    if pair.token0_address.lower() in token_filter
                    or pair.token1_address.lower() in token_filter
                ]

            # Update cache
            async with self._cache_lock:
                self._token_pair_cache[cache_key] = (token_pairs, time.time())

            return token_pairs

        except Exception as e:
            logger.error(f"Error getting token pairs from {dex.id}: {e}")
            return []

    async def _get_most_connected_tokens(
        self, token_graph: DefaultDict[str, List[Tuple[str, Any]]], count: int = 5 # Use Any
    ) -> Set[str]:
        """
        Get the most connected tokens in the graph.

        Args:
            token_graph: Graph of tokens
            count: Number of tokens to return

        Returns:
            Set of most connected token addresses
        """
        # Count connections for each token
        connection_counts = {
            token: len(connections) for token, connections in token_graph.items()
        }

        # Sort by connection count and limit to count
        sorted_tokens = sorted(
            connection_counts.items(), key=lambda x: x[1], reverse=True
        )
        most_connected = [token for token, _ in sorted_tokens[:count]]

        return set(most_connected)

    async def _find_triangular_paths(
        self,
        dex: BaseDEX, # Use BaseDEX
        token_graph: DefaultDict[str, List[Tuple[str, Any]]], # Use Any
        base_token: str,
        market_condition: Dict[str, Any], # Use Dict
        min_profit_wei: int,
    ) -> List[ArbitrageOpportunity]:
        """
        Find triangular arbitrage paths starting from a base token.

        Args:
            dex: DEX to use for pricing
            token_graph: Graph of tokens
            base_token: Base token to start from
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei

        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        base_token = base_token.lower()

        # Ensure base token is in the graph
        if base_token not in token_graph:
            return []

        # Find all 2-hop paths from base_token back to base_token
        # Note: We specifically target 3-token paths (triangular arbitrage)
        for token1_addr, pair1 in token_graph[base_token]:
            for token2_addr, pair2 in token_graph[token1_addr]:
                # Check if we have a path back to base_token
                if token2_addr != base_token and base_token in [
                    addr for addr, _ in token_graph[token2_addr]
                ]:
                    # Find the pair connecting token2 and base_token
                    pair3 = None
                    for addr, pair in token_graph[token2_addr]:
                        if addr == base_token:
                            pair3 = pair
                            break

                    if pair3:
                        # We have a triangular path
                        path = [
                            (base_token, token1_addr, pair1),
                            (token1_addr, token2_addr, pair2),
                            (token2_addr, base_token, pair3),
                        ]

                        # Calculate profitability
                        opportunity = await self._calculate_triangular_profit(
                            dex=dex,
                            path=path,
                            market_condition=market_condition,
                            min_profit_wei=min_profit_wei,
                        )

                        if opportunity:
                            opportunities.append(opportunity)

        return opportunities

    async def _calculate_triangular_profit(
        self,
        dex: BaseDEX, # Use BaseDEX
        path: List[Tuple[str, str, Any]], # Use Any
        market_condition: Dict[str, Any], # Use Dict
        min_profit_wei: int,
    ) -> Optional[ArbitrageOpportunity]:
        """
        Calculate profit for a triangular arbitrage path.

        Args:
            dex: DEX to use for pricing
            path: Path of token pairs
            market_condition: Current market condition
            min_profit_wei: Minimum profit in wei

        Returns:
            ArbitrageOpportunity if profitable, None otherwise
        """
        # Extract tokens and pairs
        base_token = path[0][0]
        intermediate_token1 = path[0][1]
        intermediate_token2 = path[1][1]

        pair1 = path[0][2]
        pair2 = path[1][2]
        pair3 = path[2][2]

        # Get token information (symbols, etc.) - Use getattr for safety
        base_token_symbol = None
        token1_symbol = None
        token2_symbol = None

        if base_token == getattr(pair1, 'token0_address', '').lower():
            base_token_symbol = getattr(pair1, 'token0_symbol', 'TOKEN0')
            token1_symbol = getattr(pair1, 'token1_symbol', 'TOKEN1')
        else:
            base_token_symbol = getattr(pair1, 'token1_symbol', 'TOKEN1')
            token1_symbol = getattr(pair1, 'token0_symbol', 'TOKEN0')

        if intermediate_token1 == getattr(pair2, 'token0_address', '').lower():
            token2_symbol = getattr(pair2, 'token1_symbol', 'TOKEN1')
        else:
            token2_symbol = getattr(pair2, 'token0_symbol', 'TOKEN0')

        # Calculate price ratio for each step
        try:
            # Step 1: base_token -> intermediate_token1
            step1_price = await self._get_price_for_pair(
                dex=dex, from_token=base_token, to_token=intermediate_token1, pair=pair1
            )

            # Step 2: intermediate_token1 -> intermediate_token2
            step2_price = await self._get_price_for_pair(
                dex=dex,
                from_token=intermediate_token1,
                to_token=intermediate_token2,
                pair=pair2,
            )

            # Step 3: intermediate_token2 -> base_token
            step3_price = await self._get_price_for_pair(
                dex=dex, from_token=intermediate_token2, to_token=base_token, pair=pair3
            )

            # Calculate overall price ratio
            overall_ratio = step1_price * step2_price * step3_price

            # If ratio > 1, then profitable (minus gas, slippage)
            profit_percentage = (overall_ratio - Decimal("1")) * Decimal("100")

            # Skip if profit is too small
            if profit_percentage < self.min_profit_percentage:
                return None

            # Calculate token amounts for a sample trade
            input_amount_wei = int(1 * 10**18)  # 1 token as sample

            # Calculate amounts for each step
            intermediate1_amount_wei = int(input_amount_wei * step1_price)
            intermediate2_amount_wei = int(intermediate1_amount_wei * step2_price)
            output_amount_wei = int(intermediate2_amount_wei * step3_price)

            # Calculate profit
            expected_profit_wei = output_amount_wei - input_amount_wei

            # Estimate gas costs
            # Use average gas costs from market condition or default values
            gas_price = Decimal(str(market_condition.get('gas_price', 50 * 10**9))) # Use .get()
            priority_fee = Decimal(str(market_condition.get('priority_fee', 1.5 * 10**9))) # Use .get()

            # Estimate gas usage
            estimated_gas_step1 = 150000  # Approximate gas for swap
            estimated_gas_step2 = 150000  # Approximate gas for swap
            estimated_gas_step3 = 150000  # Approximate gas for swap
            total_gas_estimate = (
                estimated_gas_step1 + estimated_gas_step2 + estimated_gas_step3
            )

            # Calculate gas cost
            gas_cost_wei = Decimal(total_gas_estimate) * (gas_price + priority_fee)

            # Add buffer for potential increases
            gas_cost_with_buffer = (
                gas_cost_wei
                * (Decimal("100") + self.gas_cost_buffer_percentage)
                / Decimal("100")
            )

            # Check if profit exceeds gas costs and minimum profit threshold
            if (
                Decimal(expected_profit_wei) <= gas_cost_with_buffer # Compare Decimals
                or expected_profit_wei < min_profit_wei
            ):
                return None

            # Create path list of dictionaries
            path_list = [
                { # Step 1: base_token -> intermediate_token1
                    "dex_id": dex.id,
                    "dex_name": getattr(dex, 'name', dex.id),
                    "input_token_address": base_token,
                    "input_token_symbol": base_token_symbol or "unknown",
                    "input_amount_wei": input_amount_wei,
                    "output_token_address": intermediate_token1,
                    "output_token_symbol": token1_symbol or "unknown",
                    "output_amount_wei": intermediate1_amount_wei,
                    "action": "swap",
                    "gas_estimate": estimated_gas_step1,
                },
                { # Step 2: intermediate_token1 -> intermediate_token2
                    "dex_id": dex.id,
                    "dex_name": getattr(dex, 'name', dex.id),
                    "input_token_address": intermediate_token1,
                    "input_token_symbol": token1_symbol or "unknown",
                    "input_amount_wei": intermediate1_amount_wei,
                    "output_token_address": intermediate_token2,
                    "output_token_symbol": token2_symbol or "unknown",
                    "output_amount_wei": intermediate2_amount_wei,
                    "action": "swap",
                    "gas_estimate": estimated_gas_step2,
                },
                { # Step 3: intermediate_token2 -> base_token
                    "dex_id": dex.id,
                    "dex_name": getattr(dex, 'name', dex.id),
                    "input_token_address": intermediate_token2,
                    "input_token_symbol": token2_symbol or "unknown",
                    "input_amount_wei": intermediate2_amount_wei,
                    "output_token_address": base_token,
                    "output_token_symbol": base_token_symbol or "unknown",
                    "output_amount_wei": output_amount_wei,
                    "action": "swap",
                    "gas_estimate": estimated_gas_step3,
                },
            ]

            # Calculate profit margin as percentage
            profit_margin_percentage = profit_percentage

            # Calculate profit after gas costs
            profit_after_gas = expected_profit_wei - gas_cost_wei

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                profit_percentage=profit_percentage,
                market_condition=market_condition,
                path_pairs=[pair1, pair2, pair3],
            )

            # Create opportunity using the structure from models.py
            opportunity = ArbitrageOpportunity(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                token_in=base_token,
                token_out=base_token, # Output is same as input for triangular
                amount_in_wei=int(input_amount_wei),
                path=path_list,
                dexes=[dex.id], # Only one DEX involved
                input_price_usd=0.0, # Placeholder
                output_price_usd=0.0, # Placeholder
                expected_profit_wei=int(expected_profit_wei),
                expected_profit_usd=0.0, # Placeholder
                gas_cost_wei=int(gas_cost_wei),
                gas_cost_usd=0.0, # Placeholder
                net_profit_usd=0.0, # Placeholder
                confidence_score=float(confidence_score),
                risk_factors={},
                price_validated=False,
                liquidity_validated=False,
                execution_deadline=datetime.fromtimestamp(int(time.time()) + 300),
                max_slippage=float(self.max_slippage),
                flashloan_required=False,
            )

            return opportunity

        except Exception as e:
            logger.error(f"Error calculating triangular profit: {e}")
            return None

    async def _get_price_for_pair(
        self, dex: BaseDEX, from_token: str, to_token: str, pair: Any # Use BaseDEX and Any
    ) -> Decimal:
        """
        Get the price ratio for a token pair with caching.

        Args:
            dex: DEX to get price from
            from_token: Address of token to trade from
            to_token: Address of token to trade to
            pair: Token pair object

        Returns:
            Price ratio (how much of to_token you get for 1 from_token)
        """
        # Create cache key
        cache_key = f"{dex.id}_{from_token}_{to_token}"

        # Check cache
        async with self._cache_lock:
            cached = self._price_cache.get(cache_key)
            current_time = time.time()

            if cached and (current_time - cached[1] < self._cache_ttl):
                return cached[0]

        # Get price from DEX using get_amounts_out
        try:
            # Determine decimals
            decimals_from = await dex.get_token_decimals(from_token)
            decimals_to = await dex.get_token_decimals(to_token)

            # Get quote for 1 unit of from_token
            amount_in = Decimal(10**decimals_from) # 1 unit in wei
            path = [from_token, to_token]
            amounts_out = await dex.get_amounts_out(amount_in / Decimal(10**decimals_from), path) # Pass human-readable amount

            if len(amounts_out) > 1:
                price = amounts_out[1] # Amount of to_token received for 1 from_token
            else:
                price = Decimal("0") # Failed quote

            # Update cache
            async with self._cache_lock:
                self._price_cache[cache_key] = (price, time.time())

            return price

        except Exception as e:
            logger.error(
                f"Error getting price from {dex.id} for {from_token} -> {to_token}: {e}"
            )
            # Return 0 price to indicate no profitable trade
            return Decimal("0")

    def _calculate_confidence_score(
        self,
        profit_percentage: Decimal,
        market_condition: Dict[str, Any], # Use Dict
        path_pairs: List[Any], # Use Any
    ) -> Decimal:
        """
        Calculate confidence score for a triangular arbitrage opportunity.

        Args:
            profit_percentage: Profit percentage
            market_condition: Current market condition
            path_pairs: List of token pairs in the path

        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from profit percentage
        # Higher profit = higher confidence
        base_confidence = min(profit_percentage / Decimal("5"), Decimal("1"))

        # Adjust for market volatility
        volatility_factor = Decimal("1")
        market_volatility = market_condition.get('market_volatility', 0.0) # Use .get()
        if market_volatility:
            # Higher volatility = lower confidence
            volatility_factor = max(
                Decimal("1") - Decimal(str(market_volatility)) / Decimal("100"), # Use variable
                Decimal("0.2"),
            )

        # Adjust for liquidity
        liquidity_factor = Decimal("1")
        total_liquidity = Decimal("0")
        pair_count = 0

        for pair in path_pairs:
            liquidity_usd = getattr(pair, 'liquidity_usd', None) # Use getattr
            if liquidity_usd:
                total_liquidity += Decimal(str(liquidity_usd)) # Convert to Decimal
                pair_count += 1

        if pair_count > 0:
            avg_liquidity = total_liquidity / Decimal(pair_count)
            liquidity_factor = min(avg_liquidity / self.min_liquidity_usd, Decimal("1"))
        else:
            liquidity_factor = Decimal("0.5")  # Default if no liquidity data

        # Adjust for network congestion
        congestion_factor = Decimal("1")
        network_congestion = market_condition.get('network_congestion', 0.0) # Use .get()
        if network_congestion:
            # Higher congestion = lower confidence
            congestion_factor = max(
                Decimal("1") - Decimal(str(network_congestion)) / Decimal("100"), # Use variable
                Decimal("0.2"),
            )

        # Triangular arbitrage involves more complexity, reduce confidence slightly
        complexity_factor = Decimal("0.9")  # 10% reduction due to complexity

        # Calculate final confidence score
        confidence = (
            base_confidence
            * volatility_factor
            * liquidity_factor
            * congestion_factor
            * complexity_factor
        )

        # Ensure score is between 0 and 1
        return max(min(confidence, Decimal("1")), Decimal("0"))


async def create_triangular_detector(
    dexes: List[BaseDEX], config: Dict[str, Any] = None # Use BaseDEX
) -> "TriangularDetector": # Use string literal for forward reference
    """
    Factory function to create a triangular detector.

    Args:
        dexes: List of DEXs to monitor
        config: Configuration dictionary

    Returns:
        Initialized triangular detector
    """
    return TriangularDetector(dexes=dexes, config=config)
