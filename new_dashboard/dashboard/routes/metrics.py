"""API routes for metrics data."""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..core.logging import get_logger, log_execution_time
from ..core.dependencies import get_metrics_service

router = APIRouter()
logger = get_logger("metrics_routes")

@router.get("/current")
@log_execution_time(logger)
async def get_current_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get current system metrics."""
    return await metrics_service.get_current_metrics()

@router.get("/performance")
@log_execution_time(logger)
async def get_performance_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get performance metrics."""
    metrics = await metrics_service.get_current_metrics()
    return metrics.get("performance", {})