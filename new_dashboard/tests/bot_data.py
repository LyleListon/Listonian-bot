"""
Bot Data Integration

This module handles reading data from the arbitrage bot's logs and data storage,
allowing the dashboard to display real bot activity and performance.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("arbitrage_dashboard.bot_data")

# Paths to bot data sources
LOG_DIR = Path("logs")
DATA_DIR = Path("data")
PERFORMANCE_DIR = DATA_DIR / "performance"
TRANSACTIONS_DIR = DATA_DIR / "transactions"

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
PERFORMANCE_DIR.mkdir(exist_ok=True)
TRANSACTIONS_DIR.mkdir(exist_ok=True)

# Regular expressions for log parsing
RE_ARBITRAGE_OPPORTUNITY = re.compile(r"Found arbitrage opportunity: (.*)")
RE_TRANSACTION_EXECUTED = re.compile(r"Executed transaction: (.*)")
RE_PROFIT_MADE = re.compile(r"Profit made: ([0-9.]+) ([A-Z]+)")
RE_ERROR = re.compile(r"ERROR: (.*)")
RE_GAS_USED = re.compile(r"Gas used: ([0-9]+)")

def get_recent_log_entries(max_entries: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent log entries from the bot's log files.
    
    Args:
        max_entries: Maximum number of entries to return
        
    Returns:
        List of log entries as dictionaries with timestamp, level, and message
    """
    entries = []
    
    # Find bot log files
    log_files = list(LOG_DIR.glob("arbitrage*.log"))
    if not log_files:
        logger.warning("No arbitrage bot log files found")
        return entries
    
    # Sort by modification time (newest first)
    log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Parse the most recent log file
    try:
        with open(log_files[0], "r") as f:
            # Read the file backwards to get most recent entries first
            lines = f.readlines()
            
            for line in reversed(lines):
                if len(entries) >= max_entries:
                    break
                    
                # Parse log entry
                try:
                    # Example: 2025-02-28 03:15:42,123 - arbitrage_bot.core.path_finder - INFO - Found arbitrage opportunity...
                    parts = line.strip().split(" - ", 3)
                    if len(parts) >= 4:
                        timestamp_str, module, level, message = parts
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                        
                        entry = {
                            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "module": module,
                            "level": level,
                            "message": message
                        }
                        entries.append(entry)
                except Exception as e:
                    logger.debug(f"Failed to parse log line: {e}")
                    continue
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
    
    return entries

def get_arbitrage_opportunities(max_entries: int = 10) -> List[Dict[str, Any]]:
    """
    Extract arbitrage opportunities from log entries.
    
    Args:
        max_entries: Maximum number of opportunities to return
        
    Returns:
        List of arbitrage opportunities with details
    """
    opportunities = []
    
    # Get log entries
    log_entries = get_recent_log_entries(max_entries=500)  # Get more entries to find opportunities
    
    for entry in log_entries:
        if len(opportunities) >= max_entries:
            break
            
        message = entry.get("message", "")
        match = RE_ARBITRAGE_OPPORTUNITY.search(message)
        
        if match:
            try:
                opportunity_data = match.group(1)
                # Try to parse as JSON if possible
                try:
                    opportunity = json.loads(opportunity_data)
                except:
                    # If not JSON, create a simple dict
                    opportunity = {"description": opportunity_data}
                
                opportunity["timestamp"] = entry.get("timestamp")
                opportunities.append(opportunity)
            except Exception as e:
                logger.debug(f"Failed to parse opportunity: {e}")
    
    return opportunities

