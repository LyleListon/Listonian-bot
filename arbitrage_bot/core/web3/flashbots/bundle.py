"""
Flashbots Bundle

This module contains components for creating, managing, and
submitting transaction bundles through Flashbots.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple

from ..interfaces import Web3Client, Transaction, TransactionReceipt

logger = logging.getLogger(__name__)


class FlashbotsBundleResponse:
    """
    Response from a Flashbots bundle submission.
    
    Contains bundle ID, status, and other relevant information.
    """
    
    def __init__(
        self,
        bundle_hash: str,
        response_data: Dict[str, Any]
    ):
        """
        Initialize a bundle response.
        
        Args:
            bundle_hash: Hash of the submitted bundle
            response_data: Raw response data from Flashbots
        """
        self.bundle_hash = bundle_hash
        self.response_data = response_data
        self.submission_time = time.time()
        
        # Parse standard fields
        self.target_block = response_data.get("targetBlock")
        self.simulation_result = response_data.get("simulationResult")
        self.simulation_success = False
        
        if self.simulation_result:
            self.simulation_success = self.simulation_result.get("success", False)
            
        # Status tracking
        self.included = False
        self.included_block = None
        self.mined_transactions = []
    
    def update_status(self, status_data: Dict[str, Any]) -> None:
        """
        Update the bundle status with fresh data.
        
        Args:
            status_data: New status data from Flashbots
        """
        if not status_data:
            return
            
        self.included = status_data.get("included", self.included)
        self.included_block = status_data.get("includedBlock", self.included_block)
        
        if "transactions" in status_data:
            self.mined_transactions = status_data["transactions"]
    
    @property
    def is_included(self) -> bool:
        """Check if the bundle was included in a block."""
        return self.included
    
    @property
    def is_simulation_successful(self) -> bool:
        """Check if the bundle simulation was successful."""
        return self.simulation_success
    
    def __repr__(self) -> str:
        """Get string representation of the bundle response."""
        status = "Included" if self.included else "Pending"
        return (
            f"FlashbotsBundleResponse(hash={self.bundle_hash}, "
            f"status={status}, "
            f"target_block={self.target_block})"
        )


class FlashbotsBundle:
    """
    Container for a bundle of transactions to be submitted via Flashbots.
    
    Handles bundle creation, signing, simulation, and submission.
    """
    
    def __init__(
        self,
        web3_client: Web3Client,
        flashbots_provider: Any,  # Avoid circular import
        config: Dict[str, Any] = None
    ):
        """
        Initialize a Flashbots bundle.
        
        Args:
            web3_client: Web3 client for blockchain interactions
            flashbots_provider: Flashbots provider for submission
            config: Configuration dictionary
        """
        self.web3_client = web3_client
        self.flashbots_provider = flashbots_provider
        self.config = config or {}
        
        # Configuration
        self.block_offset = int(self.config.get("block_offset", 1))
        self.bundle_validity_minutes = int(self.config.get("bundle_validity_minutes", 2))
        self.simulation_required = bool(self.config.get("simulation_required", True))
        self.min_profit_wei = int(self.config.get("min_profit_wei", 0))
        
        # State
        self.transactions: List[Transaction] = []
        self.tx_hashes: List[str] = []
        self.signed_transactions: List[Dict[str, Any]] = []
        self.responses: List[FlashbotsBundleResponse] = []
        self._bundle_lock = asyncio.Lock()
        
        logger.info("FlashbotsBundle initialized")
    
    async def add_transaction(
        self,
        transaction: Transaction,
        sign_immediately: bool = True
    ) -> None:
        """
        Add a transaction to the bundle.
        
        Args:
            transaction: Transaction to add
            sign_immediately: Whether to sign the transaction immediately
        """
        async with self._bundle_lock:
            logger.info(f"Adding transaction to bundle: {transaction}")
            
            # Add to tracked transactions
            self.transactions.append(transaction)
            
            # Sign immediately if requested
            if sign_immediately:
                await self._sign_transaction(transaction)
    
    async def add_transactions(
        self,
        transactions: List[Transaction],
        sign_immediately: bool = True
    ) -> None:
        """
        Add multiple transactions to the bundle.
        
        Args:
            transactions: List of transactions to add
            sign_immediately: Whether to sign the transactions immediately
        """
        async with self._bundle_lock:
            logger.info(f"Adding {len(transactions)} transactions to bundle")
            
            # Add to tracked transactions
            self.transactions.extend(transactions)
            
            # Sign immediately if requested
            if sign_immediately:
                for tx in transactions:
                    await self._sign_transaction(tx)
    
    async def _sign_transaction(
        self,
        transaction: Transaction
    ) -> None:
        """
        Sign a transaction and add it to the signed transactions list.
        
        Args:
            transaction: Transaction to sign
        """
        try:
            # Ensure transaction is fully formed
            if not transaction.from_address:
                transaction.from_address = self.web3_client.get_default_account()
            
            if transaction.nonce is None:
                nonce = await self.web3_client.get_transaction_count(transaction.from_address)
                transaction.nonce = nonce
            
            # Get gas parameters if not set
            if not transaction.gas:
                gas_estimate = await self.web3_client.estimate_gas(transaction)
                # Add 20% buffer for safety
                transaction.gas = int(gas_estimate * 1.2)
            
            # Get gas price if not set (for legacy transactions)
            if not transaction.gas_price and not (transaction.max_fee_per_gas and transaction.max_priority_fee_per_gas):
                gas_price = await self.web3_client.get_gas_price()
                # Add 10% to gas price for better inclusion chances
                transaction.gas_price = int(gas_price * 1.1)
            
            # Sign the transaction
            signed_tx = await self.web3_client.sign_transaction(transaction)
            
            if not signed_tx:
                logger.error("Failed to sign transaction for bundle")
                return
            
            # Add to signed transactions
            signed_bundle_tx = {
                "hash": signed_tx.hash,
                "raw": signed_tx.raw_transaction.hex(),
                "tx": transaction
            }
            
            self.signed_transactions.append(signed_bundle_tx)
            self.tx_hashes.append(signed_tx.hash)
            logger.info(f"Transaction signed and added to bundle: {signed_tx.hash}")
            
        except Exception as e:
            logger.error(f"Error signing transaction: {e}")
    
    async def sign_all_transactions(self) -> None:
        """Sign all transactions in the bundle that aren't already signed."""
        async with self._bundle_lock:
            # Find transactions that aren't signed yet
            tx_hashes_set = set(self.tx_hashes)
            
            for tx in self.transactions:
                # Create temporary tx hash for checking
                temp_hash = f"{tx.from_address}:{tx.nonce}"
                
                if temp_hash not in tx_hashes_set:
                    await self._sign_transaction(tx)
    
    async def simulate(self) -> Dict[str, Any]:
        """
        Simulate the bundle to validate execution and potential profit.
        
        Returns:
            Simulation results including gas used, execution success,
            and potential profit information
        """
        logger.info("Simulating Flashbots bundle")
        
        async with self._bundle_lock:
            # Ensure all transactions are signed
            await self.sign_all_transactions()
            
            if not self.signed_transactions:
                logger.error("No signed transactions to simulate")
                return {"success": False, "error": "No signed transactions"}
            
            # Submit for simulation
            try:
                result = await self.flashbots_provider.simulate_bundle(self.signed_transactions)
                
                if not result:
                    logger.warning("Bundle simulation returned no result")
                    return {"success": False, "error": "Simulation returned no result"}
                
                # Log simulation results
                if result.get("results"):
                    successful_txs = sum(1 for r in result["results"] if r.get("success", False))
                    logger.info(f"Bundle simulation: {successful_txs}/{len(result['results'])} transactions successful")
                
                # Check for simulation errors
                if "error" in result:
                    logger.error(f"Bundle simulation error: {result['error']}")
                
                # Calculate profit/cost
                profit_analysis = self._analyze_simulation_profit(result)
                result.update(profit_analysis)
                
                return result
                
            except Exception as e:
                logger.error(f"Error simulating bundle: {e}")
                return {"success": False, "error": str(e)}
    
    def _analyze_simulation_profit(
        self,
        simulation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze the simulation result to determine profit.
        
        Args:
            simulation_result: Result from Flashbots simulation
            
        Returns:
            Analysis including profit, cost, and profit-to-cost ratio
        """
        # Default analysis result
        analysis = {
            "profitable": False,
            "profit_wei": 0,
            "cost_wei": 0,
            "profit_ratio": 0.0
        }
        
        # Extract coinbase payments (direct profit indication)
        coinbase_diff = 0
        if "coinbaseDiff" in simulation_result:
            coinbase_diff = int(simulation_result["coinbaseDiff"], 16) if isinstance(simulation_result["coinbaseDiff"], str) else int(simulation_result["coinbaseDiff"])
            analysis["profit_wei"] += coinbase_diff
        
        # Calculate gas costs
        gas_used = 0
        gas_price = 0
        
        if "results" in simulation_result:
            for tx_result in simulation_result["results"]:
                if tx_result.get("gasUsed"):
                    gas_used += int(tx_result["gasUsed"])
                
                # Use max of gas prices for conservative estimate
                if "gasPrice" in tx_result:
                    tx_gas_price = int(tx_result["gasPrice"], 16) if isinstance(tx_result["gasPrice"], str) else int(tx_result["gasPrice"])
                    gas_price = max(gas_price, tx_gas_price)
        
        # Calculate total gas cost
        gas_cost = gas_used * gas_price
        analysis["cost_wei"] = gas_cost
        
        # Determine if profitable
        pure_profit = analysis["profit_wei"] - analysis["cost_wei"]
        analysis["profit_wei"] = pure_profit
        analysis["profitable"] = pure_profit > self.min_profit_wei
        
        # Calculate profit ratio if cost is non-zero
        if analysis["cost_wei"] > 0:
            analysis["profit_ratio"] = pure_profit / analysis["cost_wei"]
        
        return analysis
    
    async def submit(
        self,
        target_block_number: Optional[int] = None,
        simulate_first: bool = True
    ) -> Optional[FlashbotsBundleResponse]:
        """
        Submit the bundle to Flashbots.
        
        Args:
            target_block_number: Target block for bundle inclusion
            simulate_first: Whether to simulate before submission
            
        Returns:
            Bundle response if submission was successful
        """
        logger.info("Preparing to submit Flashbots bundle")
        
        async with self._bundle_lock:
            # Ensure all transactions are signed
            await self.sign_all_transactions()
            
            if not self.signed_transactions:
                logger.error("No signed transactions to submit")
                return None
            
            # Simulate first if requested
            if simulate_first and self.simulation_required:
                simulation_result = await self.simulate()
                
                if not simulation_result.get("success", False):
                    logger.error("Bundle simulation failed, aborting submission")
                    return None
                
                # Check for profitability if minimum is set
                if self.min_profit_wei > 0 and not simulation_result.get("profitable", False):
                    logger.warning(
                        f"Bundle not profitable enough. Profit: {simulation_result.get('profit_wei', 0)} wei, "
                        f"Minimum: {self.min_profit_wei} wei"
                    )
                    return None
            
            # Submit the bundle
            try:
                # Get target block if not provided
                if target_block_number is None:
                    current_block = await self.web3_client.get_block_number()
                    target_block_number = current_block + self.block_offset
                
                # Set up bundle parameters
                bundle_hash = await self.flashbots_provider.send_bundle(self.signed_transactions)
                
                if not bundle_hash:
                    logger.error("Failed to submit bundle")
                    return None
                
                # Create response object
                response_data = {
                    "targetBlock": target_block_number,
                    "simulationResult": None  # Will be populated later if needed
                }
                
                # Retrieve simulation result if available
                if simulate_first and self.simulation_required:
                    response_data["simulationResult"] = await self.simulate()
                
                # Create and store bundle response
                bundle_response = FlashbotsBundleResponse(bundle_hash, response_data)
                self.responses.append(bundle_response)
                
                logger.info(f"Bundle submitted successfully: {bundle_hash}, targeting block {target_block_number}")
                return bundle_response
                
            except Exception as e:
                logger.error(f"Error submitting bundle: {e}")
                return None
    
    async def check_inclusion(
        self,
        bundle_hash: str
    ) -> bool:
        """
        Check if a submitted bundle was included in a block.
        
        Args:
            bundle_hash: Hash of the bundle to check
            
        Returns:
            True if the bundle was included, False otherwise
        """
        logger.info(f"Checking inclusion for bundle: {bundle_hash}")
        
        try:
            # Get latest status
            stats = await self.flashbots_provider.get_bundle_stats(bundle_hash)
            
            if not stats:
                logger.warning(f"No stats available for bundle {bundle_hash}")
                return False
            
            # Update stored response if we have it
            for response in self.responses:
                if response.bundle_hash == bundle_hash:
                    response.update_status(stats)
                    
                    if response.is_included:
                        logger.info(f"Bundle {bundle_hash} was included in block {response.included_block}")
                        return True
            
            # Check inclusion directly from stats
            is_included = stats.get("included", False)
            
            if is_included:
                included_block = stats.get("includedBlock")
                logger.info(f"Bundle {bundle_hash} was included in block {included_block}")
                return True
            
            logger.info(f"Bundle {bundle_hash} not yet included")
            return False
            
        except Exception as e:
            logger.error(f"Error checking bundle inclusion: {e}")
            return False
    
    async def get_tx_receipts(self) -> List[Optional[TransactionReceipt]]:
        """
        Get transaction receipts for all transactions in the bundle.
        
        Returns:
            List of transaction receipts
        """
        logger.info("Getting receipts for bundle transactions")
        
        receipts: List[Optional[TransactionReceipt]] = []
        
        for tx_hash in self.tx_hashes:
            try:
                receipt = await self.web3_client.get_transaction_receipt(tx_hash)
                receipts.append(receipt)
                
                if receipt:
                    logger.info(f"Transaction {tx_hash} status: {'Success' if receipt.status else 'Failed'}")
                else:
                    logger.info(f"Transaction {tx_hash} not yet mined")
                    
            except Exception as e:
                logger.error(f"Error getting receipt for {tx_hash}: {e}")
                receipts.append(None)
        
        return receipts
    
    async def wait_for_inclusion(
        self,
        bundle_hash: str,
        timeout: float = 60.0,
        check_interval: float = 2.0
    ) -> bool:
        """
        Wait for a bundle to be included in a block.
        
        Args:
            bundle_hash: Hash of the bundle to wait for
            timeout: Maximum time to wait in seconds
            check_interval: Interval between checks in seconds
            
        Returns:
            True if the bundle was included, False if timeout occurred
        """
        logger.info(f"Waiting for bundle inclusion: {bundle_hash}")
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            included = await self.check_inclusion(bundle_hash)
            
            if included:
                return True
            
            # Wait before checking again
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Bundle {bundle_hash} inclusion wait timed out after {timeout} seconds")
        return False
    
    async def cancel(
        self,
        bundle_hash: Optional[str] = None
    ) -> bool:
        """
        Cancel a previously submitted bundle.
        
        Args:
            bundle_hash: Hash of the bundle to cancel, or None to cancel all
            
        Returns:
            True if cancellation was successful
        """
        if bundle_hash:
            logger.info(f"Cancelling bundle: {bundle_hash}")
            return await self.flashbots_provider.cancel_bundle(bundle_hash)
        
        # Cancel all bundles if no specific hash provided
        logger.info("Cancelling all submitted bundles")
        
        success = True
        for response in self.responses:
            # Only cancel bundles that aren't already included
            if not response.is_included:
                bundle_success = await self.flashbots_provider.cancel_bundle(response.bundle_hash)
                
                if not bundle_success:
                    success = False
                    logger.warning(f"Failed to cancel bundle: {response.bundle_hash}")
        
        return success
    
    async def clear(self) -> None:
        """Clear all transactions and responses from the bundle."""
        async with self._bundle_lock:
            logger.info("Clearing bundle")
            
            self.transactions = []
            self.tx_hashes = []
            self.signed_transactions = []
            self.responses = []


async def create_flashbots_bundle(
    web3_client: Web3Client,
    flashbots_provider: Any,
    config: Dict[str, Any] = None
) -> FlashbotsBundle:
    """
    Factory function to create a Flashbots bundle.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        flashbots_provider: Flashbots provider for submission
        config: Configuration parameters
        
    Returns:
        Initialized Flashbots bundle
    """
    return FlashbotsBundle(
        web3_client=web3_client,
        flashbots_provider=flashbots_provider,
        config=config
    )