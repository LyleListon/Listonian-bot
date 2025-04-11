"""Opportunity model for arbitrage trading."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List # Removed Optional


@dataclass
class Opportunity:
    """Represents an arbitrage opportunity."""

    dex_from: str
    dex_to: str
    token_path: List[str]
    amount_in: Decimal
    amount_out: Decimal
    profit_usd: float
    gas_cost_usd: float
    price_impact: float
    status: str
    details: dict

    def is_profitable(self) -> bool:
        """Check if opportunity is profitable after gas costs."""
        return self.profit_usd > self.gas_cost_usd

    def net_profit(self) -> float:
        """Calculate net profit after gas costs."""
        return self.profit_usd - self.gas_cost_usd

    def profit_percentage(self) -> float:
        """Calculate profit percentage."""
        return (self.amount_out - self.amount_in) / self.amount_in * 100

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "dex_from": self.dex_from,
            "dex_to": self.dex_to,
            "token_path": self.token_path,
            "amount_in": str(self.amount_in),
            "amount_out": str(self.amount_out),
            "profit_usd": self.profit_usd,
            "gas_cost_usd": self.gas_cost_usd,
            "price_impact": self.price_impact,
            "status": self.status,
            "details": self.details,
            "net_profit": self.net_profit(),
            "profit_percentage": self.profit_percentage(),
        }
