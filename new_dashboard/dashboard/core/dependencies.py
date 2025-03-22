"""FastAPI dependency functions."""

from ..services.service_manager import service_manager

async def get_metrics_service():
    """Get the metrics service."""
    return service_manager.metrics_service

async def get_memory_service():
    """Get the memory service."""
    return service_manager.memory_service

async def get_system_service():
    """Get the system service."""
    return service_manager.system_service