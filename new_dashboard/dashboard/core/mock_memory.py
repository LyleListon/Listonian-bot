"""Mock memory bank for testing."""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import random

class MockMemoryStats:
    """Mock memory statistics."""
    def __init__(self):
        self.cache_size = random.randint(1000, 10000)
        self.total_size_bytes = random.randint(10000, 100000)
        self.total_entries = random.randint(100, 1000)
        self.categories = ["opportunities", "trades", "metrics"]
        self.cache_hits = random.randint(1000, 5000)
        self.cache_misses = random.randint(100, 500)

class MockMemoryBank:
    """Mock memory bank for testing."""

    def __init__(self):
        self._opportunities = self._generate_opportunities()
        self._trade_history = self._generate_trade_history()
        self._memory_stats = MockMemoryStats()

    async def get_recent_opportunities(self, max_age: int = 300) -> List[Dict[str, Any]]:
        """Get mock recent opportunities."""
        return self._opportunities

    async def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get mock trade history."""
        return self._trade_history[:limit]

    async def get_memory_stats(self) -> MockMemoryStats:
        """Get mock memory statistics."""
        return self._memory_stats

    def _generate_opportunities(self) -> List[Dict[str, Any]]:
        """Generate mock opportunities."""
        opportunities = []
        now = datetime.utcnow()
        
        for i in range(10):
            timestamp = now - timedelta(seconds=random.randint(0, 300))
            opportunities.append({
                "id": f"opp_{i}",
                "profit": random.uniform(0.1, 10.0),
                "dex_pair": f"DEX_{random.randint(1, 5)}/PAIR_{random.randint(1, 5)}",
                "timestamp": timestamp.isoformat(),
                "status": random.choice(["pending", "executed", "failed"]),
                "gas_estimate": random.uniform(0.01, 0.5),
                "confidence": random.uniform(0.5, 1.0)
            })
        
        return sorted(opportunities, key=lambda x: x["timestamp"], reverse=True)

    def _generate_trade_history(self) -> List[Dict[str, Any]]:
        """Generate mock trade history."""
        trades = []
        now = datetime.utcnow()
        
        for i in range(100):
            timestamp = now - timedelta(minutes=random.randint(1, 1440))
            success = random.random() > 0.2
            
            trade = {
                "timestamp": timestamp.isoformat(),
                "success": success,
                "net_profit": random.uniform(0.1, 5.0) if success else 0,
                "gas_cost": random.uniform(0.01, 0.2),
                "tx_hash": f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
            }
            
            if not success:
                trade["error"] = random.choice([
                    "Insufficient liquidity",
                    "Price slippage too high",
                    "Transaction reverted",
                    "Gas price spike"
                ])
            
            trades.append(trade)
        
        return sorted(trades, key=lambda x: x["timestamp"], reverse=True)

async def create_memory_bank() -> MockMemoryBank:
    """Create a mock memory bank instance."""
    return MockMemoryBank()