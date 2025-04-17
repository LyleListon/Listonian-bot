#!/usr/bin/env python3
"""
Reset Memory Bank

This script resets the memory bank by creating empty JSON files.
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).resolve().parent.parent
print(f"Project root: {project_root}")

# Set the memory bank directory
memory_bank_dir = project_root / "memory-bank"
print(f"Memory bank directory: {memory_bank_dir}")

# Create memory bank directory structure
trades_dir = memory_bank_dir / "trades"
metrics_dir = memory_bank_dir / "metrics"
state_dir = memory_bank_dir / "state"

os.makedirs(trades_dir, exist_ok=True)
os.makedirs(metrics_dir, exist_ok=True)
os.makedirs(state_dir, exist_ok=True)

print(f"Created directories: {trades_dir}, {metrics_dir}, {state_dir}")

# Create empty trades file
empty_trades = {
    "trade_history": [],
    "timestamp": datetime.now(timezone.utc).isoformat()
}

trades_file = trades_dir / "recent_trades.json"
print(f"Writing to trades file: {trades_file}")
with open(trades_file, 'w') as f:
    json.dump(empty_trades, f, indent=2)

# Create empty metrics file
empty_metrics = {
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
    },
    "timestamp": datetime.now(timezone.utc).isoformat()
}

metrics_file = metrics_dir / "metrics.json"
print(f"Writing to metrics file: {metrics_file}")
with open(metrics_file, 'w') as f:
    json.dump(empty_metrics, f, indent=2)

# Create empty state file
empty_state = {
    "last_run": datetime.now(timezone.utc).isoformat(),
    "status": "initializing",
    "config_hash": "",
    "version": "1.0.0",
    "use_real_data_only": True
}

state_file = state_dir / "bot_state.json"
print(f"Writing to state file: {state_file}")
with open(state_file, 'w') as f:
    json.dump(empty_state, f, indent=2)

print("Memory bank reset successfully")
