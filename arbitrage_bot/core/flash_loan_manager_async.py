"""
Async Flash Loan Manager Module

This module provides asynchronous flash loan management capabilities for arbitrage operations.

DEPRECATED: Use unified_flash_loan_manager.py instead.
"""

import logging
import warnings
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Emit deprecation warning
warnings.warn(
    "The AsyncFlashLoanManager class is deprecated. "
    "Use UnifiedFlashLoanManager from unified_flash_loan_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

class AsyncFlashLoanManager:
    """
    Manages flash loan operations asynchronously.
    
    DEPRECATED: Use UnifiedFlashLoanManager instead.
    
    This class now serves as a compatibility wrapper around UnifiedFlashLoanManager,
    providing the same interface as the original AsyncFlashLoanManager but using the
    unified implementation internally.
    """
    
    def __init__(self, web3_manager, config: Dict[str, Any], flashbots_manager=None):
        """
        Initialize the AsyncFlashLoanManager.
        
        Args:
            web3_manager: Web3Manager instance
            config: Configuration dictionary
            flashbots_manager: FlashbotsManager instance
        """
        self.web3_manager = web3_manager
        self.flashbots_manager = flashbots_manager
        
        # Get flash loan config
        flash_config = config.get('flash_loans', {})
        
        # Set properties from config
        self.enabled = flash_config.get('enabled', True)
        self.use_flashbots = flash_config.get('use_flashbots', True)
        self.min_profit_basis_points = flash_config.get('min_profit_basis_points', 200)
        self.max_trade_size = flash_config.get('max_trade_size', '1')
        self.slippage_tolerance = flash_config.get('slippage_tolerance', 50)
        self.transaction_timeout = flash_config.get('transaction_timeout', 180)
        self.balancer_vault = flash_config.get('balancer_vault', '0xBA12222222228d8Ba445958a75a0704d566BF2C8')
        
        # Get contract addresses
        contract_addresses = flash_config.get('contract_address', {})
        self.contract_address = contract_addresses.get('mainnet', '')
        
        # Import UnifiedFlashLoanManager here to avoid circular imports
        from .unified_flash_loan_manager import UnifiedFlashLoanManager
        self._unified_manager = UnifiedFlashLoanManager(web3_manager, config, flashbots_manager)
        
        logger.info("AsyncFlashLoanManager initialized (compatibility wrapper)")
        logger.info("Flash loans enabled: %s", self.enabled)
        logger.info("Using Flashbots: %s", self.use_flashbots)
    
    async def _ensure_initialized(self):
        """Ensure the unified manager is initialized."""
        if not self._unified_manager.initialized:
            await self._unified_manager.initialize()
    
    async def validate_arbitrage_opportunity(self, 
                                          input_token: str, 
                                          output_token: str, 
                                          input_amount: int,
                                          expected_output: int,
                                          route: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate an arbitrage opportunity accounting for flash loan costs.
        
        Args:
            input_token: Address of the input token
            output_token: Address of the output token
            input_amount: Amount of input token in wei
            expected_output: Expected amount of output token in wei
            route: List of steps in the arbitrage route
            
        Returns:
            Validation result with profitability assessment
        """
        await self._ensure_initialized()
        
        return await self._unified_manager.validate_arbitrage_opportunity(
            input_token=input_token,
            output_token=output_token,
            input_amount=input_amount,
            expected_output=expected_output,
            route=route
        )
    
    async def prepare_flash_loan_transaction(self,
                                          token_address: str,
                                          amount: int,
                                          route: List[Dict[str, Any]],
                                          min_profit: int = 0) -> Dict[str, Any]:
        """
        Prepare a flash loan transaction.
        
        Args:
            token_address: Address of the token to borrow
            amount: Amount to borrow in wei
            route: List of steps in the arbitrage route
            min_profit: Minimum profit threshold
            
        Returns:
            Prepared transaction details
        """
        await self._ensure_initialized()
        
        return await self._unified_manager.prepare_flash_loan_transaction(
            token_address=token_address,
            amount=amount,
            route=route,
            min_profit=min_profit
        )
    
    async def execute_flash_loan_arbitrage(self,
                                        token_address: str,
                                        amount: int,
                                        route: List[Dict[str, Any]],
                                        min_profit: int,
                                        use_flashbots: bool = None) -> Dict[str, Any]:
        """
        Execute a flash loan arbitrage.
        
        Args:
            token_address: Address of the token to borrow
            amount: Amount to borrow in wei
            route: List of steps in the arbitrage route
            min_profit: Minimum profit threshold
            use_flashbots: Whether to use Flashbots (overrides default)
            
        Returns:
            Execution result
        """
        await self._ensure_initialized()
        
        # Set use_flashbots if provided, otherwise use default
        use_flashbots = use_flashbots if use_flashbots is not None else self.use_flashbots
        
        return await self._unified_manager.execute_flash_loan_arbitrage(
            token_address=token_address,
            amount=amount,
            route=route,
            min_profit=min_profit,
            use_flashbots=use_flashbots
        )
    
    async def is_token_supported(self, token_address: str) -> bool:
        """
        Check if a token is supported for flash loans.
        
        Args:
            token_address: Token address to check
            
        Returns:
            bool: True if token is supported
        """
        await self._ensure_initialized()
        return await self._unified_manager.is_token_supported(token_address)
    
    async def get_max_flash_loan_amount(self, token_address: str) -> int:
        """
        Get maximum flash loan amount for a token.
        
        Args:
            token_address: Token address
            
        Returns:
            int: Maximum loan amount in wei
        """
        await self._ensure_initialized()
        return await self._unified_manager.get_max_flash_loan_amount(token_address)
    
    async def get_supported_tokens(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a dictionary of supported tokens for flash loans.
        
        Returns:
            Dictionary mapping token addresses to token info
        """
        await self._ensure_initialized()
        return await self._unified_manager.get_supported_tokens()
    
    async def close(self):
        """Close the flash loan manager and release resources."""
        if self._unified_manager is not None:
            await self._unified_manager.close()
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_initialized()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


async def create_flash_loan_manager(web3_manager, config: Dict[str, Any] = None, flashbots_manager = None) -> AsyncFlashLoanManager:
    """
    Create and initialize an AsyncFlashLoanManager instance.
    
    DEPRECATED: Use create_flash_loan_manager from unified_flash_loan_manager instead.
    
    Args:
        web3_manager: Web3Manager instance
        config: Configuration dictionary
        flashbots_manager: FlashbotsManager instance
        
    Returns:
        Initialized AsyncFlashLoanManager instance
    """
    warnings.warn(
        "This create_flash_loan_manager function is deprecated. "
        "Use create_flash_loan_manager from unified_flash_loan_manager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Create AsyncFlashLoanManager
    flash_loan_manager = AsyncFlashLoanManager(web3_manager, config, flashbots_manager)
    
    # Ensure it's initialized
    await flash_loan_manager._ensure_initialized()
    
    return flash_loan_manager