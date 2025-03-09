"""Type definitions for arbitrage system."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class ErrorType:
    """Type of error that occurred."""
    code: int
    name: str
    description: str

@dataclass
class ErrorDetails:
    """Detailed error information."""
    error_type: ErrorType
    message: str
    timestamp: float
    context: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None

@dataclass
class TransactionDetails:
    """Details of a blockchain transaction."""
    hash: str
    from_address: str
    to_address: str
    value: int
    gas_limit: int
    gas_price: int
    nonce: int
    data: str
    chain_id: int
    status: 'TransactionStatus'
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    timestamp: Optional[float] = None
    confirmation_time: Optional[float] = None

@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    opportunities_found: int
    opportunities_valid: int
    opportunities_invalid: int
    executions_attempted: int
    executions_successful: int
    executions_failed: int
    total_profit: int
    total_profit_eth: float
    total_gas_used: int
    success_rate: float
    average_profit_per_execution: Optional[float] = None
    average_gas_per_execution: Optional[float] = None
    timestamp: float = 0.0

@dataclass
class ArbitrageSettings:
    """Configuration settings for arbitrage system."""
    auto_execute: bool = False
    min_profit_threshold_eth: float = 0.01
    max_opportunities_per_cycle: int = 5
    discovery_interval_seconds: float = 30.0
    execution_interval_seconds: float = 60.0
    min_confidence_threshold: float = 0.7
    max_slippage_percent: float = 0.5
    max_gas_price_gwei: float = 50.0
    use_flashbots: bool = True
    use_flash_loans: bool = True
    max_flash_loan_fee_percent: float = 0.09
    max_concurrent_executions: int = 2
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    transaction_timeout_seconds: float = 180.0