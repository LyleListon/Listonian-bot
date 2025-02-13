"""Base DEX abstract class providing common functionality for DEX implementations."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from decimal import Decimal
from web3.types import TxReceipt

from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)

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
        """
        self.w3 = web3_manager.w3
        self.web3_manager = web3_manager
        self.config = config
        self.router_address = config['router']
        self.factory_address = config['factory']
        self.initialized = False
        
        # Initialize contracts
        self.router = None
        self.factory = None
        self.router_contract = None
        self.factory_contract = None
        
        # Set up logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def initialize(self) -> bool:
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
    async def get_quote_with_impact(
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

    async def get_amounts_out(self, amount_in: int, path: List[str]) -> List[int]:
        """
        Get expected output amounts for a trade.
        
        Args:
            amount_in: Input amount in wei
            path: List of token addresses in the swap path
            
        Returns:
            List[int]: List of amounts out for each hop in the path
        """
        try:
            quote = await self.get_quote_with_impact(amount_in, path)
            if quote:
                return [amount_in, quote['amount_out']]
            return []
        except Exception as e:
            self.logger.error(f"Failed to get amounts out: {e}")
            return []

    @abstractmethod
    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        path: List[str],
        to: str,
        deadline: int
    ) -> TxReceipt:
        """
        Execute a token swap.
        
        Args:
            amount_in: Input amount in wei
            amount_out_min: Minimum output amount in wei
            path: List of token addresses in the swap path
            to: Recipient address
            deadline: Transaction deadline timestamp
            
        Returns:
            TxReceipt: Transaction receipt
            
        Raises:
            Exception: If swap fails
        """
        pass

    async def _validate_path(self, path: List[str]) -> bool:
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

    async def _validate_amounts(
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
    async def get_24h_volume(self, token0: str, token1: str) -> Decimal:
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
    async def get_total_liquidity(self) -> Decimal:
        """
        Get total liquidity across all pairs.
        
        Returns:
            Decimal: Total liquidity in base currency
        """
        pass

    async def _retry_async(self, func, *args, retries=3, delay=1):
        """
        Retry an async function with exponential backoff.
        
        Args:
            func: Function to retry (can be sync or async)
            *args: Arguments to pass to the function
            retries: Number of retries
            delay: Initial delay between retries in seconds
            
        Returns:
            Any: Result of the function call
            
        Raises:
            Exception: If all retries fail
        """
        import asyncio
        last_error = None
        
        for i in range(retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args)
                else:
                    # If it's a contract function, call it
                    if hasattr(func, 'call'):
                        result = func.call()
                    else:
                        result = func(*args)
                return result
            except Exception as e:
                last_error = e
                if i < retries - 1:
                    await asyncio.sleep(delay * (2 ** i))
                continue
                
        raise last_error

    def _log_transaction(
        self,
        tx_hash: str,
        amount_in: int,
        amount_out: int,
        path: List[str]
    ) -> None:
        """
        Log transaction details.
        
        Args:
            tx_hash: Transaction hash
            amount_in: Input amount in wei
            amount_out: Output amount in wei
            path: Trading path
        """
        self.logger.info(
            f"Transaction executed - Hash: {tx_hash}\n"
            f"Input: {amount_in} {path[0]}\n"
            f"Output: {amount_out} {path[-1]}"
        )
