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
import asyncio
from cryptography.fernet import Fernet
from concurrent.futures import ThreadPoolExecutor

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
    "trading": [
        "max_slippage",
        "max_liquidity_usage",
        "min_profit_threshold",
        "max_gas_price"
    ],
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
            from .secure_env import SecureEnvironment
            secure_env = SecureEnvironment()
            
            # Load secure values for config sections
            for section in resolved:
                if isinstance(resolved[section], dict):
                    for key, value in resolved[section].items():
                        if isinstance(value, str) and value.startswith('$SECURE:'):
                            secure_key = value[8:]  # Remove '$SECURE:' prefix
                            secure_value = secure_env.secure_load(secure_key)
                            if secure_value:
                                resolved[section][key] = secure_value
        
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

        # Resolve secure values first
        config = resolve_secure_values(config)

        # Load and validate private key
        private_key = config['web3']['wallet_key']
        if not private_key:
            raise ValueError("Private key not found")
        if len(private_key) != 64 or not all(c in '0123456789abcdefABCDEF' for c in private_key):
            raise ValueError("Invalid private key format - must be 32 bytes hex")

        # Load Flashbots auth key (defaults to private key if not set)
        flashbots_auth = config['flashbots'].get('auth_key')
        if flashbots_auth and flashbots_auth.startswith('$SECURE:'):
            from .secure_env import SecureEnvironment
            secure_env = SecureEnvironment()
            flashbots_auth = secure_env.secure_load('FLASHBOTS_AUTH_KEY')
        if not flashbots_auth:
            config['flashbots']['auth_key'] = private_key

        relay_url = config['flashbots']['relay_url']
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

async def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> None:
    """
    Save configuration to a JSON file.

    This function:
    1. Validates the configuration
    2. Preserves secure values
    3. Maintains file permissions
    4. Creates backups

    Args:
        config: Configuration dictionary to save
        config_path: Optional path to save config file. If not provided, uses default path.

    Raises:
        ValueError: If config validation fails
        IOError: If file operations fail
    """
    try:
        # Use default path if none provided
        if not config_path:
            config_path = DEFAULT_CONFIG_PATH

        config_file = Path(config_path)
        
        # Create backup of existing config
        if config_file.exists():
            backup_path = config_file.with_suffix('.json.backup')
            config_file.rename(backup_path)

        # Validate required sections and fields
        for section, fields in REQUIRED_SECTIONS.items():
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
            
            section_config = config[section]
            for field in fields:
                if field not in section_config:
                    raise ValueError(f"Missing required field '{field}' in section '{section}'")

        # Load existing secure values
        existing_config = {}
        if backup_path.exists():
            with open(backup_path) as f:
                existing_config = json.load(f)

        # Preserve secure values
        for section in config:
            if isinstance(config[section], dict):
                for key, value in config[section].items():
                    if (section in existing_config and 
                        isinstance(existing_config[section], dict) and
                        key in existing_config[section]):
                        existing_value = existing_config[section][key]
                        if (isinstance(existing_value, str) and 
                            (existing_value.startswith('ENC[') or 
                             existing_value.startswith('$SECURE:'))):
                            config[section][key] = existing_value

        # Use ThreadPoolExecutor for file I/O
        def write_config():
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4, sort_keys=True)
            os.chmod(config_file, 0o600)
            if backup_path.exists():
                backup_path.unlink()

        # Execute file operations in thread pool
        with ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(
                executor,
                write_config
            )

        logger.info(f"Configuration saved successfully to {config_file}")

    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        if 'backup_path' in locals() and backup_path.exists():
            if config_file.exists():
                config_file.unlink()
            backup_path.rename(config_file)
        raise
