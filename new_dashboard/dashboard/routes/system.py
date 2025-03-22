"""API routes for system status and health checks."""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from datetime import datetime, timedelta

from ..core.logging import get_logger, log_execution_time
from ..core.dependencies import get_system_service

router = APIRouter()
logger = get_logger("system_routes")

@router.get("/status")
@log_execution_time(logger)
async def get_system_status(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get current system status."""
    return await system_service.get_system_status()

@router.get("/health")
@log_execution_time(logger)
async def health_check(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get system health status."""
    status = await system_service.get_system_status()
    
    # Check component health
    components = status.get("components", {})
    critical_components = ["memory_bank", "metrics"]
    critical_failures = [
        name for name in critical_components
        if components.get(name, {}).get("status") != "healthy"
    ]
    
    # Check network status
    network = status.get("network", {})
    is_connected = network.get("connected", False)
    
    return {
        "status": "healthy" if not critical_failures and is_connected else "unhealthy",
        "components": components,
        "network": network,
        "issues": {
            "critical_components": critical_failures,
            "network": not is_connected
        } if critical_failures or not is_connected else None,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/resources")
@log_execution_time(logger)
async def get_resource_usage(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get system resource usage."""
    status = await system_service.get_system_status()
    return status.get("system", {})

@router.get("/uptime")
@log_execution_time(logger)
async def get_uptime(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get system uptime information."""
    status = await system_service.get_system_status()
    uptime_seconds = status.get("system", {}).get("uptime", 0)
    
    # Calculate human-readable uptime
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return {
        "uptime_seconds": uptime_seconds,
        "uptime_human": f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s",
        "started_at": (
            datetime.utcnow() - timedelta(seconds=uptime_seconds)
        ).isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }