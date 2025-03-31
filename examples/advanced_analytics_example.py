"""
Advanced Analytics Example

This example demonstrates how to use the advanced analytics components
to track profits, analyze performance, and generate reports.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from decimal import Decimal

from arbitrage_bot.core.analytics import (
    create_analytics_system,
    create_profit_tracker,
    create_trading_journal,
    create_alert_system
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Run the advanced analytics example."""
    logger.info("Starting Advanced Analytics Example")
    
    # Initialize components
    profit_tracker = await create_profit_tracker()
    trading_journal = await create_trading_journal()
    alert_system = await create_alert_system({
        'alert_channels': ['log'],  # Only log alerts for this example
        'alert_thresholds': {
            'profit': {
                'warning': {'operator': '<', 'value': 0.01},
                'error': {'operator': '<', 'value': 0}
            },
            'gas_cost': {
                'warning': {'operator': '>', 'value': 0.05}
            }
        }
    })
    
    # Track some sample trades
    await track_sample_trades(profit_tracker, trading_journal, alert_system)
    
    # Analyze profits
    await analyze_profits(profit_tracker)
    
    # Analyze trade outcomes
    await analyze_trades(trading_journal)
    
    # Check for alerts
    await check_alerts(alert_system)
    
    logger.info("Advanced Analytics Example completed")

async def track_sample_trades(profit_tracker, trading_journal, alert_system):
    """Track some sample trades for demonstration."""
    logger.info("Tracking sample trades")
    
    # Sample token addresses (checksummed)
    token_a = "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"  # UNI
    token_b = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
    token_c = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
    
    # Sample trade 1 - profitable
    trade1 = {
        'token_in': token_a,
        'token_out': token_b,
        'amount_in': 10.0,
        'amount_out': 0.05,
        'profit': 0.02,
        'gas_cost': 0.005,
        'timestamp': datetime.utcnow() - timedelta(hours=2),
        'dexes': ['uniswap', 'sushiswap'],
        'path': [token_a, token_b],
        'category': 'profitable',
        'tags': ['high_profit', 'gas_efficient'],
        'notes': 'Good arbitrage opportunity between Uniswap and Sushiswap'
    }
    
    # Sample trade 2 - break even
    trade2 = {
        'token_in': token_b,
        'token_out': token_c,
        'amount_in': 0.1,
        'amount_out': 200.0,
        'profit': 0.005,
        'gas_cost': 0.005,
        'timestamp': datetime.utcnow() - timedelta(hours=1),
        'dexes': ['uniswap'],
        'path': [token_b, token_c],
        'category': 'break_even',
        'tags': ['low_profit'],
        'notes': 'Break even trade due to gas costs'
    }
    
    # Sample trade 3 - unprofitable
    trade3 = {
        'token_in': token_c,
        'token_out': token_a,
        'amount_in': 100.0,
        'amount_out': 4.8,
        'profit': -0.01,
        'gas_cost': 0.006,
        'timestamp': datetime.utcnow() - timedelta(minutes=30),
        'dexes': ['sushiswap'],
        'path': [token_c, token_a],
        'category': 'unprofitable',
        'tags': ['loss', 'gas_heavy'],
        'notes': 'Price moved against us during execution'
    }
    
    # Track trades with profit tracker
    await profit_tracker.track_profit(trade1)
    await profit_tracker.track_profit(trade2)
    await profit_tracker.track_profit(trade3)
    
    # Log trades in trading journal
    await trading_journal.log_trade(trade1)
    await trading_journal.log_trade(trade2)
    await trading_journal.log_trade(trade3)
    
    # Check for alerts based on trade metrics
    await alert_system.check_threshold_alerts({
        'profit': trade1['profit'],
        'gas_cost': trade1['gas_cost']
    })
    
    await alert_system.check_threshold_alerts({
        'profit': trade2['profit'],
        'gas_cost': trade2['gas_cost']
    })
    
    await alert_system.check_threshold_alerts({
        'profit': trade3['profit'],
        'gas_cost': trade3['gas_cost']
    })
    
    logger.info(f"Tracked {3} sample trades")

async def analyze_profits(profit_tracker):
    """Analyze profits using the profit tracker."""
    logger.info("Analyzing profits")
    
    # Get profit summary
    profit_summary = await profit_tracker.get_profit_summary()
    logger.info(f"Profit Summary: {json.dumps(profit_summary['summary'], indent=2)}")
    
    # Get profit by token pair
    token_pair_profits = await profit_tracker.get_profit_by_token_pair(timeframe="24h")
    logger.info(f"Token Pair Profits (24h): {json.dumps(token_pair_profits, indent=2)}")
    
    # Get ROI
    roi = await profit_tracker.get_roi(timeframe="24h")
    logger.info(f"ROI (24h): {json.dumps(roi, indent=2)}")
    
    # Get top token pairs
    top_pairs = await profit_tracker.get_top_token_pairs(timeframe="24h", limit=3)
    logger.info(f"Top Token Pairs (24h): {json.dumps(top_pairs, indent=2)}")
    
    # Get profit time series
    time_series = await profit_tracker.get_profit_time_series(timeframe="24h", interval="1h")
    logger.info(f"Profit Time Series (24h, 1h intervals): {len(time_series['timestamps'])} data points")

async def analyze_trades(trading_journal):
    """Analyze trades using the trading journal."""
    logger.info("Analyzing trades")
    
    # Get all trades
    trades = await trading_journal.get_trades(timeframe="24h")
    logger.info(f"Retrieved {len(trades)} trades from the last 24 hours")
    
    # Analyze trade outcomes
    outcomes = await trading_journal.analyze_trade_outcomes(timeframe="24h")
    logger.info(f"Trade Outcomes (24h): {json.dumps(outcomes, indent=2)}")
    
    # Extract learning insights
    insights = await trading_journal.extract_learning_insights(timeframe="24h")
    logger.info(f"Learning Insights (24h): {json.dumps(insights, indent=2)}")
    
    # Get trade categories and tags
    categories = await trading_journal.get_trade_categories()
    tags = await trading_journal.get_trade_tags()
    logger.info(f"Trade Categories: {categories}")
    logger.info(f"Trade Tags: {tags}")

async def check_alerts(alert_system):
    """Check and retrieve alerts."""
    logger.info("Checking alerts")
    
    # Get all alerts
    alerts = await alert_system.get_alerts()
    logger.info(f"Retrieved {len(alerts)} alerts")
    
    # Get alert summary
    summary = await alert_system.get_alert_summary()
    logger.info(f"Alert Summary: {json.dumps(summary, indent=2)}")
    
    # Add a custom alert
    await alert_system.add_alert(
        alert_type="custom",
        message="This is a custom alert for demonstration purposes",
        severity="info",
        data={'example': True}
    )
    
    # Check for anomalies
    await alert_system.check_anomaly_alerts(
        metric_name="profit",
        current_value=-0.05,  # Anomalous negative profit
        historical_values=[0.02, 0.015, 0.01, 0.02, 0.025, 0.018, 0.022, 0.019, 0.021, 0.02]
    )

if __name__ == "__main__":
    asyncio.run(main())