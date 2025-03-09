"""
Arbitrage System Data Models

This module defines the data models used by the arbitrage system to represent
opportunities, routes, execution results, and other core concepts.
"""

import asyncio
import enum
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class StrategyType(enum.Enum):
    """Types of arbitrage strategies."""
    CROSS_DEX = "cross_dex"
    TRIANGULAR = "triangular"
    MULTI_PATH = "multi_path"
    FLASH_LOAN = "flash_loan"
    CUSTOM = "custom"


class ExecutionStatus(enum.Enum):
    """Status of an arbitrage execution."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REVERTED = "reverted"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TransactionStatus(enum.Enum):
    """Status of a blockchain transaction."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DROPPED = "dropped"
    REPLACED = "replaced"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class TokenAmount:
    """Represents an amount of a specific token."""
    token_address: str  # Checksummed token address
    amount: int  # Amount in wei
    symbol: Optional[str] = None  # Token symbol (optional)
    decimals: int = 18  # Token decimals
    
    @property
    def amount_float(self) -> float:
        """Get the amount as a float in token units (not wei)."""
        return float(self.amount) / (10 ** self.decimals)
    
    @property
    def amount_decimal(self) -> Decimal:
        """Get the amount as a Decimal in token units (not wei)."""
        return Decimal(self.amount) / Decimal(10 ** self.decimals)
    
    def __str__(self) -> str:
        """String representation of the token amount."""
        if self.symbol:
            return f"{self.amount_float} {self.symbol}"
        return f"{self.amount_float} {self.token_address[:6]}...{self.token_address[-4:]}"


@dataclass
class DEXInfo:
    """Information about a decentralized exchange."""
    dex_id: str  # Unique identifier for the DEX
    name: str  # Human-readable name
    version: str = "1.0"  # DEX protocol version
    chain_id: int = 1  # Chain ID where the DEX is deployed
    factory_address: Optional[str] = None  # Factory contract address (if applicable)
    router_address: Optional[str] = None  # Router contract address (if applicable)
    extra_addresses: Dict[str, str] = field(default_factory=dict)  # Additional contract addresses
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def __str__(self) -> str:
        """String representation of the DEX."""
        return f"{self.name} v{self.version} on chain {self.chain_id}"


@dataclass
class PoolInfo:
    """Information about a liquidity pool."""
    pool_address: str  # Checksummed pool address
    dex_info: DEXInfo  # Information about the DEX this pool belongs to
    tokens: List[str]  # List of token addresses (checksummed)
    fee_tier: Optional[int] = None  # Fee tier in basis points (e.g., 30 = 0.3%)
    is_stable: bool = False  # Whether this is a stable pool
    reserves: Optional[List[int]] = None  # Current reserves (if available)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def __str__(self) -> str:
        """String representation of the pool."""
        token_str = "-".join([t[:6] for t in self.tokens])
        fee_str = f" ({self.fee_tier/100}%)" if self.fee_tier else ""
        return f"{self.dex_info.name} {token_str}{fee_str}"


@dataclass
class TradeStep:
    """A single step in an arbitrage route."""
    pool_info: PoolInfo  # Information about the pool
    token_in: str  # Input token address (checksummed)
    token_out: str  # Output token address (checksummed)
    amount_in: Optional[int] = None  # Input amount in wei (if known)
    min_amount_out: Optional[int] = None  # Minimum output amount in wei (if known)
    expected_amount_out: Optional[int] = None  # Expected output amount in wei (if known)
    actual_amount_out: Optional[int] = None  # Actual output amount in wei (after execution)
    max_slippage: float = 0.005  # Maximum allowed slippage (default 0.5%)
    index: int = 0  # Step index in the route
    
    def __str__(self) -> str:
        """String representation of the trade step."""
        token_in_short = f"{self.token_in[:6]}...{self.token_in[-4:]}"
        token_out_short = f"{self.token_out[:6]}...{self.token_out[-4:]}"
        
        if self.amount_in and self.expected_amount_out:
            return f"Step {self.index}: {self.amount_in} {token_in_short} -> ~{self.expected_amount_out} {token_out_short} via {self.pool_info.dex_info.name}"
        else:
            return f"Step {self.index}: {token_in_short} -> {token_out_short} via {self.pool_info.dex_info.name}"


