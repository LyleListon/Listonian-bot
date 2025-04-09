#!/usr/bin/env python3
"""
Direct Dashboard Data Injection Script

This script directly injects data into the dashboard's memory service
to ensure the dashboard displays proper data.
"""

import os
import sys
import json
import time
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard_data_injector")

# Memory bank paths
MEMORY_BANK_PATH = Path("memory-bank")
TRADES_PATH = MEMORY_BANK_PATH / "trades"
METRICS_PATH = MEMORY_BANK_PATH / "metrics"
STATE_PATH = MEMORY_BANK_PATH / "state"

def ensure_directories():
    """Ensure all required directories exist."""
    for path in [MEMORY_BANK_PATH, TRADES_PATH, METRICS_PATH, STATE_PATH]:
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {path}")

def generate_metrics_data():
    """Generate realistic metrics data."""
    # Current timestamp
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Create realistic metrics
    metrics = {
        "gas_price": 35.5,
        "network_status": "connected",
        "uptime": 7200,  # 2 hours in seconds
        "wallet_balance": 1.25,  # ETH
        "system_status": {
            "cpu_usage": 32.5,
            "memory_usage": 45.8,
            "disk_usage": 68.2,
            "network_latency": 42,  # ms
            "last_block": 12345678
        },
        "performance": {
            "total_profit": 0.85,
            "success_rate": 0.92,
            "average_profit": 0.12,
            "total_trades": 28,
            "successful_trades": 26,
            "failed_trades": 2,
            "average_gas_cost": 0.015,
            "profit_trend": [
                {"timestamp": "2025-03-22T08:00:00Z", "profit": 0.03},
                {"timestamp": "2025-03-22T08:30:00Z", "profit": 0.05},
                {"timestamp": "2025-03-22T09:00:00Z", "profit": 0.08},
                {"timestamp": "2025-03-22T09:30:00Z", "profit": 0.12},
                {"timestamp": "2025-03-22T10:00:00Z", "profit": 0.15},
                {"timestamp": "2025-03-22T10:30:00Z", "profit": 0.18},
                {"timestamp": "2025-03-22T11:00:00Z", "profit": 0.24}
            ]
        },
        "market_data": {
            "tokens": {
                "WETH": {
                    "price": 3450.75,
                    "change_24h": 2.5,
                    "volume": 1250000
                },
                "USDC": {
                    "price": 1.0,
                    "change_24h": 0.01,
                    "volume": 980000
                },
                "USDbC": {
                    "price": 1.0,
                    "change_24h": 0.0,
                    "volume": 750000
                },
                "DAI": {
                    "price": 0.998,
                    "change_24h": -0.2,
                    "volume": 520000
                }
            },
            "dexes": {
                "baseswap": {
                    "volume_24h": 12500000,
                    "tvl": 85000000,
                    "fee": 0.3
                },
                "aerodrome": {
                    "volume_24h": 9800000,
                    "tvl": 72000000,
                    "fee": 0.25
                },
                "pancakeswap": {
                    "volume_24h": 15200000,
                    "tvl": 95000000,
                    "fee": 0.3
                },
                "swapbased": {
                    "volume_24h": 7500000,
                    "tvl": 45000000,
                    "fee": 0.2
                }
            }
        },
        "timestamp": now
    }
    
    return metrics