def get_transaction_history(max_entries: int = 10) -> List[Dict[str, Any]]:
    """
    Get transaction history from log files and transaction directory.
    
    Args:
        max_entries: Maximum number of transactions to return
        
    Returns:
        List of transactions with details
    """
    transactions = []
    
    # First try to read from transaction files
    try:
        tx_files = list(TRANSACTIONS_DIR.glob("*.json"))
        if tx_files:
            # Sort by modification time (newest first)
            tx_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            for tx_file in tx_files[:max_entries]:
                try:
                    with open(tx_file, "r") as f:
                        tx_data = json.load(f)
                        transactions.append(tx_data)
                except Exception as e:
                    logger.debug(f"Failed to parse transaction file {tx_file}: {e}")
    except Exception as e:
        logger.error(f"Failed to read transaction files: {e}")
    
    # If we don't have enough transactions, try to extract from logs
    if len(transactions) < max_entries:
        needed = max_entries - len(transactions)
        log_entries = get_recent_log_entries(max_entries=500)
        
        for entry in log_entries:
            if len(transactions) >= max_entries:
                break
                
            message = entry.get("message", "")
            match = RE_TRANSACTION_EXECUTED.search(message)
            
            if match:
                try:
                    tx_data = match.group(1)
                    # Try to parse as JSON if possible
                    try:
                        tx = json.loads(tx_data)
                    except:
                        # If not JSON, create a simple dict
                        tx = {"hash": tx_data}
                    
                    tx["timestamp"] = entry.get("timestamp")
                    transactions.append(tx)
                except Exception as e:
                    logger.debug(f"Failed to parse transaction: {e}")
    
    return transactions

def get_profit_summary() -> Dict[str, Any]:
    """
    Get profit summary from performance data and logs.
    
    Returns:
        Dictionary with profit metrics
    """
    summary = {
        "total_profit_eth": 0.0,
        "total_profit_usd": 0.0,
        "profitable_trades": 0,
        "failed_trades": 0,
        "average_profit": 0.0,
        "last_profit": 0.0,
        "last_profit_time": "Never"
    }
    
    # Try to read from performance files
    try:
        perf_files = list(PERFORMANCE_DIR.glob("*.json"))
        if perf_files:
            # Sort by modification time (newest first)
            perf_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Read the most recent performance file
            with open(perf_files[0], "r") as f:
                try:
                    perf_data = json.load(f)
                    if isinstance(perf_data, dict):
                        summary.update(perf_data)
                except Exception as e:
                    logger.error(f"Failed to parse performance data: {e}")
    except Exception as e:
        logger.error(f"Failed to read performance files: {e}")
    
    # If no data found, try to extract from logs
    if summary["total_profit_eth"] == 0.0:
        log_entries = get_recent_log_entries(max_entries=1000)
        
        for entry in log_entries:
            message = entry.get("message", "")
            match = RE_PROFIT_MADE.search(message)
            
            if match:
                try:
                    profit = float(match.group(1))
                    token = match.group(2)
                    
                    if token.upper() == "ETH":
                        summary["total_profit_eth"] += profit
                        summary["profitable_trades"] += 1
                        summary["last_profit"] = profit
                        summary["last_profit_time"] = entry.get("timestamp", "Unknown")
                except Exception as e:
                    logger.debug(f"Failed to parse profit: {e}")
    
    # Calculate average profit if we have trades
    if summary["profitable_trades"] > 0:
        summary["average_profit"] = summary["total_profit_eth"] / summary["profitable_trades"]
    
    return summary

def get_system_errors(max_entries: int = 10) -> List[Dict[str, Any]]:
    """
    Get system errors from log files.
    
    Args:
        max_entries: Maximum number of errors to return
        
    Returns:
        List of errors with details
    """
    errors = []
    
    # Get log entries
    log_entries = get_recent_log_entries(max_entries=500)
    
    for entry in log_entries:
        if len(errors) >= max_entries:
            break
            
        level = entry.get("level", "")
        message = entry.get("message", "")
        
        if level == "ERROR" or "ERROR:" in message:
            errors.append({
                "timestamp": entry.get("timestamp", "Unknown"),
                "module": entry.get("module", "Unknown"),
                "message": message
            })
    
    return errors