@dataclass
class ArbitrageRoute:
    """A complete arbitrage route with multiple steps."""
    steps: List[TradeStep]  # List of trade steps
    start_token: str  # Starting token address (checksummed)
    end_token: str  # Ending token address (checksummed)
    
    def __post_init__(self):
        """Validate the route and set step indices."""
        if not self.steps:
            raise ValueError("Route must have at least one step")
        
        # Set step indices
        for i, step in enumerate(self.steps):
            step.index = i
        
        # Validate route continuity
        for i in range(len(self.steps) - 1):
            if self.steps[i].token_out != self.steps[i + 1].token_in:
                raise ValueError(f"Route is not continuous: Step {i} outputs {self.steps[i].token_out} but Step {i + 1} inputs {self.steps[i + 1].token_in}")
        
        # Validate start and end tokens
        if self.steps[0].token_in != self.start_token:
            raise ValueError(f"Start token {self.start_token} does not match first step input {self.steps[0].token_in}")
        
        if self.steps[-1].token_out != self.end_token:
            raise ValueError(f"End token {self.end_token} does not match last step output {self.steps[-1].token_out}")
    
    @property
    def dexes(self) -> Set[str]:
        """Get the set of DEX IDs used in this route."""
        return {step.pool_info.dex_info.dex_id for step in self.steps}
    
    @property
    def is_circular(self) -> bool:
        """Check if this is a circular route (start token == end token)."""
        return self.start_token == self.end_token
    
    @property
    def tokens(self) -> Set[str]:
        """Get the set of token addresses used in this route."""
        tokens = {self.start_token, self.end_token}
        for step in self.steps:
            tokens.add(step.token_in)
            tokens.add(step.token_out)
        return tokens
    
    def __str__(self) -> str:
        """String representation of the route."""
        step_strs = []
        for step in self.steps:
            in_token = step.token_in[:6]
            out_token = step.token_out[:6]
            dex = step.pool_info.dex_info.name
            step_strs.append(f"{in_token}->{out_token}({dex})")
            
        return " -> ".join(step_strs)


