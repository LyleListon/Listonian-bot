"""
Configuration Loader Module

This module provides functionality for:
- Loading configuration files
- Validating configuration settings
- Providing default values
- Resolving secure values
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import base64
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "configs/production.json"
REQUIRED_SECTIONS = {
    "web3": ["rpc_url", "chain_id", "wallet_key"],
    "flashbots": ["relay_url", "auth_key", "min_profit", "max_gas_price"],
    "flash_loan": ["enabled", "use_flashbots", "min_profit", "aave_pool"],
    "path_finder": ["max_paths_to_check", "max_path_length", "max_parallel_requests"],
    "scan": ["interval", "amount_wei", "max_paths"],
    "monitoring": ["stats_interval", "log_level"],
    "tokens": ["WETH", "USDC"],
    "mev_protection": [
        "enabled",
        "use_flashbots",
        "max_bundle_size",
        "max_blocks_ahead",
        "min_priority_fee",
        "max_priority_fee",
        "sandwich_detection",
        "frontrun_detection",
        "backrun_detection",
        "time_bandit_detection",
        "profit_threshold",
        "gas_threshold",
        "confidence_threshold",
        "adaptive_gas"
    ]
}

def resolve_secure_values(config: Dict[str, Any], secure_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolve secure values in configuration.
    
    This function handles:
    - Decryption of encrypted values
    - Loading values from environment variables
    - Loading values from secure files
    
    Args:
        config: Configuration dictionary
        secure_key: Optional encryption key for secure values
        
    Returns:
        Configuration with resolved secure values
    """
    try:
        # Create a copy to avoid modifying original
        resolved = config.copy()
        
        # Get secure key from environment if not provided
        if not secure_key:
            secure_key = os.environ.get('SECURE_KEY')
        
        if secure_key:
            # Initialize Fernet cipher
            fernet = Fernet(base64.b64encode(secure_key.encode()))
            
            # Decrypt any encrypted values
            for section in resolved:
                if isinstance(resolved[section], dict):
                    for key, value in resolved[section].items():
                        if isinstance(value, str) and value.startswith('ENC['):
                            # Extract encrypted value
                            encrypted = value[4:-1]
                            # Decrypt
                            decrypted = fernet.decrypt(encrypted.encode())
                            resolved[section][key] = decrypted.decode()
        
        # Load values from environment variables
        for section in resolved:
            if isinstance(resolved[section], dict):
                for key, value in resolved[section].items():
                    env_var = f"{section.upper()}_{key.upper()}"
                    if env_var in os.environ:
                        resolved[section][key] = os.environ[env_var]
        
        # Load values from secure files
        secure_dir = Path("secure")
        if secure_dir.exists():
            for file in secure_dir.glob("*.json"):
                with open(file) as f:
                    secure_values = json.load(f)
                    # Update config with secure values
                    for section, values in secure_values.items():
                        if section in resolved:
                            resolved[section].update(values)
        
        return resolved
    
    except Exception as e:
        logger.error(f"Error resolving secure values: {e}")
        raise

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

        # Validate required sections and fields
        for section, fields in REQUIRED_SECTIONS.items():
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
            
            section_config = config[section]
            for field in fields:
                if field not in section_config:
                    raise ValueError(f"Missing required field '{field}' in section '{section}'")

        # Validate token addresses are checksummed
        for token_name, token_info in config["tokens"].items():
            if isinstance(token_info, dict):
                address = token_info.get('address')
                if not address or not isinstance(address, str) or not address.startswith("0x"):
                    raise ValueError(f"Invalid token address format for {token_name}: {address}")
                
                # Validate decimals field
                if 'decimals' not in token_info:
                    raise ValueError(f"Missing decimals for token {token_name}")
                if not isinstance(token_info['decimals'], int):
                    raise ValueError(f"Invalid decimals format for {token_name}")

        # Validate Flashbots configuration
        flashbots_config = config['flashbots']
        auth_key = flashbots_config['auth_key']
        if not auth_key.startswith('0x') or len(auth_key) != 66:
            raise ValueError("Invalid Flashbots auth key format - must be 32 bytes hex")

        relay_url = flashbots_config['relay_url']
        if not relay_url.startswith(('http://', 'https://')):
            raise ValueError("Invalid Flashbots relay URL format")

        # Validate flash loan configuration
        flash_loan_config = config['flash_loan']
        if not isinstance(flash_loan_config['enabled'], bool):
            raise ValueError("flash_loan.enabled must be a boolean")
        if not isinstance(flash_loan_config['use_flashbots'], bool):
            raise ValueError("flash_loan.use_flashbots must be a boolean")
        aave_pool = flash_loan_config['aave_pool']
        if not aave_pool.startswith('0x'):
            raise ValueError("Invalid Aave pool address format")

        # Validate MEV protection settings
        mev_config = config['mev_protection']
        if not isinstance(mev_config['enabled'], bool):
            raise ValueError("mev_protection.enabled must be a boolean")
        if not isinstance(mev_config['use_flashbots'], bool):
            raise ValueError("mev_protection.use_flashbots must be a boolean")
        if not isinstance(mev_config['max_bundle_size'], int):
            raise ValueError("mev_protection.max_bundle_size must be an integer")
        if not isinstance(mev_config['max_blocks_ahead'], int):
            raise ValueError("mev_protection.max_blocks_ahead must be an integer")

        # Convert numeric strings to proper types
        mev_config['min_priority_fee'] = str(mev_config['min_priority_fee'])
        mev_config['max_priority_fee'] = str(mev_config['max_priority_fee'])
        mev_config['profit_threshold'] = str(mev_config['profit_threshold'])
        mev_config['gas_threshold'] = str(mev_config['gas_threshold'])
        mev_config['confidence_threshold'] = str(mev_config['confidence_threshold'])

        # Add default values for optional settings
        config.setdefault("logging", {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "logs/arbitrage.log",
            "max_size": 10485760,
            "backup_count": 5
        })

        config.setdefault("performance", {
            "cache_ttl": 300,
            "max_concurrent_paths": 10,
            "batch_size": 100
        })

        # Resolve any secure values
        config = resolve_secure_values(config)

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

def load_production_config() -> Dict[str, Any]:
    """
    Load production configuration with additional validation.
    
    This function specifically loads the production config file
    and performs extra validation checks required for production.
    
    Returns:
        Production configuration dictionary
    
    Raises:
        Various exceptions if validation fails
    """
    return load_config(DEFAULT_CONFIG_PATH)
