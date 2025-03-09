@echo off
echo ===============================================================================
echo ARBITRAGE LOG DASHBOARD - REAL DATA MONITOR
echo ===============================================================================
echo.
echo This dashboard reads REAL data from your logs instead of using simulations.
echo.
echo FEATURES:
echo  - Reads actual opportunity checks from your existing log files
echo  - Shows real transaction history and profitability metrics 
echo  - Provides detailed statistics on trading pairs and DEXes
echo  - Zero simulation - all data comes directly from your logs
echo.
echo The dashboard looks for logs in these locations:
echo  - logs/arbitrage_checks.log
echo  - logs/opportunity_checks.log
echo  - logs/trading_checks.csv
echo  - data/arbitrage_checks.csv
echo.
echo To add your own log files, place them in the logs/ directory.
echo.
echo Opening http://localhost:9097 in your browser...
echo Press Ctrl+C to stop the server when done.
echo ===============================================================================

start "" http://localhost:9097
python enhanced_arbitrage_dashboard.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred while running the dashboard
    echo Please check Python installation and required modules:
    echo  - sqlite3 (standard library)
    echo  - csv (standard library)
    echo.
    pause
) else (
    echo.
    echo Server stopped.
    echo ===============================================================================
)

pause