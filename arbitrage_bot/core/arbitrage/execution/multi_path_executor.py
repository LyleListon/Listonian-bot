"""
Multi-Path Executor for Arbitrage

This module provides functionality for executing multi-path arbitrage
opportunities, including parallel execution, atomic execution with Flashbots
bundles, fallback strategies, and execution timing optimization.

Key features:
- Parallel execution of multiple paths
- Atomic execution with Flashbots bundles
- Fallback strategies for failed paths
- Execution timing optimization
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import numpy as np
from collections import defaultdict

from ..path.interfaces import ArbitragePath, MultiPathOpportunity
from ...flashbots.bundle import BundleManager
from ...flashbots.simulation import SimulationManager
from ...utils.async_utils import gather_with_concurrency
from ...utils.retry import with_retry
from ...web3.interfaces import Web3Client, Transaction

logger = logging.getLogger(__name__)


class MultiPathExecutor:
    """
    Executes multi-path arbitrage opportunities.

    This class implements algorithms for parallel execution of multiple paths,
    atomic execution with Flashbots bundles, fallback strategies for failed
    paths, and execution timing optimization.
    """

    def __init__(
        self,
        web3_client: Web3Client,
        bundle_manager: Optional[BundleManager] = None,
        simulation_manager: Optional[SimulationManager] = None,
        max_concurrent_paths: int = 3,
        execution_timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        min_success_rate: float = 0.7,
    ):
        """
        Initialize the multi-path executor.

        Args:
            web3_client: Web3 client for blockchain interaction
            bundle_manager: Optional bundle manager for Flashbots bundles
            simulation_manager: Optional simulation manager for simulating executions
            max_concurrent_paths: Maximum number of paths to execute concurrently (default: 3)
            execution_timeout: Timeout for execution in seconds (default: 30.0)
            retry_attempts: Number of retry attempts for failed executions (default: 3)
            retry_delay: Delay between retry attempts in seconds (default: 1.0)
            min_success_rate: Minimum success rate for execution (default: 0.7)
        """
        self.web3_client = web3_client
        self.bundle_manager = bundle_manager
        self.simulation_manager = simulation_manager
        self.max_concurrent_paths = max_concurrent_paths
        self.execution_timeout = execution_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.min_success_rate = min_success_rate

        # Thread safety
        self._lock = asyncio.Lock()

        # Execution state
        self._active_executions = {}
        self._execution_history = []

        logger.info(
            f"Initialized MultiPathExecutor with max_concurrent_paths={max_concurrent_paths}, "
            f"execution_timeout={execution_timeout}s"
        )

    async def execute_opportunity(
        self,
        opportunity: MultiPathOpportunity,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a multi-path arbitrage opportunity.

        Args:
            opportunity: Multi-path opportunity to execute
            context: Optional context information
                - gas_price: Current gas price in gwei
                - priority_fee: Priority fee in gwei
                - execution_strategy: Execution strategy ("parallel", "sequential", "atomic")
                - fallback_enabled: Whether to enable fallback strategies

        Returns:
            Execution results
        """
        async with self._lock:
            try:
                if not opportunity.paths or not opportunity.allocations:
                    return {
                        "success": False,
                        "error": "Invalid opportunity: no paths or allocations",
                    }

                # Apply context
                context = context or {}

                # Validate opportunity
                validation_result = self._validate_opportunity(opportunity)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "error": f"Invalid opportunity: {validation_result['reason']}",
                    }

                # Determine execution strategy
                execution_strategy = context.get("execution_strategy", "parallel")

                # Execute based on strategy
                if execution_strategy == "atomic":
                    # Execute all paths atomically using Flashbots bundle
                    result = await self._execute_atomic(opportunity, context)
                elif execution_strategy == "sequential":
                    # Execute paths sequentially
                    result = await self._execute_sequential(opportunity, context)
                else:
                    # Execute paths in parallel (default)
                    result = await self._execute_parallel(opportunity, context)

                # Update execution history
                self._update_execution_history(opportunity, result)

                return result

            except Exception as e:
                logger.error(f"Error executing opportunity: {e}")
                return {"success": False, "error": str(e)}

    async def simulate_execution(
        self,
        opportunity: MultiPathOpportunity,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Simulate the execution of a multi-path arbitrage opportunity.

        Args:
            opportunity: Multi-path opportunity to simulate
            context: Optional context information

        Returns:
            Simulation results
        """
        try:
            if not self.simulation_manager:
                return {"success": False, "error": "Simulation manager not available"}

            if not opportunity.paths or not opportunity.allocations:
                return {
                    "success": False,
                    "error": "Invalid opportunity: no paths or allocations",
                }

            # Apply context
            context = context or {}

            # Determine execution strategy
            execution_strategy = context.get("execution_strategy", "parallel")

            # Create transactions for simulation
            transactions = []

            if execution_strategy == "atomic":
                # Create transactions for atomic execution
                transactions = await self._create_atomic_transactions(
                    opportunity, context
                )
            else:
                # Create transactions for each path
                for i, (path, allocation) in enumerate(
                    zip(opportunity.paths, opportunity.allocations)
                ):
                    path_txs = await self._create_path_transactions(
                        path, allocation, context
                    )
                    transactions.extend(path_txs)

            # Create bundle for simulation
            if self.bundle_manager:
                bundle = await self.bundle_manager.create_bundle(transactions)

                # Simulate bundle
                success, simulation_results = (
                    await self.simulation_manager.simulate_bundle(bundle)
                )

                if success:
                    return {
                        "success": True,
                        "bundle": bundle,
                        "simulation_results": simulation_results,
                        "expected_profit": simulation_results.get("mevValue", 0),
                        "gas_cost": simulation_results.get("totalCost", 0),
                    }
                else:
                    return {
                        "success": False,
                        "error": "Bundle simulation failed",
                        "simulation_results": simulation_results,
                    }
            else:
                # Simulate transactions individually
                simulation_results = []

                for tx in transactions:
                    # Simulate transaction
                    tx_result = await self.web3_client.estimate_gas(tx)
                    simulation_results.append(tx_result)

                return {
                    "success": True,
                    "transactions": transactions,
                    "simulation_results": simulation_results,
                }

        except Exception as e:
            logger.error(f"Error simulating execution: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Cancel an active execution.

        Args:
            execution_id: ID of the execution to cancel

        Returns:
            Cancellation results
        """
        async with self._lock:
            try:
                if execution_id not in self._active_executions:
                    return {
                        "success": False,
                        "error": f"Execution {execution_id} not found",
                    }

                # Get execution
                execution = self._active_executions[execution_id]

                # Cancel execution
                if "task" in execution and not execution["task"].done():
                    execution["task"].cancel()

                # Remove from active executions
                del self._active_executions[execution_id]

                return {
                    "success": True,
                    "execution_id": execution_id,
                    "message": f"Execution {execution_id} cancelled",
                }

            except Exception as e:
                logger.error(f"Error cancelling execution: {e}")
                return {"success": False, "error": str(e)}

    def _validate_opportunity(
        self, opportunity: MultiPathOpportunity
    ) -> Dict[str, Any]:
        """
        Validate a multi-path opportunity.

        Args:
            opportunity: Multi-path opportunity to validate

        Returns:
            Validation results
        """
        try:
            # Check if opportunity is valid
            if not opportunity.is_valid:
                return {"valid": False, "reason": "Opportunity is not valid"}

            # Check if opportunity has expired
            if opportunity.expiration is not None and opportunity.expiration < int(
                time.time()
            ):
                return {"valid": False, "reason": "Opportunity has expired"}

            # Check if opportunity has sufficient profit
            if opportunity.expected_profit <= 0:
                return {"valid": False, "reason": "Opportunity has no expected profit"}

            # Check if opportunity has sufficient confidence
            if opportunity.confidence_level < self.min_success_rate:
                return {
                    "valid": False,
                    "reason": f"Opportunity confidence {opportunity.confidence_level} is below minimum {self.min_success_rate}",
                }

            return {"valid": True}

        except Exception as e:
            logger.error(f"Error validating opportunity: {e}")
            return {"valid": False, "reason": str(e)}

    async def _execute_atomic(
        self, opportunity: MultiPathOpportunity, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute all paths atomically using Flashbots bundle.

        Args:
            opportunity: Multi-path opportunity to execute
            context: Context information

        Returns:
            Execution results
        """
        try:
            if not self.bundle_manager:
                return {
                    "success": False,
                    "error": "Bundle manager not available for atomic execution",
                }

            # Create transactions for all paths
            transactions = await self._create_atomic_transactions(opportunity, context)

            # Create bundle
            bundle = await self.bundle_manager.create_bundle(transactions)

            # Simulate bundle if simulation manager is available
            if self.simulation_manager:
                success, simulation_results = (
                    await self.simulation_manager.simulate_bundle(bundle)
                )

                if not success:
                    return {
                        "success": False,
                        "error": "Bundle simulation failed",
                        "simulation_results": simulation_results,
                    }

                # Check if simulation shows profit
                if simulation_results.get("mevValue", 0) <= simulation_results.get(
                    "totalCost", 0
                ):
                    return {
                        "success": False,
                        "error": "Bundle simulation shows no profit",
                        "simulation_results": simulation_results,
                    }

            # Submit bundle
            success, bundle_hash = await self.bundle_manager.submit_bundle(bundle)

            if not success:
                return {"success": False, "error": "Bundle submission failed"}

            # Wait for bundle to be included
            inclusion_result = await self._wait_for_bundle_inclusion(bundle_hash)

            # Create result
            result = {
                "success": inclusion_result["success"],
                "execution_strategy": "atomic",
                "bundle_hash": bundle_hash,
                "transactions": transactions,
                "inclusion_result": inclusion_result,
            }

            if not inclusion_result["success"] and context.get(
                "fallback_enabled", True
            ):
                # Try fallback strategy
                logger.warning(f"Atomic execution failed, trying fallback strategy")
                fallback_result = await self._execute_parallel(opportunity, context)

                # Update result with fallback information
                result["fallback_result"] = fallback_result
                result["success"] = fallback_result["success"]

            return result

        except Exception as e:
            logger.error(f"Error executing atomic opportunity: {e}")
            return {"success": False, "error": str(e), "execution_strategy": "atomic"}

    async def _execute_sequential(
        self, opportunity: MultiPathOpportunity, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute paths sequentially.

        Args:
            opportunity: Multi-path opportunity to execute
            context: Context information

        Returns:
            Execution results
        """
        try:
            # Execute paths one by one
            path_results = []

            for i, (path, allocation) in enumerate(
                zip(opportunity.paths, opportunity.allocations)
            ):
                # Skip paths with zero allocation
                if allocation <= 0:
                    continue

                # Execute path
                path_result = await self._execute_path(path, allocation, context)
                path_results.append(path_result)

                # Stop if path execution failed and fallback is not enabled
                if not path_result["success"] and not context.get(
                    "fallback_enabled", True
                ):
                    break

            # Calculate overall success
            success_count = sum(1 for result in path_results if result["success"])
            success_rate = success_count / len(path_results) if path_results else 0

            # Create result
            result = {
                "success": success_rate >= self.min_success_rate,
                "execution_strategy": "sequential",
                "path_results": path_results,
                "success_rate": success_rate,
            }

            return result

        except Exception as e:
            logger.error(f"Error executing sequential opportunity: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_strategy": "sequential",
            }

    async def _execute_parallel(
        self, opportunity: MultiPathOpportunity, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute paths in parallel.

        Args:
            opportunity: Multi-path opportunity to execute
            context: Context information

        Returns:
            Execution results
        """
        try:
            # Create execution tasks
            tasks = []

            for i, (path, allocation) in enumerate(
                zip(opportunity.paths, opportunity.allocations)
            ):
                # Skip paths with zero allocation
                if allocation <= 0:
                    continue

                # Create task for path execution
                task = asyncio.create_task(
                    self._execute_path(path, allocation, context)
                )
                tasks.append(task)

            # Execute paths in parallel with concurrency limit
            path_results = await gather_with_concurrency(
                self.max_concurrent_paths, *tasks
            )

            # Calculate overall success
            success_count = sum(1 for result in path_results if result["success"])
            success_rate = success_count / len(path_results) if path_results else 0

            # Create result
            result = {
                "success": success_rate >= self.min_success_rate,
                "execution_strategy": "parallel",
                "path_results": path_results,
                "success_rate": success_rate,
            }

            return result

        except Exception as e:
            logger.error(f"Error executing parallel opportunity: {e}")
            return {"success": False, "error": str(e), "execution_strategy": "parallel"}

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _execute_path(
        self, path: ArbitragePath, allocation: Decimal, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single arbitrage path.

        Args:
            path: Arbitrage path to execute
            allocation: Allocated capital for the path
            context: Context information

        Returns:
            Execution results
        """
        try:
            # Create transactions for the path
            transactions = await self._create_path_transactions(
                path, allocation, context
            )

            if not transactions:
                return {
                    "success": False,
                    "error": "Failed to create transactions for path",
                    "path": path,
                }

            # Execute transactions
            tx_results = []

            for tx in transactions:
                # Send transaction
                tx_hash = await self.web3_client.send_transaction(tx)

                if not tx_hash:
                    return {
                        "success": False,
                        "error": "Failed to send transaction",
                        "path": path,
                        "tx_results": tx_results,
                    }

                # Wait for transaction to be mined
                tx_receipt = await self.web3_client.wait_for_transaction_receipt(
                    tx_hash, timeout=self.execution_timeout
                )

                # Check if transaction was successful
                if not tx_receipt or tx_receipt.get("status") != 1:
                    return {
                        "success": False,
                        "error": "Transaction failed",
                        "path": path,
                        "tx_hash": tx_hash,
                        "tx_receipt": tx_receipt,
                        "tx_results": tx_results,
                    }

                # Add to results
                tx_results.append({"tx_hash": tx_hash, "tx_receipt": tx_receipt})

            # Calculate profit
            profit = self._calculate_path_profit(path, tx_results)

            return {
                "success": True,
                "path": path,
                "allocation": allocation,
                "tx_results": tx_results,
                "profit": profit,
            }

        except Exception as e:
            logger.error(f"Error executing path: {e}")
            return {"success": False, "error": str(e), "path": path}

    async def _create_atomic_transactions(
        self, opportunity: MultiPathOpportunity, context: Dict[str, Any]
    ) -> List[Transaction]:
        """
        Create transactions for atomic execution of all paths.

        Args:
            opportunity: Multi-path opportunity
            context: Context information

        Returns:
            List of transactions
        """
        try:
            transactions = []

            # Create transactions for each path
            for i, (path, allocation) in enumerate(
                zip(opportunity.paths, opportunity.allocations)
            ):
                # Skip paths with zero allocation
                if allocation <= 0:
                    continue

                # Create transactions for this path
                path_txs = await self._create_path_transactions(
                    path, allocation, context
                )
                transactions.extend(path_txs)

            return transactions

        except Exception as e:
            logger.error(f"Error creating atomic transactions: {e}")
            return []

    async def _create_path_transactions(
        self, path: ArbitragePath, allocation: Decimal, context: Dict[str, Any]
    ) -> List[Transaction]:
        """
        Create transactions for a path.

        Args:
            path: Arbitrage path
            allocation: Allocated capital for the path
            context: Context information

        Returns:
            List of transactions
        """
        try:
            # This is a placeholder - in a real implementation,
            # we would create actual transactions based on the path

            # For now, return an empty list
            return []

        except Exception as e:
            logger.error(f"Error creating path transactions: {e}")
            return []

    async def _wait_for_bundle_inclusion(self, bundle_hash: str) -> Dict[str, Any]:
        """
        Wait for a bundle to be included in a block.

        Args:
            bundle_hash: Hash of the bundle

        Returns:
            Inclusion results
        """
        try:
            # This is a placeholder - in a real implementation,
            # we would wait for the bundle to be included in a block

            # For now, return success
            return {
                "success": True,
                "bundle_hash": bundle_hash,
                "block_number": 0,
                "block_timestamp": 0,
            }

        except Exception as e:
            logger.error(f"Error waiting for bundle inclusion: {e}")
            return {"success": False, "error": str(e), "bundle_hash": bundle_hash}

    def _calculate_path_profit(
        self, path: ArbitragePath, tx_results: List[Dict[str, Any]]
    ) -> Decimal:
        """
        Calculate profit from path execution.

        Args:
            path: Arbitrage path
            tx_results: Transaction results

        Returns:
            Profit amount
        """
        try:
            # This is a placeholder - in a real implementation,
            # we would calculate the actual profit from the transaction results

            # For now, return the expected profit
            return path.profit or Decimal("0")

        except Exception as e:
            logger.error(f"Error calculating path profit: {e}")
            return Decimal("0")

    def _update_execution_history(
        self, opportunity: MultiPathOpportunity, result: Dict[str, Any]
    ) -> None:
        """
        Update execution history.

        Args:
            opportunity: Multi-path opportunity
            result: Execution results
        """
        try:
            # Add to execution history
            self._execution_history.append(
                {"timestamp": time.time(), "opportunity": opportunity, "result": result}
            )

            # Limit history size
            if len(self._execution_history) > 100:
                self._execution_history = self._execution_history[-100:]

        except Exception as e:
            logger.error(f"Error updating execution history: {e}")
