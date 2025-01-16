"""Configuration loading utilities."""

import logging
import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Configuration related errors."""

    pass


class ConfigLoader:
    """Configuration loader class."""

    def __init__(self, testing: bool = False):
        """
        Initialize config loader.

        Args:
            testing (bool, optional): Whether to use test configuration
        """
        self.testing = testing
        self._config = None
        self._ensure_config()

    def _ensure_config(self):
        """Ensure configuration exists."""
        if not ensure_config_exists(self.testing):
            raise ConfigurationError("Failed to create configuration")

    def get_config(self) -> Dict[str, Any]:
        """
        Get full configuration.

        Returns:
            Dict[str, Any]: Configuration data
        """
        if self._config is None:
            self._config = load_config(self.testing)
        return self._config

    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key (str): Configuration key
            default (Any, optional): Default value if key not found

        Returns:
            Any: Configuration value
        """
        return get_config_value(key, default, self.testing)

    def update(self, updates: Dict[str, Any]) -> bool:
        """
        Update configuration values.

        Args:
            updates (Dict[str, Any]): Configuration updates

        Returns:
            bool: True if successful
        """
        success = update_config(updates, self.testing)
        if success:
            self._config = None  # Force reload on next get
        return success

    def get_risk_params(self) -> Dict[str, Any]:
        """
        Get risk management parameters.

        Returns:
            Dict[str, Any]: Risk parameters
        """
        config = self.get_config()
        return {
            "min_profit_threshold": config.get("execution", {}).get(
                "min_profit_threshold", 0.002
            ),
            "max_slippage": config.get("trading", {}).get("max_slippage", 0.01),
            "min_liquidity": config.get("trading", {}).get("min_liquidity", 1000),
            "max_trade_size": config.get("trading", {}).get("max_trade_size", 1.0),
        }


def create_config_loader(testing: bool = False) -> ConfigLoader:
    """
    Create configuration loader instance.

    Args:
        testing (bool, optional): Whether to use test configuration

    Returns:
        ConfigLoader: Configuration loader instance
    """
    return ConfigLoader(testing)


def ensure_config_exists(testing: bool = False) -> bool:
    """
    Ensure configuration file exists.

    Args:
        testing (bool, optional): Whether to use test configuration

    Returns:
        bool: True if config exists or was created
    """
    if testing:
        return True

    config_paths = [
        Path("config.json"),
        Path("configs/config.json"),
        Path("arbitrage_bot/configs/config.json"),
    ]

    # Check if config exists
    for path in config_paths:
        if path.exists():
            return True

    # Try to copy template
    template_paths = [
        Path("config.template.json"),
        Path("configs/config.template.json"),
        Path("arbitrage_bot/configs/config.template.json"),
    ]

    for template_path in template_paths:
        if template_path.exists():
            try:
                # Create config directory if needed
                config_path = Path("config.json")
                config_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy template to config
                shutil.copy2(template_path, config_path)
                logger.info(f"Created config from template: {config_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to copy config template: {e}")
                continue

    # Create default config
    try:
        config = {
            "network": "mainnet",
            "rpc_url": "http://localhost:8545",
            "auto_execute": False,
            "execution": {
                "enabled": True,
                "loop_interval": 10,
                "min_profit_threshold": 0.002,
                "max_concurrent_trades": 1,
            },
            "monitoring": {"update_interval": 10, "log_level": "INFO"},
            "trading": {
                "max_slippage": 0.01,
                "min_liquidity": 1000,
                "max_trade_size": 1.0,
            },
        }

        config_path = Path("config.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Created default config: {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to create default config: {e}")
        return False


