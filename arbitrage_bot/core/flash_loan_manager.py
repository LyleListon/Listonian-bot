"""
Flash loan management for arbitrage operations.

This module now uses the unified flash loan manager implementation internally
while maintaining backward compatibility with existing code.

DEPRECATED: Use unified_flash_loan_manager.py instead.
"""

import logging
import warnings
from typing import Dict, List, Any, Optional
from decimal import Decimal
from web3 import Web3
from eth_typing import Address

from .unified_flash_loan_manager import UnifiedFlashLoanManager, create_flash_loan_manager_sync

logger = logging.getLogger(__name__)

# Emit deprecation warning
warnings.warn(
    "The FlashLoanManager class is deprecated. "
    "Use UnifiedFlashLoanManager from unified_flash_loan_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

class FlashLoanManager:
    """
    Manages flash loan operations for arbitrage.
    
    DEPRECATED: Use UnifiedFlashLoanManager instead.
    
    This class now serves as a compatibility wrapper around UnifiedFlashLoanManager,
    providing the same interface as the original FlashLoanManager but using the
    unified implementation internally.
    """
    
    def __init__(self, web3_manager: Any, config: Dict[str, Any]):
        """Initialize flash loan manager."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self.enabled = config.get('flash_loans', {}).get('enabled', False)
        self.initialized = False
        
        # Contract addresses
        self.arbitrage_contract = None
        self.arbitrage_abi = None
        self.weth_address = config.get('tokens', {}).get('WETH')
        self.usdc_address = config.get('tokens', {}).get('USDC')
        
        # Parameters
        self.min_profit_bps = config.get('flash_loans', {}).get('min_profit_basis_points', 200)
        self.max_trade_size = Web3.to_wei(config.get('flash_loans', {}).get('max_trade_size', '0.1'), 'ether')
        
        # Create the unified manager internally
        self._unified_manager = None
        
        logger.info("FlashLoanManager initialized (compatibility wrapper)")
        
        if not self.enabled:
            logger.warning("Flash loans are currently disabled in config")
    
    def initialize(self) -> bool:
        """Initialize flash loan manager."""
        try:
            if not self.enabled:
                logger.info("Flash loans are disabled, skipping initialization")
                return True
            
            # Create and initialize the unified manager if needed
            if self._unified_manager is None:
                self._unified_manager = create_flash_loan_manager_sync(
                    web3_manager=self.web3_manager,
                    config=self.config
                )
            
            # Get unified manager's contract
            self.arbitrage_contract = self._unified_manager.arbitrage_contract
            self.arbitrage_abi = self._unified_manager.arbitrage_abi
            
            if self.arbitrage_contract:
                self.initialized = True
                logger.info(f"Flash loan manager initialized with contract at {self.arbitrage_contract.address}")
                return True
            else:
                logger.error("No flash loan contract address available")
                return False
            
        except Exception as e:
            logger.error(f"Failed to initialize flash loan manager: {e}")
            return False
    
    def check_flash_loan_availability(self, token_address: str, amount: Decimal) -> bool:
        """
        Check if flash loan is available for given token and amount.
        
        Args:
            token_address (str): Token address
            amount (Decimal): Amount to borrow
            
        Returns:
            bool: True if flash loan is available
        """
        if not self.enabled or not self.initialized:
            return False
        
        if self._unified_manager is None:
            return False
            
        # Use unified manager's implementation
        return self._unified_manager.is_token_supported_sync(token_address)
    
    def estimate_flash_loan_cost(self, token_address: str, amount: Decimal) -> Decimal:
        """
        Estimate cost of flash loan.
        
        Args:
            token_address (str): Token address
            amount (Decimal): Amount to borrow
            
        Returns:
            Decimal: Estimated cost in token units
        """
        if not self.enabled or not self.initialized:
            return Decimal('0')
            
        if self._unified_manager is None:
            # Old implementation as fallback
            fee_rate = Decimal('0.0009')
            return amount * fee_rate
            
        # Use unified manager's implementation
        cost_info = self._unified_manager.estimate_flash_loan_cost_sync(token_address, amount)
        return Decimal(str(cost_info["protocol_fee"]))
    
    def prepare_flash_loan(self, token_address: str, amount: Decimal) -> Optional[Dict[str, Any]]:
        """
        Prepare flash loan transaction data.
        
        Args:
            token_address (str): Token address
            amount (Decimal): Amount to borrow
            
        Returns:
            Optional[Dict[str, Any]]: Transaction data if successful
        """
        if not self.enabled or not self.initialized:
            return None
            
        try:
            amount_wei = Web3.to_wei(amount, 'ether')
            
            if self._unified_manager is None:
                # Old implementation as fallback
                return {
                    'token': Web3.to_checksum_address(token_address),
                    'amount': amount_wei,
                    'contract': self.arbitrage_contract.address if self.arbitrage_contract else None
                }
            
            # Use unified manager's implementation
            # Note: This doesn't provide the exact same output format as before,
            # but it contains the necessary information
            result = self._unified_manager.prepare_flash_loan_transaction_sync(
                token_address=token_address,
                amount=amount_wei,
                route=[],  # Empty route as this wasn't required in original implementation
                min_profit=0
            )
            
            if result["success"]:
                return {
                    'token': Web3.to_checksum_address(token_address),
                    'amount': amount_wei,
                    'contract': self.arbitrage_contract.address if self.arbitrage_contract else None,
                    'transaction': result.get('transaction', {})
                }
            else:
                return None
            
        except Exception as e:
            logger.error(f"Error preparing flash loan: {e}")
            return None
            
    def execute_arbitrage(
        self,
        token_in: str,
        token_out: str,
        amount: int,
        buy_dex: str,
        sell_dex: str,
        min_profit: int
    ) -> Optional[Dict[str, Any]]:
        """
        Execute flash loan arbitrage.
        
        Args:
            token_in (str): Input token address
            token_out (str): Output token address
            amount (int): Amount to borrow
            buy_dex (str): DEX to buy from
            sell_dex (str): DEX to sell on
            min_profit (int): Minimum profit in wei
            
        Returns:
            Optional[Dict[str, Any]]: Transaction receipt if successful
        """
        if not self.enabled or not self.initialized:
            return None
            
        # Construct a simplified route for unified manager
        route = [
            {
                "dex_id": int(buy_dex) if buy_dex.isdigit() else 1,
                "token_in": token_in,
                "token_out": token_out
            },
            {
                "dex_id": int(sell_dex) if sell_dex.isdigit() else 2,
                "token_in": token_out,
                "token_out": token_in
            }
        ]
        
        if self._unified_manager is None:
            logger.error("Unified manager not initialized")
            return None
        
        # Use unified manager's implementation
        result = self._unified_manager.execute_flash_loan_arbitrage_sync(
            token_address=token_in,
            amount=amount,
            route=route,
            min_profit=min_profit,
            use_flashbots=False  # Original implementation didn't use Flashbots
        )
        
        if result["success"]:
            # Try to format result similar to original implementation
            if "transaction_hash" in result:
                try:
                    receipt = self.w3.eth.get_transaction_receipt(result["transaction_hash"])
                    return receipt
                except Exception:
                    return result
            return result
        else:
            logger.error(f"Error executing flash loan arbitrage: {result.get('error')}")
            return None


def create_flash_loan_manager(
    web3_manager: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None
) -> FlashLoanManager:
    """
    Create and initialize a flash loan manager instance.
    
    DEPRECATED: Use create_flash_loan_manager_sync from unified_flash_loan_manager instead.
    
    Args:
        web3_manager: Optional Web3Manager instance
        config: Optional configuration dictionary
        
    Returns:
        FlashLoanManager: Initialized flash loan manager
    """
    warnings.warn(
        "create_flash_loan_manager is deprecated. "
        "Use create_flash_loan_manager_sync from unified_flash_loan_manager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    try:
        # Load dependencies if not provided
        if web3_manager is None or config is None:
            # Import here to avoid circular imports
            from .web3.web3_manager import create_web3_manager
            from ..utils.config_loader import load_config
            
            if config is None:
                config = load_config()
            
            if web3_manager is None:
                web3_manager = create_web3_manager()
        
        # Create manager instance
        manager = FlashLoanManager(web3_manager=web3_manager, config=config)
        manager.initialize()
        logger.info("Flash loan manager created (compatibility wrapper)")
        return manager
        
    except Exception as e:
        logger.error(f"Failed to create flash loan manager: {e}")
        raise
