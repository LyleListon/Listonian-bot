"""API routes for metrics data."""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..core.logging import get_logger, log_execution_time
from ..core.dependencies import get_metrics_service

router = APIRouter()
logger = get_logger("metrics_routes")

# Log available routes on module load
logger.debug("Initializing metrics router")
logger.debug("Router base path: /api/metrics")
logger.debug("Available endpoints: [GET] /current, [GET] /performance")

@router.get("/current", name="get_current_metrics")
@log_execution_time
async def get_current_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get current system metrics."""
    logger.debug("Handling GET /current request")
    logger.debug("Using metrics service: %s", metrics_service)
    return await metrics_service.get_current_metrics()

@router.get("/performance")
@log_execution_time
async def get_performance_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get performance metrics."""
    metrics = await metrics_service.get_current_metrics()
    return metrics.get("metrics", {})