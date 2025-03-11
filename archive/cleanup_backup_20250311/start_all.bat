@echo off
echo ===============================================================================
echo STARTING ARBITRAGE SYSTEM WITH ENHANCED DASHBOARD
echo ===============================================================================

echo Starting production system...
start "Arbitrage Production System" cmd /k "start_production.bat"

echo Starting enhanced dashboard...
start "Enhanced Dashboard" cmd /k "start_enhanced_dashboard.bat"

echo.
echo System started! Check the opened windows for details.
echo Press any key to exit this window...
pause > nul