@dataclass
class ArbitrageOpportunity:
    """An arbitrage opportunity discovered by the system."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Unique identifier
    strategy_type: StrategyType  # Type of arbitrage strategy
    route: ArbitrageRoute  # The arbitrage route
    input_amount: int  # Input amount in wei
    expected_output: int  # Expected output amount in wei
    expected_profit: int  # Expected profit in wei
    confidence_score: float  # Confidence in the opportunity (0-1)
    gas_estimate: int = 0  # Estimated gas cost
    gas_price: int = 0  # Current gas price in wei
    priority_fee: int = 0  # Priority fee in wei
    max_slippage: float = 0.005  # Maximum allowed slippage (default 0.5%)
    flash_loan_required: bool = False  # Whether a flash loan is required
    flash_loan_source: Optional[str] = None  # Source of flash loan if required
    discovery_time: float = field(default_factory=time.time)  # Time when opportunity was discovered
    validation_results: Dict[str, Any] = field(default_factory=dict)  # Results of validation checks
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    @property
    def expected_profit_after_gas(self) -> int:
        """Calculate expected profit after gas costs."""
        gas_cost = self.gas_estimate * (self.gas_price + self.priority_fee)
        return self.expected_profit - gas_cost
    
    @property
    def is_profitable_after_gas(self) -> bool:
        """Check if the opportunity is profitable after gas costs."""
        return self.expected_profit_after_gas > 0
    
    @property
    def profit_margin_percentage(self) -> float:
        """Calculate profit margin as a percentage of input amount."""
        if self.input_amount == 0:
            return 0.0
        return (self.expected_profit_after_gas / self.input_amount) * 100
    
    @property
    def age_seconds(self) -> float:
        """Calculate the age of the opportunity in seconds."""
        return time.time() - self.discovery_time
    
    def __str__(self) -> str:
        """String representation of the opportunity."""
        profit_eth = self.expected_profit / 10**18
        profit_gas_eth = self.expected_profit_after_gas / 10**18
        
        return (
            f"Opportunity {self.id[:8]} ({self.strategy_type.value}): "
            f"Expected profit: {profit_eth:.6f} ETH ({profit_gas_eth:.6f} ETH after gas) | "
            f"Confidence: {self.confidence_score:.2f} | Route: {self.route}"
        )


@dataclass
class TransactionDetails:
    """Details of a blockchain transaction."""
    tx_hash: Optional[str] = None  # Transaction hash if available
    from_address: Optional[str] = None  # Sender address
    to_address: Optional[str] = None  # Recipient address
    data: Optional[str] = None  # Transaction data
    value: int = 0  # Value in wei
    nonce: Optional[int] = None  # Transaction nonce
    gas_limit: Optional[int] = None  # Gas limit
    gas_price: Optional[int] = None  # Gas price in wei
    max_fee_per_gas: Optional[int] = None  # Maximum fee per gas in wei (EIP-1559)
    max_priority_fee_per_gas: Optional[int] = None  # Maximum priority fee per gas in wei (EIP-1559)
    chain_id: int = 1  # Chain ID
    status: TransactionStatus = TransactionStatus.PENDING  # Transaction status
    block_number: Optional[int] = None  # Block number if confirmed
    block_hash: Optional[str] = None  # Block hash if confirmed
    gas_used: Optional[int] = None  # Gas used if confirmed
    effective_gas_price: Optional[int] = None  # Effective gas price if confirmed
    timestamp: Optional[int] = None  # Timestamp if confirmed
    receipt: Optional[Dict[str, Any]] = None  # Full transaction receipt if confirmed
    
    @property
    def is_complete(self) -> bool:
        """Check if the transaction has completed (succeeded or failed)."""
        return self.status in (TransactionStatus.CONFIRMED, TransactionStatus.FAILED)
    
    @property
    def is_pending(self) -> bool:
        """Check if the transaction is still pending."""
        return self.status == TransactionStatus.PENDING
    
    @property
    def gas_cost(self) -> Optional[int]:
        """Calculate the gas cost in wei if the transaction has completed."""
        if self.gas_used is not None and self.effective_gas_price is not None:
            return self.gas_used * self.effective_gas_price
        return None
    
    def __str__(self) -> str:
        """String representation of the transaction."""
        if self.tx_hash:
            return f"Transaction {self.tx_hash[:10]}...{self.tx_hash[-6:]} ({self.status.value})"
        return f"Pending transaction to {self.to_address[:10]}..."


@dataclass
class ExecutionResult:
    """Result of an arbitrage opportunity execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Unique identifier
    opportunity_id: str  # ID of the opportunity that was executed
    strategy_id: str  # ID of the strategy used for execution
    status: ExecutionStatus = ExecutionStatus.PENDING  # Current status
    input_amount: int  # Input amount in wei
    actual_output: Optional[int] = None  # Actual output amount in wei after execution
    actual_profit: Optional[int] = None  # Actual profit in wei after execution
    gas_used: Optional[int] = None  # Actual gas used
    gas_price: Optional[int] = None  # Actual gas price in wei
    transactions: List[TransactionDetails] = field(default_factory=list)  # List of transaction details
    flash_loan_fee: int = 0  # Flash loan fee in wei if applicable
    start_time: float = field(default_factory=time.time)  # Time when execution started
    end_time: Optional[float] = None  # Time when execution completed
    error_message: Optional[str] = None  # Error message if execution failed
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate the duration of the execution in seconds."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time
    
    @property
    def is_complete(self) -> bool:
        """Check if the execution has completed."""
        return self.status in (
            ExecutionStatus.SUCCEEDED, 
            ExecutionStatus.FAILED, 
            ExecutionStatus.REVERTED, 
            ExecutionStatus.TIMEOUT, 
            ExecutionStatus.CANCELLED
        )
    
    @property
    def is_successful(self) -> bool:
        """Check if the execution was successful."""
        return self.status == ExecutionStatus.SUCCEEDED
    
    @property
    def total_gas_cost(self) -> Optional[int]:
        """Calculate total gas cost across all transactions."""
        if not all(tx.gas_cost is not None for tx in self.transactions):
            return None
        return sum(tx.gas_cost for tx in self.transactions)
    
    @property
    def net_profit(self) -> Optional[int]:
        """Calculate net profit after gas costs and fees."""
        if self.actual_profit is None or self.total_gas_cost is None:
            return None
        return self.actual_profit - self.total_gas_cost - self.flash_loan_fee
    
    def __str__(self) -> str:
        """String representation of the execution result."""
        result = f"Execution {self.id[:8]} for opportunity {self.opportunity_id[:8]}: {self.status.value}"
        
        if self.is_successful and self.actual_profit is not None:
            profit_eth = self.actual_profit / 10**18
            result += f" | Profit: {profit_eth:.6f} ETH"
            
            if self.net_profit is not None:
                net_eth = self.net_profit / 10**18
                result += f" (Net: {net_eth:.6f} ETH)"
        
        if self.duration_seconds is not None:
            result += f" | Duration: {self.duration_seconds:.2f}s"
            
        if self.error_message:
            result += f" | Error: {self.error_message}"
            
        return result