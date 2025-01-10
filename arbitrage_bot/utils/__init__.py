"""Utility functions for arbitrage bot."""

from .web3_utils import (
    get_web3,
    get_contract,
    estimate_gas,
    validate_address,
    get_token_balance,
    get_eth_balance,
)
from .config_loader import load_config
from .database import Database
from .rate_limiter import RateLimiter, create_rate_limiter
from .market_analyzer import MarketAnalyzer
from .mcp_helper import (
    get_mcp_client,
    call_mcp_tool,
    access_mcp_resource,
    close_mcp_clients,
    MockClient,
)

__all__ = [
    "get_web3",
    "get_contract",
    "estimate_gas",
    "validate_address",
    "get_token_balance",
    "get_eth_balance",
    "load_config",
    "Database",
    "RateLimiter",
    "create_rate_limiter",
    "MarketAnalyzer",
    "get_mcp_client",
    "call_mcp_tool",
    "access_mcp_resource",
    "close_mcp_clients",
    "MockClient",
]
