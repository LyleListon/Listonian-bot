"""API routes for metrics and performance data."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ...core.logging import get_logger, log_execution_time
from ...core.dependencies import get_metrics_service, get_memory_service

router = APIRouter()
logger = get_logger("metrics_routes")

@router.get("/current")
@log_execution_time(logger)
async def get_current_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        return await metrics_service.get_current_metrics()
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current metrics: {str(e)}"
        )

@router.get("/performance")
@log_execution_time(logger)
async def get_performance_metrics(
    time_range: Optional[str] = "24h",
    metrics_service=Depends(get_metrics_service),
    memory_service=Depends(get_memory_service)
) -> Dict[str, Any]:
    """Get performance metrics for the specified time range."""
    try:
        # Parse time range
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid time range. Must be one of: 1h, 24h, 7d, 30d"
            )

        # Get trade history for the period
        trades = await memory_service.memory_bank.get_trade_history()
        period_trades = [
            trade for trade in trades
            if datetime.fromisoformat(trade["timestamp"]) >= start_time
        ]

        # Calculate performance metrics
        return await metrics_service._calculate_performance_metrics(period_trades)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )

@router.get("/gas")
@log_execution_time(logger)
async def get_gas_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get gas price metrics and trends."""
    try:
        return await metrics_service._calculate_gas_metrics()
    except Exception as e:
        logger.error(f"Error getting gas metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get gas metrics: {str(e)}"
        )

