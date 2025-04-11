"""Execution configuration module."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ExecutionConfig:
    """Configuration for execution management."""

    max_slippage: Decimal
    gas_limit: int
    max_gas_price: Decimal
    retry_attempts: int
    retry_delay: int
    confirmation_blocks: int
    timeout: int
