"""Transaction lifecycle monitoring for arbitrage operations."""

import asyncio
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Union, cast
from decimal import Decimal
from web3 import Web3
from web3.types import TxReceipt

from arbitrage_bot.core.events.event_emitter import Event, EventEmitter

logger = logging.getLogger(__name__)


class TransactionStatus(str, Enum):
    """Lifecycle status of a transaction."""

    PENDING = "pending"  # Transaction submitted but not confirmed
    CONFIRMING = (
        "confirming"  # Transaction included in a block but waiting for confirmations
    )
    CONFIRMED = "confirmed"  # Transaction confirmed with sufficient block confirmations
    FAILED = "failed"  # Transaction execution failed
    DROPPED = "dropped"  # Transaction dropped from mempool/replaced
    BUNDLE_PENDING = "bundle_pending"  # Flashbots bundle submitted but not included
    BUNDLE_SIMULATED = (
        "bundle_simulated"  # Bundle simulated successfully but not submitted
    )
    BUNDLE_REJECTED = "bundle_rejected"  # Bundle rejected by block builders
    BUNDLE_INCLUDED = "bundle_included"  # Bundle included in a block
    BUNDLE_FAILED = "bundle_failed"  # Bundle included but execution failed


@dataclass
class TransactionRecord:
    """Complete record of an arbitrage transaction."""

    # Identifiers
    tx_hash: str  # Transaction hash
    opportunity_id: Optional[str] = None  # Related opportunity ID

    # Transaction details
    from_address: Optional[str] = None  # Sender address
    to_address: Optional[str] = None  # Target contract
    value: int = 0  # ETH value in wei
    gas_price: int = 0  # Gas price in wei
    gas_limit: int = 0  # Gas limit
    nonce: Optional[int] = None  # Transaction nonce
    data: Optional[str] = None  # Transaction data

    # Lifecycle status
    status: TransactionStatus = TransactionStatus.PENDING
    submission_timestamp: float = field(
        default_factory=time.time
    )  # When tx was submitted
    block_number: Optional[int] = None  # Block number if confirmed
    block_timestamp: Optional[int] = None  # Block timestamp if confirmed
    confirmation_timestamp: Optional[float] = None  # When we detected confirmation
    confirmation_blocks: int = 0  # Confirmation block count
    required_confirmations: int = 12  # Required confirmations to consider final

    # Execution results
    gas_used: Optional[int] = None  # Actual gas used
    effective_gas_price: Optional[int] = None  # Effective gas price paid
    success: Optional[bool] = None  # Execution success
    error: Optional[str] = None  # Error message if failed

    # Bundle information (for Flashbots)
    bundle_id: Optional[str] = None  # Bundle ID if part of Flashbots bundle
    bundle_transactions: List[str] = field(default_factory=list)  # Other txs in bundle
    bundle_target_block: Optional[int] = None  # Target block number
    bundle_submission_count: int = 0  # Number of times bundle was submitted

    # Financial outcomes
    expected_profit: Optional[int] = None  # Expected profit in wei
    actual_profit: Optional[int] = None  # Actual profit in wei
    profit_accuracy: Optional[float] = None  # Profit prediction accuracy

    # Tags and metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransactionRecord":
        """Create instance from dictionary."""
        # Convert string status to enum
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TransactionStatus(data["status"])
        return cls(**data)

    def calculate_profit_accuracy(self) -> float:
        """Calculate accuracy of profit prediction."""
        if self.expected_profit is None or self.actual_profit is None:
            return 0.0

        # Avoid division by zero
        if self.expected_profit == 0:
            return 1.0 if self.actual_profit == 0 else 0.0

        # Calculate accuracy (1.0 = 100% accurate)
        accuracy = 1.0 - min(
            1.0,
            abs(self.actual_profit - self.expected_profit) / abs(self.expected_profit),
        )
        self.profit_accuracy = accuracy
        return accuracy


