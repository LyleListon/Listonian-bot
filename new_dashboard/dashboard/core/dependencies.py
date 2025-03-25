"""FastAPI dependency injection utilities."""

from typing import Optional
from fastapi import Depends

from ..services.service_manager import service_manager
from ..core.logging import get_logger

logger = get_logger("dependencies")

async def get_memory_service():
    """Get the memory service instance."""
    if not service_manager._initialized:
        await service_manager.initialize()
    return service_manager.memory_service

async def get_metrics_service():
    """Get the metrics service instance."""
    if not service_manager._initialized:
        await service_manager.initialize()
    return service_manager.metrics_service

async def get_system_service():
    """Get the system service instance."""
    if not service_manager._initialized:
        await service_manager.initialize()
    return service_manager.system_service

async def get_market_data_service():
    """Get the market data service instance."""
    if not service_manager._initialized:
        await service_manager.initialize()
    return service_manager.market_data_service