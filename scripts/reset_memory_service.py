#!/usr/bin/env python3
"""
Reset Memory Service

This script uses the memory service to reset the memory bank.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ["USE_REAL_DATA_ONLY"] = "true"

# Import memory service
from new_dashboard.dashboard.services.memory_service import MemoryService

async def reset_memory():
    """Reset the memory bank using the memory service."""
    print("Initializing memory service...")
    memory_service = MemoryService(str(project_root / "memory-bank"))
    await memory_service.initialize()

    print("Clearing trade history and metrics...")
    await memory_service.update_state({
        "trade_history": [],
        "metrics": {
            "gas_price": 0.0,
            "network_status": "initializing",
            "uptime": 0,
            "wallet_balance": 0.0,
            "system_status": {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "network_latency": 0,
                "last_block": 0
            },
            "performance": {
                "total_profit": 0.0,
                "success_rate": 0.0,
                "average_profit": 0.0,
                "total_trades": 0,
                "successful_trades": 0,
                "failed_trades": 0,
                "average_gas_cost": 0.0,
                "profit_trend": []
            },
            "market_data": {
                "tokens": {},
                "dexes": {}
            }
        }
    })

    print("Memory bank reset successfully")

if __name__ == "__main__":
    asyncio.run(reset_memory())
