"""Dashboard routes module."""

import logging
import asyncio
import json
import time
from datetime import datetime, timedelta
from quart import jsonify, render_template, websocket, Response, request, current_app
from typing import Optional, Dict, List
from .database import DashboardDB

logger = logging.getLogger(__name__)


def register_routes(app, db_path: str = "arbitrage_bot.db"):
    """Register dashboard routes with database connection."""
    db = DashboardDB(db_path)

    # Serve static files
    @app.route('/static/<path:filename>')
    async def serve_static(filename):
        """Serve static files."""
        logger.info(f"Serving static file: {filename}")
        return await app.send_static_file(filename)

    @app.route("/")
    async def index():
        """Render dashboard index page."""
        return await render_template("index.html")

    @app.route("/metrics")
    async def metrics_page():
        """Render metrics dashboard page."""
        return await render_template("metrics.html")

    @app.route("/opportunities")
    async def opportunities():
        """Render opportunities page."""
        return await render_template("opportunities.html")

    @app.route("/history")
    async def history():
        """Render trade history page."""
        return await render_template("history.html")

    @app.route("/settings")
    async def settings():
        """Render settings page."""
        return await render_template("settings.html")

    @app.route("/analytics")
    async def analytics():
        """Render analytics page."""
        return await render_template("analytics.html")

    @app.route("/api/metrics")
    async def get_metrics():
        """Get current performance metrics."""
        try:
            metrics = current_app.config["metrics_manager"].get_performance_metrics(window=timedelta(hours=1))
            return jsonify({
                "success": True,
                "success_rate": metrics.success_rate,
                "total_profit_usd": float(metrics.total_profit_usd),
                "total_gas_cost_eth": float(metrics.total_gas_cost_eth),
                "avg_execution_time": metrics.avg_execution_time,
                "total_trades": metrics.total_trades,
                "failed_trades": metrics.failed_trades,
                "trades_24h": metrics.trades_24h,
                "profit_24h": float(metrics.profit_24h),
                        "active_opportunities": len(await current_app.config["metrics_manager"].get_current_opportunities()),
                "rejected_opportunities": metrics.rejected_opportunities
            })
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/metrics/hourly")
    async def get_hourly_metrics():
        """Get hourly performance metrics."""
        try:
            metrics = current_app.config["metrics_manager"].get_hourly_metrics()
            return jsonify({
                "success": True,
                "metrics": {
                    timestamp: {
                        "success_rate": m.success_rate,
                        "total_profit_usd": float(m.total_profit_usd),
                        "total_gas_cost_eth": float(m.total_gas_cost_eth),
                        "avg_execution_time": m.avg_execution_time,
                        "total_trades": m.total_trades
                    }
                    for timestamp, m in metrics.items()
                }
            })
        except Exception as e:
            logger.error(f"Error getting hourly metrics: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/metrics/dex")
    async def get_dex_metrics():
        """Get DEX-specific performance metrics."""
        try:
            metrics = current_app.config["metrics_manager"].get_dex_performance()
            return jsonify({
                "success": True,
                "metrics": metrics
            })
        except Exception as e:
            logger.error(f"Error getting DEX metrics: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/metrics/failures")
    async def get_failure_analysis():
        """Get failure analysis metrics."""
        try:
            analysis = current_app.config["metrics_manager"].analyze_failures()
            return jsonify({
                "success": True,
                "analysis": analysis
            })
        except Exception as e:
            logger.error(f"Error getting failure analysis: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.websocket("/api/ws/metrics")
    async def ws_metrics():
        """WebSocket endpoint for real-time metrics updates."""
        try:
            logger.info("WebSocket connection established")
            
            # Verify metrics manager is available
            metrics_manager = current_app.config.get("metrics_manager")
            if not metrics_manager:
                logger.error("Metrics manager not found in app config")
                await websocket.send_json({
                    "error": "Metrics manager not initialized"
                })
                return
            
            while True:
                try:
                    # Get metrics with error handling
                    try:
                        metrics = metrics_manager.get_performance_metrics(window=timedelta(hours=1))
                        dex_performance = metrics_manager.get_dex_performance()
                    except Exception as e:
                        logger.error(f"Error getting metrics: {e}")
                        metrics = metrics_manager.get_performance_metrics()  # Get default metrics
                        dex_performance = {}
                    
                    alerts = []
                    if metrics.success_rate < 0.95:  # 95% threshold
                        alerts.append({
                            "severity": "danger",
                            "message": f"Success rate ({metrics.success_rate:.1%}) below threshold"
                        })
                    
                    if metrics.avg_execution_time > 5.0:  # 5 second threshold
                        alerts.append({
                            "severity": "warning",
                            "message": f"High execution time: {metrics.avg_execution_time:.2f}s"
                        })
                    
                    await websocket.send_json({
                        "timestamp": datetime.now().isoformat(),
                        "success_rate": metrics.success_rate,
                        "total_profit_usd": float(metrics.total_profit_usd),
                        "total_gas_cost_eth": float(metrics.total_gas_cost_eth),
                        "avg_execution_time": metrics.avg_execution_time,
                        "total_trades": metrics.total_trades,
                        "trades_24h": metrics.trades_24h,
                        "failed_trades": metrics.failed_trades,
                        "profit_24h": float(metrics.profit_24h),
                        "active_opportunities": len(await metrics_manager.get_current_opportunities()),
                        "rejected_opportunities": metrics.rejected_opportunities,
                        "dex_performance": dex_performance,
                        "alerts": alerts
                    })
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error sending metrics update: {e}")
                    # Continue running even if one update fails
                    await asyncio.sleep(1)
                    continue
                    
        except Exception as e:
            logger.error(f"Fatal WebSocket error: {e}")
            await websocket.close(1011)

    @app.route("/api/trades")
    async def get_trades():
        """Get recent trades."""
        try:
            trades = db.get_recent_trades(limit=5)
            return jsonify({
                "success": True,
                "trades": trades
            })
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/opportunities")
    async def get_opportunities():
        """Get current arbitrage opportunities."""
        try:
            metrics_manager = current_app.config["metrics_manager"]
            opportunities = await metrics_manager.get_current_opportunities()
            return jsonify({
                "success": True,
                "opportunities": opportunities
            })
        except Exception as e:
            logger.error(f"Error getting opportunities: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.websocket("/api/ws/trades")
    async def ws_trades():
        """WebSocket endpoint for real-time trade updates."""
        try:
            logger.info("Trade WebSocket connection established")
            
            while True:
                try:
                    trades = db.get_recent_trades(limit=5)
                    await websocket.send_json({
                        "type": "trades",
                        "data": {
                            "timestamp": int(datetime.utcnow().timestamp()),
                            "trades": trades
                        }
                    })
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error sending trade update: {e}")
                    # Continue running even if one update fails
                    await asyncio.sleep(5)
                    continue
        except Exception as e:
            logger.error(f"Fatal trade WebSocket error: {e}")
            await websocket.close(1011)

    @app.route("/api/status")
    async def get_status():
        """Get bot status."""
        try:
            metrics = current_app.config["metrics_manager"].get_performance_metrics()
            return jsonify({
                "success": True,
                "status": "running",
                "uptime": time.time() - metrics.start_time,
                "trades": metrics.total_trades,
                "profit": float(metrics.total_profit_usd)
            })
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/analytics/performance")
    async def get_analytics_performance():
        """Get performance analytics."""
        try:
            metrics = current_app.config["metrics_manager"].get_performance_metrics()
            hourly_metrics = current_app.config["metrics_manager"].get_hourly_metrics()
            
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
                "success": True,
                "metrics": {
                    "total_trades": metrics.total_trades,
                    "success_rate": metrics.success_rate,
                    "total_profit": float(metrics.total_profit_usd),
                    "avg_execution_time": metrics.avg_execution_time
                },
                "profit_history": sorted(profit_history, key=lambda x: x[0]),
                "volume_history": sorted(volume_history, key=lambda x: x[0])
            })
        except Exception as e:
            logger.error(f"Error getting analytics performance: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/analytics/charts")
    async def get_analytics_charts():
        """Get chart data for analytics."""
        try:
            dex_performance = current_app.config["metrics_manager"].get_dex_performance()
            
            # Convert DEX metrics to chart format
            dex_data = {
                dex: {
                    "success_rate": metrics["success_rate"],
                    "profit": float(metrics["total_profit_usd"]),
                    "volume": metrics["total_trades"]
                }
                for dex, metrics in dex_performance.items()
            }
            
            return jsonify({
                "success": True,
                "dex_performance": dex_data
            })
        except Exception as e:
            logger.error(f"Error getting analytics charts: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/api/analytics/analysis")
    async def get_analytics_analysis():
        """Get detailed analytics analysis."""
        try:
            failures = current_app.config["metrics_manager"].analyze_failures()
            metrics = current_app.config["metrics_manager"].get_performance_metrics()
            
            return jsonify({
                "success": True,
                "failure_analysis": failures,
                "performance_stats": {
                    "profit_per_trade": float(metrics.profit_per_trade),
                    "gas_per_trade": float(metrics.gas_per_trade),
                    "avg_execution_time": metrics.avg_execution_time,
                    "uptime": metrics.uptime
                }
            })
        except Exception as e:
            logger.error(f"Error getting analytics analysis: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return app
