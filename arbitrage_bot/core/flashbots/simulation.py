"""
Flashbots simulation manager module.

This module provides functionality for simulating transaction bundles
and validating expected profits before submission.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from web3.types import TxParams
from eth_typing import ChecksumAddress

from .manager import FlashbotsManager
from .bundle import BundleManager

logger = logging.getLogger(__name__)


class SimulationManager:
    """
    Manages Flashbots bundle simulation and profit validation.

    This class handles:
    - Bundle simulation
    - State validation
    - Profit calculation
    - Gas optimization
    """

    def __init__(
        self,
        flashbots_manager: FlashbotsManager,
        bundle_manager: BundleManager,
        max_simulations: int = 3,
        simulation_timeout: float = 5.0,
    ) -> None:
        """
        Initialize the simulation manager.

        Args:
            flashbots_manager: FlashbotsManager instance
            bundle_manager: BundleManager instance
            max_simulations: Maximum number of simulation attempts
            simulation_timeout: Simulation timeout in seconds
        """
        self.flashbots = flashbots_manager
        self.bundle_manager = bundle_manager
        self.max_simulations = max_simulations
        self.simulation_timeout = simulation_timeout
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized SimulationManager with max_simulations={max_simulations}, "
            f"timeout={simulation_timeout}s"
        )

    async def simulate_bundle(
        self, bundle: Dict[str, Any], state_block: Optional[str] = "latest"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Simulate a transaction bundle and validate results.

        Args:
            bundle: Bundle parameters
            state_block: Block number for state access

        Returns:
            Tuple[bool, Dict[str, Any]]: (success, simulation results)

        Raises:
            Exception: If simulation fails
        """
        try:
            async with self._lock:
                # Prepare simulation parameters
                params = [
                    {
                        "transactions": [
                            tx.rawTransaction.hex() for tx in bundle["transactions"]
                        ],
                        "block_number": bundle["target_block"],
                        "state_block_number": state_block,
                        "simulation_kind": "full",  # Request full simulation
                    }
                ]

                # Run simulation
                for attempt in range(self.max_simulations):
                    try:
                        async with asyncio.timeout(self.simulation_timeout):
                            response = await self.flashbots._make_request(
                                "eth_callBundle", params
                            )

                            result = response["result"]

                            if result["success"]:
                                # Parse and validate results
                                simulation_results = (
                                    await self._parse_simulation_results(result, bundle)
                                )

                                if simulation_results["profitable"]:
                                    logger.info(
                                        f"Bundle simulation successful with profit "
                                        f"{simulation_results['profit']:.6f} ETH"
                                    )
                                    return True, simulation_results
                                else:
                                    logger.warning(
                                        f"Bundle simulation showed insufficient profit: "
                                        f"{simulation_results['profit']} ETH"
                                    )
                            else:
                                logger.error(
                                    f"Bundle simulation failed: {result.get('error')}"
                                )

                    except asyncio.TimeoutError:
                        logger.warning(f"Simulation timeout on attempt {attempt + 1}")
                        continue

                    except Exception as e:
                        logger.error(f"Simulation error on attempt {attempt + 1}: {e}")
                        continue

                return False, {"error": "All simulation attempts failed"}

        except Exception as e:
            logger.error(f"Failed to simulate bundle: {e}")
            raise

    async def _parse_simulation_results(
        self, result: Dict[str, Any], bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse and validate simulation results.

        Args:
            result: Simulation result from Flashbots
            bundle: Original bundle parameters

        Returns:
            Dict[str, Any]: Parsed simulation results
        """
        try:
            # Extract key metrics
            gas_used = sum(tx["gasUsed"] for tx in result["results"])
            gas_price = bundle["gas_price"]
            total_cost = (
                Decimal(str(gas_used)) * Decimal(str(gas_price)) / Decimal("1e18")
            )  # Convert to ETH

            # Calculate state changes
            state_changes = await self._analyze_state_changes(result["stateDiff"])

            # Calculate actual profit
            profit = await self._calculate_actual_profit(state_changes, total_cost)

            # Validate profitability
            profitable = profit >= self.bundle_manager.min_profit

            return {
                "gas_used": gas_used,
                "total_cost": total_cost,
                "state_changes": state_changes,
                "profit": profit,
                "profitable": profitable,
                "coinbase_diff": result.get("coinbaseDiff"),
                "logs": result.get("logs", []),
            }

        except Exception as e:
            logger.error(f"Failed to parse simulation results: {e}")
            raise

    async def _analyze_state_changes(
        self, state_diff: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze state changes from simulation.

        Args:
            state_diff: State differences from simulation

        Returns:
            Dict[str, Any]: Analyzed state changes
        """
        try:
            changes = {"balance_changes": {}, "storage_changes": {}, "code_changes": []}

            for address, diff in state_diff.items():
                # Skip if not checksummed
                if not Web3.is_checksum_address(address):
                    continue

                # Analyze balance changes
                if "balance" in diff:
                    old_balance = int(diff["balance"].get("from", "0"), 16)
                    new_balance = int(diff["balance"].get("to", "0"), 16)
                    changes["balance_changes"][address] = {
                        "old": old_balance,
                        "new": new_balance,
                        "diff": new_balance - old_balance,
                    }

                # Analyze storage changes
                if "storage" in diff:
                    changes["storage_changes"][address] = diff["storage"]

                # Track code changes
                if "code" in diff:
                    changes["code_changes"].append(address)

            return changes

        except Exception as e:
            logger.error(f"Failed to analyze state changes: {e}")
            raise

    async def _calculate_actual_profit(
        self, state_changes: Dict[str, Any], total_cost: Decimal
    ) -> Decimal:
        """
        Calculate actual profit from state changes.

        Args:
            state_changes: Analyzed state changes
            total_cost: Total transaction cost

        Returns:
            Decimal: Actual profit in ETH
        """
        try:
            profit = Decimal("0")

            # Calculate profit from balance changes
            for address, change in state_changes["balance_changes"].items():
                if address == self.flashbots.account.address:
                    # Convert to ETH
                    balance_diff = Decimal(str(change["diff"])) / Decimal("1e18")
                    profit += balance_diff

            # Subtract transaction costs
            net_profit = profit - total_cost

            return net_profit

        except Exception as e:
            logger.error(f"Failed to calculate actual profit: {e}")
            raise

    async def verify_bundle_profitability(
        self, bundle: Dict[str, Any], min_profit_threshold: Decimal
    ) -> Tuple[bool, Decimal]:
        """
        Verify if a bundle is profitable based on simulation.

        Args:
            bundle: Bundle to verify
            min_profit_threshold: Minimum profit threshold in ETH

        Returns:
            Tuple[bool, Decimal]: (is_profitable, expected_profit)
        """
        try:
            # Simulate bundle
            success, simulation_results = await self.simulate_bundle(bundle)

            if not success:
                logger.warning("Bundle simulation failed during profitability check")
                return False, Decimal("0")

            # Extract profit from simulation results
            profit = simulation_results.get("profit", Decimal("0"))

            # Check if profit meets threshold
            is_profitable = profit >= min_profit_threshold

            if is_profitable:
                logger.info(
                    f"Bundle is profitable: {profit:.6f} ETH >= {min_profit_threshold:.6f} ETH"
                )
            else:
                logger.warning(
                    f"Bundle is not profitable enough: {profit:.6f} ETH < {min_profit_threshold:.6f} ETH"
                )

            return is_profitable, profit

        except Exception as e:
            logger.error(f"Failed to verify bundle profitability: {e}")
            return False, Decimal("0")

    async def optimize_bundle_gas(
        self, bundle: Dict[str, Any], base_fee: int, priority_multiplier: float = 1.1
    ) -> Dict[str, Any]:
        """
        Optimize bundle gas settings for better inclusion probability.

        Args:
            bundle: Bundle to optimize
            base_fee: Current base fee
            priority_multiplier: Priority fee multiplier

        Returns:
            Dict[str, Any]: Optimized bundle
        """
        try:
            # Make a copy of the bundle to avoid modifying the original
            optimized_bundle = bundle.copy()
            transactions = optimized_bundle.get("transactions", [])

            # Calculate optimal gas settings
            gas_price = int(base_fee * 1.1)  # 10% buffer
            priority_fee = int(
                1e9 * priority_multiplier
            )  # Base priority fee with multiplier

            # Update transactions with optimized gas settings
            updated_txs = []
            for tx in transactions:
                # Create a copy of the transaction
                updated_tx = tx.copy()

                # Update gas parameters
                updated_tx.update(
                    {
                        "gasPrice": gas_price,
                        "maxPriorityFeePerGas": priority_fee,
                        "maxFeePerGas": gas_price + priority_fee,
                    }
                )

                updated_txs.append(updated_tx)

            # Update bundle with optimized transactions
            optimized_bundle["transactions"] = updated_txs
            optimized_bundle["gas_price"] = gas_price
            optimized_bundle["priority_fee"] = priority_fee

            return optimized_bundle

        except Exception as e:
            logger.error(f"Failed to optimize bundle gas: {e}")
            return bundle  # Return original bundle if optimization fails
