"""API routes for system status and health checks."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ...core.logging import get_logger, log_execution_time
from ...core.dependencies import get_system_service
from ...core.config import settings

router = APIRouter()
logger = get_logger("system_routes")

@router.get("/status")
@log_execution_time(logger)
async def get_system_status(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get current system status."""
    try:
        return await system_service.get_system_status()
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system status: {str(e)}"
        )

@router.get("/health")
@log_execution_time(logger)
async def health_check(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Perform system health check."""
    try:
        # Get component health status
        component_status = await system_service._check_component_health()
        
        # Check if any critical components are unhealthy
        critical_components = ["memory_bank", "web3"]
        critical_failures = [
            name for name in critical_components
            if component_status.get(name, {}).get("status") != "healthy"
        ]
        
        # Get network status
        network_status = await system_service._check_network_status()
        
        # Determine overall health
        is_healthy = (
            len(critical_failures) == 0 and
            network_status.get("web3_connected", False)
        )
        
        response = {
            "status": "healthy" if is_healthy else "unhealthy",
            "components": component_status,
            "network": network_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if not is_healthy:
            response["issues"] = {
                "critical_components": critical_failures,
                "network_issues": not network_status.get("web3_connected", False)
            }
        
        return response

    except Exception as e:
        logger.error(f"Error performing health check: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform health check: {str(e)}"
        )

@router.get("/components/{component_name}/health")
@log_execution_time(logger)
async def get_component_health(
    component_name: str,
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get health status for a specific component."""
    try:
        health_history = system_service.get_component_health_history(component_name)
        if not health_history:
            raise HTTPException(
                status_code=404,
                detail=f"Component {component_name} not found"
            )
        return health_history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting component health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get component health: {str(e)}"
        )

@router.get("/components/health")
@log_execution_time(logger)
async def get_all_component_health(
    system_service=Depends(get_system_service)
) -> Dict[str, Dict[str, Any]]:
    """Get health status for all components."""
    try:
        return system_service.get_all_component_health()
    except Exception as e:
        logger.error(f"Error getting all component health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get all component health: {str(e)}"
        )

@router.get("/network")
@log_execution_time(logger)
async def get_network_status(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get network status."""
    try:
        return await system_service._check_network_status()
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get network status: {str(e)}"
        )

@router.get("/resources")
@log_execution_time(logger)
async def get_resource_usage(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get system resource usage."""
    try:
        status = await system_service.get_system_status()
        return status.get("system", {})
    except Exception as e:
        logger.error(f"Error getting resource usage: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get resource usage: {str(e)}"
        )

@router.get("/uptime")
@log_execution_time(logger)
async def get_uptime(
    system_service=Depends(get_system_service)
) -> Dict[str, Any]:
    """Get system uptime information."""
    try:
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
    except Exception as e:
        logger.error(f"Error getting uptime: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get uptime: {str(e)}"
        )