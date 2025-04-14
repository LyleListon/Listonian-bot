"""Factory for creating arbitrage engines."""

import logging
from typing import Dict, Any, Optional

from arbitrage_bot.common.events.event_bus import EventBus
from arbitrage_bot.core.arbitrage.base_engine import BaseArbitrageEngine
from arbitrage_bot.core.arbitrage.simple_engine import SimpleArbitrageEngine

logger = logging.getLogger(__name__)


def create_arbitrage_engine(
    config: Dict[str, Any], event_bus: EventBus
) -> BaseArbitrageEngine:
    """Create an arbitrage engine.

    Args:
        config: Configuration dictionary.
        event_bus: Event bus for publishing events.

    Returns:
        Arbitrage engine.
    """
    # Get arbitrage engine configuration
    arbitrage_config = config.get("arbitrage", {})
    engine_type = arbitrage_config.get("engine_type", "simple")

    # Create engine based on type
    if engine_type == "simple":
        logger.info("Creating simple arbitrage engine")
        return SimpleArbitrageEngine(event_bus, config)
    else:
        logger.warning(f"Unknown arbitrage engine type: {engine_type}, using simple engine")
        return SimpleArbitrageEngine(event_bus, config)
