#!/usr/bin/env python3
"""
Run Dashboard with Real-Time Data

This script initializes the memory bank with test data and starts the dashboard.
It also simulates real-time updates to the memory bank to test the dashboard's
real-time data display capabilities.
"""

import os
import sys
import json
import time
import random
import logging
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard_runner")

# Default memory bank path
DEFAULT_MEMORY_BANK_PATH = project_root / "memory-bank"

# Sample tokens and DEXes
TOKENS = ["WETH", "USDC", "USDbC", "DAI"]
DEXES = ["baseswap", "aerodrome", "pancakeswap", "swapbased"]
STRATEGIES = ["cross_dex_arbitrage", "flash_loan_arbitrage"]

async def ensure_memory_bank_initialized():
    """Ensure the memory bank is initialized."""
    memory_bank_path = os.environ.get("MEMORY_BANK_PATH", DEFAULT_MEMORY_BANK_PATH)
    memory_bank_path = Path(memory_bank_path)
    
    # Check if memory bank exists and has data
    state_file = memory_bank_path / "state" / "current_state.json"
    
    if not state_file.exists():
        logger.info("Memory bank not initialized, running initializer...")
        
        # Run the initializer script
        initializer_script = project_root / "scripts" / "initialize_memory_bank.py"
        if initializer_script.exists():
            try:
                subprocess.run([sys.executable, str(initializer_script)], check=True)
                logger.info("Memory bank initialized successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to initialize memory bank: {e}")
                return False
        else:
            logger.error(f"Initializer script not found: {initializer_script}")
            return False
    
    return True

async def generate_trade():
    """Generate a random trade."""
    # Select random token pair
    token1 = random.choice(TOKENS)
    token2 = random.choice([t for t in TOKENS if t != token1])
    token_pair = f"{token1}-{token2}"
    
    # Select random DEXes
    dex_1 = random.choice(DEXES)
    dex_2 = random.choice([d for d in DEXES if d != dex_1])
    
    # Determine success (80% success rate)
    success = random.random() < 0.8
    
    # Generate profit and gas cost
    if success:
        profit = round(random.uniform(0.01, 0.3), 4)
        gas_cost = round(random.uniform(0.005, 0.025), 4)
    else:
        profit = 0
        gas_cost = round(random.uniform(0.005, 0.025), 4)
    
    # Generate amount
    amount = round(random.uniform(0.5, 5), 2)
    
    # Select strategy
    strategy = random.choice(STRATEGIES)
    
    # Generate block number
    block_number = random.randint(12345000, 12346000)
    
    # Generate execution time
    execution_time_ms = random.randint(150, 800)
    
    # Create trade record
    trade = {
        "timestamp": datetime.now().isoformat() + "Z",
        "token_pair": token_pair,
        "dex_1": dex_1,
        "dex_2": dex_2,
        "profit": profit,
        "gas_cost": gas_cost,
        "success": success,
        "amount": amount,
        "strategy": strategy,
        "block_number": block_number,
        "execution_time_ms": execution_time_ms
    }
    
    return trade

