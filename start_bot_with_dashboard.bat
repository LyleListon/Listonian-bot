@echo off
setlocal enabledelayedexpansion

:: Set environment variables
set PYTHONUNBUFFERED=1
set LOG_LEVEL=INFO
set ENV=production

echo Creating log directories...
if not exist "logs" mkdir logs

:: Kill any existing Python processes running the dashboard or bot
echo Closing existing processes and releasing file locks...

:: More comprehensive process termination
:: Kill any Python processes that might be related to our application
wmic process where "commandline like '%%dashboard.app%%'" call terminate >nul 2>&1
wmic process where "commandline like '%%run_bot%%'" call terminate >nul 2>&1
wmic process where "commandline like '%%uvicorn%%dashboard%%'" call terminate >nul 2>&1
wmic process where "commandline like '%%python%%run_bot.py%%'" call terminate >nul 2>&1

:: Kill any cmd.exe processes with our window titles
wmic process where "commandline like '%%Arbitrage Bot%%'" call terminate >nul 2>&1
wmic process where "commandline like '%%Dashboard%%'" call terminate >nul 2>&1

:: Wait a moment for processes to close
echo Waiting for processes to terminate...
timeout /t 5 >nul

:: Start the arbitrage bot in a new terminal
echo Starting arbitrage bot...
start "Arbitrage Bot" cmd /k "python run_bot.py > logs\bot.log 2>&1"

:: Wait a moment for the bot to initialize
timeout /t 5

:: Start the dashboard in a new terminal
echo Starting dashboard...
start "Dashboard" cmd /k "set MEMORY_BANK_PATH=%CD%\memory-bank && cd new_dashboard && uvicorn dashboard.app:create_app --factory --host 0.0.0.0 --port 9050 --reload > ..\logs\dashboard.log 2>&1"

:: Open dashboard in default browser
timeout /t 3
echo Opening dashboard in browser...
start http://localhost:9050

echo System started successfully!
echo.
echo Arbitrage Bot logs: logs\bot.log
echo Dashboard logs: logs\dashboard.log
echo Dashboard URL: http://localhost:9050
echo.
echo Press Ctrl+C in respective terminals to stop the services