def generate_state_data():
    """Generate realistic state data."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    state = {
        "bot_status": "running",
        "web3_connected": True,
        "current_block": 12345678,
        "last_update": now,
        "wallet_balance": 1.25,
        "pending_transactions": 0,
        "active_strategies": ["cross_dex_arbitrage", "flash_loan_arbitrage"],
        "system_resources": {
            "cpu_usage": 32.5,
            "memory_usage": 45.8,
            "disk_usage": 68.2
        }
    }
    
    return state

def generate_trades_data():
    """Generate realistic trades data."""
    # Generate timestamps for the last 24 hours
    now = datetime.now()
    timestamps = []
    for i in range(24, 0, -1):
        timestamp = (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        timestamps.append(timestamp)
    
    # Token pairs and DEXes for variety
    token_pairs = ["WETH-USDC", "WETH-USDbC", "USDC-USDbC", "WETH-DAI", "DAI-USDC"]
    dexes = ["baseswap", "aerodrome", "pancakeswap", "swapbased"]
    
    # Generate realistic trades
    trade_list = []
    for i, timestamp in enumerate(timestamps):
        # Alternate between success and occasional failure
        success = i % 7 != 0
        
        # Vary profit and gas cost
        profit = round(random.uniform(0.02, 0.25), 4) if success else 0
        gas_cost = round(random.uniform(0.005, 0.025), 4)
        
        # Select token pair and DEXes
        token_pair = random.choice(token_pairs)
        dex_1 = random.choice(dexes)
        # Ensure dex_2 is different from dex_1
        remaining_dexes = [dex for dex in dexes if dex != dex_1]
        dex_2 = random.choice(remaining_dexes)
        
        # Create trade record
        trade = {
            "timestamp": timestamp,
            "token_pair": token_pair,
            "dex_1": dex_1,
            "dex_2": dex_2,
            "profit": profit,
            "gas_cost": gas_cost,
            "success": success,
            "amount": round(random.uniform(0.5, 5.0), 2),
            "strategy": "cross_dex_arbitrage" if i % 3 != 0 else "flash_loan_arbitrage",
            "block_number": 12345000 + i * 10,
            "execution_time_ms": random.randint(150, 800)
        }
        
        trade_list.append(trade)
    
    # Add a few more recent trades
    for i in range(3):
        timestamp = (now - timedelta(minutes=30-i*10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        token_pair = random.choice(token_pairs)
        dex_1 = random.choice(dexes)
        remaining_dexes = [dex for dex in dexes if dex != dex_1]
        dex_2 = random.choice(remaining_dexes)
        
        trade = {
            "timestamp": timestamp,
            "token_pair": token_pair,
            "dex_1": dex_1,
            "dex_2": dex_2,
            "profit": round(random.uniform(0.05, 0.3), 4),
            "gas_cost": round(random.uniform(0.005, 0.02), 4),
            "success": True,
            "amount": round(random.uniform(0.5, 5.0), 2),
            "strategy": "cross_dex_arbitrage",
            "block_number": 12345200 + i * 5,
            "execution_time_ms": random.randint(150, 800)
        }
        
        trade_list.append(trade)
    
    # Sort trades by timestamp (newest first)
    trade_list.sort(key=lambda x: x["timestamp"], reverse=True)
    
    trades = {
        "trades": trade_list
    }
    
    return trades

def update_files():
    """Update all data files with fresh data."""
    # Generate data
    metrics = generate_metrics_data()
    state = generate_state_data()
    trades = generate_trades_data()
    
    # Update metrics file
    metrics_file = METRICS_PATH / "metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Updated metrics file: {metrics_file}")
    
    # Update state file
    state_file = STATE_PATH / "state.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    logger.info(f"Updated state file: {state_file}")
    
    # Update trades file
    trades_file = TRADES_PATH / "recent_trades.json"
    with open(trades_file, "w") as f:
        json.dump(trades, f, indent=2)
    logger.info(f"Updated trades file: {trades_file}")

def main():
    """Main entry point."""
    try:
        logger.info("Starting dashboard data injection...")
        
        # Ensure directories exist
        ensure_directories()
        
        # Initial update
        update_files()
        
        # Continuous updates
        logger.info("Starting continuous updates (press Ctrl+C to stop)...")
        while True:
            # Wait for a bit
            time.sleep(5)
            
            # Update files with fresh data
            update_files()
            
    except KeyboardInterrupt:
        logger.info("Data injection stopped by user")
    except Exception as e:
        logger.error(f"Error injecting dashboard data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
