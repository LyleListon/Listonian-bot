"""API routes for metrics data."""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..core.logging import get_logger, log_execution_time
from ..core.dependencies import (
    get_metrics_service,
    get_market_data_service,
)  # Keep market_data_service import for other routes

router = APIRouter()
logger = get_logger("metrics_routes")

# Log available routes on module load
logger.debug("Initializing metrics router")
logger.debug("Router base path: /api/metrics")
logger.debug("Available endpoints: [GET] /current, [GET] /performance, [GET] /market")


@router.get("/current", name="get_current_metrics")
@log_execution_time
async def get_current_metrics(
    metrics_service=Depends(
        get_metrics_service
    ),  # Remove unused market_data_service dependency
) -> Dict[str, Any]:
    """Get current system metrics."""
    logger.debug("Handling GET /current request")

    # Get combined metrics directly from the service
    current_metrics = await metrics_service.get_current_metrics()
    logger.debug(f"Returning current metrics: {current_metrics}")
    return current_metrics


@router.get("/performance")
@log_execution_time
async def get_performance_metrics(
    metrics_service=Depends(get_metrics_service),
    market_data_service=Depends(get_market_data_service),  # Keep dependency here
) -> Dict[str, Any]:
    """Get performance metrics."""
    metrics = await metrics_service.get_current_metrics()
    market_data = (
        await market_data_service.get_current_market_data()
    )  # Keep for now, might be redundant

    # Format performance metrics - Adjusted for new MetricsService structure
    total_trades = metrics.get("metrics", {}).get("total_trades", 0)
    total_profit = metrics.get("metrics", {}).get("total_profit_eth", 0.0)
    avg_profit = (total_profit / total_trades) if total_trades > 0 else 0.0

    performance = {
        "performance": {
            "total_profit": total_profit,
            "previous_profit": 0.0,  # Placeholder - Needs historical data logic
            "success_rate": metrics.get("metrics", {}).get("success_rate", 0.0),
            "previous_success_rate": 0.0,  # Placeholder - Needs historical data logic
            "average_profit": avg_profit,
            "previous_average_profit": 0.0,  # Placeholder - Needs historical data logic
            "gas_efficiency": 0.0,  # Placeholder - Needs historical data logic
            "previous_gas_efficiency": metrics.get("metrics", {}).get(
                "profit_per_gas", 0.0
            ),  # Use calculated profit_per_gas
            "profit_distribution": metrics.get("metrics", {}).get(
                "profit_distribution_by_strategy", {}
            ),  # Use calculated profit_distribution_by_strategy
            "success_trend": [],  # Placeholder - Needs trend calculation logic
            "transactions": metrics.get(
                "trade_history", []
            ),  # Use trade history from metrics
        },
        "opportunities": {
            # Check if this path is correct in the final metrics structure
            "volume_trend": metrics.get("market_data", {})
            .get("analysis", {})
            .get("opportunity_timing", {})
            .get("hourly_distribution", {})
        },
        # Market data might be redundant if already included in metrics['market_data']
        "market": metrics.get("market_data", market_data.get("market_data", {})),
        "timestamp": metrics.get("timestamp", ""),
    }

    return performance


@router.get("/market")
@log_execution_time
async def get_market_data(
    market_data_service=Depends(get_market_data_service),
) -> Dict[str, Any]:
    """Get current market data."""
    # This remains unchanged for now, but might be redundant if market data is fully integrated into MetricsService state
    return await market_data_service.get_current_market_data()