async def update_memory_bank():
    """Update the memory bank with new data periodically."""
    memory_bank_path = os.environ.get("MEMORY_BANK_PATH", DEFAULT_MEMORY_BANK_PATH)
    memory_bank_path = Path(memory_bank_path)
    
    # Paths to files
    trades_file = memory_bank_path / "trades" / "recent_trades.json"
    metrics_file = memory_bank_path / "metrics" / "metrics.json"
    state_file = memory_bank_path / "state" / "current_state.json"
    
    while True:
        try:
            # Load current data
            with open(trades_file, 'r') as f:
                trades = json.load(f)
            
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            
            # Generate a new trade
            new_trade = await generate_trade()
            
            # Add to trades list (keep most recent 50)
            trades.insert(0, new_trade)
            trades = trades[:50]
            
            # Update metrics
            successful_trades = [t for t in trades if t["success"]]
            total_profit = sum(t["profit"] for t in successful_trades)
            total_gas = sum(t["gas_cost"] for t in trades)
            success_rate = len(successful_trades) / len(trades) if trades else 0
            
            metrics["performance"]["total_profit"] = round(total_profit, 2)
            metrics["performance"]["success_rate"] = round(success_rate, 2)
            metrics["performance"]["average_profit"] = round(total_profit / len(successful_trades) if successful_trades else 0, 2)
            metrics["performance"]["total_trades"] = len(trades)
            metrics["performance"]["successful_trades"] = len(successful_trades)
            metrics["performance"]["failed_trades"] = len(trades) - len(successful_trades)
            metrics["performance"]["average_gas_cost"] = round(total_gas / len(trades) if trades else 0, 3)
            
            # Update system metrics
            metrics["system_status"]["cpu_usage"] = round(random.uniform(20, 40), 1)
            metrics["system_status"]["memory_usage"] = round(random.uniform(30, 60), 1)
            metrics["system_status"]["disk_usage"] = round(random.uniform(50, 80), 1)
            metrics["system_status"]["network_latency"] = random.randint(30, 60)
            metrics["system_status"]["last_block"] += random.randint(1, 5)
            
            # Update gas price
            metrics["gas_price"] = round(random.uniform(30, 40), 1)
            
            # Update timestamp
            metrics["timestamp"] = datetime.now().isoformat()
            
            # Update token prices
            for token in metrics["market_data"]["tokens"]:
                if token == "WETH":
                    # Small random change to price
                    current_price = metrics["market_data"]["tokens"][token]["price"]
                    change = round(random.uniform(-20, 20), 2)
                    new_price = max(3000, min(4000, current_price + change))
                    metrics["market_data"]["tokens"][token]["price"] = new_price
                    
                    # Update 24h change
                    metrics["market_data"]["tokens"][token]["change_24h"] = round(random.uniform(-3, 5), 1)
                elif token in ["USDC", "USDbC"]:
                    # Stablecoins have very small price changes
                    metrics["market_data"]["tokens"][token]["price"] = round(random.uniform(0.999, 1.001), 3)
                    metrics["market_data"]["tokens"][token]["change_24h"] = round(random.uniform(-0.1, 0.1), 2)
                else:  # DAI
                    metrics["market_data"]["tokens"][token]["price"] = round(random.uniform(0.995, 1.002), 3)
                    metrics["market_data"]["tokens"][token]["change_24h"] = round(random.uniform(-0.3, 0.1), 1)
            
            # Create state object
            state = {
                "trade_history": trades,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
            
            # Write updated data to files
            with open(trades_file, 'w') as f:
                json.dump(trades, f, indent=2)
            
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Updated memory bank with new trade: {new_trade['token_pair']} ({new_trade['dex_1']} → {new_trade['dex_2']})")
            
            # Wait for next update (random interval between 5-15 seconds)
            await asyncio.sleep(random.uniform(5, 15))
            
        except Exception as e:
            logger.error(f"Error updating memory bank: {e}")
            await asyncio.sleep(5)  # Wait before retrying

async def run_dashboard():
    """Run the dashboard."""
    dashboard_script = project_root / "run_dashboard.py"
    
    if not dashboard_script.exists():
        logger.error(f"Dashboard script not found: {dashboard_script}")
        return False
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        env["MEMORY_BANK_PATH"] = str(DEFAULT_MEMORY_BANK_PATH)
        
        # Start the dashboard process
        process = subprocess.Popen(
            [sys.executable, str(dashboard_script)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        logger.info(f"Started dashboard process with PID {process.pid}")
        
        # Monitor the process output
        for line in process.stdout:
            print(line, end="")
        
        # Wait for the process to complete
        return_code = process.wait()
        
        if return_code != 0:
            logger.error(f"Dashboard process exited with code {return_code}")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")
        return False

async def main():
    """Main entry point."""
    try:
        # Ensure memory bank is initialized
        if not await ensure_memory_bank_initialized():
            logger.error("Failed to initialize memory bank")
            return 1
        
        # Start memory bank updater task
        updater_task = asyncio.create_task(update_memory_bank())
        
        # Run dashboard
        dashboard_result = await run_dashboard()
        
        # Cancel updater task
        updater_task.cancel()
        try:
            await updater_task
        except asyncio.CancelledError:
            pass
        
        return 0 if dashboard_result else 1
    
    except Exception as e:
        logger.error(f"Error running dashboard with data: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
