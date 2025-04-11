"""
Risk Analyzer for Flashbots Integration

This module provides functionality for:
- Analyzing mempool for MEV risks
- Detecting potential MEV attacks
- Tracking risk statistics
- Providing risk mitigation recommendations
- Measuring effectiveness through empirical metrics
"""

import logging
import time
from typing import Dict, List, Any # Removed Optional
# from decimal import Decimal # Unused
from collections import defaultdict

from ....utils.async_manager import AsyncLock, with_retry
from ..errors import Web3Error

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """Analyzes and manages MEV-related risks with empirical metrics tracking."""

    def __init__(self, web3_manager, config: Dict[str, Any]):
        """
        Initialize risk analyzer.

        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary containing:
                - mev_protection settings
                - gas price thresholds
                - risk parameters
        """
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self._request_lock = AsyncLock()

        # Initialize risk parameters with granular thresholds
        self.volatility_thresholds = {
            "low": 0.15,  # 15% variation
            "medium": 0.25,  # 25% variation
            "high": 0.35,  # 35% variation
        }
        self.min_confidence_threshold = 0.65  # Minimum confidence for attack detection

        # Initialize attack detection flags
        self.sandwich_detection = config.get("mev_protection", {}).get(
            "sandwich_detection", True
        )
        self.frontrun_detection = config.get("mev_protection", {}).get(
            "frontrun_detection", True
        )
        self.adaptive_gas = config.get("mev_protection", {}).get("adaptive_gas", True)

        # Initialize empirical metrics
        self._metrics = {
            "detection_accuracy": {
                "true_positives": 0,
                "false_positives": 0,
                "true_negatives": 0,
                "false_negatives": 0,
            },
            "gas_savings": {
                "total_saved": 0,
                "average_per_tx": 0,
                "highest_single_save": 0,
                "monthly_savings": defaultdict(int),  # Track by month
            },
            "profit_protection": {
                "protected_value_usd": 0,
                "prevented_losses_usd": 0,
                "successful_interventions": 0,
                "monthly_protection": defaultdict(float),  # Track by month
            },
            "performance_timing": {
                "analyze_mempool": [],
                "detect_attacks": [],
                "pattern_analysis": [],
            },
            "attack_patterns": defaultdict(int),  # Track specific attack types
            "confidence_distribution": defaultdict(int),  # Track confidence scores
            "block_coverage": {
                "total_blocks_analyzed": 0,
                "blocks_with_attacks": 0,
                "coverage_percentage": 0,
            },
            "risk_levels": {
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
            },
        }

        # Initialize core statistics
        self._stats = {
            "total_attacks": 0,
            "attack_types": {},
            "risk_level": "LOW",
            "last_update": 0,
        }

    def _parse_hex_or_int(self, value: Any, default: int = 0) -> int:
        """Parse a value that could be hex string or int."""
        try:
            if isinstance(value, str):
                if value.startswith("0x"):
                    return int(value, 16)
                return int(value)
            return int(value)
        except (ValueError, TypeError):
            return default

    @with_retry(max_attempts=3, base_delay=1.0)
    async def analyze_mempool_risk(self) -> Dict[str, Any]:
        """
        Analyze current mempool for MEV risks.

        Returns:
            Dict containing:
                - risk_level: Current risk level (LOW, MEDIUM, HIGH)
                - gas_price: Current gas price
                - avg_gas_price: Average gas price
                - gas_volatility: Gas price volatility
                - risk_factors: List of identified risk factors
        """
        async with self._request_lock:
            start_time = time.time()
            try:
                # Get current gas price
                gas_prediction = await self.web3_manager.get_gas_price_prediction()
                # Use the 'fast' gas price for risk analysis
                gas_price = gas_prediction.get(
                    "fast", await self.w3.eth.gas_price  # Fallback to basic gas price
                )
                gas_price = self._parse_hex_or_int(gas_price)

                # Get latest block
                block_result = await self.web3_manager.get_block("latest")
                if not block_result:
                    raise ValueError("Failed to get latest block")

                # Parse base fee
                base_fee = block_result.get("baseFeePerGas", "0x0")
                base_fee = self._parse_hex_or_int(base_fee)

                # Calculate gas price statistics
                avg_gas_price = await self._calculate_average_gas_price()
                volatility = self._calculate_gas_volatility(gas_price, avg_gas_price)

                # Identify risk factors
                risk_factors = []
                if volatility > self.volatility_thresholds["medium"]:
                    risk_factors.append("High gas price volatility")
                if gas_price > avg_gas_price * 1.8:
                    risk_factors.append("Gas price spike")

                # Determine risk level
                risk_level = self._determine_risk_level(risk_factors, volatility)

                # Update metrics
                self._metrics["risk_levels"][risk_level] += 1
                execution_time = time.time() - start_time
                self._metrics["performance_timing"]["analyze_mempool"].append(
                    execution_time
                )

                return {
                    "risk_level": risk_level,
                    "gas_price": gas_price,
                    "avg_gas_price": avg_gas_price,
                    "gas_volatility": volatility,
                    "risk_factors": risk_factors,
                    "base_fee": base_fee,
                    "execution_time": execution_time,
                }

            except Web3Error as e:
                logger.error(f"Web3 error in analyze_mempool_risk: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to analyze mempool risk: {e}")
                raise

    async def get_effectiveness_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics about the risk analyzer's effectiveness.

        Returns:
            Dict containing empirical measurements of:
            - Detection accuracy (true/false positives/negatives)
            - Gas savings (total, average, highest)
            - Profit protection (value protected, losses prevented)
            - Performance timing (operation execution times)
            - Attack patterns and confidence distribution
        """
        metrics = self._metrics.copy()

        # Calculate detection accuracy percentages
        total_detections = sum(metrics["detection_accuracy"].values())
        if total_detections > 0:
            accuracy = (
                metrics["detection_accuracy"]["true_positives"]
                + metrics["detection_accuracy"]["true_negatives"]
            ) / total_detections
            precision = (
                metrics["detection_accuracy"]["true_positives"]
                / (
                    metrics["detection_accuracy"]["true_positives"]
                    + metrics["detection_accuracy"]["false_positives"]
                )
                if metrics["detection_accuracy"]["true_positives"] > 0
                else 0
            )
        else:
            accuracy = precision = 0

        # Calculate average execution times
        avg_times = {}
        for operation, times in metrics["performance_timing"].items():
            if times:
                avg_times[operation] = sum(times) / len(times)

        # Calculate gas savings efficiency
        if metrics["profit_protection"]["successful_interventions"] > 0:
            avg_gas_saved = (
                metrics["gas_savings"]["total_saved"]
                / metrics["profit_protection"]["successful_interventions"]
            )
        else:
            avg_gas_saved = 0

        return {
            "accuracy_metrics": {
                "overall_accuracy": f"{accuracy:.2%}",
                "precision": f"{precision:.2%}",
                "detection_breakdown": metrics["detection_accuracy"],
            },
            "gas_metrics": {
                "total_gas_saved": metrics["gas_savings"]["total_saved"],
                "average_gas_saved": avg_gas_saved,
                "highest_single_save": metrics["gas_savings"]["highest_single_save"],
                "monthly_trend": dict(metrics["gas_savings"]["monthly_savings"]),
            },
            "profit_metrics": {
                "protected_value_usd": f"${metrics['profit_protection']['protected_value_usd']:,.2f}",
                "prevented_losses_usd": f"${metrics['profit_protection']['prevented_losses_usd']:,.2f}",
                "successful_interventions": metrics["profit_protection"][
                    "successful_interventions"
                ],
                "monthly_trend": dict(
                    metrics["profit_protection"]["monthly_protection"]
                ),
            },
            "performance_metrics": {
                operation: f"{avg:.3f}s" for operation, avg in avg_times.items()
            },
            "pattern_analysis": dict(metrics["attack_patterns"]),
            "confidence_distribution": dict(metrics["confidence_distribution"]),
            "block_coverage": metrics["block_coverage"],
            "risk_level_distribution": dict(metrics["risk_levels"]),
        }

    async def _calculate_average_gas_price(self) -> int:
        """Calculate average gas price over recent blocks."""
        try:
            current_block = await self.web3_manager.get_block_number()
            prices = []

            for block_number in range(current_block - 10, current_block + 1):
                block_result = await self.web3_manager.get_block(block_number)
                if block_result:
                    base_fee = block_result.get("baseFeePerGas", "0x0")
                    base_fee = self._parse_hex_or_int(base_fee)
                    prices.append(base_fee)

            return sum(prices) // len(prices) if prices else 0

        except Exception as e:
            logger.error(f"Failed to calculate average gas price: {e}")
            return 0

    def _calculate_gas_volatility(self, current: int, average: int) -> float:
        """Calculate gas price volatility."""
        if average == 0:
            return 0
        return abs(current - average) / average

    def _determine_risk_level(self, risk_factors: List[str], volatility: float) -> str:
        """Determine overall risk level."""
        if len(risk_factors) >= 2 or volatility > self.volatility_thresholds["high"]:
            return "HIGH"
        elif (
            len(risk_factors) == 1 or volatility > self.volatility_thresholds["medium"]
        ):
            return "MEDIUM"
        return "LOW"

    def _update_metrics(self, attack_result: Dict[str, Any]) -> None:
        """Update metrics based on attack detection result."""
        if not attack_result:
            return

        # Update confidence distribution
        confidence = int(attack_result["confidence"] * 100)
        confidence_bucket = (
            f"{confidence - (confidence % 5)}%-{confidence - (confidence % 5) + 5}%"
        )
        self._metrics["confidence_distribution"][confidence_bucket] += 1

        # Update attack patterns
        pattern = attack_result.get("pattern_type", "unknown")
        self._metrics["attack_patterns"][pattern] += 1

        # Update gas savings if available
        if "gas_saved" in attack_result:
            gas_saved = attack_result["gas_saved"]
            self._metrics["gas_savings"]["total_saved"] += gas_saved
            self._metrics["gas_savings"]["highest_single_save"] = max(
                self._metrics["gas_savings"]["highest_single_save"], gas_saved
            )

            # Update monthly tracking
            current_month = time.strftime("%Y-%m")
            self._metrics["gas_savings"]["monthly_savings"][current_month] += gas_saved

        # Update profit protection if available
        if "value_protected" in attack_result:
            value_protected = attack_result["value_protected"]
            self._metrics["profit_protection"]["protected_value_usd"] += value_protected
            self._metrics["profit_protection"]["successful_interventions"] += 1

            # Update monthly tracking
            self._metrics["profit_protection"]["monthly_protection"][
                current_month
            ] += value_protected

        # Update performance timing if available
        if "execution_time" in attack_result:
            operation = "pattern_analysis"
            self._metrics["performance_timing"][operation].append(
                attack_result["execution_time"]
            )
