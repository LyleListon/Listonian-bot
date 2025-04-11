"""
Flash Loan Interfaces

This module defines the protocols and data models for flash loan interactions.
These protocols provide a standard interface for different flash loan providers.
"""

# import asyncio # Unused
import logging
# from abc import ABC # Unused
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto
from typing import ( # Removed Callable, Union, TypeVar
    Dict,
    List,
    Protocol,
    Any,
    Optional,
    runtime_checkable,
)
from datetime import datetime

from ....core.web3.interfaces import TransactionReceipt # Removed Web3Client, Transaction

logger = logging.getLogger(__name__)


class FlashLoanStatus(Enum):
    """Status of a flash loan operation."""

    PENDING = auto()
    EXECUTED = auto()
    FAILED = auto()
    REVERTED = auto()
    TIMEOUT = auto()


@dataclass
class TokenAmount:
    """Represents an amount of a specific token."""

    token_address: str
    amount: Decimal
    decimals: int = 18

    @property
    def raw_amount(self) -> int:
        """Get the raw amount in the token's smallest unit."""
        return int(self.amount * (10**self.decimals))


@dataclass
class FlashLoanParams:
    """
    Parameters for a flash loan request.

    Attributes:
        token_amounts: Mapping of token addresses to amounts to borrow
        receiver_address: Address that will receive the flash loan
        callback_data: Optional data to pass to the callback function
        referral_code: Optional referral code for the flash loan provider
        max_fee: Maximum acceptable fee for the flash loan
        deadline: Deadline for the flash loan execution (timestamp)
        slippage_tolerance: Maximum acceptable slippage (as a percentage)
        transaction_params: Additional parameters for the transaction
    """

    token_amounts: List[TokenAmount]
    receiver_address: str
    callback_data: Optional[bytes] = None
    referral_code: Optional[int] = None
    max_fee: Optional[Decimal] = None
    deadline: Optional[int] = None
    slippage_tolerance: Decimal = Decimal("0.005")  # 0.5% default
    transaction_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate parameters after initialization."""
        if not self.token_amounts:
            raise ValueError("At least one token amount must be specified")

        if not self.receiver_address:
            raise ValueError("Receiver address must be specified")

        # Set default deadline if not provided
        if self.deadline is None:
            # Default to 10 minutes from now
            self.deadline = int(datetime.now().timestamp()) + 600


@dataclass
class FlashLoanResult:
    """
    Result of a flash loan operation.

    Attributes:
        success: Whether the flash loan was successful
        transaction_hash: Hash of the transaction
        transaction_receipt: Receipt of the transaction
        status: Status of the flash loan
        tokens_borrowed: List of borrowed token amounts
        fee_paid: Fee paid for the flash loan
        gas_used: Gas used for the transaction
        execution_time: Time taken to execute the flash loan (seconds)
        error_message: Error message if the flash loan failed
        logs: Logs from the flash loan transaction
    """

    success: bool
    transaction_hash: Optional[str] = None
    transaction_receipt: Optional[TransactionReceipt] = None
    status: FlashLoanStatus = FlashLoanStatus.PENDING
    tokens_borrowed: List[TokenAmount] = field(default_factory=list)
    fee_paid: Optional[Decimal] = None
    gas_used: Optional[int] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_borrowed(self) -> Decimal:
        """Calculate total amount borrowed in base currency."""
        # This is a placeholder - in a real implementation, this would
        # convert all borrowed tokens to a base currency using price feeds
        return sum(token.amount for token in self.tokens_borrowed)


@runtime_checkable
class FlashLoanCallback(Protocol):
    """
    Protocol for flash loan callbacks.

    Any class implementing this protocol can be used as a callback
    for flash loan operations.
    """

    async def on_flash_loan(
        self,
        sender: str,
        tokens: List[str],
        amounts: List[int],
        fees: List[int],
        user_data: bytes,
    ) -> bool:
        """
        Called when a flash loan is received.

        Args:
            sender: Address of the flash loan provider
            tokens: List of token addresses received
            amounts: List of token amounts received
            fees: List of fees to pay for each token
            user_data: Custom data passed by the user

        Returns:
            True if the operation succeeded, False otherwise
        """
        ...

    async def on_flash_loan_completed(self, result: FlashLoanResult) -> None:
        """
        Called when a flash loan is completed.

        Args:
            result: Result of the flash loan operation
        """
        ...

    async def on_flash_loan_failed(self, result: FlashLoanResult) -> None:
        """
        Called when a flash loan fails.

        Args:
            result: Result of the flash loan operation
        """
        ...


@runtime_checkable
class FlashLoanProvider(Protocol):
    """
    Protocol for flash loan providers.

    Any class implementing this protocol can be used as a flash loan provider
    in the arbitrage system.
    """

    @property
    def name(self) -> str:
        """Get the name of the flash loan provider."""
        ...

    @property
    def supported_tokens(self) -> List[str]:
        """Get a list of supported token addresses."""
        ...

    async def initialize(self) -> None:
        """Initialize the flash loan provider."""
        ...

    async def execute_flash_loan(
        self, params: FlashLoanParams, callback: FlashLoanCallback
    ) -> FlashLoanResult:
        """
        Execute a flash loan.

        Args:
            params: Parameters for the flash loan
            callback: Callback to handle the flash loan

        Returns:
            Result of the flash loan operation
        """
        ...

    async def get_flash_loan_fee(self, token_address: str, amount: Decimal) -> Decimal:
        """
        Get the fee for a flash loan.

        Args:
            token_address: Address of the token to borrow
            amount: Amount to borrow

        Returns:
            Fee for the flash loan
        """
        ...

    async def check_liquidity(self, token_address: str, amount: Decimal) -> bool:
        """
        Check if there's enough liquidity for a flash loan.

        Args:
            token_address: Address of the token to borrow
            amount: Amount to borrow

        Returns:
            True if there's enough liquidity, False otherwise
        """
        ...

    async def max_flash_loan(self, token_address: str) -> Decimal:
        """
        Get the maximum amount that can be borrowed in a flash loan.

        Args:
            token_address: Address of the token to borrow

        Returns:
            Maximum amount that can be borrowed
        """
        ...

    async def estimate_gas(self, params: FlashLoanParams) -> int:
        """
        Estimate the gas required for a flash loan.

        Args:
            params: Parameters for the flash loan

        Returns:
            Estimated gas required
        """
        ...

    async def close(self) -> None:
        """Close the flash loan provider and clean up resources."""
        ...
