"""Arbitrage models module."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from .enums import StrategyType, OpportunityStatus, ExecutionStatus, TransactionStatus

@dataclass
class RouteStep:
    """A single step in an arbitrage route."""
    dex_id: str
    input_token_address: str
    output_token_address: str
    pool_address: str
    input_amount: int
    expected_output: int

@dataclass
class ArbitrageRoute:
    """A complete arbitrage route."""
    steps: List[RouteStep]
    input_token_address: str
    output_token_address: str
    input_amount: int
    expected_output: int
    expected_profit: int

@dataclass
class ArbitrageOpportunity:
    """An arbitrage opportunity."""
    id: str
    strategy_type: StrategyType
    route: ArbitrageRoute
    input_amount: int
    expected_output: int
    expected_profit: int
    confidence_score: float
    detector_id: str
    gas_estimate: int
    status: OpportunityStatus = OpportunityStatus.PENDING
    error_message: Optional[str] = None
    validator_id: Optional[str] = None
    timestamp: float = 0.0

@dataclass
class ExecutionResult:
    """Result of an arbitrage execution."""
    id: str
    opportunity_id: str
    status: ExecutionStatus
    timestamp: float
    transaction_hash: str
    transaction_details: 'TransactionDetails'
    success: bool
    actual_profit: Optional[int] = None
    expected_profit: int = 0
    gas_used: Optional[int] = None
    gas_price: Optional[int] = None
    strategy_id: Optional[str] = None
    confirmations: int = 0