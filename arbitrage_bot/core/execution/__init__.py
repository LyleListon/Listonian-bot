"""Execution system for managing trade execution across DEXes."""

from typing import Dict, List, Optional, NamedTuple, Tuple
from dataclasses import dataclass
from decimal import Decimal
import json
import time
import asyncio
from web3 import Web3
from eth_typing import HexStr
from ..storage.factory import create_storage_hub
from ..memory import MemoryBank
from ..distribution import DistributionManager

@dataclass
class ExecutionConfig:
    """Configuration for execution system."""
    max_slippage: Decimal  # Maximum allowed slippage
    gas_limit: int  # Gas limit for transactions
    max_gas_price: Decimal  # Maximum gas price to pay
    retry_attempts: int  # Number of retry attempts
    retry_delay: int  # Delay between retries in seconds
    confirmation_blocks: int  # Number of blocks to wait for confirmation
    timeout: int  # Transaction timeout in seconds

class TransactionStatus(NamedTuple):
    """Status information for a transaction."""
    status: str  # pending, submitted, confirmed, failed
    hash: Optional[HexStr]  # Transaction hash
    block_number: Optional[int]  # Block number of confirmation
    gas_used: Optional[int]  # Gas used by transaction
    gas_price: Optional[int]  # Gas price used
    error: Optional[str]  # Error message if failed

class ExecutionManager:
    """Manages trade execution across DEXes."""
    
    def __init__(self, config: ExecutionConfig, web3: Web3,
                 distribution_manager: DistributionManager,
                 memory_bank: Optional[MemoryBank] = None):
        """Initialize execution manager.
        
        Args:
            config: Execution configuration
            web3: Web3 instance for blockchain interaction
            distribution_manager: Distribution manager instance
            memory_bank: Optional memory bank for caching
        """
        self.config = config
        self.web3 = web3
        self.distribution_manager = distribution_manager
        self.memory_bank = memory_bank
        self.storage = create_storage_hub(memory_bank=memory_bank)
        
        # Track active executions
        self._active_executions: Dict[str, TransactionStatus] = {}
        
        # Initialize event loop for async operations
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
    
    async def execute_trade(self, trade_id: str, amount: Decimal,
                          pair: str) -> List[TransactionStatus]:
        """Execute a trade across DEXes.
        
        Args:
            trade_id: Unique identifier for the trade
            amount: Total amount to trade
            pair: Trading pair (e.g. "ETH/USDC")
            
        Returns:
            List of transaction statuses for each executed trade
        """
        # Get DEX allocations from distribution manager
        allocations = self.distribution_manager.get_dex_allocation(amount, pair)
        
        # Execute trades in parallel
        tasks = []
        for dex, alloc_amount in allocations:
            task = asyncio.create_task(
                self._execute_single_trade(trade_id, dex, alloc_amount, pair)
            )
            tasks.append(task)
        
        # Wait for all trades to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        statuses = []
        for i, result in enumerate(results):
            dex, _ = allocations[i]
            if isinstance(result, Exception):
                # Handle failed execution
                status = TransactionStatus(
                    status="failed",
                    hash=None,
                    block_number=None,
                    gas_used=None,
                    gas_price=None,
                    error=str(result)
                )
            else:
                status = result
            
            # Update distribution manager
            if status.status == "confirmed":
                self.distribution_manager.update_exposure(
                    dex=dex,
                    pair=pair,
                    amount=allocations[i][1]
                )
            
            statuses.append(status)
        
        return statuses
    
    async def _execute_single_trade(self, trade_id: str, dex: str,
                                  amount: Decimal, pair: str) -> TransactionStatus:
        """Execute a trade on a single DEX.
        
        Args:
            trade_id: Trade identifier
            dex: DEX to execute on
            amount: Amount to trade
            pair: Trading pair
            
        Returns:
            Transaction status
        """
        # Build transaction
        try:
            # TODO: Implement DEX-specific transaction building
            tx = {
                'from': self.web3.eth.default_account,
                'gas': self.config.gas_limit,
                'gasPrice': min(
                    self.web3.eth.gas_price,
                    int(self.config.max_gas_price * 10**9)
                ),
                'nonce': self.web3.eth.get_transaction_count(
                    self.web3.eth.default_account
                )
            }
            
            # Update status
            status = TransactionStatus(
                status="pending",
                hash=None,
                block_number=None,
                gas_used=None,
                gas_price=tx['gasPrice'],
                error=None
            )
            self._active_executions[trade_id] = status
            
            # Submit transaction
            # TODO: Implement actual transaction submission
            tx_hash = HexStr('0x0')  # Placeholder
            
            # Update status
            status = TransactionStatus(
                status="submitted",
                hash=tx_hash,
                block_number=None,
                gas_used=None,
                gas_price=tx['gasPrice'],
                error=None
            )
            self._active_executions[trade_id] = status
            
            # Wait for confirmation
            receipt = await self._wait_for_transaction(tx_hash)
            
            if receipt['status'] == 1:
                status = TransactionStatus(
                    status="confirmed",
                    hash=tx_hash,
                    block_number=receipt['blockNumber'],
                    gas_used=receipt['gasUsed'],
                    gas_price=tx['gasPrice'],
                    error=None
                )
            else:
                status = TransactionStatus(
                    status="failed",
                    hash=tx_hash,
                    block_number=receipt['blockNumber'],
                    gas_used=receipt['gasUsed'],
                    gas_price=tx['gasPrice'],
                    error="Transaction reverted"
                )
            
            self._active_executions[trade_id] = status
            return status
            
        except Exception as e:
            status = TransactionStatus(
                status="failed",
                hash=None,
                block_number=None,
                gas_used=None,
                gas_price=None,
                error=str(e)
            )
            self._active_executions[trade_id] = status
            return status
    
    async def _wait_for_transaction(self, tx_hash: HexStr) -> Dict:
        """Wait for transaction confirmation.
        
        Args:
            tx_hash: Transaction hash to wait for
            
        Returns:
            Transaction receipt
            
        Raises:
            TimeoutError: If transaction not confirmed within timeout
            Exception: If transaction fails
        """
        start_time = time.time()
        while True:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    return receipt
            except Exception:
                pass
            
            if time.time() - start_time > self.config.timeout:
                raise TimeoutError(f"Transaction {tx_hash.hex()} timed out")
            
            await asyncio.sleep(1)
    
    def get_execution_status(self, trade_id: str) -> Optional[TransactionStatus]:
        """Get status of a trade execution.
        
        Args:
            trade_id: Trade identifier
            
        Returns:
            Transaction status if found, None otherwise
        """
        return self._active_executions.get(trade_id)
    
    def get_active_executions(self) -> Dict[str, TransactionStatus]:
        """Get all active executions.
        
        Returns:
            Dictionary of trade ID to transaction status
        """
        return dict(self._active_executions)
    
    def clear_completed_executions(self) -> None:
        """Clear completed executions from tracking."""
        self._active_executions = {
            k: v for k, v in self._active_executions.items()
            if v.status in ["pending", "submitted"]
        }
