"""
Bundle Optimizer for Flashbots Integration

This module provides functionality for:
- Optimizing transaction bundles
- Calculating optimal gas settings
- Managing bundle submission strategies
- Validating bundle profitability
"""

import logging
import time
from typing import Dict, List, Any, Optional
from decimal import Decimal

from ....utils.async_manager import AsyncLock, with_retry
from .risk_analyzer import RiskAnalyzer

logger = logging.getLogger(__name__)


class BundleOptimizer:
    """Optimizes Flashbots bundles for maximum profitability and success rate."""

    def __init__(
        self, web3_manager, risk_analyzer: RiskAnalyzer, config: Dict[str, Any]
    ):
        """
        Initialize bundle optimizer.

        Args:
            web3_manager: Web3Manager instance
            risk_analyzer: RiskAnalyzer instance
            config: Configuration dictionary containing:
                - mev_protection settings
                - gas optimization parameters
                - profit thresholds
        """
        self.web3_manager = web3_manager
        self.risk_analyzer = risk_analyzer
        self.config = config
        self._request_lock = AsyncLock()

        # Initialize optimization parameters
        mev_config = config.get("mev_protection", {})
        self.max_bundle_size = mev_config.get("max_bundle_size", 5)
        self.max_blocks_ahead = mev_config.get("max_blocks_ahead", 3)
        self.min_priority_fee = Decimal(mev_config.get("min_priority_fee", "1.5"))
        self.max_priority_fee = Decimal(mev_config.get("max_priority_fee", "3"))
        self.adaptive_gas = mev_config.get("adaptive_gas", True)

    @with_retry(retries=3, delay=1.0)
    async def optimize_bundle_strategy(
        self,
        transactions: List[Dict[str, Any]],
        target_token_addresses: List[str],
        expected_profit: int,
        priority_level: str = "medium",
    ) -> Dict[str, Any]:
        """
        Optimize bundle strategy based on current conditions.

        Args:
            transactions: List of transactions to include in bundle
            target_token_addresses: List of token addresses involved
            expected_profit: Expected profit in wei
            priority_level: Desired priority level (low, medium, high)

        Returns:
            Dict containing:
                - gas_settings: Optimized gas settings
                - block_targets: Target block numbers
                - mev_risk_assessment: Current MEV risk assessment
                - recommendation: Strategy recommendation
        """
        async with self._request_lock:
            try:
                # Get current conditions
                risk_assessment = await self.risk_analyzer.analyze_mempool_risk()
                current_block = await self.web3_manager.w3.eth.block_number

                # Calculate optimal gas settings
                gas_settings = await self._calculate_gas_settings(
                    risk_assessment, priority_level, expected_profit
                )

                # Determine target blocks
                block_targets = await self._determine_block_targets(
                    current_block, risk_assessment["risk_level"]
                )

                # Generate recommendation
                recommendation = self._generate_strategy_recommendation(
                    risk_assessment, gas_settings, expected_profit
                )

                return {
                    "gas_settings": gas_settings,
                    "block_targets": block_targets,
                    "mev_risk_assessment": risk_assessment,
                    "recommendation": recommendation,
                }

            except Exception as e:
                logger.error(f"Failed to optimize bundle strategy: {e}")
                raise

    async def validate_bundle_profitability(
        self,
        transactions: List[Dict[str, Any]],
        gas_settings: Dict[str, Any],
        expected_profit: int,
    ) -> Dict[str, Any]:
        """
        Validate if bundle will be profitable with current settings.

        Args:
            transactions: List of transactions in bundle
            gas_settings: Gas settings to use
            expected_profit: Expected profit in wei

        Returns:
            Dict containing:
                - is_profitable: Whether bundle is profitable
                - net_profit: Expected net profit
                - gas_cost: Total gas cost
                - recommendation: Optimization recommendation
        """
        try:
            # Calculate total gas cost
            total_gas = sum(tx.get("gas", 0) for tx in transactions)
            gas_price = gas_settings["max_fee_per_gas"]
            total_gas_cost = total_gas * gas_price

            # Calculate net profit
            net_profit = expected_profit - total_gas_cost
            is_profitable = net_profit > 0

            # Generate recommendation
            if not is_profitable:
                recommendation = self._generate_optimization_recommendation(
                    total_gas_cost, expected_profit
                )
            else:
                recommendation = "Bundle is profitable with current settings"

            return {
                "is_profitable": is_profitable,
                "net_profit": net_profit,
                "gas_cost": total_gas_cost,
                "recommendation": recommendation,
            }

        except Exception as e:
            logger.error(f"Failed to validate bundle profitability: {e}")
            raise

    async def _calculate_gas_settings(
        self, risk_assessment: Dict[str, Any], priority_level: str, expected_profit: int
    ) -> Dict[str, Any]:
        """Calculate optimal gas settings based on conditions."""
        try:
            base_fee = risk_assessment["base_fee"]

            # Calculate priority fee based on risk level and priority
            priority_multipliers = {"low": 1.0, "medium": 1.5, "high": 2.0}
            risk_multipliers = {"LOW": 1.0, "MEDIUM": 1.2, "HIGH": 1.5}

            multiplier = priority_multipliers.get(
                priority_level, 1.5
            ) * risk_multipliers.get(risk_assessment["risk_level"], 1.0)

            priority_fee = int(
                self.min_priority_fee * multiplier * 10**9  # Convert to Gwei
            )

            # Ensure priority fee is within bounds
            priority_fee = min(
                max(priority_fee, int(self.min_priority_fee * 10**9)),
                int(self.max_priority_fee * 10**9),
            )

            # Calculate max fee
            max_fee = base_fee + priority_fee

            # Adjust based on expected profit if adaptive gas is enabled
            if self.adaptive_gas:
                max_profit_percentage = 0.1  # Max 10% of profit for gas
                max_allowed_fee = int(expected_profit * max_profit_percentage)
                max_fee = min(max_fee, max_allowed_fee)

            return {
                "max_fee_per_gas": max_fee,
                "max_priority_fee_per_gas": priority_fee,
            }

        except Exception as e:
            logger.error(f"Failed to calculate gas settings: {e}")
            raise

    async def _determine_block_targets(
        self, current_block: int, risk_level: str
    ) -> List[int]:
        """Determine target blocks for bundle submission."""
        try:
            if risk_level == "HIGH":
                # Target fewer blocks when risk is high
                blocks_ahead = min(2, self.max_blocks_ahead)
            elif risk_level == "MEDIUM":
                blocks_ahead = min(3, self.max_blocks_ahead)
            else:
                blocks_ahead = self.max_blocks_ahead

            return list(range(current_block + 1, current_block + blocks_ahead + 1))

        except Exception as e:
            logger.error(f"Failed to determine block targets: {e}")
            raise

    def _generate_strategy_recommendation(
        self,
        risk_assessment: Dict[str, Any],
        gas_settings: Dict[str, Any],
        expected_profit: int,
    ) -> str:
        """Generate strategy recommendation based on conditions."""
        try:
            recommendations = []

            # Gas price recommendations
            if risk_assessment["gas_volatility"] > 0.2:
                recommendations.append(
                    "High gas volatility detected. Consider increasing priority fee "
                    "or waiting for more stable conditions."
                )

            # Risk level recommendations
            if risk_assessment["risk_level"] == "HIGH":
                recommendations.append(
                    "High MEV risk detected. Using aggressive gas settings and "
                    "targeting fewer blocks for faster inclusion."
                )
            elif risk_assessment["risk_level"] == "MEDIUM":
                recommendations.append(
                    "Moderate MEV risk. Using balanced gas settings for "
                    "competitive inclusion."
                )

            # Profit recommendations
            gas_cost = gas_settings["max_fee_per_gas"]
            if gas_cost > expected_profit * 0.1:
                recommendations.append(
                    "Gas costs exceed 10% of expected profit. Consider waiting "
                    "for better conditions or optimizing transactions."
                )

            return (
                " ".join(recommendations)
                if recommendations
                else ("Current conditions are favorable for bundle submission.")
            )

        except Exception as e:
            logger.error(f"Failed to generate strategy recommendation: {e}")
            return "Failed to generate recommendation"

    def _generate_optimization_recommendation(
        self, gas_cost: int, expected_profit: int
    ) -> str:
        """Generate optimization recommendation for unprofitable bundles."""
        try:
            profit_deficit = gas_cost - expected_profit
            recommendations = [
                f"Bundle is not profitable. Current deficit: {profit_deficit} wei"
            ]

            if gas_cost > expected_profit * 0.2:
                recommendations.append(
                    "Gas costs are too high. Consider:\n"
                    "- Waiting for lower gas prices\n"
                    "- Optimizing transaction gas usage\n"
                    "- Finding higher profit opportunities"
                )

            return " ".join(recommendations)

        except Exception as e:
            logger.error(f"Failed to generate optimization recommendation: {e}")
            return "Failed to generate optimization recommendation"
