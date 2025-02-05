"""Arbitrage opportunity model."""

from dataclasses import dataclass
from typing import List, Dict, Any
from decimal import Decimal

@dataclass
class Opportunity:
    """Represents an arbitrage opportunity."""
    
    # DEX information
    dex_from: str
    dex_to: str
    
    # Token information
    token_path: List[str]  # List of token addresses in path
    amount_in: int
    amount_out: int
    
    # Profitability metrics
    profit_usd: Decimal
    gas_cost_usd: Decimal
    price_impact: float
    
    # Status information
    status: str  # Ready, Executing, Executed, Failed
    timestamp: float
    
    # Additional details
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'dex_from': self.dex_from,
            'dex_to': self.dex_to,
            'token_path': self.token_path,
            'amount_in': self.amount_in,
            'amount_out': self.amount_out,
            'profit_usd': str(self.profit_usd),
            'gas_cost_usd': str(self.gas_cost_usd),
            'price_impact': self.price_impact,
            'status': self.status,
            'timestamp': self.timestamp,
            'details': self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Opportunity':
        """Create opportunity from dictionary."""
        return cls(
            dex_from=data['dex_from'],
            dex_to=data['dex_to'],
            token_path=data['token_path'],
            amount_in=int(data['amount_in']),
            amount_out=int(data['amount_out']),
            profit_usd=Decimal(str(data['profit_usd'])),
            gas_cost_usd=Decimal(str(data['gas_cost_usd'])),
            price_impact=float(data['price_impact']),
            status=data['status'],
            timestamp=float(data['timestamp']),
            details=data['details']
        )
    
    def is_profitable(self, min_profit_usd: Decimal) -> bool:
        """Check if opportunity meets minimum profit threshold."""
        return self.profit_usd >= min_profit_usd
    
    def net_profit_usd(self) -> Decimal:
        """Calculate net profit after gas costs."""
        return self.profit_usd - self.gas_cost_usd
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate opportunity against configuration thresholds."""
        try:
            # Get thresholds from config
            min_profit = Decimal(str(config['arbitrage']['min_profit_usd']))
            max_price_impact = float(config['arbitrage']['max_price_impact'])
            
            # Check profit threshold
            if self.net_profit_usd() < min_profit:
                return False
            
            # Check price impact
            if self.price_impact > max_price_impact:
                return False
            
            # Check status
            if self.status != 'Ready':
                return False
            
            return True
            
        except (KeyError, ValueError):
            return False
