@echo off
echo ===============================================================================
echo MULTI-CHAIN ARBITRAGE DASHBOARD
echo ===============================================================================
echo.
echo This dashboard monitors arbitrage opportunities across multiple networks:
echo.
echo  [1] ETHEREUM MAINNET
echo  [2] ARBITRUM
echo  [3] BASE
echo.
echo FEATURES:
echo  - Real-time monitoring of cross-chain opportunities
echo  - Network-specific statistics and analytics
echo  - DEX comparison across different chains
echo  - Gas cost analysis for each network
echo  - Direct access to log data without API dependencies
echo.
echo The dashboard uses SQLite to process and analyze:
echo  - Arbitrage opportunity check logs
echo  - Trading pair statistics by network
echo  - DEX profitability metrics
echo  - Gas cost comparisons
echo.
echo DATA SOURCES:
echo  - logs/arbitrage_checks.log
echo  - logs/opportunity_checks.log
echo  - logs/trading_checks.csv
echo  - data/arbitrage_checks.csv
echo.
echo Opening http://localhost:9097 in your browser...
echo Press Ctrl+C to stop the server when done.
echo ===============================================================================

start "" http://localhost:9097
python multi_chain_dashboard.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred while running the dashboard
    echo.
    pause
) else (
    echo.
    echo Server stopped.
    echo ===============================================================================
)

pause