"""
Configuration Loader Module

This module provides functionality for:
- Loading configuration files
- Validating configuration settings
- Providing default values
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "configs/config.json"

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Optional path to config file. If not provided, uses default path.

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
        ValueError: If config is missing required fields
    """
    try:
        # Use default path if none provided
        if not config_path:
            config_path = DEFAULT_CONFIG_PATH

        # Convert to Path object
        config_file = Path(config_path)

        # Check if file exists
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        # Read and parse JSON
        with open(config_file) as f:
            config = json.load(f)

        # Validate required fields
        required_fields = [
            "provider_url",
            "chain_id",
            "tokens",
            "dexes",
            "flash_loan",
            "gas",
            "security"
        ]

        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")

        # Add default values if not present
        config.setdefault("logging", {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "logs/arbitrage.log",
            "max_size": 10485760,
            "backup_count": 5
        })

        config.setdefault("monitoring", {
            "enabled": True,
            "interval": 60,
            "metrics_port": 9090
        })

        config.setdefault("performance", {
            "cache_ttl": 300,
            "max_concurrent_paths": 10,
            "batch_size": 100
        })

        # Validate token addresses are checksummed
        for token, address in config["tokens"].items():
            if not address.startswith("0x"):
                raise ValueError(f"Invalid token address format for {token}: {address}")

        # Validate DEX addresses
        for dex_name, dex_config in config["dexes"].items():
            if not dex_config["factory"].startswith("0x"):
                raise ValueError(f"Invalid factory address for {dex_name}: {dex_config['factory']}")
            if not dex_config["router"].startswith("0x"):
                raise ValueError(f"Invalid router address for {dex_name}: {dex_config['router']}")

        # Validate flash loan config
        flash_loan = config["flash_loan"]
        if not flash_loan["balancer_vault"].startswith("0x"):
            raise ValueError(f"Invalid Balancer vault address: {flash_loan['balancer_vault']}")

        if not isinstance(flash_loan["min_profit"], str):
            flash_loan["min_profit"] = str(flash_loan["min_profit"])

        # Validate gas config
        gas = config["gas"]
        if not isinstance(gas["max_priority_fee"], str):
            gas["max_priority_fee"] = str(gas["max_priority_fee"])
        if not isinstance(gas["max_fee"], str):
            gas["max_fee"] = str(gas["max_fee"])

        logger.info("Configuration loaded successfully")
        return config

    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

def create_config_loader(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new configuration loader.

    Args:
        config_path: Optional path to config file

    Returns:
        Configuration dictionary
    """
    return load_config(config_path)
