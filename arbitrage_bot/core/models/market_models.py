"""Market analysis models."""

from decimal import Decimal
from typing import Optional, Dict, Any
import json
import asyncio

class MarketTrend:
    """Market trend information."""
    def __init__(
        self,
        direction: str = 'sideways',
        strength: float = 0.0,
        duration: float = 0.0,
        volatility: float = 0.0,
        confidence: float = 0.0
    ):
        self.direction = direction
        self.strength = strength
        self.duration = duration
        self.volatility = volatility
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'direction': self.direction,
            'strength': float(self.strength),
            'duration': float(self.duration),
            'volatility': float(self.volatility),
            'confidence': float(self.confidence)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketTrend':
        """Create from dictionary."""
        return cls(
            direction=str(data.get('direction', 'sideways')),
            strength=float(data.get('strength', 0.0)),
            duration=float(data.get('duration', 0.0)),
            volatility=float(data.get('volatility', 0.0)),
            confidence=float(data.get('confidence', 0.0))
        )

class MarketCondition:
    """Market condition information."""
    def __init__(
        self,
        price: Decimal,
        trend: MarketTrend,
        volume_24h: Decimal,
        liquidity: Decimal,
        volatility_24h: float,
        price_impact: float,
        last_updated: float
    ):
        self.price = price
        self.trend = trend
        self.volume_24h = volume_24h
        self.liquidity = liquidity
        self.volatility_24h = volatility_24h
        self.price_impact = price_impact
        self.last_updated = last_updated

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'price': float(self.price),
            'trend': self.trend.to_dict(),
            'volume_24h': float(self.volume_24h),
            'liquidity': float(self.liquidity),
            'volatility_24h': float(self.volatility_24h),
            'price_impact': float(self.price_impact),
            'last_updated': float(self.last_updated)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketCondition':
        """Create from dictionary."""
        return cls(
            price=Decimal(str(data.get('price', 0))),
            trend=MarketTrend.from_dict(data.get('trend', {})),
            volume_24h=Decimal(str(data.get('volume_24h', 0))),
            liquidity=Decimal(str(data.get('liquidity', 0))),
            volatility_24h=float(data.get('volatility_24h', 0)),
            price_impact=float(data.get('price_impact', 0)),
            last_updated=float(data.get('last_updated', 0))
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'MarketCondition':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

class PricePoint:
    """Price point information."""
    def __init__(
        self,
        price: Decimal,
        timestamp: float,
        volume: Optional[Decimal] = None,
        liquidity: Optional[Decimal] = None
    ):
        self.price = price
        self.timestamp = timestamp
        self.volume = volume
        self.liquidity = liquidity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'price': float(self.price),
            'timestamp': float(self.timestamp)
        }
        if self.volume is not None:
            data['volume'] = float(self.volume)
        if self.liquidity is not None:
            data['liquidity'] = float(self.liquidity)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PricePoint':
        """Create from dictionary."""
        volume = data.get('volume')
        liquidity = data.get('liquidity')
        return cls(
            price=Decimal(str(data.get('price', 0))),
            timestamp=float(data.get('timestamp', 0)),
            volume=Decimal(str(volume)) if volume is not None else None,
            liquidity=Decimal(str(liquidity)) if liquidity is not None else None
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'PricePoint':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

async def get_market_condition(token: Dict[str, Any], market_analyzer: Any) -> Optional[Dict[str, Any]]:
    """Get market condition asynchronously."""
    try:
        # Get market condition from analyzer
        condition = await market_analyzer.get_market_condition(token)
        if condition:
            # Convert to MarketCondition object
            market_condition = MarketCondition.from_dict(condition)
            # Convert back to dict for transport
            return market_condition.to_dict()
        return None
    except Exception as e:
        print("Error getting market condition: %s", str(e))
        return None
