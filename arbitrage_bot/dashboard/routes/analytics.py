"""Analytics routes for the dashboard."""

import logging
from datetime import datetime
from flask import Blueprint, render_template, jsonify
from ...core.analytics.analytics_system import AnalyticsSystem

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)

def get_metrics_manager():
    """Get metrics manager from app context."""
    from flask import current_app
    logger.info("Attempting to get metrics_manager from app config")
    metrics_manager = current_app.config.get("metrics_manager")
    if metrics_manager is None:
        logger.error("metrics_manager not found in app config")
        raise ValueError("metrics_manager not initialized")
    logger.info("Successfully retrieved metrics_manager")
    return metrics_manager

@analytics_bp.route('/api/analytics/performance')
def get_performance_metrics():
    """Get performance metrics."""
    logger.info("Handling /api/analytics/performance request")
    try:
        metrics_manager = get_metrics_manager()
        metrics = metrics_manager.get_performance_metrics()
        hourly_metrics = metrics_manager.get_hourly_metrics()
        
        # Convert hourly metrics to time series data
        profit_history = [
            [int(datetime.strptime(ts, "%Y-%m-%d %H:00").timestamp() * 1000), 
             float(m.total_profit_usd)]
            for ts, m in hourly_metrics.items()
        ]
        
        volume_history = [
            [int(datetime.strptime(ts, "%Y-%m-%d %H:00").timestamp() * 1000),
             m.total_trades]
            for ts, m in hourly_metrics.items()
        ]
        
        return jsonify({
            'success': True,
            'metrics': {
                'total_trades': metrics.total_trades,
                'success_rate': metrics.success_rate,
                'total_profit': float(metrics.total_profit_usd),
                'avg_execution_time': metrics.avg_execution_time
            },
            'profit_history': sorted(profit_history, key=lambda x: x[0]),
            'volume_history': sorted(volume_history, key=lambda x: x[0])
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@analytics_bp.route('/api/analytics/market')
def get_market_metrics():
    """Get market metrics."""
    try:
        metrics_manager = get_metrics_manager()
        dex_performance = metrics_manager.get_dex_performance()
        return jsonify({
            'success': True,
            'data': dex_performance
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@analytics_bp.route('/api/analytics/gas')
def get_gas_metrics():
    """Get gas usage metrics."""
    try:
        metrics_manager = get_metrics_manager()
        metrics = metrics_manager.get_performance_metrics()
        return jsonify({
            'success': True,
            'data': {
                'total_gas_cost': float(metrics.total_gas_cost_eth),
                'gas_per_trade': float(metrics.gas_per_trade)
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