@router.get("/opportunities")
@log_execution_time(logger)
async def get_opportunity_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get opportunity metrics and analysis."""
    try:
        return await metrics_service._calculate_opportunity_metrics()
    except Exception as e:
        logger.error(f"Error getting opportunity metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get opportunity metrics: {str(e)}"
        )

@router.get("/system")
@log_execution_time(logger)
async def get_system_metrics(
    metrics_service=Depends(get_metrics_service)
) -> Dict[str, Any]:
    """Get system performance metrics."""
    try:
        return await metrics_service._calculate_system_metrics()
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system metrics: {str(e)}"
        )

@router.get("/historical/{metric_type}")
@log_execution_time(logger)
async def get_historical_metrics(
    metric_type: str,
    time_range: Optional[str] = "24h",
    interval: Optional[str] = "1h",
    metrics_service=Depends(get_metrics_service),
    memory_service=Depends(get_memory_service)
) -> Dict[str, Any]:
    """Get historical metrics data."""
    try:
        # Validate metric type
        valid_types = ["profits", "gas", "opportunities", "performance"]
        if metric_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric type. Must be one of: {', '.join(valid_types)}"
            )

        # Parse time range and interval
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
            if interval not in ["1m", "5m", "15m"]:
                interval = "5m"
        elif time_range == "24h":
            start_time = now - timedelta(hours=24)
            if interval not in ["5m", "15m", "1h"]:
                interval = "1h"
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
            if interval not in ["1h", "6h", "12h"]:
                interval = "6h"
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
            if interval not in ["6h", "12h", "24h"]:
                interval = "24h"
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid time range. Must be one of: 1h, 24h, 7d, 30d"
            )

        # Get historical data
        if metric_type == "profits":
            trades = await memory_service.memory_bank.get_trade_history()
            return await calculate_historical_profits(trades, start_time, interval)
        elif metric_type == "gas":
            return await metrics_service._calculate_gas_metrics()
        elif metric_type == "opportunities":
            opportunities = await memory_service.memory_bank.get_recent_opportunities()
            return await calculate_historical_opportunities(opportunities, start_time, interval)
        else:  # performance
            trades = await memory_service.memory_bank.get_trade_history()
            return await calculate_historical_performance(trades, start_time, interval)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting historical metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get historical metrics: {str(e)}"
        )

async def calculate_historical_profits(
    trades: list,
    start_time: datetime,
    interval: str
) -> Dict[str, Any]:
    """Calculate historical profit data."""
    try:
        # Filter trades for time period
        period_trades = [
            trade for trade in trades
            if datetime.fromisoformat(trade["timestamp"]) >= start_time
        ]

        # Calculate interval duration
        if interval.endswith('m'):
            delta = timedelta(minutes=int(interval[:-1]))
        elif interval.endswith('h'):
            delta = timedelta(hours=int(interval[:-1]))
        else:
            delta = timedelta(hours=1)

        # Group trades by interval
        intervals = []
        current = start_time
        while current <= datetime.utcnow():
            next_time = current + delta
            period_profit = sum(
                float(trade.get("net_profit", 0))
                for trade in period_trades
                if current <= datetime.fromisoformat(trade["timestamp"]) < next_time
            )
            intervals.append({
                "timestamp": current.isoformat(),
                "profit": period_profit
            })
            current = next_time

        return {
            "intervals": intervals,
            "total_profit": sum(interval["profit"] for interval in intervals),
            "interval_size": str(delta)
        }

    except Exception as e:
        logger.error(f"Error calculating historical profits: {e}")
        raise

async def calculate_historical_opportunities(
    opportunities: list,
    start_time: datetime,
    interval: str
) -> Dict[str, Any]:
    """Calculate historical opportunity data."""
    try:
        # Filter opportunities for time period
        period_opportunities = [
            opp for opp in opportunities
            if datetime.fromisoformat(opp["timestamp"]) >= start_time
        ]

        # Calculate interval duration
        if interval.endswith('m'):
            delta = timedelta(minutes=int(interval[:-1]))
        elif interval.endswith('h'):
            delta = timedelta(hours=int(interval[:-1]))
        else:
            delta = timedelta(hours=1)

        # Group opportunities by interval
        intervals = []
        current = start_time
        while current <= datetime.utcnow():
            next_time = current + delta
            period_opps = [
                opp for opp in period_opportunities
                if current <= datetime.fromisoformat(opp["timestamp"]) < next_time
            ]
            intervals.append({
                "timestamp": current.isoformat(),
                "count": len(period_opps),
                "average_profit": (
                    sum(float(opp.get("profit", 0)) for opp in period_opps) /
                    len(period_opps) if period_opps else 0
                )
            })
            current = next_time

        return {
            "intervals": intervals,
            "total_opportunities": sum(interval["count"] for interval in intervals),
            "interval_size": str(delta)
        }

    except Exception as e:
        logger.error(f"Error calculating historical opportunities: {e}")
        raise

async def calculate_historical_performance(
    trades: list,
    start_time: datetime,
    interval: str
) -> Dict[str, Any]:
    """Calculate historical performance data."""
    try:
        # Filter trades for time period
        period_trades = [
            trade for trade in trades
            if datetime.fromisoformat(trade["timestamp"]) >= start_time
        ]

        # Calculate interval duration
        if interval.endswith('m'):
            delta = timedelta(minutes=int(interval[:-1]))
        elif interval.endswith('h'):
            delta = timedelta(hours=int(interval[:-1]))
        else:
            delta = timedelta(hours=1)

        # Group trades by interval
        intervals = []
        current = start_time
        while current <= datetime.utcnow():
            next_time = current + delta
            period_trades_slice = [
                trade for trade in period_trades
                if current <= datetime.fromisoformat(trade["timestamp"]) < next_time
            ]
            
            success_count = len([t for t in period_trades_slice if t.get("success", False)])
            total_count = len(period_trades_slice)
            
            intervals.append({
                "timestamp": current.isoformat(),
                "success_rate": success_count / total_count if total_count > 0 else 0,
                "trade_count": total_count,
                "profit": sum(float(t.get("net_profit", 0)) for t in period_trades_slice)
            })
            current = next_time

        return {
            "intervals": intervals,
            "average_success_rate": (
                sum(i["success_rate"] for i in intervals) /
                len(intervals) if intervals else 0
            ),
            "interval_size": str(delta)
        }

    except Exception as e:
        logger.error(f"Error calculating historical performance: {e}")
        raise