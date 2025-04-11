"""Models for analytics data."""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class TradeMetrics:
    """Trade-related metrics."""

    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_volume: Decimal = Decimal("0")
    total_profit: Decimal = Decimal("0")
    average_profit_per_trade: Decimal = Decimal("0")
    success_rate: float = 0.0
    trades_by_pair: Dict[str, int] = None
    trades_by_dex: Dict[str, int] = None
    profit_by_pair: Dict[str, Decimal] = None
    profit_by_dex: Dict[str, Decimal] = None
    last_24h: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize dictionaries."""
        self.trades_by_pair = self.trades_by_pair or {}
        self.trades_by_dex = self.trades_by_dex or {}
        self.profit_by_pair = self.profit_by_pair or {}
        self.profit_by_dex = self.profit_by_dex or {}
        self.last_24h = self.last_24h or {
            "trades": 0,
            "volume": Decimal("0"),
            "profit": Decimal("0"),
        }


@dataclass
class GasMetrics:
    """Gas-related metrics."""

    total_gas_used: int = 0
    total_gas_cost: Decimal = Decimal("0")
    average_gas_per_trade: float = 0.0
    average_gas_cost: Decimal = Decimal("0")
    gas_by_dex: Dict[str, Dict[str, Any]] = None
    gas_by_pair: Dict[str, Dict[str, Any]] = None
    last_24h: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize dictionaries."""
        self.gas_by_dex = self.gas_by_dex or {}
        self.gas_by_pair = self.gas_by_pair or {}
        self.last_24h = self.last_24h or {"gas_used": 0, "gas_cost": Decimal("0")}


@dataclass
class PerformanceMetrics:
    """Performance-related metrics."""

    uptime: int = 0
    total_opportunities: int = 0
    executed_opportunities: int = 0
    missed_opportunities: int = 0
    execution_success_rate: float = 0.0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    errors_by_type: Dict[str, int] = None
    last_24h: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize dictionaries."""
        self.errors_by_type = self.errors_by_type or {}
        self.last_24h = self.last_24h or {
            "opportunities": 0,
            "executions": 0,
            "errors": 0,
        }


@dataclass
class MarketMetrics:
    """Market-related metrics."""

    total_liquidity: Dict[str, Decimal] = None
    volume_24h: Dict[str, Decimal] = None
    price_volatility: Dict[str, float] = None
    spread_by_pair: Dict[str, Decimal] = None
    last_update: datetime = None

    def __post_init__(self):
        """Initialize dictionaries and datetime."""
        self.total_liquidity = self.total_liquidity or {}
        self.volume_24h = self.volume_24h or {}
        self.price_volatility = self.price_volatility or {}
        self.spread_by_pair = self.spread_by_pair or {}
        self.last_update = self.last_update or datetime.now()
