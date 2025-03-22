@echo off
setlocal enabledelayedexpansion

echo Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    echo Python not found! Please install Python 3.12 or higher.
    pause
    exit /b 1
)

echo Checking environment setup...
if not exist .env.production (
    echo Creating .env.production from template...
    copy .env.production.template .env.production
    echo Please edit .env.production with your values before continuing.
    notepad .env.production
    pause
    exit /b 1
)

echo Initializing secure storage...
python init_secure.py
if errorlevel 1 (
    echo Failed to initialize secure storage!
    pause
    exit /b 1
)

echo Creating log directory...
if not exist logs mkdir logs

echo Starting log viewer in new window...
start "Arbitrage Bot Logs" powershell -Command "Get-Content -Wait logs/arbitrage.log"

echo Starting arbitrage bot...
:start_bot
echo [%date% %time%] Starting bot...
python -m arbitrage_bot.production --mode production
if errorlevel 1 (
    echo Bot crashed or stopped with error code !errorlevel!
    echo Restarting in 10 seconds...
    timeout /t 10 /nobreak
    goto start_bot
)

pause