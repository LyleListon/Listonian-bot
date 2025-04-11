"""
Arbitrage Models

This module defines the data models used throughout the arbitrage system.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any


class StrategyType(Enum):
    """Strategy type enumeration."""

    SIMPLE = auto()
    FLASH_LOAN = auto()
    MULTI_PATH = auto()
    CUSTOM = auto()


class TransactionStatus(Enum):
    """Transaction status enumeration."""

    PENDING = auto()
    CONFIRMED = auto()
    FAILED = auto()
    REVERTED = auto()
    TIMEOUT = auto()


class ExecutionStatus(Enum):
    """Execution status enumeration."""

    PENDING = auto()
    SIMULATING = auto()
    SUBMITTING = auto()
    MONITORING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class ArbitrageOpportunity:
    """
    Represents an arbitrage opportunity.

    This class contains all information needed to execute an arbitrage trade,
    including paths, amounts, and expected profits.
    """

    # Identifiers
    id: str
    timestamp: datetime

    # Token information
    token_in: str  # Address of input token
    token_out: str  # Address of output token
    amount_in_wei: int  # Input amount in wei

    # Path information
    path: List[Dict[str, Any]]  # List of steps in the arbitrage
    dexes: List[str]  # DEXs involved in the arbitrage

    # Price information
    input_price_usd: float
    output_price_usd: float

    # Profit calculations
    expected_profit_wei: int
    expected_profit_usd: float
    gas_cost_wei: int
    gas_cost_usd: float
    net_profit_usd: float

    # Risk assessment
    confidence_score: float
    risk_factors: Dict[str, Any]

    # Validation
    price_validated: bool
    liquidity_validated: bool

    # Execution details
    execution_deadline: datetime
    max_slippage: float
    flashloan_required: bool

    # Optional fields
    simulation_result: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None

    @property
    def is_profitable(self) -> bool:
        """Check if opportunity is profitable after gas costs."""
        return self.net_profit_usd > 0

    @property
    def profit_ratio(self) -> float:
        """Calculate profit ratio."""
        input_value_usd = self.amount_in_wei * self.input_price_usd / 1e18
        return self.net_profit_usd / input_value_usd if input_value_usd > 0 else 0

    @property
    def is_executable(self) -> bool:
        """Check if opportunity can be executed."""
        return (
            self.is_profitable
            and self.price_validated
            and self.liquidity_validated
            and self.confidence_score >= 0.8
            and datetime.now() < self.execution_deadline
        )


@dataclass
class ExecutionResult:
    """
    Represents the result of an arbitrage execution.

    This class contains all information about an executed arbitrage trade,
    including transaction details and actual profits.
    """

    # Identifiers
    id: str
    opportunity_id: str
    timestamp: datetime

    # Status
    status: ExecutionStatus
    transaction_status: Optional[TransactionStatus]

    # Transaction details
    transaction_hash: Optional[str]
    block_number: Optional[int]
    gas_used: Optional[int]
    gas_price_wei: Optional[int]

    # Profit results
    actual_profit_wei: Optional[int]
    actual_profit_usd: Optional[float]
    gas_cost_wei: Optional[int]
    gas_cost_usd: Optional[float]
    net_profit_usd: Optional[float]

    # Performance metrics
    execution_time_ms: int
    latency_ms: int

    # Error details
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]

    # Optional data
    bundle_hash: Optional[str] = None
    flashbots_stats: Optional[Dict[str, Any]] = None

    @property
    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return (
            self.status == ExecutionStatus.COMPLETED
            and self.transaction_status == TransactionStatus.CONFIRMED
            and self.actual_profit_wei is not None
            and self.actual_profit_wei > 0
        )

    @property
    def profit_accuracy(self) -> Optional[float]:
        """Calculate accuracy of profit prediction."""
        if not self.is_successful or not hasattr(self, "expected_profit_usd"):
            return None

        return (
            self.actual_profit_usd / self.expected_profit_usd
            if self.expected_profit_usd > 0
            else 0
        )


@dataclass
class TokenAmount:
    """
    Represents an amount of a specific token.

    This class is used to represent token amounts throughout the system,
    including input and output amounts for trades.
    """

    token_address: str  # Address of the token
    amount_wei: int  # Amount in wei
    decimals: int = 18  # Token decimals

    @property
    def amount_human(self) -> float:
        """Get the amount in human-readable form."""
        return self.amount_wei / (10**self.decimals)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "token_address": self.token_address,
            "amount_wei": self.amount_wei,
            "decimals": self.decimals,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenAmount":
        """Create from dictionary."""
        return cls(
            token_address=data["token_address"],
            amount_wei=data["amount_wei"],
            decimals=data.get("decimals", 18),
        )
