#!/usr/bin/env python3
"""
Clear Mock Data

This script clears mock data from the memory bank and initializes it with empty structures.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("clear_mock_data")

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def clear_memory_bank():
    """Clear mock data from memory bank and initialize with empty structures."""
    try:
        # Use absolute path for memory bank directory
        memory_bank_dir = project_root / "memory-bank"
        memory_bank_dir = memory_bank_dir.resolve()

        logger.info(f"Using memory bank directory: {memory_bank_dir}")

        if not memory_bank_dir.exists():
            logger.info(f"Creating memory bank directory: {memory_bank_dir}")
            memory_bank_dir.mkdir(exist_ok=True)

        # Create subdirectories
        trades_dir = memory_bank_dir / "trades"
        metrics_dir = memory_bank_dir / "metrics"
        state_dir = memory_bank_dir / "state"

        for directory in [trades_dir, metrics_dir, state_dir]:
            if not directory.exists():
                logger.info(f"Creating directory: {directory}")
                directory.mkdir(exist_ok=True)

        # Clear and initialize trades
        trades_file = trades_dir / "recent_trades.json"
        logger.info(f"Clearing and initializing trades file: {trades_file}")

        empty_trades = {
            "trade_history": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Use string path to avoid Windows path length issues
        with open(str(trades_file), 'w') as f:
            json.dump(empty_trades, f, indent=2)

        # Clear and initialize metrics
        metrics_file = metrics_dir / "metrics.json"
        logger.info(f"Clearing and initializing metrics file: {metrics_file}")

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

        # Use string path to avoid Windows path length issues
        with open(str(metrics_file), 'w') as f:
            json.dump(empty_metrics, f, indent=2)

        # Clear and initialize state
        state_file = state_dir / "bot_state.json"
        logger.info(f"Clearing and initializing state file: {state_file}")

        empty_state = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "status": "initializing",
            "config_hash": "",
            "version": "1.0.0",
            "use_real_data_only": True
        }

        # Use string path to avoid Windows path length issues
        with open(str(state_file), 'w') as f:
            json.dump(empty_state, f, indent=2)

        logger.info("Memory bank cleared and initialized with empty structures")
    except Exception as e:
        logger.error(f"Error in clear_memory_bank: {e}", exc_info=True)
        raise

def main():
    """Main entry point."""
    logger.info("Clearing mock data from memory bank...")

    try:
        clear_memory_bank()
        logger.info("Successfully cleared mock data from memory bank")
        return 0
    except Exception as e:
        logger.error(f"Error clearing mock data: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
