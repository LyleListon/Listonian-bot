@echo off
echo ===============================================================================
echo TOKEN PRICE MONITORING DASHBOARD
echo ===============================================================================
echo.
echo This dashboard displays current token prices across all configured DEXes.
echo.

echo Starting token price dashboard...
echo.
echo OPEN THIS URL IN YOUR BROWSER: http://localhost:9096
echo.
echo Press Ctrl+C to stop the server when done.
echo.

python token_price_dashboard.py

echo.
echo Server stopped.
echo ===============================================================================
pause