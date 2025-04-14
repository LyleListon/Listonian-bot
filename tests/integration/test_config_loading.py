"""Integration tests for configuration loading."""

import os
import tempfile
import json
from pathlib import Path

import pytest

from arbitrage_bot.common.config.config_loader import (
    load_config,
    get_config_value,
    deep_merge,
    override_with_env_vars,
)


def test_load_config_with_environment():
    """Test loading configuration with a specific environment."""
    # Load test configuration
    config = load_config("test")
    
    # Verify that test-specific values are loaded
    assert config["trading"]["min_profit_threshold"] == 0.1
    assert config["trading"]["max_trade_amount"] == 0.01
    assert config["trading"]["trading_enabled"] is False
    
    # Verify that default values are preserved
    assert "gas_price_multiplier" in config["trading"]
    assert "max_slippage" in config["trading"]


def test_get_config_value():
    """Test getting values from configuration using dot notation."""
    # Create a test configuration
    config = {
        "trading": {
            "min_profit_threshold": 0.5,
            "max_trade_amount": 1.0,
        },
        "blockchain": {
            "networks": [
                {
                    "name": "ethereum",
                    "enabled": True,
                },
                {
                    "name": "bsc",
                    "enabled": False,
                },
            ],
        },
    }
    
    # Test getting simple values
    assert get_config_value(config, "trading.min_profit_threshold") == 0.5
    assert get_config_value(config, "trading.max_trade_amount") == 1.0
    
    # Test getting nested values
    assert get_config_value(config, "blockchain.networks.0.name") == "ethereum"
    assert get_config_value(config, "blockchain.networks.1.enabled") is False
    
    # Test getting non-existent values
    assert get_config_value(config, "trading.non_existent") is None
    assert get_config_value(config, "trading.non_existent", default="default") == "default"
    assert get_config_value(config, "blockchain.networks.2.name") is None


def test_deep_merge():
    """Test deep merging of dictionaries."""
    # Create base and override dictionaries
    base = {
        "trading": {
            "min_profit_threshold": 0.5,
            "max_trade_amount": 1.0,
            "trading_enabled": True,
        },
        "blockchain": {
            "networks": [
                {
                    "name": "ethereum",
                    "enabled": True,
                },
            ],
        },
    }
    
    override = {
        "trading": {
            "min_profit_threshold": 0.1,
            "trading_enabled": False,
        },
        "blockchain": {
            "networks": [
                {
                    "name": "bsc",
                    "enabled": True,
                },
            ],
        },
    }
    
    # Merge dictionaries
    deep_merge(base, override)
    
    # Verify that values are merged correctly
    assert base["trading"]["min_profit_threshold"] == 0.1
    assert base["trading"]["max_trade_amount"] == 1.0
    assert base["trading"]["trading_enabled"] is False
    assert base["blockchain"]["networks"] == [
        {
            "name": "bsc",
            "enabled": True,
        },
    ]


def test_override_with_env_vars(monkeypatch):
    """Test overriding configuration with environment variables."""
    # Create a test configuration
    config = {
        "trading": {
            "min_profit_threshold": 0.5,
            "max_trade_amount": 1.0,
            "trading_enabled": True,
        },
        "blockchain": {
            "networks": [
                {
                    "name": "ethereum",
                    "enabled": True,
                },
            ],
        },
    }
    
    # Set environment variables
    monkeypatch.setenv("LISTONIAN_TRADING_MIN_PROFIT_THRESHOLD", "0.1")
    monkeypatch.setenv("LISTONIAN_TRADING_TRADING_ENABLED", "false")
    monkeypatch.setenv("LISTONIAN_BLOCKCHAIN_NETWORKS_0_ENABLED", "false")
    
    # Override configuration with environment variables
    override_with_env_vars(config)
    
    # Verify that values are overridden correctly
    assert config["trading"]["min_profit_threshold"] == 0.1
    assert config["trading"]["max_trade_amount"] == 1.0
    assert config["trading"]["trading_enabled"] is False
    assert config["blockchain"]["networks"][0]["enabled"] is False
