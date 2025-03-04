# Arbitrage System Performance Data Collection Guide

## Overview

Effective data collection and analysis are essential for improving the arbitrage system's performance over time. This guide outlines the methods, tools, and strategies for gathering performance metrics, analyzing trade data, and using insights to optimize the system for maximum profitability.

## Table of Contents

1. [Key Performance Metrics](#key-performance-metrics)
2. [Dashboard Data Collection](#dashboard-data-collection)
3. [Log-Based Data Collection](#log-based-data-collection)
4. [Creating Custom Reports](#creating-custom-reports)
5. [Performance Visualization](#performance-visualization)
6. [Analyzing Trade Performance](#analyzing-trade-performance)
7. [System Performance Analysis](#system-performance-analysis)
8. [Data-Driven Optimization](#data-driven-optimization)
9. [Setting Up Automated Reporting](#setting-up-automated-reporting)

## Key Performance Metrics

### Profitability Metrics

1. **Gross Profit**:
   - Total profit before gas costs and fees
   - Measured in ETH and USD equivalent
   - Calculated per trade and aggregated over time

2. **Net Profit**:
   - Profit after subtracting all costs
   - Includes gas fees, flash loan fees, etc.
   - Primary indicator of system effectiveness

3. **ROI (Return on Investment)**:
   - Percentage return on deployed capital
   - Calculated as (Net Profit / Deployed Capital) × 100%
   - Higher is better, target >0.2% per trade

4. **Profit per Gas Unit**:
   - Efficiency metric for gas usage
   - Calculated as Net Profit / Gas Used
   - Important for optimizing gas strategies

### Operational Metrics

1. **Success Rate**:
   - Percentage of attempted trades that execute successfully
   - Calculated as (Successful Trades / Total Attempted) × 100%
   - Target >90% for stable operations

2. **Opportunity Discovery Rate**:
   - Number of profitable opportunities found per hour
   - Broken down by strategy type and token pairs
   - Indicates market inefficiency capture effectiveness

3. **Execution Time**:
   - Time from opportunity detection to transaction confirmation
   - Critical for time-sensitive arbitrage
   - Target <15 seconds end-to-end

4. **Gas Usage**:
   - Average gas used per trade
   - Gas cost trends over time
   - Gas usage by DEX and strategy type

## Dashboard Data Collection

### Real-time Dashboard Metrics

The FastAPI dashboard provides real-time access to key performance data:

1. **Accessing the Dashboard**:
   - Start the dashboard with `.\start_new_dashboard.bat`
   - Navigate to `http://localhost:8080`

2. **Dashboard Data Tabs**:
   - **Overview**: System-wide metrics
   - **Trades**: Individual trade details
   - **Performance**: Historical performance charts
   - **Gas**: Gas usage statistics
   - **Tokens**: Token-specific metrics

3. **Dashboard API Endpoints**:
   - `/api/status`: General system status
   - `/api/bot-data`: Complete bot dataset
   - `/api/transactions`: Transaction history
   - `/api/opportunities`: Opportunity data
   - `/api/logs`: System log entries

### Data Export

1. **Manual Export**:
   - Click "Export Data" on any dashboard page
   - Select date range and metrics
   - Choose CSV or JSON format
   - Save file to desired location

2. **API-Based Export**:
   - Use the dashboard API endpoints for automated data collection
   - Example Python script:
     ```python
     import requests
     import json
     import pandas as pd
     
     # Get transaction data
     response = requests.get("http://localhost:8080/api/transactions")
     transactions = response.json()["transactions"]
     
     # Convert to pandas DataFrame
     df = pd.DataFrame(transactions)
     
     # Save to CSV
     df.to_csv("transactions.csv", index=False)
     ```

3. **Database Integration**:
   - Connect to the dashboard's SQLite database directly
   - Located at `./new_dashboard/data/dashboard.db`
   - Use SQL queries for custom data extraction

## Log-Based Data Collection

### Log Files Overview

The system generates detailed logs that can be analyzed for performance data:

1. **Log File Locations**:
   - Production logs: `./logs/arbitrage_production_*.log`
   - Dashboard logs: `./logs/new_dashboard.log`
   - Error logs: `./logs/error_*.log`

2. **Log Format**:
   - ISO timestamp
   - Log level (INFO, WARNING, ERROR, etc.)
   - Component name
   - Message content

3. **Key Log Events**:
   - Opportunity detection
   - Trade execution
   - Transaction confirmation
   - Error conditions
   - System status changes

### Log Parsing Strategies

1. **Real-time Log Analysis**:
   - Use the log viewer in the dashboard
   - Filter by component, level, or keyword
   - Group related log entries

2. **Batch Log Processing**:
   - Parse logs with standard tools (grep, awk, etc.)
   - Example command to extract profit data:
     ```bash
     grep "Profit:" logs/arbitrage_production_*.log | cut -d ':' -f 4-5 > profits.txt
     ```

3. **Structured Log Analysis**:
   - Use the `log_analyzer.py` script in the utils directory
   - Example usage:
     ```bash
     python utils/log_analyzer.py --log-dir logs --output stats.json --metrics profit,gas,success
     ```

## Creating Custom Reports

### Report Types

1. **Daily Performance Report**:
   - Summary of the day's trading activity
   - Profit and loss statement
   - Success rate and error analysis
   - Gas usage and cost breakdown

2. **Token Performance Report**:
   - Profitability by token pair
   - Volume by token
   - Success rate by token
   - Opportunity frequency by token

3. **Strategy Performance Report**:
   - Comparison of different arbitrage strategies
   - Flash loan vs. direct trading results
   - Path length analysis
   - DEX pair performance

4. **System Health Report**:
   - Error rates and types
   - Component performance
   - Resource utilization
   - RPC provider performance

### Creating Reports with Python

1. **Basic Report Generation**:
   ```python
   import pandas as pd
   import matplotlib.pyplot as plt
   
   # Load trade data from CSV
   trades = pd.read_csv("trades.csv")
   
   # Calculate daily profits
   daily_profit = trades.groupby(pd.to_datetime(trades['timestamp']).dt.date)['net_profit'].sum()
   
   # Create report
   with open("daily_report.txt", "w") as f:
       f.write("DAILY PERFORMANCE REPORT\n")
       f.write("======================\n\n")
       f.write(f"Total Trades: {len(trades)}\n")
       f.write(f"Successful Trades: {len(trades[trades['status'] == 'success'])}\n")
       f.write(f"Success Rate: {len(trades[trades['status'] == 'success']) / len(trades) * 100:.2f}%\n")
       f.write(f"Total Profit: {trades['net_profit'].sum():.6f} ETH\n")
       f.write(f"Average Profit per Trade: {trades['net_profit'].mean():.6f} ETH\n")
       f.write(f"Total Gas Used: {trades['gas_used'].sum()}\n")
       f.write(f"Average Gas per Trade: {trades['gas_used'].mean():.0f}\n")
   
   # Create a chart
   plt.figure(figsize=(10, 5))
   daily_profit.plot(kind='bar')
   plt.title('Daily Profit')
   plt.ylabel('Profit (ETH)')
   plt.tight_layout()
   plt.savefig('daily_profit.png')
   ```

2. **Advanced Reporting with `report_generator.py`**:
   - Use the built-in report generator:
     ```bash
     python tools/report_generator.py --type daily --output-dir reports
     ```
   - Available report types:
     - `daily`: Daily performance summary
     - `token`: Token-based analysis
     - `strategy`: Strategy comparison
     - `health`: System health statistics
     - `custom`: User-defined custom report

## Performance Visualization

### Dashboard Visualizations

The dashboard includes built-in visualization tools:

1. **Performance Charts**:
   - Profit over time
   - Success rate trends
   - Gas price vs. profit correlation
   - Opportunity detection rate

2. **Custom Chart Creation**:
   - Click "Create Chart" in the Analytics tab
   - Select metrics for X and Y axes
   - Choose chart type (line, bar, scatter, etc.)
   - Set time range and grouping

3. **Visualization Export**:
   - Export any chart as PNG, SVG, or PDF
   - Download chart data as CSV
   - Share charts via URL

### External Visualization Tools

For more advanced analysis, export data to external tools:

1. **Excel/Google Sheets**:
   - Import CSV data
   - Create pivot tables and charts
   - Use for quick ad-hoc analysis

2. **Python Visualization**:
   - Use pandas, matplotlib, and seaborn
   - Create complex multi-variable analysis
   - Generate publication-quality charts

3. **Tableau/Power BI**:
   - Connect to exported data
   - Create interactive dashboards
   - Share insights with stakeholders

## Analyzing Trade Performance

### Trade Success Analysis

1. **Success Rate Factors**:
   - Analyze correlation between success and:
     - Gas price strategy
     - Slippage settings
     - Path length
     - Token liquidity
     - DEX combinations

2. **Failure Analysis**:
   - Categorize failures by type:
     - Slippage failures
     - Gas-related failures
     - MEV-related failures
     - RPC failures
     - Contract errors

3. **Success Pattern Recognition**:
   - Identify patterns in successful trades
   - Time of day correlations
   - Gas price thresholds
   - DEX pair success rates

### Profitability Analysis

1. **Profit Distribution**:
   - Analyze distribution of profits
   - Identify outliers (highly profitable trades)
   - Determine median and mode profit values

2. **Profit by Category**:
   - Break down profit by:
     - Strategy type
     - Token pairs
     - Path length
     - DEX combinations
     - Time of day

3. **ROI Analysis**:
   - Calculate ROI for different capital levels
   - Determine optimal capital deployment
   - Analyze ROI variance and stability

## System Performance Analysis

### Component Performance

1. **Path Finder Performance**:
   - Path discovery rate
   - Path validation speed
   - Path profitability accuracy

2. **Flash Loan Manager**:
   - Flash loan success rate
   - Provider comparison
   - Fee optimization

3. **MEV Protection**:
   - Front-running prevention rate
   - Bundle acceptance rate
   - Private transaction effectiveness

4. **Web3 Manager**:
   - RPC call latency
   - Connection stability
   - Transaction submission success

### Resource Utilization

1. **CPU Usage**:
   - Monitor CPU load during operation
   - Identify processing bottlenecks
   - Optimize compute-intensive components

2. **Memory Usage**:
   - Track memory consumption
   - Detect memory leaks
   - Optimize caching strategies

3. **Network Performance**:
   - Measure RPC call volume
   - Analyze network latency
   - Monitor bandwidth usage

## Data-Driven Optimization

### Parameter Optimization

Use collected data to optimize system parameters:

1. **Gas Strategy Optimization**:
   - Analyze gas price vs. inclusion time
   - Find optimal gas price strategy
   - Adjust based on network conditions

2. **Slippage Tolerance**:
   - Analyze slippage patterns by token
   - Create token-specific slippage models
   - Optimize for balance between success and profit

3. **Path Selection**:
   - Identify most profitable path patterns
   - Optimize path length constraints
   - Prioritize high-success DEX combinations

### Strategy Refinement

1. **A/B Testing Framework**:
   - Test parameter variations
   - Run parallel strategies
   - Measure performance differences

2. **Strategy Evolution**:
   - Use historical data to develop new strategies
   - Validate against past opportunities
   - Implement with careful monitoring

3. **Adaptive Parameters**:
   - Create self-tuning parameter system
   - Adjust based on recent performance
   - Develop machine learning models for prediction

## Setting Up Automated Reporting

### Scheduled Reports

1. **Daily Report Setup**:
   - Create a batch script:
     ```batch
     @echo off
     echo Generating daily report...
     python tools/report_generator.py --type daily --output-dir reports
     echo Report generated at reports/daily_%date:~-4,4%%date:~-7,2%%date:~-10,2%.pdf
     ```
   - Schedule with Windows Task Scheduler:
     - Action: Start a program
     - Program: `cmd.exe`
     - Arguments: `/c path\to\daily_report.bat`
     - Schedule: Daily at midnight

2. **Weekly Analysis**:
   - Create more comprehensive weekly reports
   - Include trend analysis and recommendations
   - Deliver via email or notification system

### Real-time Alerts

1. **Critical Metric Monitoring**:
   - Set thresholds for key metrics:
     - Success rate drops below 80%
     - Profit falls below threshold
     - Error rate exceeds 10%
     - Gas price spikes

2. **Alert Delivery**:
   - Configure alerts via:
     - Email notifications
     - SMS alerts
     - Dashboard notifications
     - Slack/Discord integration

3. **Alert Response Procedures**:
   - Document standard responses to alerts
   - Create escalation procedures
   - Implement automatic mitigations where possible

### Data Retention Policy

1. **Storage Requirements**:
   - Raw logs: 30 days
   - Aggregated data: 1 year
   - Summary reports: Indefinite

2. **Backup Strategy**:
   - Daily backups of the database
   - Weekly backups of all logs
   - Monthly archives of all data

3. **Data Analysis Archives**:
   - Maintain archive of all reports
   - Store visualizations with context
   - Document insights and actions taken

## Case Study: Performance Data Analysis Process

### Example: Investigating Declining Profitability

1. **Identify the Issue**:
   - Daily profit report shows 15% decline in profit
   - Success rate remains stable
   - No significant change in opportunity count

2. **Data Collection**:
   - Gather trade data for the period
   - Compare with previous baseline period
   - Extract relevant log entries

3. **Analysis Process**:
   ```python
   # Example analysis code
   import pandas as pd
   import matplotlib.pyplot as plt
   
   # Load data for current and previous period
   current = pd.read_csv("trades_current.csv")
   previous = pd.read_csv("trades_previous.csv")
   
   # Compare profit metrics
   current_profit = current['net_profit'].sum()
   previous_profit = previous['net_profit'].sum()
   profit_change = (current_profit - previous_profit) / previous_profit * 100
   
   # Analyze components
   gas_current = current['gas_cost'].mean()
   gas_previous = previous['gas_cost'].mean()
   gas_change = (gas_current - gas_previous) / gas_previous * 100
   
   slippage_current = current['slippage'].mean()
   slippage_previous = previous['slippage'].mean()
   slippage_change = (slippage_current - slippage_previous) / slippage_previous * 100
   
   # Output findings
   print(f"Profit Change: {profit_change:.2f}%")
   print(f"Gas Cost Change: {gas_change:.2f}%")
   print(f"Slippage Change: {slippage_change:.2f}%")
   
   # Visualize
   plt.figure(figsize=(12, 6))
   
   plt.subplot(1, 3, 1)
   plt.bar(['Previous', 'Current'], [previous_profit, current_profit])
   plt.title('Net Profit')
   
   plt.subplot(1, 3, 2)
   plt.bar(['Previous', 'Current'], [gas_previous, gas_current])
   plt.title('Average Gas Cost')
   
   plt.subplot(1, 3, 3)
   plt.bar(['Previous', 'Current'], [slippage_previous, slippage_current])
   plt.title('Average Slippage')
   
   plt.tight_layout()
   plt.savefig('profit_analysis.png')
   ```

4. **Findings and Action**:
   - Analysis reveals 35% increase in average gas costs
   - No significant change in slippage
   - Action: Optimize gas price strategy and gas limits

### Example: Success Rate Optimization

1. **Data Collection and Preparation**:
   ```python
   # Load trade data
   trades = pd.read_csv("all_trades.csv")
   
   # Create success indicator
   trades['is_success'] = trades['status'] == 'success'
   
   # Group by relevant factors
   by_gas_strategy = trades.groupby('gas_strategy')['is_success'].mean()
   by_dex_pair = trades.groupby(['buy_dex', 'sell_dex'])['is_success'].mean()
   by_path_length = trades.groupby('path_length')['is_success'].mean()
   
   # Output findings
   print("Success Rate by Gas Strategy:")
   print(by_gas_strategy)
   
   print("\nSuccess Rate by DEX Pair:")
   print(by_dex_pair.sort_values(ascending=False).head(10))
   
   print("\nSuccess Rate by Path Length:")
   print(by_path_length)
   ```

2. **Analysis and Action**:
   - Identify gas strategy with highest success
   - Find top-performing DEX pairs
   - Determine optimal path length
   - Adjust system parameters accordingly

## Next Steps: Advanced Analytics

Consider implementing these advanced analytics approaches:

1. **Machine Learning Models**:
   - Predict profitable opportunities
   - Classify potential trades by success probability
   - Optimize parameters automatically

2. **Time Series Analysis**:
   - Identify cyclical patterns in profitability
   - Forecast gas prices and market conditions
   - Develop timing-based strategies

3. **Network Analysis**:
   - Map DEX relationships and liquidity flows
   - Identify structural arbitrage patterns
   - Develop graph-based opportunity detection

---

**Last Updated**: March 2, 2025

**Contact**: For support or questions, please reach out to the development team.