def load_config(testing: bool = False) -> Dict[str, Any]:
    """
    Load configuration from file.

    Args:
        testing (bool, optional): Whether to use test configuration

    Returns:
        Dict[str, Any]: Configuration data
    """
    def merge_configs(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configurations."""
        merged = base.copy()
        for key, value in overlay.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged

    if testing:
        return {
            "network": "test",
            "rpc_url": "http://localhost:8545",
            "auto_execute": False,
            "execution": {
                "enabled": True,
                "loop_interval": 1,
                "min_profit_threshold": 0.001,
                "max_concurrent_trades": 1,
            },
            "monitoring": {"update_interval": 1, "log_level": "INFO"},
            "trading": {
                "max_slippage": 0.01,
                "min_liquidity": 100,
                "max_trade_size": 0.1,
            },
            "tokens": {
                "WETH": {
                    "address": "0x0000000000000000000000000000000000000000",
                    "decimals": 18,
                },
                "USDC": {
                    "address": "0x0000000000000000000000000000000000000001",
                    "decimals": 6,
                },
            },
            "mcp": {
                "price_validation": {
                    "enabled": True,
                    "max_deviation_percent": 5.0,
                    "required_confidence": 0.8,
                    "update_interval": 60,
                    "tokens": {
                        "WETH": "ethereum",
                        "USDC": "usd-coin",
                        "DAI": "dai"
                    }
                },
                "market_analysis": {
                    "enabled": True,
                    "metrics": ["volatility", "volume", "trend"],
                    "thresholds": {
                        "high_volatility": 0.5,
                        "medium_volatility": 0.3,
                        "min_volume_usd": 100000,
                        "min_liquidity_usd": 500000
                    },
                    "cache_duration": 300
                }
            },
        }

    # Load main config
    config = None
    config_paths = [
        Path("config.json"),
        Path("configs/config.json"),
        Path("arbitrage_bot/configs/config.json"),
        Path(os.getcwd()) / "config.json",
        Path(os.getcwd()) / "configs" / "config.json",
        Path(os.getcwd()) / "arbitrage_bot" / "configs" / "config.json",
    ]

    logger.debug("Checking main config paths:")
    for path in config_paths:
        logger.debug(f"- {path} ({'exists' if path.exists() else 'not found'})")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info(f"Loading main config from: {path}")
                break
            except Exception as e:
                logger.error(f"Failed to load main config from {path}: {e}")

    if not config:
        raise FileNotFoundError("No main configuration file found")

    # Load DEX config
    dex_config_paths = [
        Path("arbitrage_bot/configs/data/dex_config.json"),
        Path(os.getcwd()) / "arbitrage_bot" / "configs" / "data" / "dex_config.json",
    ]

    logger.debug("Checking DEX config paths:")
    for path in dex_config_paths:
        logger.debug(f"- {path} ({'exists' if path.exists() else 'not found'})")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    dex_config = json.load(f)
                logger.info(f"Loading DEX config from: {path}")
                config = merge_configs(config, dex_config)
                break
            except Exception as e:
                logger.error(f"Failed to load DEX config from {path}: {e}")

    logger.debug(f"Final merged config: {json.dumps(config, indent=2)}")
    logger.info(f"Config loaded successfully: {len(config)} top-level keys")
    return config


def get_config_value(key: str, default: Any = None, testing: bool = False) -> Any:
    """
    Get configuration value by key.

    Args:
        key (str): Configuration key
        default (Any, optional): Default value if key not found
        testing (bool, optional): Whether to use test configuration

    Returns:
        Any: Configuration value
    """
    try:
        config = load_config(testing=testing)
        keys = key.split(".")
        value = config
        for k in keys:
            value = value.get(k)
            if value is None:
                return default
        return value
    except Exception as e:
        logger.error(f"Failed to get config value for {key}: {e}")
        return default


def update_config(updates: Dict[str, Any], testing: bool = False) -> bool:
    """
    Update configuration values.

    Args:
        updates (Dict[str, Any]): Configuration updates
        testing (bool, optional): Whether to use test configuration

    Returns:
        bool: True if successful
    """
    if testing:
        return True

    try:
        config = load_config()
        config.update(updates)

        # Write to first available config path
        config_paths = [
            Path("config.json"),
            Path("configs/config.json"),
            Path("arbitrage_bot/configs/config.json"),
        ]

        for path in config_paths:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                logger.info(f"Updated config at: {path}")
                return True
            except Exception as e:
                logger.error(f"Failed to write config to {path}: {e}")
                continue

        return False

    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return False
