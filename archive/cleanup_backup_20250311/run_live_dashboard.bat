@echo off
echo ===============================================================================
echo ARBITRAGE DASHBOARD WITH LIVE LOG DATA
echo ===============================================================================
echo.
echo This dashboard displays actual log data from your arbitrage bot.
echo.

echo Creating data directory...
mkdir logs 2>nul

echo.
echo Starting dashboard with live data...
python live_data_dashboard.py

echo.
echo Dashboard stopped.
echo ===============================================================================
pause