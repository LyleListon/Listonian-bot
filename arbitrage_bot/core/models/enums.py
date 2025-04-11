"""Enums for arbitrage system."""

from enum import Enum, auto


class StrategyType(Enum):
    """Types of arbitrage strategies."""

    CROSS_DEX = auto()
    TRIANGULAR = auto()
    FLASH_LOAN = auto()
    MULTI_PATH = auto()


class OpportunityStatus(Enum):
    """Status of an arbitrage opportunity."""

    PENDING = auto()
    VALID = auto()
    INVALID = auto()
    EXECUTING = auto()
    EXECUTED = auto()
    FAILED = auto()


class ExecutionStatus(Enum):
    """Status of an arbitrage execution."""

    PENDING = auto()
    SUBMITTING = auto()
    SUBMITTED = auto()
    CONFIRMING = auto()
    SUCCESS = auto()
    FAILED = auto()
    REVERTED = auto()
    TIMEOUT = auto()


class TransactionStatus(Enum):
    """Status of a blockchain transaction."""

    PENDING = auto()
    SUBMITTED = auto()
    CONFIRMED = auto()
    FAILED = auto()
    REVERTED = auto()
    DROPPED = auto()


class ErrorType(Enum):
    """Type of error that occurred during arbitrage."""

    UNKNOWN_ERROR = auto()
    VALIDATION_ERROR = auto()
    EXECUTION_ERROR = auto()
    TRANSACTION_ERROR = auto()
    SLIPPAGE_ERROR = auto()
    GAS_ERROR = auto()
