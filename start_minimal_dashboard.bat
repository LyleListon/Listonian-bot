@echo off
echo ===============================================================================
echo MINIMAL ARBITRAGE SYSTEM DASHBOARD
echo ===============================================================================
echo.
echo Starting minimal dashboard...
call venv\Scripts\activate.bat
python minimal_dashboard.py
echo.
echo ===============================================================================
echo Press any key to exit...
pause >nul