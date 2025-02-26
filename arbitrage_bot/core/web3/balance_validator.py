"""Balance validator for transaction bundles and flash loans."""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from decimal import Decimal
from web3 import Web3

logger = logging.getLogger(__name__)

class BalanceValidationError(Exception):
    """Error raised when balance validation fails."""
    pass

class BundleBalanceValidator:
    """Validates token balances before and after bundle execution."""

    def __init__(self, web3_manager):
        """Initialize balance validator."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self._validation_lock = asyncio.Lock()
        self._tracked_tokens = {}  # address -> {symbol, decimals}
        logger.info("Bundle balance validator initialized")

    async def register_token(self, token_address: str, symbol: Optional[str] = None) -> bool:
        """Register a token for balance tracking."""
        token_address = Web3.to_checksum_address(token_address)
        
        if token_address in self._tracked_tokens:
            return True
            
        try:
            # Get token contract
            token_contract = await self.web3_manager.get_token_contract(token_address)
            if not token_contract:
                logger.error(f"Failed to get contract for token {token_address}")
                return False
                
            # Get token metadata
            decimals = await self.web3_manager.call_contract_function(
                token_contract.functions.decimals
            )
            
            if not symbol:
                symbol = await self.web3_manager.call_contract_function(
                    token_contract.functions.symbol
                )
                
            self._tracked_tokens[token_address] = {
                "symbol": symbol,
                "decimals": int(decimals)
            }
            
            logger.info(f"Registered token {symbol} ({token_address}) with {decimals} decimals")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register token {token_address}: {e}")
            return False

    async def get_token_balance(
        self, 
        token_address: str, 
        wallet_address: Optional[str] = None,
        block_identifier: Optional[str] = "latest"
    ) -> Optional[int]:
        """Get token balance for a wallet."""
        try:
            token_address = Web3.to_checksum_address(token_address)
            wallet = wallet_address or self.web3_manager.wallet_address
            
            if token_address == "0x0000000000000000000000000000000000000000":
                # ETH balance
                balance = await self.w3.eth.get_balance(wallet, block_identifier)
                return balance
                
            # Get token contract
            token_contract = await self.web3_manager.get_token_contract(token_address)
            if not token_contract:
                logger.error(f"Failed to get contract for token {token_address}")
                return None
                
            # Get balance
            balance = await self.web3_manager.call_contract_function(
                token_contract.functions.balanceOf, wallet
            )
            
            return int(balance)
            
        except Exception as e:
            logger.error(f"Failed to get token balance for {token_address}: {e}")
            return None

    async def validate_bundle_balance(
        self,
        bundle_id: str,
        token_addresses: List[str],
        account_to_check: Optional[str] = None,
        expected_profit: Optional[int] = None,
        expected_net_change: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Validate token balances before and after bundle execution.
        
        Args:
            bundle_id: Flashbots bundle ID
            token_addresses: List of token addresses to check
            account_to_check: Account to check balances for (defaults to wallet address)
            expected_profit: Expected profit in wei (optional)
            expected_net_change: Expected token balance changes (optional)
            
        Returns:
            Dict with validation results
        """
        if not hasattr(self.web3_manager, 'flashbots_manager'):
            raise BalanceValidationError("Flashbots manager not available")
            
        async with self._validation_lock:
            # Initialize result
            result = {
                "success": False,
                "bundle_id": bundle_id,
                "balances_before": {},
                "balances_after": {},
                "net_changes": {},
                "profit_verified": False,
                "expected_profit": expected_profit,
                "actual_profit": 0,
                "errors": []
            }
            
            account = account_to_check or self.web3_manager.wallet_address
            if not account:
                result["errors"].append("No account specified for balance validation")
                return result
                
            # Get current block number
            current_block = await self.w3.eth.block_number
            
            # Register tokens if needed
            for token_address in token_addresses:
                if token_address not in self._tracked_tokens:
                    await self.register_token(token_address)
            
            # Get balances before simulation
            for token_address in token_addresses:
                balance = await self.get_token_balance(token_address, account)
                if balance is not None:
                    result["balances_before"][token_address] = balance
                else:
                    result["errors"].append(f"Failed to get balance for {token_address}")
            
            try:
                # Get bundle from flashbots manager
                bundle = self.web3_manager.flashbots_manager._pending_bundles.get(bundle_id)
                if not bundle:
                    result["errors"].append(f"Bundle {bundle_id} not found")
                    return result
                
                # Simulate bundle
                simulation = await self.web3_manager.flashbots_manager.simulate_bundle(
                    bundle_id, block_tag=str(current_block)
                )
                
                if not simulation:
                    result["errors"].append("Bundle simulation failed")
                    return result
                
                # Get balances after simulation from simulation results
                if "balances" in simulation and account in simulation["balances"]:
                    eth_balance_before = simulation["balances"][account].get("before", 0)
                    eth_balance_after = simulation["balances"][account].get("after", 0)
                    
                    # Add ETH balance to results
                    eth_address = "0x0000000000000000000000000000000000000000"
                    if eth_address not in result["balances_before"]:
                        result["balances_before"][eth_address] = eth_balance_before
                    if eth_address not in token_addresses:
                        token_addresses.append(eth_address)
                    result["balances_after"][eth_address] = eth_balance_after
                
                # Extract token transfers
                token_transfers = {}
                if "logs" in simulation and hasattr(self.web3_manager.flashbots_manager, '_extract_token_transfers_from_logs'):
                    token_transfers = await self.web3_manager.flashbots_manager._extract_token_transfers_from_logs(
                        simulation["logs"], token_addresses, account
                    )
                    
                    # Update balances after from transfers
                    for token_address, amount in token_transfers.items():
                        if token_address in result["balances_before"]:
                            before = result["balances_before"][token_address]
                            result["balances_after"][token_address] = before + amount
                
                # For any missing balances, fetch them directly
                for token_address in token_addresses:
                    if token_address not in result["balances_after"]:
                        balance = await self.get_token_balance(token_address, account)
                        if balance is not None:
                            result["balances_after"][token_address] = balance
                
                # Calculate net changes
                eth_profit = 0
                for token_address in token_addresses:
                    if token_address in result["balances_before"] and token_address in result["balances_after"]:
                        before = result["balances_before"][token_address]
                        after = result["balances_after"][token_address]
                        net_change = after - before
                        result["net_changes"][token_address] = net_change
                        
                        # Check if ETH/native token changed
                        if token_address == "0x0000000000000000000000000000000000000000":
                            eth_profit = net_change
                
                # Validate expected profit if provided
                if expected_profit is not None:
                    profit_margin = expected_profit * 0.05  # 5% margin
                    min_profit = expected_profit - profit_margin
                    max_profit = expected_profit + profit_margin
                    
                    result["actual_profit"] = eth_profit
                    result["profit_verified"] = min_profit <= eth_profit <= max_profit
                    
                    if not result["profit_verified"]:
                        result["errors"].append(
                            f"Profit verification failed: expected {expected_profit}, got {eth_profit}"
                        )
                
                # Validate expected net changes if provided
                if expected_net_change:
                    all_verified = True
                    for token_address, expected_change in expected_net_change.items():
                        if token_address in result["net_changes"]:
                            actual_change = result["net_changes"][token_address]
                            margin = expected_change * 0.05  # 5% margin
                            min_change = expected_change - margin
                            max_change = expected_change + margin
                            
                            if not (min_change <= actual_change <= max_change):
                                all_verified = False
                                result["errors"].append(
                                    f"Balance change verification failed for {token_address}: " +
                                    f"expected {expected_change}, got {actual_change}"
                                )
                    
                    result["balance_changes_verified"] = all_verified
                
                # Set success flag
                result["success"] = len(result["errors"]) == 0
                
                if result["success"]:
                    logger.info(f"Bundle {bundle_id} balance validation succeeded")
                else:
                    logger.warning(f"Bundle {bundle_id} balance validation failed: {result['errors']}")
                
                return result
                
            except Exception as e:
                logger.error(f"Error during bundle balance validation: {e}")
                result["errors"].append(f"Validation error: {str(e)}")
                return result

    async def validate_flash_loan(
        self,
        tx_hash: str,
        borrowed_token: str,
        borrowed_amount: int,
        expected_profit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate a flash loan transaction.
        
        Args:
            tx_hash: Transaction hash
            borrowed_token: Borrowed token address
            borrowed_amount: Borrowed amount in token units
            expected_profit: Expected profit in wei (optional)
            
        Returns:
            Dict with validation results
        """
        async with self._validation_lock:
            # Initialize result
            result = {
                "success": False,
                "tx_hash": tx_hash,
                "borrowed_token": borrowed_token,
                "borrowed_amount": borrowed_amount,
                "loan_repaid": False,
                "profit_verified": False,
                "errors": []
            }
            
            try:
                # Register token if needed
                if borrowed_token not in self._tracked_tokens:
                    await self.register_token(borrowed_token)
                
                # Get transaction receipt
                receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
                if not receipt:
                    result["errors"].append("Transaction not found")
                    return result
                
                # Check transaction status
                if receipt.status != 1:
                    result["errors"].append("Transaction failed")
                    return result
                
                # Get event logs
                logs = receipt.logs
                
                # Extract token transfers
                account = self.web3_manager.wallet_address
                token_addresses = [borrowed_token, "0x0000000000000000000000000000000000000000"]
                
                # Extract token transfers if flashbots manager is available
                token_transfers = {}
                if hasattr(self.web3_manager, 'flashbots_manager') and hasattr(self.web3_manager.flashbots_manager, '_extract_token_transfers_from_logs'):
                    token_transfers = await self.web3_manager.flashbots_manager._extract_token_transfers_from_logs(
                        logs, token_addresses, account
                    )
                
                # Check if borrowed token was returned
                if borrowed_token in token_transfers:
                    net_change = token_transfers[borrowed_token]
                    result["loan_repaid"] = net_change >= 0
                    
                    if not result["loan_repaid"]:
                        result["errors"].append(f"Flash loan not repaid: {net_change}")
                else:
                    result["errors"].append("No token transfers found for borrowed token")
                
                # Check profit if expected
                if expected_profit is not None and "0x0000000000000000000000000000000000000000" in token_transfers:
                    eth_profit = token_transfers["0x0000000000000000000000000000000000000000"]
                    profit_margin = expected_profit * 0.05  # 5% margin
                    min_profit = expected_profit - profit_margin
                    max_profit = expected_profit + profit_margin
                    
                    result["actual_profit"] = eth_profit
                    result["profit_verified"] = min_profit <= eth_profit <= max_profit
                    
                    if not result["profit_verified"]:
                        result["errors"].append(
                            f"Profit verification failed: expected {expected_profit}, got {eth_profit}"
                        )
                
                # Set success flag
                result["success"] = result["loan_repaid"] and (
                    expected_profit is None or result["profit_verified"]
                )
                
                if result["success"]:
                    logger.info(f"Flash loan {tx_hash} validation succeeded")
                else:
                    logger.warning(f"Flash loan {tx_hash} validation failed: {result['errors']}")
                
                return result
                
            except Exception as e:
                logger.error(f"Error during flash loan validation: {e}")
                result["errors"].append(f"Validation error: {str(e)}")
                return result

async def create_balance_validator(web3_manager) -> BundleBalanceValidator:
    """Create and initialize a balance validator."""
    try:
        validator = BundleBalanceValidator(web3_manager)
        logger.info("Created bundle balance validator")
        return validator
    except Exception as e:
        logger.error(f"Failed to create balance validator: {e}")
        raise