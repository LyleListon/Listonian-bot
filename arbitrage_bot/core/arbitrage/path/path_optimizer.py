"""
Path Optimizer for Multi-Path Arbitrage

This module provides functionality for optimizing arbitrage paths for gas
efficiency, slippage prediction, path merging, and validation against current
market conditions.

Key features:
- Path optimization for gas efficiency
- Slippage prediction for each path
- Path merging for similar routes
- Path validation against current market conditions
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import numpy as np
from collections import defaultdict

from .interfaces import ArbitragePath, Pool, MultiPathOpportunity
from ..models import TokenAmount
from ...utils.async_utils import gather_with_concurrency
from ...utils.retry import with_retry
from ...web3.interfaces import Web3Client

logger = logging.getLogger(__name__)


class PathOptimizer:
    """
    Optimizes arbitrage paths for execution.

    This class implements algorithms for optimizing arbitrage paths for gas
    efficiency, predicting slippage, merging similar paths, and validating
    paths against current market conditions.
    """

    def __init__(
        self,
        web3_client: Optional[Web3Client] = None,
        max_slippage: Decimal = Decimal("0.01"),
        max_price_impact: Decimal = Decimal("0.05"),
        gas_price_buffer: float = 1.2,
        market_validation_ttl: int = 60,  # seconds
        concurrency_limit: int = 10,
    ):
        """
        Initialize the path optimizer.

        Args:
            web3_client: Web3 client for on-chain validation (optional)
            max_slippage: Maximum acceptable slippage (default: 1%)
            max_price_impact: Maximum acceptable price impact (default: 5%)
            gas_price_buffer: Buffer for gas price estimates (default: 1.2x)
            market_validation_ttl: Time-to-live for market validation cache (default: 60s)
            concurrency_limit: Maximum number of concurrent operations (default: 10)
        """
        self.web3_client = web3_client
        self.max_slippage = max_slippage
        self.max_price_impact = max_price_impact
        self.gas_price_buffer = gas_price_buffer
        self.market_validation_ttl = market_validation_ttl
        self.concurrency_limit = concurrency_limit

        # Thread safety
        self._lock = asyncio.Lock()

        # Cache for market validation
        self._market_cache = {}
        self._last_cache_cleanup = time.time()

        logger.info(
            f"Initialized PathOptimizer with max_slippage={max_slippage}, "
            f"max_price_impact={max_price_impact}, "
            f"gas_price_buffer={gas_price_buffer}"
        )

    async def optimize_path(
        self, path: ArbitragePath, context: Optional[Dict[str, Any]] = None
    ) -> ArbitragePath:
        """
        Optimize a single arbitrage path.

        Args:
            path: Arbitrage path to optimize
            context: Optional context information
                - gas_price: Current gas price in gwei
                - token_prices: Dictionary of token prices
                - market_conditions: Current market conditions
                - execution_priority: Priority for execution (e.g., "speed", "profit")

        Returns:
            Optimized arbitrage path
        """
        async with self._lock:
            try:
                # Apply context
                context = context or {}

                # Optimize gas usage
                path = await self._optimize_gas_usage(path, context)

                # Predict slippage
                path = await self._predict_slippage(path, context)

                # Validate against current market conditions
                path = await self._validate_market_conditions(path, context)

                # Adjust optimal amount based on slippage and gas costs
                path = await self._adjust_optimal_amount(path, context)

                logger.debug(
                    f"Optimized path with {len(path.pools)} hops, "
                    f"estimated gas: {path.estimated_gas}, "
                    f"confidence: {path.confidence:.2f}"
                )

                return path

            except Exception as e:
                logger.error(f"Error optimizing path: {e}")
                return path

    async def optimize_paths(
        self, paths: List[ArbitragePath], context: Optional[Dict[str, Any]] = None
    ) -> List[ArbitragePath]:
        """
        Optimize multiple arbitrage paths.

        Args:
            paths: List of arbitrage paths to optimize
            context: Optional context information

        Returns:
            List of optimized arbitrage paths
        """
        try:
            if not paths:
                return []

            # Apply context
            context = context or {}

            # Optimize paths in parallel
            optimized_paths = await gather_with_concurrency(
                self.concurrency_limit,
                *[self.optimize_path(path, context) for path in paths],
            )

            # Merge similar paths if beneficial
            if len(optimized_paths) > 1:
                optimized_paths = await self._merge_similar_paths(
                    optimized_paths, context
                )

            logger.info(f"Optimized {len(optimized_paths)} paths")

            return optimized_paths

        except Exception as e:
            logger.error(f"Error optimizing paths: {e}")
            return paths

    async def validate_path(
        self, path: ArbitragePath, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate an arbitrage path against current market conditions.

        Args:
            path: Arbitrage path to validate
            context: Optional context information

        Returns:
            Tuple of (is_valid, validation_results)
        """
        try:
            # Apply context
            context = context or {}

            # Perform validation checks
            validation_results = {}

            # Check if path is cyclic
            if not path.is_cyclic:
                validation_results["cyclic"] = False
                return False, validation_results
            else:
                validation_results["cyclic"] = True

            # Check if path has optimal amount
            if path.optimal_amount is None or path.optimal_amount <= 0:
                validation_results["has_optimal_amount"] = False
                return False, validation_results
            else:
                validation_results["has_optimal_amount"] = True

            # Check if path is profitable
            if path.profit is None or path.profit <= 0:
                validation_results["is_profitable"] = False
                return False, validation_results
            else:
                validation_results["is_profitable"] = True

            # All checks passed
            return True, validation_results

        except Exception as e:
            logger.error(f"Error validating path: {e}")
            return False, {"error": str(e)}

    async def _optimize_gas_usage(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> ArbitragePath:
        """
        Optimize gas usage for a path.

        Args:
            path: Arbitrage path to optimize
            context: Context information

        Returns:
            Gas-optimized arbitrage path
        """
        try:
            # Get current gas price from context or use default
            gas_price = context.get("gas_price", 50)  # gwei

            # Estimate base gas cost for the path
            base_gas = self._estimate_base_gas(path)

            # Apply gas price buffer for safety
            buffered_gas = int(base_gas * self.gas_price_buffer)

            # Update path with optimized gas estimate
            path.estimated_gas = buffered_gas

            # Calculate gas cost in ETH
            gas_cost_eth = Decimal(str(buffered_gas * gas_price)) / Decimal(
                "1000000000"
            )
            path.estimated_gas_cost = gas_cost_eth

            return path

        except Exception as e:
            logger.error(f"Error optimizing gas usage: {e}")
            return path

    async def _predict_slippage(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> ArbitragePath:
        """
        Predict slippage for a path.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            Path with slippage prediction
        """
        try:
            if path.optimal_amount is None:
                return path

            # Calculate slippage for each hop
            total_slippage = Decimal("0")

            for i, pool in enumerate(path.pools):
                # Get tokens for this hop
                token_in = path.tokens[i]
                token_out = path.tokens[i + 1]

                # Estimate amount at this hop
                amount = path.optimal_amount

                # Calculate slippage based on pool liquidity and amount
                hop_slippage = self._calculate_hop_slippage(
                    pool, token_in, token_out, amount
                )

                # Accumulate slippage
                total_slippage += hop_slippage

            # Cap total slippage at max_slippage
            capped_slippage = min(total_slippage, self.max_slippage)

            # Update path with slippage prediction
            if "metadata" not in path.__dict__:
                path.__dict__["metadata"] = {}

            path.__dict__["metadata"]["predicted_slippage"] = capped_slippage

            # Adjust expected output based on slippage
            if path.expected_output is not None:
                slippage_factor = Decimal("1") - capped_slippage
                adjusted_output = path.expected_output * slippage_factor
                path.__dict__["metadata"]["adjusted_output"] = adjusted_output

            return path

        except Exception as e:
            logger.error(f"Error predicting slippage: {e}")
            return path

    async def _validate_market_conditions(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> ArbitragePath:
        """
        Validate path against current market conditions.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            Validated arbitrage path
        """
        try:
            # Check cache first
            path_id = self._get_path_identifier(path)
            current_time = time.time()

            if path_id in self._market_cache:
                cache_entry = self._market_cache[path_id]
                if current_time - cache_entry["timestamp"] < self.market_validation_ttl:
                    # Use cached validation result
                    validation_result = cache_entry["result"]
                    path.confidence *= validation_result.get("confidence_factor", 1.0)
                    return path

            # Clean up cache if needed
            if current_time - self._last_cache_cleanup > self.market_validation_ttl:
                self._cleanup_cache()

            # Validate market conditions
            validation_result = {"confidence_factor": 1.0}

            # Check if web3 client is available for on-chain validation
            if self.web3_client:
                # Validate pool reserves
                reserves_valid = await self._validate_pool_reserves(path)
                validation_result["reserves_valid"] = reserves_valid

                if not reserves_valid:
                    validation_result["confidence_factor"] *= 0.5

            # Update path confidence based on validation
            path.confidence *= validation_result.get("confidence_factor", 1.0)

            # Cache validation result
            self._market_cache[path_id] = {
                "timestamp": current_time,
                "result": validation_result,
            }

            return path

        except Exception as e:
            logger.error(f"Error validating market conditions: {e}")
            return path

    async def _adjust_optimal_amount(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> ArbitragePath:
        """
        Adjust optimal amount based on slippage and gas costs.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            Path with adjusted optimal amount
        """
        try:
            if path.optimal_amount is None or path.expected_output is None:
                return path

            # Get predicted slippage
            predicted_slippage = Decimal("0")
            if (
                "metadata" in path.__dict__
                and "predicted_slippage" in path.__dict__["metadata"]
            ):
                predicted_slippage = path.__dict__["metadata"]["predicted_slippage"]

            # Get gas cost in ETH
            gas_cost_eth = path.estimated_gas_cost

            # Calculate adjusted profit
            original_profit = path.expected_output - path.optimal_amount
            slippage_impact = path.expected_output * predicted_slippage
            adjusted_profit = original_profit - slippage_impact - gas_cost_eth

            # If adjusted profit is negative, reduce confidence
            if adjusted_profit <= 0:
                path.confidence *= 0.5
            else:
                # Update path with adjusted profit
                if "metadata" not in path.__dict__:
                    path.__dict__["metadata"] = {}

                path.__dict__["metadata"]["adjusted_profit"] = adjusted_profit

            return path

        except Exception as e:
            logger.error(f"Error adjusting optimal amount: {e}")
            return path

    async def _merge_similar_paths(
        self, paths: List[ArbitragePath], context: Dict[str, Any]
    ) -> List[ArbitragePath]:
        """
        Merge similar paths if beneficial.

        Args:
            paths: List of arbitrage paths
            context: Context information

        Returns:
            List of merged arbitrage paths
        """
        try:
            if len(paths) <= 1:
                return paths

            # Group paths by similarity
            similarity_groups = self._group_by_similarity(paths)

            # Process each group
            merged_paths = []

            for group in similarity_groups:
                if len(group) <= 1:
                    # No merging needed for single paths
                    merged_paths.extend(group)
                    continue

                # Check if merging is beneficial
                if self._is_merging_beneficial(group, context):
                    # Merge paths in the group
                    merged_path = self._merge_paths(group)
                    merged_paths.append(merged_path)
                else:
                    # Keep paths separate
                    merged_paths.extend(group)

            logger.debug(f"Merged {len(paths)} paths into {len(merged_paths)} paths")

            return merged_paths

        except Exception as e:
            logger.error(f"Error merging similar paths: {e}")
            return paths

    def _estimate_base_gas(self, path: ArbitragePath) -> int:
        """
        Estimate base gas cost for a path.

        Args:
            path: Arbitrage path

        Returns:
            Estimated gas cost in gas units
        """
        try:
            # Base gas cost for a transaction
            base_gas = 21000

            # Gas cost per hop
            hop_gas_costs = {
                "uniswap_v2": 90000,
                "uniswap_v3": 120000,
                "sushiswap": 90000,
                "default": 100000,
            }

            # Calculate total gas
            total_gas = base_gas

            for i, pool in enumerate(path.pools):
                dex = path.dexes[i] if i < len(path.dexes) else "default"
                hop_gas = hop_gas_costs.get(dex, hop_gas_costs["default"])
                total_gas += hop_gas

            return total_gas

        except Exception as e:
            logger.error(f"Error estimating base gas: {e}")
            return 500000  # Default gas limit

    def _calculate_hop_slippage(
        self, pool: Pool, token_in: str, token_out: str, amount: Decimal
    ) -> Decimal:
        """
        Calculate slippage for a single hop.

        Args:
            pool: Liquidity pool
            token_in: Input token address
            token_out: Output token address
            amount: Input amount

        Returns:
            Estimated slippage as a decimal (0.0-1.0)
        """
        try:
            # Check if pool has reserves
            if pool.reserves0 is None or pool.reserves1 is None:
                return Decimal("0.01")  # Default slippage if reserves unknown

            # Determine token order in the pool
            if token_in == pool.token0 and token_out == pool.token1:
                # token0 -> token1
                reserve_in = pool.reserves0
                reserve_out = pool.reserves1
            elif token_in == pool.token1 and token_out == pool.token0:
                # token1 -> token0
                reserve_in = pool.reserves1
                reserve_out = pool.reserves0
            else:
                # Invalid token pair
                logger.warning(
                    f"Invalid token pair: {token_in} -> {token_out} in pool {pool.address}"
                )
                return Decimal("0.01")  # Default slippage

            # Calculate amount relative to reserve
            amount_ratio = amount / reserve_in

            # Apply slippage model based on pool type
            if pool.pool_type == "constant_product":
                # For constant product pools (e.g., Uniswap V2),
                # slippage increases quadratically with amount ratio
                slippage = amount_ratio * amount_ratio
            elif pool.pool_type == "stable":
                # For stable pools, slippage is lower
                slippage = amount_ratio * amount_ratio * Decimal("0.5")
            else:
                # Default to constant product model
                slippage = amount_ratio * amount_ratio

            # Cap slippage at reasonable values
            return min(slippage, Decimal("0.1"))  # Max 10% slippage

        except Exception as e:
            logger.error(f"Error calculating hop slippage: {e}")
            return Decimal("0.01")  # Default slippage

    async def _validate_pool_reserves(self, path: ArbitragePath) -> bool:
        """
        Validate pool reserves on-chain.

        Args:
            path: Arbitrage path

        Returns:
            True if reserves are valid, False otherwise
        """
        try:
            if not self.web3_client:
                return True  # Skip validation if web3 client not available

            # This is a placeholder for actual on-chain validation
            # In a real implementation, we would query the pool contracts
            # to verify their current reserves

            return True

        except Exception as e:
            logger.error(f"Error validating pool reserves: {e}")
            return False

    def _group_by_similarity(
        self, paths: List[ArbitragePath]
    ) -> List[List[ArbitragePath]]:
        """
        Group paths by similarity.

        Args:
            paths: List of arbitrage paths

        Returns:
            List of path groups
        """
        try:
            if not paths:
                return []

            # Calculate similarity matrix
            n = len(paths)
            similarity_matrix = np.zeros((n, n))

            for i in range(n):
                for j in range(i + 1, n):
                    similarity = self._calculate_path_similarity(paths[i], paths[j])
                    similarity_matrix[i, j] = similarity
                    similarity_matrix[j, i] = similarity

            # Group paths using a simple threshold-based approach
            similarity_threshold = (
                0.7  # Paths with similarity > 0.7 are considered similar
            )
            groups = []
            visited = set()

            for i in range(n):
                if i in visited:
                    continue

                group = [paths[i]]
                visited.add(i)

                for j in range(n):
                    if j in visited:
                        continue

                    if similarity_matrix[i, j] > similarity_threshold:
                        group.append(paths[j])
                        visited.add(j)

                groups.append(group)

            return groups

        except Exception as e:
            logger.error(f"Error grouping paths by similarity: {e}")
            return [[path] for path in paths]  # Each path in its own group

    def _calculate_path_similarity(
        self, path1: ArbitragePath, path2: ArbitragePath
    ) -> float:
        """
        Calculate similarity between two paths.

        Args:
            path1: First arbitrage path
            path2: Second arbitrage path

        Returns:
            Similarity score (0.0-1.0)
        """
        try:
            # Check if paths have the same start and end tokens
            if (
                path1.start_token != path2.start_token
                or path1.end_token != path2.end_token
            ):
                return 0.0

            # Calculate token overlap
            tokens1 = set(path1.tokens)
            tokens2 = set(path2.tokens)
            token_overlap = len(tokens1.intersection(tokens2)) / len(
                tokens1.union(tokens2)
            )

            # Calculate pool overlap
            pools1 = set(pool.address for pool in path1.pools)
            pools2 = set(pool.address for pool in path2.pools)
            pool_overlap = len(pools1.intersection(pools2)) / len(pools1.union(pools2))

            # Calculate DEX overlap
            dexes1 = set(path1.dexes)
            dexes2 = set(path2.dexes)
            dex_overlap = len(dexes1.intersection(dexes2)) / len(dexes1.union(dexes2))

            # Combine overlaps with weights
            similarity = token_overlap * 0.4 + pool_overlap * 0.4 + dex_overlap * 0.2

            return similarity

        except Exception as e:
            logger.error(f"Error calculating path similarity: {e}")
            return 0.0

    def _is_merging_beneficial(
        self, paths: List[ArbitragePath], context: Dict[str, Any]
    ) -> bool:
        """
        Check if merging paths is beneficial.

        Args:
            paths: List of similar arbitrage paths
            context: Context information

        Returns:
            True if merging is beneficial, False otherwise
        """
        try:
            if len(paths) <= 1:
                return False

            # Calculate total profit of individual paths
            total_profit = sum(path.profit for path in paths if path.profit is not None)

            # Calculate total gas cost of individual paths
            total_gas_cost = sum(
                path.estimated_gas_cost
                for path in paths
                if path.estimated_gas_cost is not None
            )

            # Estimate profit of merged path
            merged_profit = total_profit * 0.9  # Assume 10% loss due to merging

            # Estimate gas cost of merged path
            merged_gas_cost = total_gas_cost * 0.7  # Assume 30% gas savings

            # Compare net profits
            individual_net_profit = total_profit - total_gas_cost
            merged_net_profit = merged_profit - merged_gas_cost

            return merged_net_profit > individual_net_profit

        except Exception as e:
            logger.error(f"Error checking if merging is beneficial: {e}")
            return False

    def _merge_paths(self, paths: List[ArbitragePath]) -> ArbitragePath:
        """
        Merge similar paths into a single path.

        Args:
            paths: List of similar arbitrage paths

        Returns:
            Merged arbitrage path
        """
        try:
            if not paths:
                return None

            if len(paths) == 1:
                return paths[0]

            # Sort paths by profit
            sorted_paths = sorted(
                paths,
                key=lambda p: p.profit if p.profit is not None else Decimal("0"),
                reverse=True,
            )

            # Use the most profitable path as the base
            base_path = sorted_paths[0]

            # Merge metadata
            merged_metadata = {}
            if hasattr(base_path, "metadata"):
                merged_metadata.update(base_path.__dict__.get("metadata", {}))

            # Add merged_from information
            merged_metadata["merged_from"] = [
                self._get_path_identifier(path) for path in paths
            ]

            # Create merged path
            merged_path = ArbitragePath(
                tokens=base_path.tokens,
                pools=base_path.pools,
                dexes=base_path.dexes,
                swap_data=base_path.swap_data,
                optimal_amount=base_path.optimal_amount,
                expected_output=base_path.expected_output,
                path_yield=base_path.path_yield,
                confidence=base_path.confidence * 0.9,  # Reduce confidence slightly
                estimated_gas=base_path.estimated_gas,
                estimated_gas_cost=base_path.estimated_gas_cost,
                execution_priority=min(path.execution_priority for path in paths),
            )

            # Add merged metadata
            merged_path.__dict__["metadata"] = merged_metadata

            return merged_path

        except Exception as e:
            logger.error(f"Error merging paths: {e}")
            return paths[0] if paths else None

    def _get_path_identifier(self, path: ArbitragePath) -> str:
        """
        Generate a unique identifier for a path.

        Args:
            path: Arbitrage path

        Returns:
            Unique identifier string
        """
        try:
            # Create a string representation of the path
            path_elements = []

            for i, token in enumerate(path.tokens):
                path_elements.append(token)
                if i < len(path.pools):
                    path_elements.append(path.pools[i].address)

            return ":".join(path_elements)

        except Exception as e:
            logger.error(f"Error generating path identifier: {e}")
            return str(hash(tuple(path.tokens)))

    def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()
            expired_keys = []

            for key, entry in self._market_cache.items():
                if current_time - entry["timestamp"] > self.market_validation_ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._market_cache[key]

            self._last_cache_cleanup = current_time

            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
