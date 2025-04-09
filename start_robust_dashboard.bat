@echo off
echo Starting Robust Bot Dashboard System
echo ===================================

echo Step 1: Starting robust API server...
start cmd /k python robust_bot_api_server.py

echo Step 2: Waiting for API server to initialize (5 seconds)...
timeout /t 5 /nobreak > nul

echo Step 3: Starting HTTP server for dashboard...
start cmd /k python -m http.server 8080

echo Step 4: Opening dashboard in browser...
timeout /t 2 /nobreak > nul
start http://localhost:8080/robust_dashboard.html

echo.
echo Dashboard system started successfully!
echo API Server: http://localhost:8081
echo Dashboard: http://localhost:8080/robust_dashboard.html
echo.
echo Press any key to exit this window (servers will continue running)...
pause > nul
