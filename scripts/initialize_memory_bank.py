#!/usr/bin/env python3
"""
Memory Bank Initializer

This script initializes the memory bank with basic data structures.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("memory_bank_initializer")

# Memory bank paths
MEMORY_BANK_PATH = project_root / "memory-bank"
TRADES_PATH = MEMORY_BANK_PATH / "trades"
METRICS_PATH = MEMORY_BANK_PATH / "metrics"
STATE_PATH = MEMORY_BANK_PATH / "state"

# Sample DEXes
DEXES = ["baseswap", "aerodrome", "pancakeswap", "swapbased"]

# Sample token pairs
TOKEN_PAIRS = ["WETH-USDC", "WETH-USDbC", "USDC-USDbC", "WETH-cbETH", "WETH-wstETH"]

async def ensure_directories():
    """Ensure all required directories exist."""
    for path in [MEMORY_BANK_PATH, TRADES_PATH, METRICS_PATH, STATE_PATH]:
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {path}")

async def create_sample_trade(timestamp):
    """Create a sample trade record."""
    dex_1 = random.choice(DEXES)
    dex_2 = random.choice([d for d in DEXES if d != dex_1])
    token_pair = random.choice(TOKEN_PAIRS)
    
    # Random profit between -0.05 and 0.2 ETH
    profit = random.uniform(-0.05, 0.2)
    success = profit > 0
    
    # Random gas cost between 0.001 and 0.01 ETH
    gas_cost = random.uniform(0.001, 0.01)
    
    # Generate random tx hash
    tx_hash = "0x" + "".join(random.choice("0123456789abcdef") for _ in range(64))
    
    return {
        "timestamp": timestamp.isoformat(),
        "opportunity": {
            "token_pair": token_pair,
            "dex_1": dex_1,
            "dex_2": dex_2,
            "potential_profit": abs(profit) + gas_cost,
            "confidence": random.uniform(0.5, 0.95)
        },
        "success": success,
        "net_profit": profit,
        "gas_cost": gas_cost,
        "tx_hash": tx_hash,
        "error": None if success else "Slippage exceeded"
    }

async def create_sample_trades():
    """Create sample trade records."""
    logger.info("Creating sample trade records...")
    
    # Create trades for the last 7 days
    now = datetime.now()
    for days_ago in range(7, 0, -1):
        # Create 5-20 trades per day
        num_trades = random.randint(5, 20)
        start_date = now - timedelta(days=days_ago)
        
        for i in range(num_trades):
            # Random time during the day
            hours = random.randint(0, 23)
            minutes = random.randint(0, 59)
            seconds = random.randint(0, 59)
            timestamp = start_date.replace(hour=hours, minute=minutes, second=seconds)
            
            # Create trade
            trade = await create_sample_trade(timestamp)
            
            # Save trade to file
            trade_file = TRADES_PATH / f"trade_{int(timestamp.timestamp())}.json"
            with open(trade_file, "w") as f:
                json.dump(trade, f, indent=2)
    
    logger.info(f"Created sample trades in {TRADES_PATH}")

async def create_system_state():
    """Create system state file."""
    logger.info("Creating system state file...")
    
    state = {
        "timestamp": datetime.now().isoformat(),
        "status": "running",
        "uptime": random.randint(3600, 86400),  # 1 hour to 1 day in seconds
        "version": "1.0.0",
        "network": {
            "chain_id": 8453,
            "gas_price": random.uniform(0.1, 2.0),
            "block_number": random.randint(5000000, 6000000),
            "connected": True
        },
        "performance": {
            "cpu_usage": random.uniform(10, 50),
            "memory_usage": random.uniform(100, 500),
            "disk_usage": random.uniform(10, 80)
        },
        "components": {
            "arbitrage_bot": {
                "status": "running",
                "last_update": (datetime.now() - timedelta(minutes=random.randint(1, 30))).isoformat()
            },
            "dashboard": {
                "status": "running",
                "last_update": (datetime.now() - timedelta(minutes=random.randint(1, 30))).isoformat()
            },
            "memory_bank": {
                "status": "healthy",
                "last_update": (datetime.now() - timedelta(minutes=random.randint(1, 30))).isoformat()
            }
        }
    }
    
    # Save state to file
    state_file = STATE_PATH / "system_state.json"
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    
    logger.info(f"Created system state file: {state_file}")

async def create_metrics():
    """Create metrics files."""
    logger.info("Creating metrics files...")
    
    # Create performance metrics
    performance = {
        "timestamp": datetime.now().isoformat(),
        "success_rate": random.uniform(0.7, 0.95),
        "total_profit_usd": random.uniform(100, 1000),
        "total_gas_cost_eth": random.uniform(0.1, 1.0),
        "avg_execution_time": random.uniform(0.5, 2.0),
        "total_trades": random.randint(50, 200),
        "failed_trades": random.randint(5, 20),
        "trades_24h": random.randint(5, 20),
        "profit_24h": random.uniform(10, 100),
        "active_opportunities": random.randint(0, 5),
        "rejected_opportunities": random.randint(10, 50)
    }
    
    # Create DEX performance metrics
    dex_performance = {}
    for dex in DEXES:
        dex_performance[dex] = {
            "success_rate": random.uniform(0.6, 0.95),
            "total_profit_usd": random.uniform(20, 300),
            "total_trades": random.randint(10, 50),
            "avg_profit_per_trade": random.uniform(0.5, 5.0)
        }
    
    # Create token pair metrics
    token_metrics = {}
    for pair in TOKEN_PAIRS:
        token_metrics[pair] = {
            "success_rate": random.uniform(0.6, 0.95),
            "total_profit_usd": random.uniform(20, 300),
            "total_trades": random.randint(10, 50),
            "avg_profit_per_trade": random.uniform(0.5, 5.0)
        }
    
    # Save metrics to files
    metrics_files = {
        "performance.json": performance,
        "dex_performance.json": dex_performance,
        "token_metrics.json": token_metrics
    }
    
    for filename, data in metrics_files.items():
        file_path = METRICS_PATH / filename
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    
    logger.info(f"Created metrics files in {METRICS_PATH}")

async def main():
    """Main entry point."""
    try:
        logger.info("Initializing memory bank...")
        
        # Ensure directories exist
        await ensure_directories()
        
        # Create sample data
        await create_sample_trades()
        await create_system_state()
        await create_metrics()
        
        logger.info("Memory bank initialization complete")
        
    except Exception as e:
        logger.error(f"Error initializing memory bank: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
