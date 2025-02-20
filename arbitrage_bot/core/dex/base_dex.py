"""Base DEX abstract class providing common functionality for DEX implementations."""

import logging
import time
import eventlet
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Set
from decimal import Decimal
from web3.types import TxReceipt
from web3 import Web3

from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)

# Common DEX method signatures
COMMON_METHOD_SIGNATURES = {
    'swapExactTokensForTokens': '0x38ed1739',
    'swapTokensForExactTokens': '0x8803dbee',
    'swapExactETHForTokens': '0x7ff36ab5',
    'swapTokensForExactETH': '0x4a25d94a',
    'swapExactTokensForETH': '0x18cbafe5',
    'swapETHForExactTokens': '0xfb3bdb41',
    'exactInput': '0xc04b8d59',
    'exactInputSingle': '0x414bf389',
    'exactOutput': '0xf28c0498',
    'exactOutputSingle': '0xdb3e2198'
}

class BaseDEX(ABC):
    """Abstract base class for DEX implementations."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """
        Initialize base DEX functionality.

        Args:
            web3_manager: Web3Manager instance for blockchain interaction
            config: Configuration dictionary containing:
                - router: Router contract address
                - factory: Factory contract address
                - fee: Trading fee (optional)
                - quoter: Quoter contract address (optional, for V3)
                - wallet: Wallet configuration (optional)
                - name: DEX name for ABI loading (required)
        """
        self.w3 = web3_manager.w3
        self.web3_manager = web3_manager
        self.config = config
        self.router_address = config['router']
        self.factory_address = config['factory']
        self.name = config.get('name', 'unknown')  # Add name parameter
        self.initialized = False
        
        # Initialize contracts
        self.router = None
        self.factory = None
        self.router_contract = None
        self.factory_contract = None
        
        # Set up logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_method_signatures(self) -> Set[str]:
        """Get common method signatures for this DEX."""
        return set(COMMON_METHOD_SIGNATURES.values())

    def get_router_address(self) -> str:
        """Get router contract address."""
        return self.router_address

    def check_and_approve_token(self, token_address: str, amount: int) -> bool:
        """
        Check and approve token spending for router.
        Uses EIP-1559 gas parameters for approval transactions.

        Args:
            token_address: Token contract address
            amount: Amount to approve

        Returns:
            bool: True if approved, False otherwise
        """
        try:
            # Get token contract
            token_contract = self.web3_manager.get_token_contract(token_address)
            
            # Get current allowance
            current_allowance = token_contract.functions.allowance(
                self.web3_manager.wallet_address,
                self.router_address
            ).call()
            
            # If allowance is sufficient, return True
            if current_allowance >= amount:
                self.logger.debug(f"Token {token_address} already approved for {current_allowance}")
                return True
                
            # Get initial balance to verify approval
            balance_before = token_contract.functions.balanceOf(
                self.web3_manager.wallet_address
            ).call()
            
            # Get gas parameters for approval
            gas_data = {
                'maxFeePerGas': self.web3_manager.w3.eth.get_block('latest')['baseFeePerGas'] * 2,
                'maxPriorityFeePerGas': self.web3_manager.w3.eth.max_priority_fee_per_gas,
                'gas': 100000  # Standard gas limit for approvals
            }

            # Build and send approval transaction
            receipt = self.web3_manager.build_and_send_transaction(
                token_contract,
                'approve',
                self.router_address,
                amount * 2,  # Double for future use
                tx_params=gas_data
            )

            # Log approval details
            self.logger.info(
                f"Token approval sent:\n"
                f"Token: {token_address}\n"
                f"Amount: {amount * 2}\n"
                f"TX Hash: {receipt['transactionHash'].hex()}"
            )
            
            if receipt and receipt['status'] == 1:
                # Verify approval by checking allowance
                new_allowance = token_contract.functions.allowance(
                    self.web3_manager.wallet_address,
                    self.router_address
                ).call()
                
                if new_allowance >= amount:
                    self.logger.info(f"Approved {amount} of token {token_address} for router {self.router_address}")
                    return True
                else:
                    self.logger.error(f"Approval verification failed for {token_address}")
                    return False
            else:
                self.logger.error(f"Token approval failed for {token_address}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to approve token {token_address}: {e}")
            return False

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the DEX interface.
        
        Must be implemented by concrete classes to:
        1. Load necessary contract ABIs
        2. Initialize contract instances
        3. Test connections
        4. Set up any DEX-specific requirements
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get quote including price impact and liquidity depth analysis.
        
        Args:
            amount_in: Input amount in wei
            path: List of token addresses in the swap path
            
        Returns:
            Optional[Dict[str, Any]]: Quote details including:
                - amount_in: Input amount
                - amount_out: Expected output amount
                - price_impact: Estimated price impact percentage
                - liquidity_depth: Available liquidity
                - fee_rate: DEX fee rate
                - estimated_gas: Estimated gas cost
                - min_out: Minimum output with slippage
        """
        pass

    def get_amounts_out(self, amount_in: int, path: List[str]) -> List[int]:
        """
        Get expected output amounts for a trade.
        
        Args:
            amount_in: Input amount in wei
            path: List of token addresses in the swap path
            
        Returns:
            List[int]: List of amounts out for each hop in the path
        """
        try:
            quote = self.get_quote_with_impact(amount_in, path)
            if quote:
                return [amount_in, quote['amount_out']]
            return []
        except Exception as e:
            self.logger.error(f"Failed to get amounts out: {e}")
            return []

    @abstractmethod
    def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int,
        gas: Optional[int] = None,
        maxFeePerGas: Optional[int] = None,
        maxPriorityFeePerGas: Optional[int] = None
    ) -> TxReceipt:
        """
        Execute a token swap.
        
        Args:
            amount_in: Input amount in wei
            amount_out_min: Minimum output amount in wei
            path: List of token addresses in the swap path
            to: Recipient address
            deadline: Transaction deadline timestamp
            gas: Gas limit for the transaction
            maxFeePerGas: Maximum fee per gas (EIP-1559)
            maxPriorityFeePerGas: Maximum priority fee per gas (EIP-1559)
            
        Returns:
            TxReceipt: Transaction receipt
            
        Raises:
            Exception: If swap fails
        """
        pass

    def _validate_path(self, path: List[str]) -> bool:
        """
        Validate a trading path.
        
        Args:
            path: List of token addresses
            
        Returns:
            bool: True if path is valid
            
        Raises:
            ValueError: If path is invalid
        """
        if len(path) < 2:
            raise ValueError("Path must contain at least 2 tokens")
            
        for token in path:
            if not self.w3.is_address(token):
                raise ValueError(f"Invalid token address in path: {token}")
                
        return True

    def _validate_amounts(
        self,
        amount_in: Optional[int] = None,
        amount_out_min: Optional[int] = None
    ) -> bool:
        """
        Validate transaction amounts.
        
        Args:
            amount_in: Input amount in wei (optional)
            amount_out_min: Minimum output amount in wei (optional)
            
        Returns:
            bool: True if amounts are valid
            
        Raises:
            ValueError: If amounts are invalid
        """
        if amount_in is not None and amount_in <= 0:
            raise ValueError("Input amount must be positive")
            
        if amount_out_min is not None and amount_out_min <= 0:
            raise ValueError("Minimum output amount must be positive")
            
        return True

    def _handle_error(self, error: Exception, context: str) -> None:
        """
        Standardized error handling.
        
        Args:
            error: Exception that occurred
            context: Context where error occurred
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        self.logger.error(
            f"Error in {context} - {error_type}: {error_msg}",
            exc_info=True
        )
        
        # Re-raise with context
        raise type(error)(
            f"{context} failed: {error_msg}"
        ) from error

    @abstractmethod
    def get_24h_volume(self, token0: str, token1: str) -> Decimal:
        """
        Get 24-hour trading volume for a token pair.
        
        Args:
            token0: First token address
            token1: Second token address
            
        Returns:
            Decimal: 24-hour trading volume in base currency
        """
        pass

    @abstractmethod
    def get_total_liquidity(self) -> Decimal:
        """
        Get total liquidity across all pairs.
        
        Returns:
            Decimal: Total liquidity in base currency
        """
        pass

    def _retry(self, func: Callable, *args, retries=3, delay=1):
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Arguments to pass to the function
            retries: Number of retries
            delay: Initial delay between retries in seconds
            
        Returns:
            Any: Result of the function call
            
        Raises:
            Exception: If all retries fail
        """
        last_error = None
        
        for i in range(retries):
            try:
                # Execute the function
                result = func() if callable(func) else func
                return result
                
            except Exception as e:
                last_error = e
                if i < retries - 1:
                    eventlet.sleep(delay * (2 ** i))
                continue
                
        raise last_error

    def _log_transaction(
        self,
        tx_hash: str,
        amount_in: int,
        amount_out: int,
        path: List[str],
        recipient: str
    ) -> None:
        """
        Log transaction details.
        
        Args:
            tx_hash: Transaction hash
            amount_in: Input amount in wei
            amount_out: Output amount in wei
            path: Trading path
            recipient: Recipient address
        """
        self.logger.info(
            f"\nTransaction Details:\n"
            f"==================\n"
            f"Hash: {tx_hash}\n"
            f"Input Token: {path[0]} (Amount: {amount_in})\n"
            f"Output Token: {path[-1]} (Amount: {amount_out})\n"
            f"Recipient: {recipient}\n"
        )

    @abstractmethod
    def get_token_price(self, token_address: str) -> float:
        """
        Get current price for a token.
        
        Args:
            token_address: Token contract address
            
        Returns:
            float: Current token price in base currency
            
        Raises:
            ValueError: If token address is invalid or price cannot be fetched
        """
        pass

    def get_supported_tokens(self) -> List[str]:
        """
        Get list of supported tokens for this DEX.
        
        Returns:
            List[str]: List of supported token addresses
        """
        try:
            # Get tokens from config
            tokens = self.config.get('tokens', {})
            return [token['address'] for token in tokens.values()]
            
        except Exception as e:
            self.logger.error(f"Failed to get supported tokens: {e}")
            return []
