@echo off
echo ===============================================================================
echo SIMPLE ARBITRAGE LOG VIEWER (PORT 9090)
echo ===============================================================================
echo.
echo This simple viewer displays your arbitrage bot log files without dependencies.
echo.

echo Starting log viewer on port 9090...
echo.
echo OPEN THIS URL IN YOUR BROWSER: http://localhost:9090
echo.
echo Press Ctrl+C to stop the server when done.
echo.

python log_viewer.py

echo.
echo Server stopped.
echo ===============================================================================
pause