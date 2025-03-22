@echo off
setlocal enabledelayedexpansion

echo Starting arbitrage bot and dashboard...

:: Create a unique identifier for this session
set SESSION_ID=%RANDOM%

:: Kill any existing dashboard instances
taskkill /F /FI "WINDOWTITLE eq Arbitrage Dashboard*" /T >nul 2>&1

:: Start dashboard with unique title
start "Arbitrage Dashboard [%SESSION_ID%]" cmd /k "python -m new_dashboard.dashboard"

:: Wait for dashboard to initialize
echo Waiting for dashboard to start...
timeout /t 2 /nobreak >nul

:: Verify dashboard is running
netstat -ano | findstr ":8080" >nul
if errorlevel 1 (
    echo Failed to start dashboard
    goto cleanup
)

:: Start the main bot
start "Arbitrage Bot [%SESSION_ID%]" cmd /k "start_arbitrage_bot.bat"

:: Wait for bot to initialize
timeout /t 3 /nobreak >nul

:: Open dashboard in default browser
start http://localhost:8080

echo.
echo System started successfully:
echo - Dashboard running [Session: %SESSION_ID%]
echo - Bot running with log viewer
echo - Dashboard available at http://localhost:8080
echo.
echo Press Ctrl+C to stop all components...

:: Wait for Ctrl+C
:wait
timeout /t 1 /nobreak >nul
goto wait

:cleanup
:: Clean up only our session's processes
echo.
echo Cleaning up...
taskkill /F /FI "WINDOWTITLE eq Arbitrage Dashboard [%SESSION_ID%]*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Arbitrage Bot [%SESSION_ID%]*" /T >nul 2>&1

echo System stopped.
exit /b