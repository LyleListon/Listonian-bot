@echo off
echo Starting Dashboard with Real Data
echo ================================

echo Step 1: Starting bot API server...
start cmd /k python bot_api_server.py

echo Step 2: Waiting for API server to initialize (3 seconds)...
timeout /t 3 /nobreak > nul

echo Step 3: Starting HTTP server for dashboard...
start cmd /k python -m http.server 8080

echo Step 4: Waiting for HTTP server to initialize (2 seconds)...
timeout /t 2 /nobreak > nul

echo Step 5: Opening dashboard in browser...
start http://localhost:8080/dashboard.html

echo.
echo Dashboard system started successfully!
echo API Server: http://localhost:8081
echo Dashboard: http://localhost:8080/dashboard.html
echo.
echo Press any key to exit this window (servers will continue running)...
pause > nul
