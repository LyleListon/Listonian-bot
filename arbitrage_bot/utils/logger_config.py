"""Logging configuration for the arbitrage bot."""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

def setup_logging(log_level=logging.DEBUG):  # Changed default to DEBUG
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    metrics_formatter = logging.Formatter(
        '%(asctime)s - %(message)s'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # File handler for general logs - using DEBUG level for detailed logging
    general_log = log_dir / f'arbitrage_{datetime.now().strftime("%Y%m%d")}.log'
    file_handler = logging.handlers.RotatingFileHandler(
        general_log,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(logging.DEBUG)  # Set to DEBUG for detailed file logs
    root_logger.addHandler(file_handler)

    # Console handler for ERROR and above only
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(logging.ERROR)  # Keep ERROR level for console
    root_logger.addHandler(console_handler)
    
    # Set up metrics logger - keep at INFO since these are important metrics
    metrics_logger = logging.getLogger('metrics')
    metrics_logger.setLevel(logging.INFO)
    metrics_logger.propagate = False
    
    # File handler for metrics
    metrics_log = log_dir / f'metrics_{datetime.now().strftime("%Y%m%d")}.log'
    metrics_handler = logging.handlers.RotatingFileHandler(
        metrics_log,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    metrics_handler.setFormatter(metrics_formatter)
    metrics_logger.addHandler(metrics_handler)
    
    # Set up opportunity logger - keep at INFO since these are important events
    opportunity_logger = logging.getLogger('opportunities')
    opportunity_logger.setLevel(logging.INFO)
    opportunity_logger.propagate = False
    
    # File handler for opportunities
    opportunity_log = log_dir / f'opportunities_{datetime.now().strftime("%Y%m%d")}.log'
    opportunity_handler = logging.handlers.RotatingFileHandler(
        opportunity_log,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    opportunity_handler.setFormatter(detailed_formatter)
    opportunity_logger.addHandler(opportunity_handler)
    
    # Set up execution logger - keep at INFO since these are important events
    execution_logger = logging.getLogger('execution')
    execution_logger.setLevel(logging.INFO)
    execution_logger.propagate = False
    
    # File handler for execution
    execution_log = log_dir / f'execution_{datetime.now().strftime("%Y%m%d")}.log'
    execution_handler = logging.handlers.RotatingFileHandler(
        execution_log,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    execution_handler.setFormatter(detailed_formatter)
    execution_logger.addHandler(execution_handler)

def log_metric(name: str, value: float, **tags):
    """Log a metric with optional tags."""
    metrics_logger = logging.getLogger('metrics')
    tag_str = ' '.join(f'{k}={v}' for k, v in tags.items())
    metrics_logger.info(f'{name}={value} {tag_str}')

def log_opportunity(opportunity: dict):
    """Log an arbitrage opportunity."""
    opportunity_logger = logging.getLogger('opportunities')
    opportunity_logger.info(
        f"Found opportunity:\n"
        f"  DEX: {opportunity['dex_from']} -> {opportunity['dex_to']}\n"
        f"  Token: {opportunity['token']}\n"
        f"  Price diff: {opportunity['price_diff']*100:.2f}%\n"
        f"  Amount: {opportunity['amount_in']} ETH\n"
        f"  Expected profit: ${opportunity['profit_usd']:.2f}\n"
        f"  Path: {' -> '.join(opportunity['token_path'])}"
    )

def log_execution(tx_hash: str, status: str, profit: float, gas_cost: float):
    """Log a trade execution."""
    execution_logger = logging.getLogger('execution')
    execution_logger.info(
        f"Trade execution:\n"
        f"  Hash: {tx_hash}\n"
        f"  Status: {status}\n"
        f"  Profit: ${profit:.2f}\n"
        f"  Gas cost: ${gas_cost:.2f}\n"
        f"  Net profit: ${profit - gas_cost:.2f}"
    )

def log_system_metrics(
    memory_usage: float,
    cpu_usage: float,
    thread_count: int,
    active_approvals: int
):
    """Log system health metrics."""
    metrics_logger = logging.getLogger('metrics')
    metrics_logger.info(
        f"System metrics:\n"
        f"  Memory usage: {memory_usage:.1f}MB\n"
        f"  CPU usage: {cpu_usage:.1f}%\n"
        f"  Thread count: {thread_count}\n"
        f"  Active approvals: {active_approvals}"
    )
