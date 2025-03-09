@echo off
echo ===============================================================================
echo BASIC ARBITRAGE DASHBOARD
echo ===============================================================================
echo.
echo This dashboard uses Python's built-in HTTP server with no external dependencies.
echo.

echo Creating data directory...
mkdir data 2>nul

echo.
echo Starting basic dashboard...
python basic_dashboard.py

echo.
echo Dashboard stopped.
echo ===============================================================================
pause