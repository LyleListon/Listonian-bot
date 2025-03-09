# Arbitrage Monitoring Dashboard

This document outlines the real-time monitoring dashboard for the arbitrage system, designed to track performance metrics and optimize profitability.

## Overview

The monitoring dashboard provides real-time visibility into all aspects of the arbitrage system:

- **Profit Metrics**: Track total and average profits, profit margins, and profit after gas costs
- **Arbitrage Performance**: Monitor paths found, paths executed, and success rates
- **Flash Loan Stats**: Track flash loan executions, success rates, costs, and volumes
- **MEV Protection**: Monitor attack detection, bundle submissions, and risk levels
- **Gas Usage**: Track gas prices, gas usage, and total gas costs

## Key Features

1. **Real-time Metrics**: Continuously updated performance metrics
2. **Visual Charts**: Graphical representation of all performance indicators
3. **Alerting System**: Configurable alerts for high-risk or high-opportunity situations
4. **Historical Data**: Persistent storage of historical metrics for trend analysis
5. **Web Interface**: Easy-to-use browser-based dashboard accessible from any device

## Getting Started

### Starting the Dashboard

1. Execute the `start_monitor.bat` script:
   ```
   start_monitor.bat
   ```

2. Access the dashboard in any web browser:
   ```
   http://localhost:8080
   ```

### Adding Metrics from Your Arbitrage System

Add the following code to your arbitrage system to send metrics to the dashboard:

```python
from dashboard.arbitrage_monitor import update_metrics

async def send_metrics_to_dashboard():
    # Prepare metrics
    metrics = {
        "arbitrage": {
            "paths_found": 15,
            "paths_executed": 8,
            "success_rate": 53.33,
            "avg_execution_time": 120
        },
        "flash_loan": {
            "loans_executed": 8,
            "success_rate": 100.0,
            "average_cost": 0.0009,
            "total_volume": 10.5
        },
        "mev_protection": {
            "attacks_detected": 3,
            "bundles_submitted": 8,
            "bundle_success_rate": 87.5,
            "risk_level": "medium"
        },
        "gas": {
            "average_gas_price": 35.2,
            "average_gas_used": 350000,
            "total_gas_cost": 0.012,
            "tx_count": 8
        },
        "profit": {
            "total_profit": 0.085,
            "average_profit": 0.0106,
            "profit_after_gas": 0.073,
            "profit_margin": 3.2
        }
    }
    
    # Send to dashboard
    await update_metrics("http://localhost:8080", metrics)
```

## Dashboard Sections

### 1. Profit Metrics

![Profit Metrics](../dashboard/static/profit_metrics.png)

- **Total Profit**: Cumulative profit in ETH
- **Average Profit**: Average profit per arbitrage execution
- **Profit After Gas**: Net profit after gas costs
- **Profit Margin**: Percentage profit relative to investment

### 2. Arbitrage Performance

![Arbitrage Performance](../dashboard/static/arbitrage_performance.png)

- **Paths Found**: Number of profitable arbitrage paths discovered
- **Paths Executed**: Number of paths successfully executed
- **Success Rate**: Percentage of found paths successfully executed
- **Average Execution Time**: Average time to execute an arbitrage transaction

### 3. Flash Loan Performance

![Flash Loan Performance](../dashboard/static/flash_loan_performance.png)

- **Loans Executed**: Number of flash loans initiated
- **Success Rate**: Percentage of successful flash loans
- **Average Cost**: Average cost per flash loan in ETH
- **Total Volume**: Total volume of flash loans in ETH

### 4. MEV Protection Performance

![MEV Protection](../dashboard/static/mev_protection.png)

- **Attacks Detected**: Number of potential MEV attacks detected
- **Bundles Submitted**: Number of bundles submitted to Flashbots
- **Bundle Success Rate**: Percentage of bundles successfully included
- **Risk Level**: Current MEV risk assessment (low, medium, high)

### 5. Gas Metrics

![Gas Metrics](../dashboard/static/gas_metrics.png)

- **Average Gas Price**: Current average gas price in GWEI
- **Average Gas Used**: Average gas units used per transaction
- **Total Gas Cost**: Cumulative gas costs in ETH
- **Transactions Count**: Total number of transactions sent

## Configuration

The dashboard can be configured by editing `config/monitor_config.json`:

```json
{
  "host": "localhost",
  "port": 8080,
  "refresh_interval": 30,
  "data_directory": "monitoring_data",
  "metrics_history_size": 100,
  "charts_enabled": true,
  "alerts_enabled": true,
  "profit_threshold_alert": 0.001,
  "gas_price_threshold_alert": 150,
  "mev_risk_threshold_alert": "high"
}
```

## Alerting System

The dashboard includes an alerting system that can notify you of important events:

1. **Profit Alerts**: Triggered when profit exceeds configured thresholds
2. **Gas Price Alerts**: Triggered when gas prices exceed configured thresholds
3. **MEV Risk Alerts**: Triggered when MEV risk reaches configured levels

Alerts are logged to the console and displayed on the dashboard.

## Data Storage

Metrics are stored in JSON files in the `monitoring_data` directory:

- `arbitrage_YYYYMMDD.json`
- `flash_loan_YYYYMMDD.json`
- `mev_protection_YYYYMMDD.json`
- `gas_YYYYMMDD.json`
- `profit_YYYYMMDD.json`

These files can be used for offline analysis and reporting.

## Integration with Complete Arbitrage System

The monitoring dashboard is designed to work seamlessly with the complete arbitrage system:

1. **Initialize components** in your startup code
2. **Send metrics** after each arbitrage attempt
3. **Configure alerts** based on your risk tolerance
4. **Analyze performance** to improve your strategies

See the `cline_docs/arbitrage_integration_guide.md` for complete system integration details.

## Dashboard API

The dashboard provides a REST API for programmatic access:

- `GET /api/metrics`: Get all metrics
- `POST /api/metrics`: Submit new metrics
- `GET /api/metrics/arbitrage`: Get arbitrage metrics
- `GET /api/metrics/flash_loan`: Get flash loan metrics
- `GET /api/metrics/mev_protection`: Get MEV protection metrics
- `GET /api/metrics/gas`: Get gas metrics
- `GET /api/metrics/profit`: Get profit metrics

## Requirements

- Python 3.10+
- Required packages: aiohttp, aiofiles, pandas, matplotlib
- Web browser for viewing the dashboard

## Conclusion

The arbitrage monitoring dashboard provides critical real-time visibility into your arbitrage system's performance. By tracking key metrics and providing alerting capabilities, it helps optimize your trading strategies and maximize profits.