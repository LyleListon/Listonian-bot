#!/usr/bin/env python3
"""
Memory Bank Monitor

This script monitors the memory bank and provides information about its state.
It can also perform maintenance tasks like cleanup and validation.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("memory_bank_monitor")

# Memory bank paths
MEMORY_BANK_PATH = project_root / "memory-bank"
TRADES_PATH = MEMORY_BANK_PATH / "trades"
METRICS_PATH = MEMORY_BANK_PATH / "metrics"
STATE_PATH = MEMORY_BANK_PATH / "state"

class MemoryBankMonitor:
    """Monitor and manage the memory bank."""
    
    def __init__(self, base_path: Path = MEMORY_BANK_PATH):
        """Initialize the monitor."""
        self.base_path = base_path
        self.trades_path = base_path / "trades"
        self.metrics_path = base_path / "metrics"
        self.state_path = base_path / "state"
        
    async def check_directories(self) -> Dict[str, bool]:
        """Check if all required directories exist."""
        directories = {
            "base": self.base_path,
            "trades": self.trades_path,
            "metrics": self.metrics_path,
            "state": self.state_path
        }
        
        results = {}
        for name, path in directories.items():
            exists = path.exists() and path.is_dir()
            results[name] = exists
            if not exists:
                logger.warning(f"Directory {name} does not exist: {path}")
        
        return results
    
    async def count_files(self) -> Dict[str, int]:
        """Count files in each directory."""
        counts = {
            "trades": 0,
            "metrics": 0,
            "state": 0
        }
        
        for name, path in {
            "trades": self.trades_path,
            "metrics": self.metrics_path,
            "state": self.state_path
        }.items():
            if path.exists():
                counts[name] = len(list(path.glob("*.json")))
        
        return counts
    
    async def get_latest_files(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get information about the latest files in each directory."""
        results = {
            "trades": [],
            "metrics": [],
            "state": []
        }
        
        for name, path in {
            "trades": self.trades_path,
            "metrics": self.metrics_path,
            "state": self.state_path
        }.items():
            if not path.exists():
                continue
            
            files = sorted(path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            
            for file_path in files[:limit]:
                try:
                    stat = file_path.stat()
                    results[name].append({
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error getting file info for {file_path}: {e}")
        
        return results
    
    async def get_system_state(self) -> Optional[Dict[str, Any]]:
        """Get the current system state."""
        state_file = self.state_path / "system_state.json"
        if not state_file.exists():
            return None
        
        try:
            with open(state_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading system state: {e}")
            return None
    
    async def get_performance_metrics(self) -> Optional[Dict[str, Any]]:
        """Get the current performance metrics."""
        metrics_file = self.metrics_path / "performance.json"
        if not metrics_file.exists():
            return None
        
        try:
            with open(metrics_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading performance metrics: {e}")
            return None
    
    async def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades."""
        trades = []
        
        if not self.trades_path.exists():
            return trades
        
        trade_files = sorted(self.trades_path.glob("trade_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        for file_path in trade_files[:limit]:
            try:
                with open(file_path) as f:
                    trade = json.load(f)
                    trades.append(trade)
            except Exception as e:
                logger.error(f"Error reading trade file {file_path}: {e}")
        
        return trades
    
    async def cleanup_old_files(self, days: int = 7) -> Dict[str, int]:
        """Clean up files older than the specified number of days."""
        cutoff = datetime.now() - timedelta(days=days)
        counts = {
            "trades": 0,
            "metrics": 0,
            "state": 0
        }
        
        for name, path in {
            "trades": self.trades_path,
            "metrics": self.metrics_path,
            "state": self.state_path
        }.items():
            if not path.exists():
                continue
            
            for file_path in path.glob("*.json"):
                try:
                    stat = file_path.stat()
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    
                    if modified < cutoff:
                        file_path.unlink()
                        counts[name] += 1
                except Exception as e:
                    logger.error(f"Error cleaning up file {file_path}: {e}")
        
        return counts
    
    async def validate_json_files(self) -> Dict[str, Dict[str, int]]:
        """Validate all JSON files in the memory bank."""
        results = {
            "trades": {"valid": 0, "invalid": 0},
            "metrics": {"valid": 0, "invalid": 0},
            "state": {"valid": 0, "invalid": 0}
        }
        
        for name, path in {
            "trades": self.trades_path,
            "metrics": self.metrics_path,
            "state": self.state_path
        }.items():
            if not path.exists():
                continue
            
            for file_path in path.glob("*.json"):
                try:
                    with open(file_path) as f:
                        json.load(f)
                    results[name]["valid"] += 1
                except Exception as e:
                    logger.error(f"Invalid JSON file {file_path}: {e}")
                    results[name]["invalid"] += 1
        
        return results
    
    async def get_memory_bank_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the memory bank."""
        directories = await self.check_directories()
        file_counts = await self.count_files()
        latest_files = await self.get_latest_files()
        system_state = await self.get_system_state()
        performance_metrics = await self.get_performance_metrics()
        recent_trades = await self.get_recent_trades(5)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "directories": directories,
            "file_counts": file_counts,
            "latest_files": latest_files,
            "system_state": system_state,
            "performance_metrics": performance_metrics,
            "recent_trades": recent_trades
        }

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Memory Bank Monitor")
    parser.add_argument("--status", action="store_true", help="Show memory bank status")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Clean up files older than DAYS days")
    parser.add_argument("--validate", action="store_true", help="Validate JSON files")
    parser.add_argument("--trades", type=int, metavar="LIMIT", help="Show recent trades")
    parser.add_argument("--metrics", action="store_true", help="Show performance metrics")
    parser.add_argument("--state", action="store_true", help="Show system state")
    
    args = parser.parse_args()
    
    monitor = MemoryBankMonitor()
    
    # Default to status if no arguments provided
    if not any(vars(args).values()):
        args.status = True
    
    if args.status:
        status = await monitor.get_memory_bank_status()
        print(json.dumps(status, indent=2))
    
    if args.cleanup:
        counts = await monitor.cleanup_old_files(args.cleanup)
        print(f"Cleaned up files older than {args.cleanup} days:")
        for name, count in counts.items():
            print(f"  {name}: {count}")
    
    if args.validate:
        results = await monitor.validate_json_files()
        print("JSON validation results:")
        for name, counts in results.items():
            print(f"  {name}: {counts['valid']} valid, {counts['invalid']} invalid")
    
    if args.trades:
        trades = await monitor.get_recent_trades(args.trades)
        print(f"Recent trades ({len(trades)}):")
        for trade in trades:
            print(f"  {trade['timestamp']} - {trade['opportunity']['token_pair']} - {'Success' if trade['success'] else 'Failed'} - Profit: {trade['net_profit']}")
    
    if args.metrics:
        metrics = await monitor.get_performance_metrics()
        if metrics:
            print("Performance metrics:")
            print(json.dumps(metrics, indent=2))
        else:
            print("No performance metrics found")
    
    if args.state:
        state = await monitor.get_system_state()
        if state:
            print("System state:")
            print(json.dumps(state, indent=2))
        else:
            print("No system state found")

if __name__ == "__main__":
    asyncio.run(main())
