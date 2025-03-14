@echo off
echo ===============================================================================
echo ARBITRAGE SYSTEM DASHBOARD
echo ===============================================================================
echo.
echo Starting dashboard...
call venv\Scripts\activate.bat
python arbitrage_bot\dashboard\start_dashboard.py
echo.
echo ===============================================================================
echo Press any key to exit...
pause >nul