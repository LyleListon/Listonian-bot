"""Flashbots manager for MEV protection and bundle submissions."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Union, Tuple, Set
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.types import TxReceipt, BlockData
import json
import os
from pathlib import Path
from .flashbots_provider import FlashbotsProvider

logger = logging.getLogger(__name__)

class FlashbotsConnectionError(Exception):
    """Error raised when Flashbots connection fails."""
    pass

class FlashbotsManager:
    """Manages Flashbots interactions and bundle submissions."""

    def __init__(
        self,
        web3_manager,
        auth_signer_key = None,
        flashbots_relay_url = "https://relay.flashbots.net",
        balance_validator = None
    ):
        """Initialize Flashbots manager."""
        self.web3_manager = web3_manager
        self.relay_url = flashbots_relay_url
        self.auth_signer = None
        if auth_signer_key:
            self.auth_signer = Account.from_key(auth_signer_key)
        
        # Bundle management
        self._pending_bundles = {}
        self._simulation_results = {}
        self._bundle_token_transfers = {}
        
        # Profit calculation settings
        self._min_profit_threshold = 0  # Min profit in wei to consider bundle profitable
        self._gas_price_buffer = 1.2    # Multiply gas price by this factor for safety
        self._slippage_tolerance = 0.02 # 2% slippage tolerance
        self._max_price_impact = 0.05   # 5% max price impact allowed
        
        # Balance validator
        self.balance_validator = balance_validator
        
        logger.info("Initialized Flashbots manager with profit threshold: %d wei", self._min_profit_threshold)

    async def setup_flashbots_provider(self):
        """Setup Flashbots provider with authentication."""
        try:
            # Create a new auth signer if not provided
            if not self.auth_signer:
                self.auth_signer = Account.create()
            
            # Setup Flashbots provider
            self.web3_manager.w3.flashbots = FlashbotsProvider(
                self.web3_manager.w3,
                self.auth_signer,
                self.relay_url
            )
            
            # Initialize balance validator if needed
            await self._setup_balance_validator()
            
            logger.info("Flashbots provider setup complete")
            return True
            
        except Exception as e:
            logger.error("Failed to setup Flashbots provider: %s", str(e))
            raise FlashbotsConnectionError(str(e))

    async def _setup_balance_validator(self):
        """Setup balance validator if not already provided."""
        if self.balance_validator:
            return
        
        try:
            # Import here to avoid circular imports
            from .balance_validator import create_balance_validator
            
            # Create balance validator
            self.balance_validator = await create_balance_validator(self.web3_manager)
            logger.info("Created balance validator for Flashbots manager")
            
        except ImportError:
            logger.warning("Balance validator not available, bundle validation will be limited")
        except Exception as e:
            logger.error("Failed to setup balance validator: %s", str(e))

    async def close(self):
        """Clean up resources."""
        try:
            if hasattr(self.web3_manager.w3, 'flashbots') and hasattr(self.web3_manager.w3.flashbots, 'close'):
                await self.web3_manager.w3.flashbots.close()
                logger.info("Closed Flashbots provider")
        except Exception as e:
            logger.error("Error closing Flashbots manager: %s", str(e))

    async def create_bundle(
        self,
        target_block,
        transactions,
        min_timestamp = None,
        max_timestamp = None,
        revert_on_fail = True
    ):
        """Create a transaction bundle for Flashbots."""
        try:
            # Prepare bundle params
            bundle_params = {
                "txs": transactions,
                "blockNumber": target_block,
                "minTimestamp": min_timestamp,
                "maxTimestamp": max_timestamp,
                "revertingTxHashes": [] if revert_on_fail else None
            }
            
            # Generate bundle id
            bundle_id = Web3.keccak(text=str(bundle_params)).hex()
            
            # Store bundle
            self._pending_bundles[bundle_id] = bundle_params
            
            logger.info("Created bundle %s for block %d", bundle_id, target_block)
            return bundle_id
            
        except Exception as e:
            logger.error("Failed to create bundle: %s", str(e))
            raise

    async def simulate_bundle(
        self,
        bundle_id,
        block_tag = "latest"
    ):
        """Simulate a bundle before submission."""
        try:
            bundle = self._pending_bundles.get(bundle_id)
            if not bundle:
                raise ValueError("Bundle {} not found".format(bundle_id))
            
            # Simulate bundle
            simulation = await self.web3_manager.w3.flashbots.simulate(
                bundle["txs"],
                block_tag=block_tag
            )
            
            # Store simulation results
            self._simulation_results[bundle_id] = simulation
            
            logger.info("Simulated bundle %s", bundle_id)
            return simulation
            
        except Exception as e:
            logger.error("Failed to simulate bundle: %s", str(e))
            raise

    async def submit_bundle(
        self,
        bundle_id,
        target_block = None
    ) -> Dict[str, Any]:
        """Submit a bundle to Flashbots."""
        try:
            validation_result = None
            
            # Validate bundle before submission if we have a validator
            if self.balance_validator:
                # Get or run simulation if not available
                if bundle_id not in self._simulation_results:
                    await self.simulate_bundle(bundle_id)
                
                bundle_simulation = self._simulation_results.get(bundle_id)
                if bundle_simulation:
                    # Extract token addresses from the simulation
                    token_addresses = set()
                    if "logs" in bundle_simulation:
                        for log in bundle_simulation.get("logs", []):
                            if "address" in log:
                                token_addresses.add(log["address"])
                    
                    # Add ETH address
                    token_addresses.add("0x0000000000000000000000000000000000000000")
                    
                    # Validate bundle
                    validation_result = await self.balance_validator.validate_bundle_balance(
                        bundle_id, list(token_addresses))
                    logger.info(f"Bundle {bundle_id} validation: {validation_result['success']}")
            
            bundle = self._pending_bundles.get(bundle_id)
            if not bundle:
                raise ValueError("Bundle {} not found".format(bundle_id))
            
            # Use provided target block or bundle's target
            target = target_block or bundle["blockNumber"]
            
            # Submit bundle
            result = await self.web3_manager.w3.flashbots.send_bundle(
                bundle["txs"],
                target_block_number=target
            )
            
            logger.info("Submitted bundle %s for block %d", bundle_id, target)
            
            # Return enhanced result with validation if available
            submission_result = {"submit_result": result}
            if validation_result:
                submission_result["validation"] = validation_result
                
            return submission_result
            
        except Exception as e:
            logger.error("Failed to submit bundle: %s", str(e))
            raise

    async def get_bundle_status(
        self,
        bundle_id
    ):
        """Get status of a submitted bundle."""
        try:
            bundle = self._pending_bundles.get(bundle_id)
            if not bundle:
                raise ValueError("Bundle {} not found".format(bundle_id))
            
            # Get bundle status
            status = await self.web3_manager.w3.flashbots.get_bundle_stats(bundle_id)
            
            logger.info("Bundle %s status: %s", bundle_id, status)
            return status
            
        except Exception as e:
            logger.error("Failed to get bundle status: %s", str(e))
            raise

    async def calculate_bundle_profit(
        self,
        bundle_id,
        token_addresses: Optional[List[str]] = None,
        account_to_check: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate potential profit from a bundle simulation."""
        try:
            simulation = self._simulation_results.get(bundle_id)
            if not simulation:
                raise ValueError("No simulation results for bundle {}".format(bundle_id))
            
            # Calculate profit from coinbase payments
            coinbase_payment = simulation.get("coinbaseDiff", 0)
            if isinstance(coinbase_payment, str):
                coinbase_payment = int(coinbase_payment, 16) if coinbase_payment.startswith('0x') else int(coinbase_payment)
            
            # Calculate gas costs
            gas_used = simulation.get("gasUsed", 0)
            if isinstance(gas_used, str):
                gas_used = int(gas_used, 16) if gas_used.startswith('0x') else int(gas_used)
                
            gas_price = simulation.get("gasPrice", 0)
            if isinstance(gas_price, str):
                gas_price = int(gas_price, 16) if gas_price.startswith('0x') else int(gas_price)
                
            # Add buffer to gas price for safety
            buffered_gas_price = int(gas_price * self._gas_price_buffer)
            gas_cost = gas_used * buffered_gas_price
            
            # Initialize profit calculation result
            profit_result = {
                "net_profit_wei": 0,
                "coinbase_payment": coinbase_payment,
                "gas_cost": gas_cost,
                "token_transfers": {},
                "profitable": False,
                "details": {},
                "errors": []
            }
            
            # Get token transfers and balance changes if available in simulation
            token_transfers = {}
            
            # Check for token transfers in logs
            if "logs" in simulation:
                token_transfers = await self._extract_token_transfers_from_logs(
                    simulation["logs"],
                    token_addresses,
                    account_to_check or self.web3_manager.wallet_address
                )
                profit_result["token_transfers"] = token_transfers
            
            # Calculate token value changes
            token_value_change = 0
            if token_transfers:
                for token, amount in token_transfers.items():
                    try:
                        # Convert token amount to ETH value (simplified)
                        token_price = await self.web3_manager.get_token_price(token)
                        if token_price:
                            token_value = float(amount) * token_price
                            token_value_change += token_value
                            profit_result["details"][token] = {
                                "amount": amount,
                                "price": token_price,
                                "value": token_value
                            }
                    except Exception as e:
                        profit_result["errors"].append(f"Failed to calculate value for token {token}: {str(e)}")
            
            # Calculate direct ETH balance changes
            eth_balance_change = 0
            if "balances" in simulation and account_to_check:
                # Extract balance changes from before/after states
                if account_to_check in simulation["balances"]:
                    before = simulation["balances"][account_to_check].get("before", 0)
                    after = simulation["balances"][account_to_check].get("after", 0)
                    if isinstance(before, str):
                        before = int(before, 16) if before.startswith('0x') else int(before)
                    if isinstance(after, str):
                        after = int(after, 16) if after.startswith('0x') else int(after)
                    eth_balance_change = after - before
                    profit_result["eth_balance_change"] = eth_balance_change
            
            # Calculate net profit
            net_profit = coinbase_payment - gas_cost + eth_balance_change + int(token_value_change)
            profit_result["net_profit_wei"] = net_profit
            profit_result["profitable"] = net_profit > self._min_profit_threshold
            
            logger.info("Bundle %s profit calculation: %d wei (gas cost: %d wei)", bundle_id, net_profit, gas_cost)
            return profit_result
            
        except Exception as e:
            logger.error("Failed to calculate bundle profit (bundle_id=%s): %s", bundle_id, str(e))
            raise

    async def optimize_bundle_gas(
        self,
        bundle_id,
        max_priority_fee
    ):
        """Optimize gas settings for a bundle."""
        try:
            bundle = self._pending_bundles.get(bundle_id)
            if not bundle:
                raise ValueError("Bundle {} not found".format(bundle_id))
            
            # Get current base fee
            block = await self.web3_manager.get_block("latest")
            base_fee = block.get("baseFeePerGas", 0)
            
            # Calculate optimal gas settings
            optimal_settings = {
                "maxFeePerGas": base_fee * 2,  # Double the base fee
                "maxPriorityFeePerGas": min(max_priority_fee, base_fee),  # Cap priority fee
                "gasLimit": block.get("gasLimit", 0) // 2  # Use half block gas limit
            }
            
            logger.info("Optimized gas settings for bundle %s: %s", bundle_id, optimal_settings)
            return optimal_settings
            
        except Exception as e:
            logger.error("Failed to optimize bundle gas: %s", str(e))
            raise
            
    async def _extract_token_transfers_from_logs(
        self,
        logs: List[Dict[str, Any]],
        token_addresses: Optional[List[str]] = None,
        account_to_check: Optional[str] = None
    ) -> Dict[str, int]:
        """Extract token transfers from transaction logs."""
        try:
            # ERC20 Transfer event signature
            transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
            
            # Create a set of token addresses to check (lowercase for case-insensitive comparison)
            token_set = None
            if token_addresses:
                token_set = {addr.lower() for addr in token_addresses}
            
            # Account to check (lowercase for case-insensitive comparison)
            account = account_to_check.lower() if account_to_check else None
            
            # Track token transfers
            transfers = {}
            
            for log in logs:
                # Check if log is a Transfer event
                if log.get("topics") and len(log["topics"]) > 0 and log["topics"][0] == transfer_topic:
                    # Get contract address (token)
                    token_address = log.get("address", "").lower()
                    
                    # Skip if we're filtering by token and this isn't in our list
                    if token_set and token_address not in token_set:
                        continue
                    
                    # Parse transfer event data
                    # Topics: [0:event_signature, 1:from, 2:to]
                    # Data: amount
                    topics = log.get("topics", [])
                    if len(topics) >= 3:
                        from_addr = Web3.to_checksum_address("0x" + topics[1][-40:]).lower()
                        to_addr = Web3.to_checksum_address("0x" + topics[2][-40:]).lower()
                        
                        # Only track transfers to/from the account we care about
                        if account and (from_addr == account or to_addr == account):
                            amount = int(log.get("data", "0x0"), 16)
                            transfers[token_address] = transfers.get(token_address, 0) + (amount if to_addr == account else -amount)
            
            return transfers
            
        except Exception as e:
            logger.error("Failed to extract token transfers: %s", str(e))
            return {}

    async def validate_and_submit_bundle(
        self,
        bundle_id: str,
        token_addresses: Optional[List[str]] = None,
        min_profit: Optional[int] = None,
        expected_net_change: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Validate bundle balance and submit if valid.
        
        Args:
            bundle_id: ID of the bundle to validate and submit
            token_addresses: List of token addresses to track (optional)
            min_profit: Minimum required profit in wei (optional)
            expected_net_change: Expected token balance changes (optional)
            
        Returns:
            Dict containing submission result and validation details
        """
        try:
            # Ensure we have a balance validator
            if not self.balance_validator:
                await self._setup_balance_validator()
                if not self.balance_validator:
                    raise ValueError("Balance validator not available")
            
            # Make sure the bundle is simulated
            if bundle_id not in self._simulation_results:
                await self.simulate_bundle(bundle_id)
            
            # Validate bundle balance
            validation = await self.balance_validator.validate_bundle_balance(
                bundle_id=bundle_id,
                token_addresses=token_addresses or [],
                expected_profit=min_profit,
                expected_net_change=expected_net_change
            )
            
            # If validation succeeded or no profit check was required, submit the bundle
            if validation["success"] or (min_profit is None and expected_net_change is None):
                # Get target block
                bundle = self._pending_bundles.get(bundle_id)
                if not bundle:
                    raise ValueError(f"Bundle {bundle_id} not found")
                
                target_block = bundle.get("blockNumber")
                result = await self.submit_bundle(bundle_id, target_block)
                
                return {"submit_result": result, "validation": validation}
            else:
                return {"submit_result": None, "validation": validation, "status": "rejected"}
                
        except Exception as e:
            logger.error(f"Failed to validate and submit bundle: {e}")
            raise
