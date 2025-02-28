@echo off
echo ===============================================================================
echo ARBITRAGE SYSTEM PRODUCTION MODE
echo ===============================================================================
echo.
echo Starting arbitrage system...
call venv\Scripts\activate.bat
python production.py
echo.
echo ===============================================================================
echo Press any key to exit...
pause >nul
