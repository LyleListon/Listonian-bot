"""
Configuration Loader Module

This module provides utilities for loading and managing configuration.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = 'configs/config.json'
DEFAULT_CONFIG = {
    "provider_url": "YOUR_ETHEREUM_NODE_URL",
    "chain_id": 1,
    "private_key": "YOUR_PRIVATE_KEY",
    "wallet_address": "YOUR_WALLET_ADDRESS",
    "log_level": "INFO",
    "max_paths_to_check": 100,
    "min_profit_threshold": 0.001,
    "slippage_tolerance": 50,
    "gas_limit_buffer": 20,
    "tokens": {
        "WETH": {
            "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "decimals": 18
        },
        "USDC": {
            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "decimals": 6
        }
    }
}

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        # Check if the config file exists
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info("Successfully loaded configuration from %s", config_path)
                return config
        else:
            # If config file doesn't exist, create a default one
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            logger.info("Created default configuration at %s", config_path)
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error("Failed to load configuration from %s: %s", config_path, e)
        logger.info("Using default configuration")
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any], config_path: str = DEFAULT_CONFIG_PATH) -> bool:
    """
    Save configuration to a JSON file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to the configuration file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Successfully saved configuration to %s", config_path)
        return True
    except Exception as e:
        logger.error("Failed to save configuration to %s: %s", config_path, e)
        return False

def get_config_value(key: str, default=None, config: Dict[str, Any] = None) -> Any:
    """
    Get a configuration value, with a default if not found.
    
    Args:
        key: Configuration key to retrieve
        default: Default value if key not found
        config: Configuration dictionary (if None, will load from file)
        
    Returns:
        Configuration value or default
    """
    if config is None:
        config = load_config()
    
    # Handle nested keys with dot notation (e.g., "flash_loans.enabled")
    if '.' in key:
        parts = key.split('.')
        value = config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    
    return config.get(key, default)

def update_config_value(key: str, value: Any, config_path: str = DEFAULT_CONFIG_PATH) -> bool:
    """
    Update a configuration value and save to file.
    
    Args:
        key: Configuration key to update
        value: New value
        config_path: Path to the configuration file
        
    Returns:
        True if successful, False otherwise
    """
    config = load_config(config_path)
    
    # Handle nested keys with dot notation
    if '.' in key:
        parts = key.split('.')
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    else:
        config[key] = value
    
    return save_config(config, config_path)
