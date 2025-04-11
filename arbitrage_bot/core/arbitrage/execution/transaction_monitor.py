"""
Transaction Monitor

This module contains the implementation of the TransactionMonitor,
which is responsible for monitoring and tracking transaction status.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, Tuple

from ...web3.interfaces import Web3Client, TransactionReceipt
from ..interfaces import TransactionMonitor as TransactionMonitorInterface
from ..models import ArbitrageOpportunity, TransactionInfo

logger = logging.getLogger(__name__)


class TransactionMonitor(TransactionMonitorInterface):
    """
    Transaction Monitor for tracking blockchain transactions.

    This monitor tracks the status of arbitrage transactions,
    provides updates, and handles timeouts and retries.
    """

    def __init__(self, web3_client: Web3Client, config: Dict[str, Any] = None):
        """
        Initialize the transaction monitor.

        Args:
            web3_client: Web3 client for blockchain interactions
            config: Configuration dictionary
        """
        self.web3_client = web3_client
        self.config = config or {}

        # Configuration
        self.poll_interval = float(self.config.get("poll_interval", 2.0))  # 2 seconds
        self.max_attempts = int(
            self.config.get("max_attempts", 30)
        )  # 30 attempts (60 seconds with default poll)
        self.confirmation_blocks = int(
            self.config.get("confirmation_blocks", 1)
        )  # Number of blocks to consider confirmed

        # Transaction tracking
        self._monitored_transactions: Dict[str, TransactionInfo] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._transaction_lock = asyncio.Lock()

        logger.info("TransactionMonitor initialized")

    async def monitor_transaction(
        self,
        transaction_hash: str,
        opportunity: Optional[ArbitrageOpportunity] = None,
        **kwargs,
    ) -> Optional[TransactionInfo]:
        """
        Monitor a transaction until it completes or times out.

        Args:
            transaction_hash: Hash of the transaction to monitor
            opportunity: Optional opportunity associated with the transaction
            **kwargs: Additional monitoring parameters

        Returns:
            Updated transaction info or None if monitoring failed
        """
        logger.info(f"Starting to monitor transaction: {transaction_hash}")

        # Extract monitoring parameters
        wait_for_confirmations = kwargs.get("wait_for_confirmations", True)
        timeout = float(kwargs.get("timeout", self.poll_interval * self.max_attempts))

        # Check if already monitoring this transaction
        async with self._transaction_lock:
            if transaction_hash in self._monitored_transactions:
                logger.info(
                    f"Transaction {transaction_hash} is already being monitored"
                )
                return self._monitored_transactions[transaction_hash]

            # Create initial transaction info if not provided
            if transaction_hash not in self._monitored_transactions:
                self._monitored_transactions[transaction_hash] = TransactionInfo(
                    transaction_hash=transaction_hash,
                    from_address=None,
                    to_address=None,
                    data=None,
                    value=None,
                    gas_limit=None,
                    gas_price=None,
                    max_fee_per_gas=None,
                    priority_fee=None,
                    nonce=None,
                    status=None,
                    gas_used=None,
                    effective_gas_price=None,
                    block_number=None,
                    timestamp=int(time.time()),
                    error_message=None,
                )

            # Create monitoring task if not already running
            if (
                transaction_hash not in self._monitoring_tasks
                or self._monitoring_tasks[transaction_hash].done()
            ):
                self._monitoring_tasks[transaction_hash] = asyncio.create_task(
                    self._monitor_transaction_task(
                        transaction_hash=transaction_hash,
                        wait_for_confirmations=wait_for_confirmations,
                        timeout=timeout,
                    )
                )

        try:
            # Wait for monitoring to complete or timeout
            await asyncio.wait_for(
                self._monitoring_tasks[transaction_hash], timeout=timeout
            )

        except asyncio.TimeoutError:
            logger.warning(f"Monitoring of transaction {transaction_hash} timed out")

            # Update transaction info with timeout
            async with self._transaction_lock:
                tx_info = self._monitored_transactions[transaction_hash]
                tx_info.error_message = "Monitoring timed out"

        except Exception as e:
            logger.error(f"Error monitoring transaction {transaction_hash}: {e}")

            # Update transaction info with error
            async with self._transaction_lock:
                tx_info = self._monitored_transactions[transaction_hash]
                tx_info.error_message = f"Monitoring error: {e}"

        # Return the current transaction info
        async with self._transaction_lock:
            return self._monitored_transactions.get(transaction_hash)

    async def _monitor_transaction_task(
        self, transaction_hash: str, wait_for_confirmations: bool, timeout: float
    ) -> None:
        """
        Internal task to monitor a transaction.

        Args:
            transaction_hash: Hash of the transaction to monitor
            wait_for_confirmations: Whether to wait for confirmations
            timeout: Monitoring timeout in seconds
        """
        try:
            attempts = 0
            last_block_number = None

            while attempts < self.max_attempts:
                try:
                    # Get transaction receipt
                    receipt = await self.web3_client.get_transaction_receipt(
                        transaction_hash
                    )

                    if receipt:
                        # Update transaction info with receipt data
                        await self._update_transaction_info(transaction_hash, receipt)

                        # If not waiting for confirmations, we're done
                        if not wait_for_confirmations:
                            logger.info(
                                f"Transaction {transaction_hash} received receipt and not waiting for confirmations"
                            )
                            return

                        # Check if we have enough confirmations
                        current_block_number = await self.web3_client.get_block_number()
                        confirmations = 0

                        if receipt.block_number and current_block_number:
                            confirmations = current_block_number - receipt.block_number

                        if confirmations >= self.confirmation_blocks:
                            logger.info(
                                f"Transaction {transaction_hash} confirmed with "
                                f"{confirmations} confirmations"
                            )
                            return

                        # Track last seen block number to detect chain reorgs
                        if last_block_number and receipt.block_number:
                            if receipt.block_number < last_block_number:
                                logger.warning(
                                    f"Possible chain reorganization detected for "
                                    f"transaction {transaction_hash}: "
                                    f"block {receipt.block_number} < {last_block_number}"
                                )

                        last_block_number = receipt.block_number

                        # Wait for next poll with reduced interval for confirmations
                        await asyncio.sleep(self.poll_interval * 0.5)
                    else:
                        # Transaction not mined yet
                        logger.debug(
                            f"Transaction {transaction_hash} not mined yet, attempt {attempts+1}/{self.max_attempts}"
                        )
                        attempts += 1
                        await asyncio.sleep(self.poll_interval)

                except Exception as e:
                    logger.error(
                        f"Error checking transaction {transaction_hash} status: {e}"
                    )
                    attempts += 1
                    await asyncio.sleep(self.poll_interval)

            # If we get here, we've exceeded max attempts
            logger.warning(
                f"Transaction {transaction_hash} monitoring exceeded max attempts"
            )

            # Update transaction info with timeout
            async with self._transaction_lock:
                tx_info = self._monitored_transactions[transaction_hash]
                tx_info.error_message = "Monitoring exceeded max attempts"

        except Exception as e:
            logger.error(
                f"Error in monitor_transaction_task for {transaction_hash}: {e}"
            )

            # Update transaction info with error
            async with self._transaction_lock:
                tx_info = self._monitored_transactions[transaction_hash]
                tx_info.error_message = f"Monitoring task error: {e}"

    async def _update_transaction_info(
        self, transaction_hash: str, receipt: TransactionReceipt
    ) -> None:
        """
        Update transaction info with receipt data.

        Args:
            transaction_hash: Hash of the transaction
            receipt: Transaction receipt
        """
        async with self._transaction_lock:
            # Get current transaction info
            tx_info = self._monitored_transactions[transaction_hash]

            # Update with receipt data
            tx_info.status = receipt.status
            tx_info.gas_used = receipt.gas_used
            tx_info.effective_gas_price = receipt.effective_gas_price
            tx_info.block_number = receipt.block_number

            # Add error message if transaction failed
            if not receipt.status:
                tx_info.error_message = "Transaction reverted"
                logger.warning(f"Transaction {transaction_hash} reverted")
            else:
                logger.info(
                    f"Transaction {transaction_hash} succeeded in block {receipt.block_number}"
                )

    async def get_transaction_info(
        self, transaction_hash: str
    ) -> Optional[TransactionInfo]:
        """
        Get the current info for a monitored transaction.

        Args:
            transaction_hash: Hash of the transaction

        Returns:
            Transaction info or None if not monitored
        """
        async with self._transaction_lock:
            return self._monitored_transactions.get(transaction_hash)

    async def get_monitored_transactions(self) -> List[str]:
        """
        Get the list of transaction hashes being monitored.

        Returns:
            List of transaction hashes
        """
        async with self._transaction_lock:
            return list(self._monitored_transactions.keys())

    async def stop_monitoring(self, transaction_hash: str) -> bool:
        """
        Stop monitoring a transaction.

        Args:
            transaction_hash: Hash of the transaction to stop monitoring

        Returns:
            True if monitoring was stopped, False if not found
        """
        async with self._transaction_lock:
            if transaction_hash in self._monitoring_tasks:
                # Cancel the monitoring task
                self._monitoring_tasks[transaction_hash].cancel()
                del self._monitoring_tasks[transaction_hash]

                # Remove from monitored transactions
                if transaction_hash in self._monitored_transactions:
                    del self._monitored_transactions[transaction_hash]

                logger.info(f"Stopped monitoring transaction {transaction_hash}")
                return True
            else:
                logger.warning(f"Transaction {transaction_hash} not being monitored")
                return False

    async def close(self) -> None:
        """Close the transaction monitor and release resources."""
        logger.info("Closing TransactionMonitor")

        # Cancel all monitoring tasks
        async with self._transaction_lock:
            for tx_hash, task in self._monitoring_tasks.items():
                logger.info(f"Cancelling monitoring task for transaction {tx_hash}")
                task.cancel()

            self._monitoring_tasks.clear()
            self._monitored_transactions.clear()


async def create_transaction_monitor(
    web3_client: Web3Client, config: Dict[str, Any] = None
) -> TransactionMonitor:
    """
    Factory function to create a transaction monitor.

    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration dictionary

    Returns:
        Initialized transaction monitor
    """
    return TransactionMonitor(web3_client=web3_client, config=config)