class TransactionLifecycleMonitor:
    """
    Monitors transactions throughout their lifecycle.

    Tracks transactions from submission to confirmation, analyzes results,
    and provides insights into transaction performance and success rates.
    """

    def __init__(
        self,
        event_emitter: EventEmitter,
        web3_manager,  # Avoiding circular import
        confirmations_required: int = 12,
        polling_interval: int = 15,
        max_track_transactions: int = 1000,
    ):
        """
        Initialize transaction lifecycle monitor.

        Args:
            event_emitter: EventEmitter instance
            web3_manager: Web3Manager instance for blockchain interaction
            confirmations_required: Required confirmations for finality
            polling_interval: Block polling interval in seconds
            max_track_transactions: Maximum transactions to track
        """
        self.event_emitter = event_emitter
        self.web3_manager = web3_manager
        self.confirmations_required = confirmations_required
        self.polling_interval = polling_interval
        self.max_track_transactions = max_track_transactions

        # Transaction tracking
        self._transactions: Dict[str, TransactionRecord] = {}
        self._pending_transactions: Set[str] = set()
        self._pending_bundles: Dict[str, List[str]] = {}  # bundle_id -> [tx_hash, ...]

        # Statistics
        self._success_count = 0
        self._fail_count = 0
        self._total_gas_used = 0
        self._profit_accuracy_sum = 0.0
        self._profit_accuracy_count = 0

        # Control flags
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._monitor_task = None
        self._lock = asyncio.Lock()

        logger.info("Initialized transaction lifecycle monitor")

    async def start(self) -> bool:
        """
        Start transaction monitoring.

        Returns:
            True if started successfully
        """
        async with self._lock:
            if self._running:
                logger.warning("Transaction monitor already running")
                return False

            logger.info("Starting transaction lifecycle monitor")
            self._running = True
            self._shutdown_event.clear()

            # Register event handlers
            await self._register_event_handlers()

            # Start monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_loop())

            return True

    async def stop(self) -> bool:
        """
        Stop transaction monitoring.

        Returns:
            True if stopped successfully
        """
        async with self._lock:
            if not self._running:
                logger.warning("Transaction monitor not running")
                return False

            logger.info("Stopping transaction lifecycle monitor")
            self._running = False
            self._shutdown_event.set()

            # Unregister event handlers
            await self._unregister_event_handlers()

            # Wait for monitoring task to complete
            if self._monitor_task:
                try:
                    await asyncio.wait_for(self._monitor_task, 10)
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for monitoring task to complete")
                self._monitor_task = None

            return True

    async def _register_event_handlers(self) -> None:
        """Register event handlers."""
        # Transaction submission handler
        await self.event_emitter.on(
            "transaction:submitted", self._handle_transaction_submitted
        )

        # Bundle submission handler
        await self.event_emitter.on(
            "flashbots:bundle_submitted", self._handle_bundle_submitted
        )

        # Bundle included handler
        await self.event_emitter.on(
            "flashbots:bundle_included", self._handle_bundle_included
        )

        # Bundle simulation results
        await self.event_emitter.on(
            "flashbots:bundle_simulated", self._handle_bundle_simulated
        )

    async def _unregister_event_handlers(self) -> None:
        """Unregister event handlers."""
        await self.event_emitter.off(
            "transaction:submitted", self._handle_transaction_submitted
        )
        await self.event_emitter.off(
            "flashbots:bundle_submitted", self._handle_bundle_submitted
        )
        await self.event_emitter.off(
            "flashbots:bundle_included", self._handle_bundle_included
        )
        await self.event_emitter.off(
            "flashbots:bundle_simulated", self._handle_bundle_simulated
        )

    async def _handle_transaction_submitted(self, event: Event[Any]) -> None:
        """
        Handle transaction submission event.

        Args:
            event: Event with transaction data
        """
        try:
            data = event.data
            if not isinstance(data, dict):
                return

            tx_hash = data.get("tx_hash")
            if not tx_hash:
                return

            # Create or update transaction record
            await self.track_transaction(
                tx_hash=tx_hash,
                opportunity_id=data.get("opportunity_id"),
                from_address=data.get("from"),
                to_address=data.get("to"),
                value=data.get("value", 0),
                gas_price=data.get("gas_price", 0),
                gas_limit=data.get("gas", 0),
                nonce=data.get("nonce"),
                data=data.get("data"),
                expected_profit=data.get("expected_profit"),
                bundle_id=data.get("bundle_id"),
            )

        except Exception as e:
            logger.error(f"Error handling transaction submitted event: {e}")

    async def _handle_bundle_submitted(self, event: Event[Any]) -> None:
        """
        Handle Flashbots bundle submission event.

        Args:
            event: Event with bundle data
        """
        try:
            data = event.data
            if not isinstance(data, dict):
                return

            bundle_id = data.get("bundle_id")
            tx_hashes = data.get("tx_hashes", [])
            target_block = data.get("target_block")

            if not bundle_id or not tx_hashes:
                return

            # Track bundle
            self._pending_bundles[bundle_id] = tx_hashes

            # Update transaction records
            for tx_hash in tx_hashes:
                if tx_hash in self._transactions:
                    tx_record = self._transactions[tx_hash]
                    tx_record.bundle_id = bundle_id
                    tx_record.bundle_transactions = [
                        h for h in tx_hashes if h != tx_hash
                    ]
                    tx_record.bundle_target_block = target_block
                    tx_record.bundle_submission_count += 1
                    tx_record.status = TransactionStatus.BUNDLE_PENDING
                else:
                    # Create minimal record for unknown transaction
                    await self.track_transaction(
                        tx_hash=tx_hash,
                        bundle_id=bundle_id,
                        bundle_transactions=tx_hashes,
                        bundle_target_block=target_block,
                        status=TransactionStatus.BUNDLE_PENDING,
                    )

        except Exception as e:
            logger.error(f"Error handling bundle submitted event: {e}")

    async def _handle_bundle_included(self, event: Event[Any]) -> None:
        """
        Handle Flashbots bundle inclusion event.

        Args:
            event: Event with bundle inclusion data
        """
        try:
            data = event.data
            if not isinstance(data, dict):
                return

            bundle_id = data.get("bundle_id")
            tx_hashes = data.get("tx_hashes", [])
            block_number = data.get("block_number")

            if not bundle_id or not tx_hashes:
                return

            # Update transaction records
            for tx_hash in tx_hashes:
                if tx_hash in self._transactions:
                    tx_record = self._transactions[tx_hash]
                    tx_record.bundle_id = bundle_id
                    tx_record.block_number = block_number
                    tx_record.status = TransactionStatus.BUNDLE_INCLUDED

                    # Add to pending list for detailed receipt fetching
                    self._pending_transactions.add(tx_hash)

            # Remove from pending bundles
            if bundle_id in self._pending_bundles:
                del self._pending_bundles[bundle_id]

        except Exception as e:
            logger.error(f"Error handling bundle included event: {e}")

    async def _handle_bundle_simulated(self, event: Event[Any]) -> None:
        """
        Handle Flashbots bundle simulation event.

        Args:
            event: Event with bundle simulation data
        """
        try:
            data = event.data
            if not isinstance(data, dict):
                return

            bundle_id = data.get("bundle_id")
            tx_hashes = data.get("tx_hashes", [])
            success = data.get("success", False)
            simulation_results = data.get("results", {})

            if not bundle_id or not tx_hashes:
                return

            # Update transaction records
            for tx_hash in tx_hashes:
                if tx_hash in self._transactions:
                    tx_record = self._transactions[tx_hash]
                    tx_record.bundle_id = bundle_id

                    # Get transaction-specific results
                    tx_result = next(
                        (
                            r
                            for r in simulation_results.get("results", [])
                            if r.get("txHash") == tx_hash
                        ),
                        {},
                    )

                    if success:
                        tx_record.status = TransactionStatus.BUNDLE_SIMULATED
                        tx_record.gas_used = tx_result.get("gasUsed")
                    else:
                        tx_record.status = TransactionStatus.BUNDLE_FAILED
                        tx_record.error = tx_result.get(
                            "error"
                        ) or simulation_results.get("error")

        except Exception as e:
            logger.error(f"Error handling bundle simulation event: {e}")

    async def track_transaction(
        self,
        tx_hash: str,
        opportunity_id: Optional[str] = None,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        value: Optional[int] = None,
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None,
        nonce: Optional[int] = None,
        data: Optional[str] = None,
        expected_profit: Optional[int] = None,
        status: Optional[Union[str, TransactionStatus]] = None,
        bundle_id: Optional[str] = None,
        bundle_transactions: Optional[List[str]] = None,
        bundle_target_block: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TransactionRecord:
        """
        Start tracking a transaction.

        Args:
            tx_hash: Transaction hash
            opportunity_id: Associated opportunity ID
            from_address: Sender address
            to_address: Recipient address
            value: ETH value in wei
            gas_price: Gas price in wei
            gas_limit: Gas limit
            nonce: Transaction nonce
            data: Transaction data
            expected_profit: Expected profit in wei
            status: Initial status
            bundle_id: Flashbots bundle ID
            bundle_transactions: Other transactions in bundle
            bundle_target_block: Target block for bundle
            metadata: Additional metadata

        Returns:
            The created or updated transaction record
        """
        async with self._lock:
            # Check if already tracking
            if tx_hash in self._transactions:
                # Update existing record with new information
                record = self._transactions[tx_hash]

                if opportunity_id is not None:
                    record.opportunity_id = opportunity_id
                if from_address is not None:
                    record.from_address = from_address
                if to_address is not None:
                    record.to_address = to_address
                if value is not None:
                    record.value = value
                if gas_price is not None:
                    record.gas_price = gas_price
                if gas_limit is not None:
                    record.gas_limit = gas_limit
                if nonce is not None:
                    record.nonce = nonce
                if data is not None:
                    record.data = data
                if expected_profit is not None:
                    record.expected_profit = expected_profit
                if status is not None:
                    record.status = (
                        TransactionStatus(status) if isinstance(status, str) else status
                    )
                if bundle_id is not None:
                    record.bundle_id = bundle_id
                if bundle_transactions is not None:
                    record.bundle_transactions = bundle_transactions
                if bundle_target_block is not None:
                    record.bundle_target_block = bundle_target_block
                if metadata is not None:
                    record.metadata.update(metadata)
            else:
                # Create new record
                record = TransactionRecord(
                    tx_hash=tx_hash,
                    opportunity_id=opportunity_id,
                    from_address=from_address,
                    to_address=to_address,
                    value=value or 0,
                    gas_price=gas_price or 0,
                    gas_limit=gas_limit or 0,
                    nonce=nonce,
                    data=data,
                    expected_profit=expected_profit,
                    status=(
                        TransactionStatus(status)
                        if isinstance(status, str)
                        else (status or TransactionStatus.PENDING)
                    ),
                    bundle_id=bundle_id,
                    bundle_transactions=bundle_transactions or [],
                    bundle_target_block=bundle_target_block,
                    metadata=metadata or {},
                )

                self._transactions[tx_hash] = record

                # Add to pending set for monitoring
                if record.status in [
                    TransactionStatus.PENDING,
                    TransactionStatus.BUNDLE_PENDING,
                ]:
                    self._pending_transactions.add(tx_hash)

                # Track bundle if needed
                if bundle_id and bundle_id not in self._pending_bundles:
                    self._pending_bundles[bundle_id] = [tx_hash]
                elif bundle_id:
                    self._pending_bundles[bundle_id].append(tx_hash)

                # Trim transaction list if needed
                if len(self._transactions) > self.max_track_transactions:
                    self._trim_transactions()

            # Emit event for the transaction record
            await self.event_emitter.emit(
                "transaction:tracking", record.to_dict(), source="transaction_monitor"
            )

            return record

    async def update_transaction_status(
        self,
        tx_hash: str,
        status: Union[str, TransactionStatus],
        block_number: Optional[int] = None,
        gas_used: Optional[int] = None,
        success: Optional[bool] = None,
        error: Optional[str] = None,
        actual_profit: Optional[int] = None,
    ) -> Optional[TransactionRecord]:
        """
        Update transaction status.

        Args:
            tx_hash: Transaction hash
            status: New status
            block_number: Block number for confirmed transactions
            gas_used: Gas used by transaction
            success: Transaction success flag
            error: Error message if failed
            actual_profit: Actual profit achieved

        Returns:
            Updated transaction record or None if not found
        """
        async with self._lock:
            if tx_hash not in self._transactions:
                logger.warning(f"Attempted to update unknown transaction: {tx_hash}")
                return None

            record = self._transactions[tx_hash]

            # Update status
            old_status = record.status
            record.status = (
                TransactionStatus(status) if isinstance(status, str) else status
            )

            # Update other fields
            if block_number is not None:
                record.block_number = block_number

            if gas_used is not None:
                record.gas_used = gas_used

            if success is not None:
                record.success = success

            if error is not None:
                record.error = error

            if actual_profit is not None:
                record.actual_profit = actual_profit
                # Calculate profit accuracy
                record.calculate_profit_accuracy()

            # Update timestamps for confirmed transactions
            if (
                record.status == TransactionStatus.CONFIRMED
                and old_status != TransactionStatus.CONFIRMED
            ):
                record.confirmation_timestamp = time.time()

                # Update statistics
                if record.success:
                    self._success_count += 1
                else:
                    self._fail_count += 1

                if record.gas_used:
                    self._total_gas_used += record.gas_used

                if record.profit_accuracy is not None:
                    self._profit_accuracy_sum += record.profit_accuracy
                    self._profit_accuracy_count += 1

                # Remove from pending transactions
                if tx_hash in self._pending_transactions:
                    self._pending_transactions.remove(tx_hash)

                # Emit event for transaction completion
                await self.event_emitter.emit(
                    "transaction:completed",
                    record.to_dict(),
                    source="transaction_monitor",
                )

            # Emit event for status update
            await self.event_emitter.emit(
                "transaction:status_updated",
                {
                    "tx_hash": tx_hash,
                    "old_status": old_status,
                    "new_status": record.status,
                    "timestamp": time.time(),
                },
                source="transaction_monitor",
            )

            return record

    def _trim_transactions(self) -> None:
        """Trim transaction list to maximum size."""
        # Keep all pending transactions
        pending = {
            tx_hash: record
            for tx_hash, record in self._transactions.items()
            if tx_hash in self._pending_transactions
        }

        # For non-pending, sort by timestamp and keep newest
        non_pending = {
            tx_hash: record
            for tx_hash, record in self._transactions.items()
            if tx_hash not in self._pending_transactions
        }

        sorted_transactions = sorted(
            non_pending.items(), key=lambda x: x[1].submission_timestamp, reverse=True
        )

        # Calculate how many we can keep
        keep_count = min(
            len(sorted_transactions), self.max_track_transactions - len(pending)
        )

        # Update transactions dict
        self._transactions = pending.copy()
        for i in range(keep_count):
            tx_hash, record = sorted_transactions[i]
            self._transactions[tx_hash] = record

    async def _monitor_loop(self) -> None:
        """Main monitoring loop for transaction status updates."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Check pending transaction status
                    await self._check_pending_transactions()

                    # Check pending bundles
                    await self._check_pending_bundles()

                    # Wait for next interval or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(), timeout=self.polling_interval
                        )
                    except asyncio.TimeoutError:
                        # Normal timeout, continue polling
                        pass

                except Exception as e:
                    logger.error(f"Error in transaction monitor loop: {e}")
                    await asyncio.sleep(5)  # Brief delay on error

        except asyncio.CancelledError:
            logger.info("Transaction monitor task cancelled")
            raise

        except Exception as e:
            logger.error(f"Unexpected error in transaction monitor: {e}")

    async def _check_pending_transactions(self) -> None:
        """Check status of pending transactions."""
        if not self._pending_transactions:
            return

        # Get current block for confirmation count
        try:
            current_block = await self.web3_manager.w3.eth.block_number
        except Exception as e:
            logger.error(f"Error getting current block number: {e}")
            return

        # Process transactions in batches to avoid overloading the node
        batch_size = 10
        pending_list = list(self._pending_transactions)

        for i in range(0, len(pending_list), batch_size):
            batch = pending_list[i : i + batch_size]

            for tx_hash in batch:
                try:
                    # Skip if transaction is no longer in pending list
                    if tx_hash not in self._pending_transactions:
                        continue

                    # Get transaction receipt
                    receipt = await self.web3_manager.w3.eth.get_transaction_receipt(
                        tx_hash
                    )

                    if receipt:
                        # Transaction is mined
                        block_number = receipt.blockNumber
                        confirmations = current_block - block_number + 1

                        record = self._transactions[tx_hash]
                        record.block_number = block_number
                        record.gas_used = receipt.gasUsed
                        record.effective_gas_price = receipt.effectiveGasPrice
                        record.success = receipt.status == 1
                        record.confirmation_blocks = confirmations

                        # Get block timestamp
                        try:
                            block = await self.web3_manager.w3.eth.get_block(
                                block_number
                            )
                            record.block_timestamp = block.timestamp
                        except Exception as e:
                            logger.error(f"Error getting block timestamp: {e}")

                        # Update status based on confirmations
                        if confirmations >= self.confirmations_required:
                            await self.update_transaction_status(
                                tx_hash=tx_hash,
                                status=TransactionStatus.CONFIRMED,
                                block_number=block_number,
                                gas_used=receipt.gasUsed,
                                success=(receipt.status == 1),
                            )
                        else:
                            record.status = TransactionStatus.CONFIRMING

                except Exception as e:
                    logger.error(
                        f"Error checking transaction status for {tx_hash}: {e}"
                    )

    async def _check_pending_bundles(self) -> None:
        """Check status of pending Flashbots bundles."""
        if not self._pending_bundles:
            return

        # Get current block
        try:
            current_block = await self.web3_manager.w3.eth.block_number
        except Exception as e:
            logger.error(f"Error getting current block number: {e}")
            return

        # Process each pending bundle
        for bundle_id, tx_hashes in list(self._pending_bundles.items()):
            # Check if we're still tracking this bundle
            if bundle_id not in self._pending_bundles:
                continue

            # Check the target block - if we're past it, the bundle likely failed
            target_block = None
            for tx_hash in tx_hashes:
                if tx_hash in self._transactions:
                    target_block = self._transactions[tx_hash].bundle_target_block
                    break

            if target_block and current_block > target_block + 2:
                # Bundle likely missed the target blocks
                logger.info(
                    f"Bundle {bundle_id} missed target block {target_block}, current block {current_block}"
                )

                # Update status for all transactions
                for tx_hash in tx_hashes:
                    if tx_hash in self._transactions:
                        await self.update_transaction_status(
                            tx_hash=tx_hash,
                            status=TransactionStatus.BUNDLE_REJECTED,
                            error="Bundle missed target block",
                        )

                # Remove from pending bundles
                del self._pending_bundles[bundle_id]

    def get_transaction(self, tx_hash: str) -> Optional[TransactionRecord]:
        """
        Get transaction record by hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction record or None if not found
        """
        return self._transactions.get(tx_hash)

    def get_transactions(
        self,
        status: Optional[Union[str, TransactionStatus]] = None,
        bundle_id: Optional[str] = None,
        opportunity_id: Optional[str] = None,
        min_submission_time: Optional[float] = None,
        max_submission_time: Optional[float] = None,
        count: int = 100,
        include_pending: bool = True,
    ) -> List[TransactionRecord]:
        """
        Get transactions with optional filtering.

        Args:
            status: Filter by status
            bundle_id: Filter by bundle ID
            opportunity_id: Filter by opportunity ID
            min_submission_time: Minimum submission timestamp
            max_submission_time: Maximum submission timestamp
            count: Maximum records to return
            include_pending: Whether to include pending transactions

        Returns:
            List of matching transaction records
        """
        results = []

        # Convert string status to enum if needed
        status_enum = None
        if status:
            status_enum = (
                TransactionStatus(status) if isinstance(status, str) else status
            )

        # Filter transactions
        for record in self._transactions.values():
            # Skip pending if not requested
            if not include_pending and record.tx_hash in self._pending_transactions:
                continue

            # Apply filters
            if status_enum and record.status != status_enum:
                continue

            if bundle_id and record.bundle_id != bundle_id:
                continue

            if opportunity_id and record.opportunity_id != opportunity_id:
                continue

            if (
                min_submission_time
                and record.submission_timestamp < min_submission_time
            ):
                continue

            if (
                max_submission_time
                and record.submission_timestamp > max_submission_time
            ):
                continue

            results.append(record)

        # Sort by submission time (newest first)
        results.sort(key=lambda r: r.submission_timestamp, reverse=True)

        # Return requested count
        return results[:count]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get transaction monitoring statistics.

        Returns:
            Dictionary of statistics
        """
        # Calculate success rate
        total_completed = self._success_count + self._fail_count
        success_rate = (
            self._success_count / total_completed if total_completed > 0 else 0
        )

        # Calculate average profit accuracy
        avg_profit_accuracy = (
            self._profit_accuracy_sum / self._profit_accuracy_count
            if self._profit_accuracy_count > 0
            else 0
        )

        return {
            "tracked_transactions": len(self._transactions),
            "pending_transactions": len(self._pending_transactions),
            "pending_bundles": len(self._pending_bundles),
            "successful_transactions": self._success_count,
            "failed_transactions": self._fail_count,
            "success_rate": success_rate,
            "total_gas_used": self._total_gas_used,
            "avg_profit_accuracy": avg_profit_accuracy,
            "profit_accuracy_samples": self._profit_accuracy_count,
        }


async def create_transaction_monitor(
    event_emitter: EventEmitter, web3_manager
) -> TransactionLifecycleMonitor:
    """
    Create and initialize a transaction lifecycle monitor.

    Args:
        event_emitter: EventEmitter instance
        web3_manager: Web3Manager instance

    Returns:
        Initialized TransactionLifecycleMonitor
    """
    monitor = TransactionLifecycleMonitor(event_emitter, web3_manager)
    await monitor.start()
    return monitor
