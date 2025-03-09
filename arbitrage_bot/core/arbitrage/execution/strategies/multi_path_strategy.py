"""
Multi-Path Arbitrage Execution Strategy

This module implements a strategy for executing multi-path arbitrage opportunities
with Flashbots protection for MEV resistance and atomic execution.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union, Tuple

from ....web3.interfaces import Web3Client, Transaction
from ....web3.flashbots.interfaces import FlashbotsBundle, BundleSimulationResult
from ....web3.flashbots.provider import FlashbotsProvider
from ....web3.flashbots.simulator import BundleSimulator
from ....finance.flash_loans.factory import FlashLoanFactory
from ....finance.flash_loans.interfaces import FlashLoanProvider, FlashLoanTransaction
from ...path.interfaces import MultiPathOpportunity
from ...execution.interfaces import (
    ExecutionStrategy,
    ExecutionResult,
    ExecutionStatus
)

logger = logging.getLogger(__name__)


class MultiPathStrategy(ExecutionStrategy):
    """
    Strategy for executing multi-path arbitrage opportunities using Flashbots.
    
    This strategy executes multiple arbitrage paths in a single transaction bundle
    with Flashbots protection, optionally using flash loans for capital efficiency.
    """
    
    def __init__(
        self,
        web3_client: Web3Client,
        flashbots_provider: FlashbotsProvider,
        flash_loan_factory: Optional[FlashLoanFactory] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the multi-path execution strategy.
        
        Args:
            web3_client: Web3 client for blockchain interactions
            flashbots_provider: Provider for Flashbots interactions
            flash_loan_factory: Optional factory for flash loan providers
            config: Configuration parameters for the strategy
        """
        self.web3_client = web3_client
        self.flashbots_provider = flashbots_provider
        self.flash_loan_factory = flash_loan_factory
        self.config = config or {}
        
        # Configuration
        self.slippage_tolerance = Decimal(self.config.get("slippage_tolerance", "0.005"))
        self.profit_threshold_multiplier = Decimal(self.config.get("profit_threshold_multiplier", "1.5"))
        self.gas_buffer = Decimal(self.config.get("gas_buffer", "1.2"))
        self.max_wait_blocks = self.config.get("max_wait_blocks", 5)
        self.use_flash_loans = self.config.get("use_flash_loans", True)
        
        # Components
        self.bundle_simulator = None
        
        # State
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """
        Initialize the strategy.
        
        This method sets up the bundle simulator and ensures the strategy
        is ready for use.
        
        Returns:
            True if initialization succeeds, False otherwise
        """
        async with self._initialization_lock:
            if self._is_initialized:
                logger.debug("Multi-path strategy already initialized")
                return True
            
            try:
                logger.info("Initializing multi-path strategy")
                
                # Initialize flash loan factory if provided
                if self.flash_loan_factory and not await self.flash_loan_factory.is_initialized():
                    if not await self.flash_loan_factory.initialize():
                        logger.error("Failed to initialize flash loan factory")
                        return False
                
                # Initialize bundle simulator
                self.bundle_simulator = BundleSimulator(
                    self.web3_client,
                    config=self.config.get("simulator", {})
                )
                await self.bundle_simulator.initialize()
                
                # Ensure Flashbots provider is initialized
                if not await self.flashbots_provider.is_initialized():
                    await self.flashbots_provider.initialize()
                
                self._is_initialized = True
                logger.info("Multi-path strategy initialized successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to initialize multi-path strategy: {e}")
                return False
    
    async def _ensure_initialized(self) -> None:
        """Ensure the strategy is initialized."""
        if not self._is_initialized:
            success = await self.initialize()
            if not success:
                raise RuntimeError("Failed to initialize multi-path strategy")
    
    async def is_applicable(self, opportunity: MultiPathOpportunity) -> bool:
        """
        Check if this strategy is applicable to the given opportunity.
        
        Args:
            opportunity: Arbitrage opportunity to check
            
        Returns:
            True if the strategy is applicable, False otherwise
        """
        await self._ensure_initialized()
        
        try:
            # Check if opportunity is valid
            if not opportunity.is_valid:
                logger.info("Opportunity is not valid")
                return False
            
            # Check if sufficient balance is available (or if flash loans are enabled)
            if not self.use_flash_loans:
                balance = await self._get_token_balance(
                    opportunity.start_token,
                    await self._get_account_address()
                )
                
                if balance < opportunity.required_amount:
                    logger.info(
                        f"Insufficient balance: {balance} < {opportunity.required_amount}"
                    )
                    return False
            else:
                # Check if flash loans are available for the required token and amount
                if self.flash_loan_factory:
                    provider = await self.flash_loan_factory.get_provider(
                        opportunity.start_token,
                        opportunity.required_amount
                    )
                    
                    if not provider:
                        logger.info(
                            f"No flash loan provider available for {opportunity.start_token}"
                        )
                        return False
            
            # Check if the opportunity is profitable enough
            return await self.is_profitable(opportunity)
            
        except Exception as e:
            logger.error(f"Error checking applicability: {e}")
            return False
    
    async def is_profitable(self, opportunity: MultiPathOpportunity) -> bool:
        """
        Check if the opportunity is profitable using this strategy.
        
        Args:
            opportunity: Arbitrage opportunity to check
            
        Returns:
            True if the opportunity is profitable, False otherwise
        """
        await self._ensure_initialized()
        
        try:
            # Get costs
            costs = await self._calculate_costs(opportunity)
            
            # Calculate minimum required profit
            min_profit = costs["total_cost"] * self.profit_threshold_multiplier
            
            # Check if the opportunity is profitable enough
            is_profitable = opportunity.expected_profit > min_profit
            
            logger.info(
                f"Profit check: profit={opportunity.expected_profit}, "
                f"min_required={min_profit}, profitable={is_profitable}"
            )
            
            return is_profitable
            
        except Exception as e:
            logger.error(f"Error checking profitability: {e}")
            return False
    
    async def execute(
        self,
        opportunity: MultiPathOpportunity,
        execution_params: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute the multi-path arbitrage opportunity.
        
        Args:
            opportunity: Multi-path arbitrage opportunity to execute
            execution_params: Additional parameters for execution
            
        Returns:
            Result of the execution
        """
        await self._ensure_initialized()
        
        execution_params = execution_params or {}
        
        # Create a default result with status=FAILED
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            opportunity=opportunity,
            transaction_hash=None,
            gas_used=0,
            gas_price=0,
            profit_amount=Decimal("0"),
            profit_token=opportunity.start_token,
            error_message="Execution not attempted"
        )
        
        try:
            logger.info(f"Executing multi-path opportunity with {len(opportunity.paths)} paths")
            
            # Check if the opportunity is profitable
            if not await self.is_profitable(opportunity):
                logger.warning("Opportunity is not profitable, skipping execution")
                result.error_message = "Opportunity is not profitable"
                return result
            
            # Prepare execution batch
            if self.use_flash_loans and self.flash_loan_factory:
                # With flash loan
                flash_loan_tx, swap_txs = await self._prepare_flash_loan_execution(
                    opportunity, execution_params
                )
                
                if not flash_loan_tx:
                    logger.error("Failed to prepare flash loan transaction")
                    result.error_message = "Failed to prepare flash loan transaction"
                    return result
                
                txs = [flash_loan_tx] + swap_txs
            else:
                # Direct execution without flash loan
                txs = await self._prepare_direct_execution(
                    opportunity, execution_params
                )
                
                if not txs:
                    logger.error("Failed to prepare execution transactions")
                    result.error_message = "Failed to prepare execution transactions"
                    return result
            
            # Create Flashbots bundle
            bundle = await self._create_flashbots_bundle(txs, execution_params)
            
            if not bundle:
                logger.error("Failed to create Flashbots bundle")
                result.error_message = "Failed to create Flashbots bundle"
                return result
            
            # Sign bundle
            signed_bundle = await self.flashbots_provider.sign_bundle(bundle)
            
            # Simulate bundle
            simulation_result = await self.bundle_simulator.simulate(signed_bundle)
            
            if not simulation_result.success:
                logger.error(f"Bundle simulation failed: {simulation_result.error}")
                result.error_message = f"Bundle simulation failed: {simulation_result.error}"
                return result
            
            # Verify profitability from simulation
            min_profit_threshold = float(execution_params.get(
                "min_profit_threshold",
                0.001
            ))
            
            is_profitable = await self.bundle_simulator.verify_profitability(
                simulation_result,
                min_profit_threshold=min_profit_threshold
            )
            
            if not is_profitable:
                logger.warning("Bundle is not profitable based on simulation")
                result.error_message = "Bundle is not profitable based on simulation"
                return result
            
            # Submit bundle
            submission_result = await self.flashbots_provider.submit_bundle(signed_bundle)
            
            if not submission_result.success:
                logger.error(f"Bundle submission failed: {submission_result.error}")
                result.error_message = f"Bundle submission failed: {submission_result.error}"
                return result
            
            logger.info(f"Bundle submitted: {submission_result.bundle_hash}")
            
            # Wait for bundle inclusion
            target_block = await self.web3_client.get_block_number() + bundle.blocks_into_future
            stats = await self.flashbots_provider.wait_for_bundle_inclusion(
                submission_result.bundle_hash,
                target_block,
                max_wait_blocks=self.max_wait_blocks
            )
            
            if not stats or not stats.get("is_included"):
                logger.warning(f"Bundle not included within {self.max_wait_blocks} blocks")
                result.error_message = f"Bundle not included within {self.max_wait_blocks} blocks"
                return result
            
            # Bundle was included, update result
            block_number = stats.get("block_number")
            transaction_hash = stats.get("transaction_hash")
            gas_used = stats.get("gas_used", 0)
            gas_price = stats.get("gas_price", 0)
            
            logger.info(
                f"Bundle included in block {block_number}, "
                f"transaction hash: {transaction_hash}"
            )
            
            # Get actual profit from simulation or calculation
            actual_profit = await self._calculate_actual_profit(
                opportunity,
                stats,
                simulation_result
            )
            
            result.status = ExecutionStatus.EXECUTED
            result.transaction_hash = transaction_hash
            result.gas_used = gas_used
            result.gas_price = gas_price
            result.profit_amount = actual_profit
            result.error_message = None
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing opportunity: {e}", exc_info=True)
            result.error_message = str(e)
            return result
    
    async def _prepare_flash_loan_execution(
        self,
        opportunity: MultiPathOpportunity,
        execution_params: Dict[str, Any]
    ) -> Tuple[Transaction, List[Transaction]]:
        """
        Prepare flash loan execution for a multi-path opportunity.
        
        Args:
            opportunity: Multi-path opportunity to execute
            execution_params: Additional parameters for execution
            
        Returns:
            Tuple of flash loan transaction and list of swap transactions
        """
        try:
            # Get flash loan provider
            if not self.flash_loan_factory:
                logger.error("Flash loan factory not available")
                return None, []
            
            provider = await self.flash_loan_factory.get_provider(
                opportunity.start_token,
                opportunity.required_amount
            )
            
            if not provider:
                logger.error(f"No flash loan provider for {opportunity.start_token}")
                return None, []
            
            # Get account address
            account_address = execution_params.get("account_address")
            if not account_address:
                account_address = await self._get_account_address()
            
            # Create flash loan transaction
            flash_loan_tx = FlashLoanTransaction(
                token_address=opportunity.start_token,
                amount=opportunity.required_amount,
                recipient=account_address,
                callback_data="0x"  # Will be filled by provider
            )
            
            # Generate swap transactions from opportunity paths
            swap_txs = await self._generate_swap_transactions(
                opportunity, execution_params
            )
            
            # Convert flash loan transaction to Web3 transaction
            # This is a simplified version - in a real implementation,
            # we would need to prepare the actual calldata for the flash loan
            web3_tx = Transaction(
                from_address=account_address,
                to_address=provider.get_contract_address(),
                data="0x",  # Flash loan calldata would go here
                value=0,
                gas=execution_params.get("gas", 1000000),
                gas_price=None,  # Will be set by Flashbots
                nonce=None  # Will be auto-filled
            )
            
            return web3_tx, swap_txs
            
        except Exception as e:
            logger.error(f"Error preparing flash loan execution: {e}")
            return None, []
    
    async def _prepare_direct_execution(
        self,
        opportunity: MultiPathOpportunity,
        execution_params: Dict[str, Any]
    ) -> List[Transaction]:
        """
        Prepare direct execution for a multi-path opportunity without flash loans.
        
        Args:
            opportunity: Multi-path opportunity to execute
            execution_params: Additional parameters for execution
            
        Returns:
            List of transactions for execution
        """
        try:
            # Generate swap transactions from opportunity paths
            return await self._generate_swap_transactions(opportunity, execution_params)
            
        except Exception as e:
            logger.error(f"Error preparing direct execution: {e}")
            return []
    
    async def _generate_swap_transactions(
        self,
        opportunity: MultiPathOpportunity,
        execution_params: Dict[str, Any]
    ) -> List[Transaction]:
        """
        Generate transactions for executing swaps in a multi-path opportunity.
        
        Args:
            opportunity: Multi-path opportunity to execute
            execution_params: Additional parameters for execution
            
        Returns:
            List of transactions for swaps
        """
        try:
            # Get account address
            account_address = execution_params.get("account_address")
            if not account_address:
                account_address = await self._get_account_address()
            
            txs = []
            
            # Process each path
            for i, (path, allocation) in enumerate(zip(opportunity.paths, opportunity.allocations)):
                if allocation <= 0:
                    continue
                
                # Generate transactions for this path
                path_txs = []
                
                for j, swap_data in enumerate(path.swap_data):
                    # In a real implementation, we would need to prepare the
                    # actual calldata for the swap based on the swap_data
                    # This is a simplified version
                    tx = Transaction(
                        from_address=account_address,
                        to_address=swap_data.get("router_address", "0x"),
                        data=swap_data.get("calldata", "0x"),
                        value=0,
                        gas=swap_data.get("gas_estimate", 200000),
                        gas_price=None,  # Will be set by Flashbots
                        nonce=None  # Will be auto-filled
                    )
                    
                    path_txs.append(tx)
                
                txs.extend(path_txs)
            
            return txs
            
        except Exception as e:
            logger.error(f"Error generating swap transactions: {e}")
            return []
    
    async def _create_flashbots_bundle(
        self,
        transactions: List[Transaction],
        execution_params: Dict[str, Any]
    ) -> Optional[FlashbotsBundle]:
        """
        Create a Flashbots bundle from transactions.
        
        Args:
            transactions: List of transactions to include in the bundle
            execution_params: Additional parameters for execution
            
        Returns:
            Flashbots bundle or None if creation fails
        """
        try:
            blocks_into_future = execution_params.get("blocks_into_future", 2)
            
            # Create bundle
            bundle = FlashbotsBundle(
                transactions=transactions,
                blocks_into_future=blocks_into_future
            )
            
            return bundle
            
        except Exception as e:
            logger.error(f"Error creating Flashbots bundle: {e}")
            return None
    
    async def _calculate_costs(
        self,
        opportunity: MultiPathOpportunity
    ) -> Dict[str, Decimal]:
        """
        Calculate costs for executing a multi-path opportunity.
        
        This includes gas costs, flash loan fees, and other execution costs.
        
        Args:
            opportunity: Multi-path opportunity to calculate costs for
            
        Returns:
            Dictionary of cost components and total cost
        """
        try:
            costs = {
                "gas_cost": Decimal("0"),
                "flash_loan_fee": Decimal("0"),
                "slippage_cost": Decimal("0"),
                "total_cost": Decimal("0")
            }
            
            # Calculate gas cost
            gas_estimate = sum(path.estimated_gas for path in opportunity.paths)
            gas_price = await self.web3_client.get_gas_price()
            gas_cost_eth = Decimal(gas_estimate) * Decimal(gas_price) / Decimal(10**18)
            
            # Convert gas cost to token cost (simplified)
            # In a real implementation, we would use a price feed
            eth_price_usd = Decimal("2000")  # Placeholder
            token_price_usd = Decimal("1")   # Placeholder
            gas_cost = gas_cost_eth * eth_price_usd / token_price_usd
            
            costs["gas_cost"] = gas_cost
            
            # Calculate flash loan fee if applicable
            if self.use_flash_loans and self.flash_loan_factory:
                provider = await self.flash_loan_factory.get_provider(
                    opportunity.start_token,
                    opportunity.required_amount
                )
                
                if provider:
                    fee_rate = provider.get_fee_rate()
                    costs["flash_loan_fee"] = opportunity.required_amount * fee_rate
            
            # Calculate slippage cost
            costs["slippage_cost"] = opportunity.required_amount * self.slippage_tolerance
            
            # Calculate total cost
            costs["total_cost"] = sum(
                cost for key, cost in costs.items()
                if key != "total_cost"
            )
            
            return costs
            
        except Exception as e:
            logger.error(f"Error calculating costs: {e}")
            return {
                "gas_cost": Decimal("0"),
                "flash_loan_fee": Decimal("0"),
                "slippage_cost": Decimal("0"),
                "total_cost": Decimal("0.01")  # Default cost estimate
            }
    
    async def _calculate_actual_profit(
        self,
        opportunity: MultiPathOpportunity,
        stats: Dict[str, Any],
        simulation_result: BundleSimulationResult
    ) -> Decimal:
        """
        Calculate the actual profit from the executed opportunity.
        
        Args:
            opportunity: Executed multi-path opportunity
            stats: Bundle inclusion statistics
            simulation_result: Simulation result
            
        Returns:
            Actual profit
        """
        try:
            # For now, use the expected profit
            # In a real implementation, we would calculate the actual profit
            # based on the state changes from the simulation
            return opportunity.expected_profit
            
        except Exception as e:
            logger.error(f"Error calculating actual profit: {e}")
            return Decimal("0")
    
    async def _get_account_address(self) -> str:
        """
        Get the account address to use for transactions.
        
        Returns:
            Account address (checksummed)
        """
        accounts = await self.web3_client.get_accounts()
        if not accounts:
            raise ValueError("No accounts available")
        
        return accounts[0]
    
    async def _get_token_balance(self, token_address: str, account_address: str) -> Decimal:
        """
        Get the token balance for an account.
        
        Args:
            token_address: Token address (checksummed)
            account_address: Account address (checksummed)
            
        Returns:
            Token balance as Decimal
        """
        try:
            # For simplicity, return a placeholder
            # In a real implementation, we would use a token contract
            return Decimal("100")
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return Decimal("0")
    
    async def close(self) -> None:
        """Close the strategy and clean up resources."""
        logger.info("Closing multi-path strategy")
        
        if self.bundle_simulator:
            await self.bundle_simulator.close()
        
        self._is_initialized = False