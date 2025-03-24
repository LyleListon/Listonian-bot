"""
Configuration Loader

This module provides functionality for loading and validating bot configuration.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "web3": {
        "rpc_url": "http://localhost:8545",
        "chain_id": 1,
        "retry_count": 3,
        "retry_delay": 1.0,
        "timeout": 30
    },
    "flashbots": {
        "relay_url": "https://relay.flashbots.net",
        "bundle_timeout": 30,
        "max_blocks_to_search": 25
    },
    "discovery": {
        "discovery_interval_seconds": 10,
        "max_opportunities": 100,
        "min_profit_wei": int(0.001 * 10**18),  # 0.001 ETH
        "max_path_length": 3
    },
    "execution": {
        "default_execution_strategy": "standard",
        "auto_execute": False,
        "max_concurrent_executions": 1,
        "min_confidence_score": 0.8,
        "gas_limit_buffer": 1.2,  # 20% buffer
        "slippage_tolerance": 0.005  # 0.5%
    },
    "market_data": {
        "update_interval_seconds": 60,
        "price_cache_ttl": 300,  # 5 minutes
        "liquidity_cache_ttl": 300
    },
    "analytics": {
        "performance_window_days": 30,
        "metrics_update_interval": 300,  # 5 minutes
        "trade_history_limit": 1000
    },
    "memory_bank": {
        "storage_path": "memory-bank",
        "max_trade_history": 10000,
        "backup_interval_hours": 24
    },
    "logging": {
        "level": "INFO",
        "file_path": "logs/arbitrage.log",
        "max_file_size_mb": 100,
        "backup_count": 5
    }
}

def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment and files.
    
    The configuration is loaded in the following order (later sources override earlier ones):
    1. Default configuration
    2. Configuration file (config.json)
    3. Environment variables
    
    Returns:
        Dictionary containing the configuration
    """
    config = DEFAULT_CONFIG.copy()
    
    # Load from config file if exists
    config_path = Path("config.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = json.load(f)
            config = _deep_update(config, file_config)
            logger.info("Loaded configuration from config.json")
        except Exception as e:
            logger.error(f"Error loading config.json: {e}", exc_info=True)
    
    # Load from environment variables
    config = _load_from_env(config)
    
    # Validate configuration
    _validate_config(config)
    
    return config

def _deep_update(base: Dict, update: Dict) -> Dict:
    """
    Recursively update a dictionary and handle environment variables.
    
    Args:
        base: Base dictionary to update
        update: Dictionary with updates
        
    Returns:
        Updated dictionary
    """
    def _resolve_env_var(value: str) -> str:
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, value)
        return value

    """
    Recursively update a dictionary.
    
    Args:
        base: Base dictionary to update
        update: Dictionary with updates
        
    Returns:
        Updated dictionary
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            base[key] = _deep_update(base[key], value)
        else:
            base[key] = _resolve_env_var(value)
    return base

def _load_from_env(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Environment variables should be prefixed with ARBY_ and use double underscores
    to indicate nesting. For example:
    ARBY_WEB3__RPC_URL=http://localhost:8545
    
    Args:
        config: Base configuration to update
        
    Returns:
        Updated configuration
    """
    for key, value in os.environ.items():
        if not key.startswith("ARBY_"):
            continue
        
        # Remove prefix and split into parts
        parts = key[5:].lower().split("__")
        
        # Navigate to the correct level in the config
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value, converting to appropriate type
        try:
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            elif value.replace(".", "", 1).isdigit():
                value = float(value)
            current[parts[-1]] = value
        except Exception as e:
            logger.error(f"Error parsing environment variable {key}: {e}")
    
    return config

def _validate_config(config: Dict[str, Any]) -> None:
    """
    Validate the configuration.
    
    Args:
        config: Configuration to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate required fields
    required_fields = [
        ("web3", "rpc_url"),
        ("web3", "chain_id"),
        ("flashbots", "relay_url"),
        ("discovery", "discovery_interval_seconds"),
        ("execution", "default_execution_strategy"),
        ("market_data", "update_interval_seconds"),
        ("memory_bank", "storage_path")
    ]
    
    for section, field in required_fields:
        if section not in config or field not in config[section]:
            raise ValueError(f"Missing required config field: {section}.{field}")
    
    # Validate numeric ranges
    if config["discovery"]["discovery_interval_seconds"] < 1:
        raise ValueError("discovery_interval_seconds must be >= 1")
    
    if config["execution"]["max_concurrent_executions"] < 1:
        raise ValueError("max_concurrent_executions must be >= 1")
    
    if config["market_data"]["update_interval_seconds"] < 1:
        raise ValueError("update_interval_seconds must be >= 1")
    
    if config["analytics"]["performance_window_days"] < 1:
        raise ValueError("performance_window_days must be >= 1")
    
    # Validate paths
    memory_path = Path(config["memory_bank"]["storage_path"])
    memory_path.mkdir(parents=True, exist_ok=True)
    
    log_path = Path(config["logging"]["file_path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

def load_production_config() -> Dict[str, Any]:
    """
    Load production configuration from .env.production and config.json.
    
    Returns:
        Dictionary containing the production configuration
    """
    # Load base config
    config = load_config()
    
    # Load .env.production if it exists
    env_path = Path(".env.production")
    if not env_path.exists():
        raise ValueError(".env.production file not found")
    
    # Parse .env.production file
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            logger.info(f"Loading env var: {key}={value}")
            os.environ[key.strip()] = value.strip()
    
    # Update config with production values
    rpc_url = os.environ.get("BASE_RPC_URL")
    logger.info(f"Using RPC URL: {rpc_url}")
    
    config["web3"] = {
        "rpc_url": rpc_url,
       "chain_id": 8453,
        "retry_count": 3,
        "retry_delay": 1.0,
        "timeout": 30
    }
    config["flashbots"] = {
        "relay_url": "https://relay.flashbots.net"
,
        "bundle_timeout": 30,
        "max_blocks_to_search": 25
    }
    config["execution"]["auto_execute"] = True
    
    return config
