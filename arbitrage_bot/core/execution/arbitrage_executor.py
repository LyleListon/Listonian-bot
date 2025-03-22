"""
Enhanced Arbitrage Executor Module

This module orchestrates the execution of arbitrage opportunities with:
- Advanced error handling and recovery
- Performance monitoring
- State management
- Execution metrics collection
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, NamedTuple
from decimal import Decimal
from eth_typing import ChecksumAddress
from web3 import Web3

from ...utils.async_manager import AsyncLock, with_retry
from ..interfaces import Transaction, TokenPair, ExecutionResult
from ..market.enhanced_market_analyzer import EnhancedMarketAnalyzer, OpportunityScore
from ..unified_flash_loan_manager import EnhancedFlashLoanManager
from ..web3.flashbots.flashbots_provider import FlashbotsProvider
from ..memory.memory_bank import MemoryBank

logger = logging.getLogger(__name__)

class ExecutionMetrics(NamedTuple):
    """Detailed execution metrics."""
    preparation_time: float
    simulation_time: float
    execution_time: float
    total_gas_used: int
    actual_profit: int
    success_rate: float

class ExecutionState(NamedTuple):
    """Current execution state."""
    status: str
    current_step: str
    last_error: Optional[str]
    retry_count: int
    start_time: float

class EnhancedArbitrageExecutor:
    """Enhanced arbitrage execution with advanced monitoring and recovery."""

    def __init__(
        self,
        web3: Web3,
        market_analyzer: EnhancedMarketAnalyzer,
        flash_loan_manager: EnhancedFlashLoanManager,
        flashbots_provider: FlashbotsProvider,
        memory_bank: MemoryBank,
        max_retries: int = 3,
        execution_timeout: int = 30  # 30 seconds max execution time
    ):
        """Initialize the enhanced arbitrage executor."""
        self.web3 = web3
        self.market_analyzer = market_analyzer
        self.flash_loan_manager = flash_loan_manager
        self.flashbots_provider = flashbots_provider
        self.memory_bank = memory_bank
        
        # Configuration
        self.max_retries = max_retries
        self.execution_timeout = execution_timeout
        
        # Thread safety
        self._execution_lock = AsyncLock()
        self._metrics_lock = AsyncLock()
        
        # State management
        self._current_state: Optional[ExecutionState] = None
        self._execution_metrics: List[ExecutionMetrics] = []

    async def execute_opportunity(
        self,
        token_pair: TokenPair,
        opportunity: OpportunityScore
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.
        
        Args:
            token_pair: Token pair for the arbitrage
            opportunity: Scored opportunity details
            
        Returns:
            Execution result with metrics
        """
        async with self._execution_lock:
            start_time = time.time()
            self._current_state = ExecutionState(
                status="STARTING",
                current_step="INITIALIZATION",
                last_error=None,
                retry_count=0,
                start_time=start_time
            )
            
            try:
                # Validate token addresses
                if not self._validate_addresses(token_pair):
                    raise ValueError("Invalid token addresses")
                
                # Prepare execution
                self._update_state("PREPARING", "BUNDLE_PREPARATION")
                preparation_start = time.time()
                
                # Get current prices
                prices = await self.market_analyzer.fetch_dex_prices(token_pair)
                
                # Prepare flash loan bundle
                bundle = await self.flash_loan_manager.prepare_flash_loan_bundle(
                    token_pair,
                    opportunity.gas_cost_estimate,
                    prices
                )
                
                preparation_time = time.time() - preparation_start
                
                # Simulate execution
                self._update_state("SIMULATING", "BUNDLE_SIMULATION")
                simulation_start = time.time()
                
                simulation_result = await self.flashbots_provider.simulate_bundle(bundle)
                if not simulation_result['success']:
                    raise ValueError(f"Bundle simulation failed: {simulation_result['error']}")
                
                simulation_time = time.time() - simulation_start
                
                # Execute bundle
                self._update_state("EXECUTING", "BUNDLE_SUBMISSION")
                execution_start = time.time()
                
                bundle_hash = await self._execute_with_retry(bundle)
                
                execution_time = time.time() - execution_start
                
                # Wait for confirmation
                self._update_state("CONFIRMING", "TRANSACTION_CONFIRMATION")
                receipt = await self._wait_for_confirmation(bundle_hash)
                
                # Calculate metrics
                metrics = ExecutionMetrics(
                    preparation_time=preparation_time,
                    simulation_time=simulation_time,
                    execution_time=execution_time,
                    total_gas_used=receipt['gasUsed'],
                    actual_profit=simulation_result['profitability'],
                    success_rate=1.0
                )
                
                # Update metrics history
                await self._update_metrics(metrics)
                
                # Update memory bank
                await self._update_execution_history(token_pair, metrics, True)
                
                return ExecutionResult(
                    success=True,
                    profit=metrics.actual_profit,
                    gas_used=metrics.total_gas_used,
                    execution_time=metrics.execution_time
                )
                
            except Exception as e:
                logger.error(f"Arbitrage execution failed: {e}")
                
                # Update error metrics
                error_metrics = ExecutionMetrics(
                    preparation_time=time.time() - start_time,
                    simulation_time=0,
                    execution_time=0,
                    total_gas_used=0,
                    actual_profit=0,
                    success_rate=0
                )
                
                await self._update_metrics(error_metrics)
                await self._update_execution_history(token_pair, error_metrics, False)
                
                return ExecutionResult(
                    success=False,
                    profit=0,
                    gas_used=0,
                    execution_time=time.time() - start_time,
                    error=str(e)
                )
            
            finally:
                self._current_state = None

    def _validate_addresses(self, token_pair: TokenPair) -> bool:
        """Validate token addresses are properly checksummed."""
        try:
            return (
                self.web3.to_checksum_address(token_pair.token0) == token_pair.token0 and
                self.web3.to_checksum_address(token_pair.token1) == token_pair.token1
            )
        except ValueError:
            return False

    @with_retry(retries=3, delay=1.0)
    async def _execute_with_retry(self, bundle: List[Transaction]) -> str:
        """Execute bundle with retry logic."""
        try:
            return await self.flashbots_provider.send_bundle(bundle)
        except Exception as e:
            self._current_state = self._current_state._replace(
                last_error=str(e),
                retry_count=self._current_state.retry_count + 1
            )
            raise

    async def _wait_for_confirmation(self, bundle_hash: str) -> Dict:
        """Wait for transaction confirmation with timeout."""
        start_time = time.time()
        while time.time() - start_time < self.execution_timeout:
            try:
                receipt = await self.web3.eth.get_transaction_receipt(bundle_hash)
                if receipt:
                    return receipt
            except Exception as e:
                logger.warning(f"Error checking receipt: {e}")
            
            await asyncio.sleep(1)
        
        raise TimeoutError("Transaction confirmation timeout")

    async def _update_metrics(self, metrics: ExecutionMetrics):
        """Update execution metrics history."""
        async with self._metrics_lock:
            self._execution_metrics.append(metrics)
            
            # Keep only last 100 metrics
            if len(self._execution_metrics) > 100:
                self._execution_metrics = self._execution_metrics[-100:]

    async def _update_execution_history(
        self,
        token_pair: TokenPair,
        metrics: ExecutionMetrics,
        success: bool
    ):
        """Update execution history in memory bank."""
        await self.memory_bank.store_execution_result(
            token_pair=token_pair,
            success=success,
            profit=metrics.actual_profit,
            gas_used=metrics.total_gas_used,
            execution_time=metrics.execution_time
        )

    def _update_state(self, status: str, step: str):
        """Update current execution state."""
        if self._current_state:
            self._current_state = self._current_state._replace(
                status=status,
                current_step=step
            )

    async def get_execution_stats(self) -> Dict:
        """Get current execution statistics."""
        if not self._execution_metrics:
            return {
                "total_executions": 0,
                "success_rate": 0,
                "avg_profit": 0,
                "avg_gas": 0,
                "avg_execution_time": 0
            }
        
        total = len(self._execution_metrics)
        successful = len([m for m in self._execution_metrics if m.success_rate > 0])
        
        return {
            "total_executions": total,
            "success_rate": successful / total,
            "avg_profit": sum(m.actual_profit for m in self._execution_metrics) / total,
            "avg_gas": sum(m.total_gas_used for m in self._execution_metrics) / total,
            "avg_execution_time": sum(
                m.preparation_time + m.simulation_time + m.execution_time
                for m in self._execution_metrics
            ) / total
        }

    async def get_current_state(self) -> Optional[Dict]:
        """Get current execution state."""
        if not self._current_state:
            return None
        
        return {
            "status": self._current_state.status,
            "step": self._current_state.current_step,
            "error": self._current_state.last_error,
            "retries": self._current_state.retry_count,
            "runtime": time.time() - self._current_state.start_time
        }
