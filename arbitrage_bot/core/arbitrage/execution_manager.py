"""
Execution Manager Implementation

This module provides the implementation of the ExecutionManager protocol.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from .interfaces import ExecutionStrategy, TransactionMonitor, ExecutionManager
from ..memory.memory_bank import MemoryBank
from .models import ArbitrageOpportunity, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class EnhancedExecutionManager(ExecutionManager):
    """
    Implementation of the ExecutionManager protocol.

    This class coordinates execution strategies and transaction monitors to
    execute arbitrage opportunities.
    """

    def __init__(self):
        """Initialize the execution manager."""
        self._strategies = {}  # strategy_id -> strategy
        self._monitors = {}  # monitor_id -> monitor
        self._active_executions = {}  # execution_id -> execution_info
        self._lock = asyncio.Lock()
        self._initialized = False
        self._memory_bank = MemoryBank()

    async def initialize(self) -> None:
        """Initialize the execution manager."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing execution manager")
            self._initialized = True
            await self._memory_bank.initialize()

    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            # Cancel any active executions
            for execution_id, execution_info in self._active_executions.items():
                try:
                    await self._cancel_execution(execution_id)
                except Exception as e:
                    logger.error(
                        f"Error cancelling execution {execution_id}: {e}", exc_info=True
                    )

            self._initialized = False
            self._strategies.clear()
            self._monitors.clear()
            self._active_executions.clear()
            await self._memory_bank.cleanup()

    async def register_strategy(
        self, strategy: ExecutionStrategy, strategy_id: str
    ) -> None:
        """
        Register an execution strategy.

        Args:
            strategy: The strategy to register
            strategy_id: Unique identifier for the strategy
        """
        async with self._lock:
            if strategy_id in self._strategies:
                raise ValueError(f"Strategy {strategy_id} already registered")

            self._strategies[strategy_id] = strategy
            logger.info(f"Registered strategy {strategy_id}")

    async def register_monitor(
        self, monitor: TransactionMonitor, monitor_id: str
    ) -> None:
        """
        Register a transaction monitor.

        Args:
            monitor: The monitor to register
            monitor_id: Unique identifier for the monitor
        """
        async with self._lock:
            if monitor_id in self._monitors:
                raise ValueError(f"Monitor {monitor_id} already registered")

            self._monitors[monitor_id] = monitor
            logger.info(f"Registered monitor {monitor_id}")

    async def execute_opportunity(
        self, opportunity: ArbitrageOpportunity, strategy_id: str = "default", **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.

        Args:
            opportunity: The opportunity to execute
            strategy_id: ID of the strategy to use
            **kwargs: Additional parameters

        Returns:
            Result of the execution
        """
        if not self._initialized:
            raise RuntimeError("Execution manager not initialized")

        # Get the strategy
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Execute the opportunity
        try:
            # Create execution result
            execution_id = f"exec_{opportunity.id}_{strategy_id}"
            result = ExecutionResult(
                id=execution_id,
                opportunity=opportunity,
                status=ExecutionStatus.PENDING,
                strategy_id=strategy_id,
            )

            # Add to active executions
            self._active_executions[execution_id] = {
                "result": result,
                "strategy": strategy,
                "monitors": [],
            }

            # Execute using strategy
            result = await strategy.execute_opportunity(
                opportunity=opportunity, **kwargs
            )

            # Monitor transaction if available
            if result.transaction_hash:
                monitor_tasks = []
                for monitor in self._monitors.values():
                    task = asyncio.create_task(
                        self._monitor_transaction(
                            monitor=monitor,
                            execution_id=execution_id,
                            transaction_hash=result.transaction_hash,
                        )
                    )
                    monitor_tasks.append(task)
                    self._active_executions[execution_id]["monitors"].append(task)

            # Update memory bank state
            await self._update_state(result)

            return result

        except Exception as e:
            logger.error(
                f"Error executing opportunity {opportunity.id}: {e}", exc_info=True
            )
            result = ExecutionResult(
                id=execution_id,
                opportunity=opportunity,
                status=ExecutionStatus.FAILED,
                strategy_id=strategy_id,
                error=str(e),
            )
            return result

    async def get_execution_status(self, execution_id: str) -> ExecutionStatus:
        """
        Get the status of an execution.

        Args:
            execution_id: ID of the execution

        Returns:
            Current status of the execution
        """
        execution_info = self._active_executions.get(execution_id)
        if not execution_info:
            return ExecutionStatus.NOT_FOUND

        return execution_info["result"].status

    async def _monitor_transaction(
        self, monitor: TransactionMonitor, execution_id: str, transaction_hash: str
    ) -> None:
        """Monitor a transaction and update execution status."""
        try:
            status = await monitor.monitor_transaction(
                transaction_hash=transaction_hash
            )

            # Update execution status
            execution_info = self._active_executions.get(execution_id)
            if execution_info:
                execution_info["result"].status = status

                # Remove from active executions if final
                if status.is_final:
                    await self._cleanup_execution(execution_id)

        except Exception as e:
            logger.error(
                f"Error monitoring transaction {transaction_hash}: {e}", exc_info=True
            )

    async def _cancel_execution(self, execution_id: str) -> None:
        """Cancel an active execution."""
        execution_info = self._active_executions.get(execution_id)
        if not execution_info:
            return

        # Cancel monitor tasks
        for task in execution_info["monitors"]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Update status
        execution_info["result"].status = ExecutionStatus.CANCELLED

        # Remove from active executions
        await self._cleanup_execution(execution_id)

    async def _cleanup_execution(self, execution_id: str) -> None:
        """Clean up an execution."""
        async with self._lock:
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]

    async def _update_state(self, result: ExecutionResult) -> None:
        """Update memory bank state with execution result."""
        try:
            state_dir = Path("memory-bank/state")
            state_dir.mkdir(parents=True, exist_ok=True)

            # Update executions state
            executions_file = state_dir / "executions.json"
            executions = {}
            if executions_file.exists():
                with open(executions_file, "r") as f:
                    executions = json.load(f)

            executions[result.id] = {
                "id": result.id,
                "status": result.status.value,
                "strategy_id": result.strategy_id,
                "transaction_hash": result.transaction_hash,
                "gas_used": str(result.gas_used) if result.gas_used else None,
                "error": result.error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            with open(executions_file, "w") as f:
                json.dump(executions, f, indent=2)

            # Update metrics state
            metrics_dir = self._memory_bank.base_dir / "metrics"  # Use correct subdir
            metrics_dir.mkdir(parents=True, exist_ok=True)
            metrics_file = metrics_dir / "metrics.json"
            metrics = {
                "performance": {
                    "total_executions": len(executions),
                    "successful_executions": sum(
                        1 for e in executions.values() if e["status"] == "completed"
                    ),
                    "failed_executions": sum(
                        1 for e in executions.values() if e["status"] == "failed"
                    ),
                    "gas_stats": await self._calculate_gas_stats(executions),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            with open(metrics_file, "w") as f:
                json.dump(metrics, f, indent=2)

            # Update aggregated trade history file
            trade_dir = self._memory_bank.base_dir / "trades"
            trade_dir.mkdir(parents=True, exist_ok=True)
            trade_history_file = trade_dir / "recent_trades.json"
            trade_history = []

            # Read existing history
            if trade_history_file.exists():
                try:
                    with open(trade_history_file, "r") as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "trades" in data:
                            trade_history = data["trades"]
                        elif isinstance(data, list):  # Handle older format if necessary
                            trade_history = data
                except json.JSONDecodeError:
                    logger.warning(
                        f"Could not decode existing trade history file: {trade_history_file}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error reading trade history file {trade_history_file}: {e}"
                    )

            # Prepare current trade record (ensure all necessary fields are present)
            current_trade = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_id": result.id,
                "status": result.status.value,
                "token_pair": (
                    result.opportunity.token_pair if result.opportunity else "N/A"
                ),
                "dex_1": result.opportunity.dex_1 if result.opportunity else "N/A",
                "dex_2": result.opportunity.dex_2 if result.opportunity else "N/A",
                "strategy_type": result.strategy_id,  # Assuming strategy_id represents the type
                "trade_type": (
                    result.opportunity.trade_type if result.opportunity else "unknown"
                ),  # e.g., 'flashloan', 'simple'
                "profit": (
                    str(result.net_profit) if result.net_profit else "0"
                ),  # Assuming net_profit is gross profit for now
                "gas_cost": str(result.gas_used) if result.gas_used else "0",
                "initial_investment": (
                    str(result.opportunity.amount_in) if result.opportunity else "0"
                ),  # Or borrowed amount for flashloan
                "tx_hash": result.transaction_hash,
                "error": result.error,
            }

            # Append new trade and limit history size (e.g., keep last 1000)
            trade_history.append(current_trade)
            max_history = 1000
            if len(trade_history) > max_history:
                trade_history = trade_history[-max_history:]

            # Write updated history back
            try:
                with open(trade_history_file, "w") as f:
                    # Store as a dictionary with a 'trades' key for consistency
                    json.dump({"trades": trade_history}, f, indent=2)
            except Exception as e:
                logger.error(
                    f"Error writing trade history file {trade_history_file}: {e}"
                )

        except Exception as e:
            logger.error(f"Error updating execution state: {e}", exc_info=True)

    async def _calculate_gas_stats(self, executions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate gas usage statistics."""
        gas_values = [
            float(e["gas_used"]) for e in executions.values() if e["gas_used"]
        ]
        return {
            "min": min(gas_values) if gas_values else 0,
            "max": max(gas_values) if gas_values else 0,
            "avg": sum(gas_values) / len(gas_values) if gas_values else 0,
        }
