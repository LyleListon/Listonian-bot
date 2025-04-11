"""
Path Ranker for Multi-Path Arbitrage

This module provides functionality for ranking arbitrage paths based on
profitability, risk assessment, path diversity, and historical success rate.

Key features:
- Path profitability scoring
- Risk assessment for each path
- Path diversity scoring
- Historical success rate tracking
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import numpy as np
from collections import defaultdict

from .interfaces import ArbitragePath
from ...utils.async_utils import gather_with_concurrency
from ...utils.retry import with_retry

logger = logging.getLogger(__name__)


class PathRanker:
    """
    Ranks arbitrage paths based on multiple criteria.

    This class implements algorithms for ranking arbitrage paths based on
    profitability, risk assessment, path diversity, and historical success rate.
    """

    def __init__(
        self,
        profit_weight: float = 0.5,
        risk_weight: float = 0.2,
        diversity_weight: float = 0.15,
        history_weight: float = 0.15,
        history_window: int = 100,
        concurrency_limit: int = 10,
    ):
        """
        Initialize the path ranker.

        Args:
            profit_weight: Weight for profit score (default: 0.5)
            risk_weight: Weight for risk score (default: 0.2)
            diversity_weight: Weight for diversity score (default: 0.15)
            history_weight: Weight for history score (default: 0.15)
            history_window: Window size for history tracking (default: 100)
            concurrency_limit: Maximum number of concurrent operations (default: 10)
        """
        self.profit_weight = profit_weight
        self.risk_weight = risk_weight
        self.diversity_weight = diversity_weight
        self.history_weight = history_weight
        self.history_window = history_window
        self.concurrency_limit = concurrency_limit

        # Thread safety
        self._lock = asyncio.Lock()

        # Historical performance data
        self._path_history = defaultdict(list)
        self._token_history = defaultdict(list)
        self._dex_history = defaultdict(list)

        logger.info(
            f"Initialized PathRanker with profit_weight={profit_weight}, "
            f"risk_weight={risk_weight}, "
            f"diversity_weight={diversity_weight}, "
            f"history_weight={history_weight}"
        )

    async def rank_paths(
        self, paths: List[ArbitragePath], context: Optional[Dict[str, Any]] = None
    ) -> List[ArbitragePath]:
        """
        Rank arbitrage paths based on multiple criteria.

        Args:
            paths: List of arbitrage paths to rank
            context: Optional context information
                - market_volatility: Market volatility indicator (0.0-1.0)
                - gas_price: Current gas price in gwei
                - token_prices: Dictionary of token prices
                - ranking_strategy: Ranking strategy ("balanced", "profit", "risk", "diversity")

        Returns:
            Ranked list of arbitrage paths
        """
        async with self._lock:
            try:
                if not paths:
                    return []

                # Apply context
                context = context or {}

                # Calculate scores for each path
                path_scores = await gather_with_concurrency(
                    self.concurrency_limit,
                    *[self._calculate_path_score(path, context) for path in paths],
                )

                # Sort paths by score (descending)
                ranked_paths = [
                    p
                    for _, p in sorted(
                        zip(path_scores, paths), key=lambda x: x[0], reverse=True
                    )
                ]

                logger.info(f"Ranked {len(ranked_paths)} paths")

                return ranked_paths

            except Exception as e:
                logger.error(f"Error ranking paths: {e}")
                return paths  # Return original paths as fallback

    async def update_history(
        self, path: ArbitragePath, execution_result: Dict[str, Any]
    ) -> None:
        """
        Update historical performance data for a path.

        Args:
            path: Arbitrage path
            execution_result: Execution result
                - success: Whether the execution was successful
                - profit: Actual profit
                - gas_cost: Actual gas cost
                - slippage: Actual slippage
        """
        async with self._lock:
            try:
                # Extract execution result
                success = execution_result.get("success", False)
                profit = execution_result.get("profit", Decimal("0"))
                gas_cost = execution_result.get("gas_cost", Decimal("0"))
                slippage = execution_result.get("slippage", Decimal("0"))

                # Calculate performance score
                if success and profit > gas_cost:
                    performance_score = 1.0  # Success with profit
                elif success:
                    performance_score = 0.5  # Success without profit
                else:
                    performance_score = 0.0  # Failure

                # Update path history
                path_id = self._get_path_identifier(path)
                self._path_history[path_id].append(
                    {
                        "timestamp": time.time(),
                        "performance_score": performance_score,
                        "profit": float(profit),
                        "gas_cost": float(gas_cost),
                        "slippage": float(slippage),
                    }
                )

                # Limit history size
                if len(self._path_history[path_id]) > self.history_window:
                    self._path_history[path_id] = self._path_history[path_id][
                        -self.history_window :
                    ]

                # Update token history
                for token in path.tokens:
                    self._token_history[token].append(
                        {
                            "timestamp": time.time(),
                            "performance_score": performance_score,
                        }
                    )

                    # Limit history size
                    if len(self._token_history[token]) > self.history_window:
                        self._token_history[token] = self._token_history[token][
                            -self.history_window :
                        ]

                # Update DEX history
                for dex in path.dexes:
                    self._dex_history[dex].append(
                        {
                            "timestamp": time.time(),
                            "performance_score": performance_score,
                        }
                    )

                    # Limit history size
                    if len(self._dex_history[dex]) > self.history_window:
                        self._dex_history[dex] = self._dex_history[dex][
                            -self.history_window :
                        ]

                logger.debug(
                    f"Updated history for path {path_id}: "
                    f"performance_score={performance_score}, "
                    f"profit={profit}, "
                    f"gas_cost={gas_cost}"
                )

            except Exception as e:
                logger.error(f"Error updating history: {e}")

    async def _calculate_path_score(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> float:
        """
        Calculate score for a path based on multiple criteria.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            Path score (0.0-1.0)
        """
        try:
            # Calculate profit score
            profit_score = self._calculate_profit_score(path, context)

            # Calculate risk score
            risk_score = self._calculate_risk_score(path, context)

            # Calculate diversity score
            diversity_score = self._calculate_diversity_score(path, context)

            # Calculate history score
            history_score = self._calculate_history_score(path, context)

            # Determine ranking strategy
            ranking_strategy = context.get("ranking_strategy", "balanced")

            # Apply weights based on ranking strategy
            if ranking_strategy == "profit":
                # Prioritize profit
                weights = {"profit": 0.7, "risk": 0.1, "diversity": 0.1, "history": 0.1}
            elif ranking_strategy == "risk":
                # Prioritize risk
                weights = {"profit": 0.3, "risk": 0.5, "diversity": 0.1, "history": 0.1}
            elif ranking_strategy == "diversity":
                # Prioritize diversity
                weights = {"profit": 0.3, "risk": 0.2, "diversity": 0.4, "history": 0.1}
            else:
                # Balanced approach
                weights = {
                    "profit": self.profit_weight,
                    "risk": self.risk_weight,
                    "diversity": self.diversity_weight,
                    "history": self.history_weight,
                }

            # Calculate combined score
            combined_score = (
                profit_score * weights["profit"]
                + risk_score * weights["risk"]
                + diversity_score * weights["diversity"]
                + history_score * weights["history"]
            )

            # Update path confidence based on combined score
            path.confidence = min(1.0, max(0.1, combined_score))

            return combined_score

        except Exception as e:
            logger.error(f"Error calculating path score: {e}")
            return 0.0

    def _calculate_profit_score(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> float:
        """
        Calculate profit score for a path.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            Profit score (0.0-1.0)
        """
        try:
            if (
                path.profit is None
                or path.optimal_amount is None
                or path.optimal_amount <= 0
            ):
                return 0.0

            # Calculate profit percentage
            profit_percentage = path.profit / path.optimal_amount

            # Calculate profit score
            # This is a simplified approach - in reality, we would use a more
            # sophisticated model based on historical profit distributions

            # Normalize profit percentage to 0.0-1.0 range
            # Assume 5% profit is excellent (score = 1.0)
            profit_score = min(1.0, float(profit_percentage) / 0.05)

            # Adjust for gas cost if available
            if path.estimated_gas_cost is not None and path.estimated_gas_cost > 0:
                gas_cost_ratio = path.estimated_gas_cost / path.profit
                gas_adjustment = max(0.0, 1.0 - float(gas_cost_ratio))
                profit_score *= gas_adjustment

            return profit_score

        except Exception as e:
            logger.error(f"Error calculating profit score: {e}")
            return 0.0

    def _calculate_risk_score(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> float:
        """
        Calculate risk score for a path.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            Risk score (0.0-1.0)
        """
        try:
            # Start with base risk score based on path confidence
            risk_score = path.confidence

            # Adjust for path complexity
            complexity_factor = max(0.0, 1.0 - (len(path.pools) - 1) * 0.1)
            risk_score *= complexity_factor

            # Adjust for market volatility
            market_volatility = context.get("market_volatility", 0.5)
            volatility_factor = max(0.0, 1.0 - market_volatility)
            risk_score *= volatility_factor

            # Adjust for gas price
            gas_price = context.get("gas_price", 50)  # gwei
            gas_factor = max(0.0, 1.0 - (gas_price - 20) / 200)  # Normalize to 0.0-1.0
            risk_score *= gas_factor

            return risk_score

        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.0

    def _calculate_diversity_score(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> float:
        """
        Calculate diversity score for a path.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            Diversity score (0.0-1.0)
        """
        try:
            # Calculate token diversity
            unique_tokens = set(path.tokens)
            token_diversity = len(unique_tokens) / (len(path.tokens) or 1)

            # Calculate DEX diversity
            unique_dexes = set(path.dexes)
            dex_diversity = len(unique_dexes) / (len(path.dexes) or 1)

            # Calculate combined diversity score
            diversity_score = (token_diversity + dex_diversity) / 2

            return diversity_score

        except Exception as e:
            logger.error(f"Error calculating diversity score: {e}")
            return 0.0

    def _calculate_history_score(
        self, path: ArbitragePath, context: Dict[str, Any]
    ) -> float:
        """
        Calculate history score for a path.

        Args:
            path: Arbitrage path
            context: Context information

        Returns:
            History score (0.0-1.0)
        """
        try:
            # Get path history
            path_id = self._get_path_identifier(path)
            path_history = self._path_history.get(path_id, [])

            if path_history:
                # Calculate average performance score
                path_score = sum(
                    entry["performance_score"] for entry in path_history
                ) / len(path_history)
            else:
                # No history for this exact path
                path_score = 0.5  # Neutral score

            # Get token history
            token_scores = []

            for token in path.tokens:
                token_history = self._token_history.get(token, [])

                if token_history:
                    # Calculate average performance score
                    token_score = sum(
                        entry["performance_score"] for entry in token_history
                    ) / len(token_history)
                    token_scores.append(token_score)

            # Get DEX history
            dex_scores = []

            for dex in path.dexes:
                dex_history = self._dex_history.get(dex, [])

                if dex_history:
                    # Calculate average performance score
                    dex_score = sum(
                        entry["performance_score"] for entry in dex_history
                    ) / len(dex_history)
                    dex_scores.append(dex_score)

            # Calculate combined history score
            if path_history:
                # Path history exists, give it more weight
                history_score = path_score * 0.6

                if token_scores:
                    history_score += (sum(token_scores) / len(token_scores)) * 0.2

                if dex_scores:
                    history_score += (sum(dex_scores) / len(dex_scores)) * 0.2
            else:
                # No path history, rely on token and DEX history
                if token_scores and dex_scores:
                    history_score = (sum(token_scores) / len(token_scores)) * 0.5
                    history_score += (sum(dex_scores) / len(dex_scores)) * 0.5
                elif token_scores:
                    history_score = sum(token_scores) / len(token_scores)
                elif dex_scores:
                    history_score = sum(dex_scores) / len(dex_scores)
                else:
                    # No history at all
                    history_score = 0.5  # Neutral score

            return history_score

        except Exception as e:
            logger.error(f"Error calculating history score: {e}")
            return 0.5  # Neutral score as fallback

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
