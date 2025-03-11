@echo off
echo ========================================================
echo STARTING SIMPLE DASHBOARD
echo ========================================================
echo.

echo Installing required packages...
pip install fastapi uvicorn jinja2

echo.
echo Creating required directories...
mkdir templates 2>nul
mkdir static 2>nul
mkdir static\css 2>nul

echo.
echo Starting simplified dashboard...
python simple_dashboard.py

echo.
echo Press any key to exit...
pause >nul