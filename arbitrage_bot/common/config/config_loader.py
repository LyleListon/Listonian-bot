"""Configuration loader for the arbitrage bot."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


def load_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from files and environment variables.
    
    Args:
        environment: The environment to load configuration for.
            If None, will use the ENVIRONMENT environment variable,
            or default to 'development'.
            
    Returns:
        The merged configuration dictionary.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Determine environment
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent.parent.parent
    
    # Load default configuration
    default_config_path = root_dir / "configs" / "default" / "config.json"
    with open(default_config_path, "r") as f:
        config = json.load(f)
    
    # Load environment-specific configuration
    env_config_path = root_dir / "configs" / environment / "config.json"
    if env_config_path.exists():
        with open(env_config_path, "r") as f:
            env_config = json.load(f)
        # Merge environment config into default config
        deep_merge(config, env_config)
    
    # Override with environment variables
    override_with_env_vars(config)
    
    return config


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Recursively merge override dict into base dict.
    
    Args:
        base: The base dictionary to merge into.
        override: The dictionary with values to override.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


def override_with_env_vars(config: Dict[str, Any], prefix: str = "LISTONIAN") -> None:
    """Override configuration with environment variables.
    
    Environment variables should be in the format:
    LISTONIAN_SECTION_SUBSECTION_KEY=value
    
    For example:
    LISTONIAN_TRADING_MIN_PROFIT_THRESHOLD=0.5
    
    Args:
        config: The configuration dictionary to override.
        prefix: The prefix for environment variables.
    """
    for env_var, value in os.environ.items():
        if not env_var.startswith(f"{prefix}_"):
            continue
        
        # Remove prefix and split into parts
        parts = env_var[len(f"{prefix}_"):].lower().split("_")
        
        # Navigate to the correct part of the config
        current = config
        for part in parts[:-1]:
            if part.isdigit():  # Handle array indices
                part = int(part)
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        key = parts[-1]
        if key.isdigit():  # Handle array indices
            key = int(key)
        
        # Convert value to appropriate type
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)
        elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
            value = float(value)
        
        current[key] = value


def get_config_value(config: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get a value from the configuration using a dot-separated path.
    
    Args:
        config: The configuration dictionary.
        path: The dot-separated path to the value.
        default: The default value to return if the path doesn't exist.
        
    Returns:
        The value at the specified path, or the default if not found.
    """
    parts = path.split(".")
    current = config
    
    for part in parts:
        if part.isdigit():  # Handle array indices
            part = int(part)
        
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and isinstance(part, int) and 0 <= part < len(current):
            current = current[part]
        else:
            return default
    
    return current


def save_config(config: Dict[str, Any], environment: str) -> None:
    """Save configuration to a file.
    
    Args:
        config: The configuration dictionary to save.
        environment: The environment to save the configuration for.
    """
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent.parent.parent
    
    # Create the environment directory if it doesn't exist
    env_dir = root_dir / "configs" / environment
    env_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the configuration
    config_path = env_dir / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
