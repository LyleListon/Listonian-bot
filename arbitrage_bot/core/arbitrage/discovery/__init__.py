"""
Opportunity Discovery Components

This package provides components for discovering and validating arbitrage opportunities.
"""

from .default_manager import DefaultDiscoveryManager
from .sources.manager import DEXDiscoveryManager, create_dex_discovery_manager
from .sources.base import DEXInfo, DEXProtocolType, DEXSource
from .sources.repository import DEXRepository, create_dex_repository
from .sources.validator import DEXValidator, create_dex_validator
from .sources.defillama import DefiLlamaSource, create_defillama_source
from .sources.dexscreener import DexScreenerSource, create_dexscreener_source
from .sources.defipulse import DefiPulseSource, create_defipulse_source

__all__ = [
    "DefaultDiscoveryManager",
    "DEXDiscoveryManager",
    "create_dex_discovery_manager",
    "DEXInfo",
    "DEXProtocolType",
    "DEXSource",
    "DEXRepository",
    "create_dex_repository",
    "DEXValidator",
    "create_dex_validator",
    "DefiLlamaSource",
    "create_defillama_source",
    "DexScreenerSource",
    "create_dexscreener_source",
    "DefiPulseSource",
    "create_defipulse_source"
]