"""API routes for metrics data."""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..core.logging import get_logger, log_execution_time
from ..core.dependencies import get_metrics_service, get_market_data_service

router = APIRouter()
logger = get_logger("metrics_routes")

# Log available routes on module load
logger.debug("Initializing metrics router")
logger.debug("Router base path: /api/metrics")
logger.debug("Available endpoints: [GET] /current, [GET] /performance, [GET] /market")

@router.get("/current", name="get_current_metrics")
@log_execution_time
async def get_current_metrics(
    metrics_service=Depends(get_metrics_service),
    market_data_service=Depends(get_market_data_service)
) -> Dict[str, Any]:
    """Get current system metrics."""
    logger.debug("Handling GET /current request")
    
    # Get metrics and market data
    metrics = await metrics_service.get_current_metrics()
    market_data = await market_data_service.get_current_market_data()
    
    # Combine the data
    metrics["market_data"] = market_data.get("market_data", {})
    
    return metrics

@router.get("/performance")
@log_execution_time
async def get_performance_metrics(
    metrics_service=Depends(get_metrics_service),
    market_data_service=Depends(get_market_data_service)
) -> Dict[str, Any]:
    """Get performance metrics."""
    metrics = await metrics_service.get_current_metrics()
    market_data = await market_data_service.get_current_market_data()
    
    return {
        **metrics.get("metrics", {}),
        "market": market_data.get("market_data", {})
    }

@router.get("/market")
@log_execution_time
async def get_market_data(market_data_service=Depends(get_market_data_service)) -> Dict[str, Any]:
    """Get current market data."""
    return await market_data_service.get_current_market_data()