"""Configuration management for the dashboard."""

from typing import Optional
from pydantic import BaseSettings, Field
import os
import json
from pathlib import Path


class DashboardSettings(BaseSettings):
    """Dashboard configuration settings."""

    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    port: int = Field(default=5001, description="Port to run the dashboard on")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Memory bank settings
    memory_bank_path: Path = Field(
        default=Path("data/memory"), description="Path to memory bank storage"
    )

    # Web3 settings
    rpc_url: str = Field(default="", description="RPC URL for Web3 connection")
    chain_id: int = Field(
        default=8453, description="Chain ID for Web3 connection"  # Base chain
    )

    # Metrics settings
    metrics_interval: int = Field(
        default=5, description="Interval in seconds for metrics updates"
    )
    max_metrics_age: int = Field(
        default=300, description="Maximum age in seconds for stored metrics"
    )

    # WebSocket settings
    ws_ping_interval: int = Field(
        default=25, description="WebSocket ping interval in seconds"
    )
    ws_ping_timeout: int = Field(
        default=60, description="WebSocket ping timeout in seconds"
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[Path] = Field(default=None, description="Path to log file")

    class Config:
        env_prefix = "DASHBOARD_"
        case_sensitive = False


def load_config() -> DashboardSettings:
    """Load dashboard configuration from environment and config files."""

    # Load from config.json if it exists
    config_data = {}
    config_path = Path("configs/config.json")
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            if "dashboard" in config:
                config_data = config["dashboard"]

    # Create settings instance
    settings = DashboardSettings(**config_data)

    # Ensure memory bank path exists
    settings.memory_bank_path.mkdir(parents=True, exist_ok=True)

    # Set up logging path if specified
    if settings.log_file:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)

    return settings


# Global settings instance
settings = load_config()
