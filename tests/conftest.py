"""Test configuration and fixtures."""

import os
import pytest
from pathlib import Path

from arbitrage_bot.common.config.config_loader import load_config
from arbitrage_bot.common.events.event_bus import EventBus


@pytest.fixture(scope="session")
def test_environment():
    """Set up the test environment."""
    # Store original environment variables
    original_env = dict(os.environ)
    
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="session")
def test_config(test_environment):
    """Load test configuration."""
    return load_config("test")


@pytest.fixture
def event_bus():
    """Create a new event bus for each test."""
    return EventBus()


@pytest.fixture
def mock_market_data():
    """Provide mock market data for tests."""
    return {
        "pairs": [
            {
                "dex": "uniswap_v3",
                "base_token": "ETH",
                "quote_token": "USDC",
                "price": 3500.0,
                "liquidity": 1000000.0
            },
            {
                "dex": "sushiswap",
                "base_token": "ETH",
                "quote_token": "USDC",
                "price": 3520.0,
                "liquidity": 800000.0
            }
        ]
    }