def get_dex_status() -> Dict[str, Dict[str, Any]]:
    """
    Get DEX status from logs and configuration.
    
    Returns:
        Dictionary with DEX status information
    """
    dex_status = {}
    
    # Get log entries
    log_entries = get_recent_log_entries(max_entries=1000)
    
    # Extract DEX-related log entries
    dex_entries = {}
    for entry in log_entries:
        module = entry.get("module", "")
        if "dex" in module.lower():
            dex_name = module.split(".")[-1] if "." in module else "unknown"
            if dex_name not in dex_entries:
                dex_entries[dex_name] = []
            dex_entries[dex_name].append(entry)
    
    # For each DEX, determine the status
    for dex_name, entries in dex_entries.items():
        # Default status
        status = {
            "status": "Unknown",
            "last_activity": "Unknown",
            "errors": 0
        }
        
        if entries:
            # Get the most recent timestamp
            status["last_activity"] = entries[0].get("timestamp", "Unknown")
            
            # Count errors
            for entry in entries:
                level = entry.get("level", "")
                if level == "ERROR":
                    status["errors"] += 1
            
            # Determine status based on errors
            if status["errors"] == 0:
                status["status"] = "Healthy"
            elif status["errors"] < 5:
                status["status"] = "Warning"
            else:
                status["status"] = "Error"
        
        dex_status[dex_name] = status
    
    return dex_status

def get_gas_statistics() -> Dict[str, Any]:
    """
    Get gas price statistics from logs.
    
    Returns:
        Dictionary with gas statistics
    """
    stats = {
        "average_gas_used": 0,
        "total_gas_used": 0,
        "transactions_count": 0,
        "highest_gas_used": 0
    }
    
    # Get log entries
    log_entries = get_recent_log_entries(max_entries=500)
    
    # Extract gas usage information
    gas_entries = []
    for entry in log_entries:
        message = entry.get("message", "")
        match = RE_GAS_USED.search(message)
        
        if match:
            try:
                gas_used = int(match.group(1))
                gas_entries.append(gas_used)
                
                stats["total_gas_used"] += gas_used
                stats["transactions_count"] += 1
                
                if gas_used > stats["highest_gas_used"]:
                    stats["highest_gas_used"] = gas_used
            except Exception as e:
                logger.debug(f"Failed to parse gas used: {e}")
    
    # Calculate average gas used
    if stats["transactions_count"] > 0:
        stats["average_gas_used"] = stats["total_gas_used"] // stats["transactions_count"]
    
    return stats

def get_bot_status() -> Dict[str, Any]:
    """
    Get overall bot status.
    
    Returns:
        Dictionary with bot status information
    """
    status = {
        "status": "Unknown",
        "last_activity": "Unknown",
        "errors_24h": 0,
        "opportunities_24h": 0,
        "transactions_24h": 0,
        "running": False
    }
    
    # Get log entries for the last 24 hours
    log_entries = get_recent_log_entries(max_entries=1000)
    
    if log_entries:
        # Get the most recent timestamp
        status["last_activity"] = log_entries[0].get("timestamp", "Unknown")
        
        # Check if the last activity was recent (within last 5 minutes)
        try:
            last_time = datetime.strptime(status["last_activity"], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            time_diff = (now - last_time).total_seconds()
            status["running"] = time_diff < 300  # 5 minutes
        except Exception:
            status["running"] = False
        
        # Count errors, opportunities, and transactions
        for entry in log_entries:
            message = entry.get("message", "")
            level = entry.get("level", "")
            
            if level == "ERROR" or "ERROR:" in message:
                status["errors_24h"] += 1
            
            if "arbitrage opportunity" in message.lower():
                status["opportunities_24h"] += 1
            
            if "executed transaction" in message.lower():
                status["transactions_24h"] += 1
        
        # Determine status based on errors and activity
        if status["running"]:
            if status["errors_24h"] == 0:
                status["status"] = "Healthy"
            elif status["errors_24h"] < 5:
                status["status"] = "Warning"
            else:
                status["status"] = "Error"
        else:
            status["status"] = "Inactive"
    
    return status

def get_dashboard_data() -> Dict[str, Any]:
    """
    Get all data needed for the dashboard.
    
    Returns:
        Dictionary with all dashboard data
    """
    return {
        "bot_status": get_bot_status(),
        "profit_summary": get_profit_summary(),
        "recent_transactions": get_transaction_history(max_entries=5),
        "recent_opportunities": get_arbitrage_opportunities(max_entries=5),
        "recent_errors": get_system_errors(max_entries=5),
        "dex_status": get_dex_status(),
        "gas_statistics": get_gas_statistics()
    }