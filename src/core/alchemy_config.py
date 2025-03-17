"""
Configuration settings for Alchemy SDK integration.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class WebSocketConfig:
    """WebSocket-specific configuration."""
    reconnect_attempts: int = 5
    reconnect_interval: float = 1.0
    timeout: float = 30.0
    heartbeat_interval: float = 30.0
    ping_timeout: float = 5.0

@dataclass
class NetworkConfig:
    """Network-specific configuration."""
    name: str = "base-mainnet"
    chain_id: int = 8453  # Base mainnet chain ID
    rpc_url: Optional[str] = None
    ws_url: Optional[str] = None

def default_websocket_config() -> WebSocketConfig:
    """Default WebSocket configuration factory."""
    return WebSocketConfig()

def default_network_config() -> NetworkConfig:
    """Default network configuration factory."""
    return NetworkConfig()

def default_gas_manager_config() -> Dict[str, Any]:
    """Default gas manager configuration factory."""
    return {
        'max_fee_per_gas_multiplier': 1.5,
        'max_priority_fee_per_gas_multiplier': 1.1,
        'gas_price_multiplier': 1.1,
        'gas_buffer_blocks': 5,
        'min_priority_fee': 100000000  # 0.1 Gwei
    }

@dataclass
class AlchemySettings:
    """
    Alchemy SDK configuration settings.
    
    Attributes:
        api_key: Alchemy API key
        network: Network configuration
        max_retries: Maximum number of retry attempts for RPC calls
        retry_delay: Delay between retry attempts in seconds
        timeout: Default timeout for RPC calls in seconds
        websocket: WebSocket configuration
        gas_manager: Gas price management settings
        ws_reconnect_attempts: Number of WebSocket reconnection attempts
        ws_reconnect_interval: Interval between reconnection attempts
    """
    api_key: str
    network: NetworkConfig = field(default_factory=default_network_config)
    max_retries: int = 5
    retry_delay: float = 1.0
    timeout: float = 30.0
    websocket: WebSocketConfig = field(default_factory=default_websocket_config)
    gas_manager: Dict[str, Any] = field(default_factory=default_gas_manager_config)
    ws_reconnect_attempts: int = field(default=5)
    ws_reconnect_interval: float = field(default=1.0)

    @property
    def rpc_url(self) -> str:
        """Get the RPC URL for the configured network."""
        if self.network.rpc_url:
            return self.network.rpc_url
        return f"https://base-mainnet.g.alchemy.com/v2/{self.api_key}"

    @property
    def ws_url(self) -> str:
        """Get the WebSocket URL for the configured network."""
        if self.network.ws_url:
            return self.network.ws_url
        return f"wss://base-mainnet.g.alchemy.com/v2/{self.api_key}"

# Default configuration for Base mainnet
DEFAULT_CONFIG = AlchemySettings(
    api_key="kRXhWVt8YU_8LnGS20145F5uBDFbL_k0",
    network=NetworkConfig(
        name="base-mainnet",
        chain_id=8453
    )
)