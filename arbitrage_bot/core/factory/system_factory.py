"""Factory functions for creating arbitrage system instances."""

import json
import logging
from typing import Dict, Any, Optional

from ..systems.base_system import BaseArbitrageSystem
from ..interfaces.arbitrage import OpportunityDiscoveryManager, ExecutionManager
from ..interfaces.monitoring import ArbitrageAnalytics, MarketDataProvider

logger = logging.getLogger(__name__)


async def create_arbitrage_system(
    config: Dict[str, Any],
    discovery_manager: Optional[OpportunityDiscoveryManager] = None,
    execution_manager: Optional[ExecutionManager] = None,
    analytics_manager: Optional[ArbitrageAnalytics] = None,
    market_data_provider: Optional[MarketDataProvider] = None,
    use_legacy: bool = False,
) -> BaseArbitrageSystem:
    """
    Create an arbitrage system instance.

    Args:
        config: System configuration
        discovery_manager: Optional discovery manager instance
        execution_manager: Optional execution manager instance
        analytics_manager: Optional analytics manager instance
        market_data_provider: Optional market data provider instance
        use_legacy: Whether to use legacy component implementations

    Returns:
        Configured arbitrage system instance
    """
    try:
        # Create managers if not provided
        if discovery_manager is None:
            if use_legacy:
                from ..legacy.discovery import create_legacy_discovery_manager

                discovery_manager = await create_legacy_discovery_manager(config)
            else:
                from ..discovery import create_discovery_manager

                discovery_manager = await create_discovery_manager(config)

        if execution_manager is None:
            if use_legacy:
                from ..legacy.execution import create_legacy_execution_manager

                execution_manager = await create_legacy_execution_manager(config)
            else:
                from ..execution import create_execution_manager

                execution_manager = await create_execution_manager(config)

        if analytics_manager is None:
            if use_legacy:
                from ..legacy.analytics import create_legacy_analytics_manager

                analytics_manager = await create_legacy_analytics_manager(config)
            else:
                from ..analytics import create_analytics_manager

                analytics_manager = await create_analytics_manager(config)

        if market_data_provider is None:
            if use_legacy:
                from ..legacy.market_data import create_legacy_market_data_provider

                market_data_provider = await create_legacy_market_data_provider(config)
            else:
                from ..market_data import create_market_data_provider

                market_data_provider = await create_market_data_provider(config)

        # Create system instance
        system = BaseArbitrageSystem(
            discovery_manager=discovery_manager,
            execution_manager=execution_manager,
            analytics_manager=analytics_manager,
            market_data_provider=market_data_provider,
            config=config,
        )

        logger.info("Created arbitrage system instance")
        return system

    except Exception as e:
        logger.error("Failed to create arbitrage system: %s", str(e))
        raise


async def create_arbitrage_system_from_config(
    config_path: str, use_legacy: bool = False
) -> BaseArbitrageSystem:
    """
    Create an arbitrage system from a config file.

    Args:
        config_path: Path to config file
        use_legacy: Whether to use legacy component implementations

    Returns:
        Configured arbitrage system instance
    """
    try:
        # Load config
        with open(config_path, "r") as f:
            config = json.load(f)

        # Create system
        return await create_arbitrage_system(config=config, use_legacy=use_legacy)

    except Exception as e:
        logger.error("Failed to create arbitrage system from config: %s", str(e))
        raise
