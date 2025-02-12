@echo off
echo Starting Listonian Arbitrage Bot Setup...

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Set timestamp for log files
set timestamp=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%

:: Redirect all output to log files
echo Setting up environment... > logs\setup_%timestamp%.log 2> logs\setup_%timestamp%.err

:: Check Python installation
python --version > nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or higher. >> logs\setup_%timestamp%.err
    exit /b 1
)

:: Create and activate virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt >> logs\setup_%timestamp%.log 2>> logs\setup_%timestamp%.err
if errorlevel 1 (
    echo Error: Failed to install dependencies. Check logs\setup_%timestamp%.err for details.
    exit /b 1
)

:: Check config files
if not exist configs\config.json (
    echo Error: config.json not found. Please create configs\config.json with your settings.
    exit /b 1
)

if not exist configs\wallet_config.json (
    echo Error: wallet_config.json not found. Please create configs\wallet_config.json with your wallet settings.
    exit /b 1
)

:: Start dashboard in background
echo Starting dashboard...
start "Arbitrage Dashboard" cmd /c "python start_dashboard.py > logs\dashboard_%timestamp%.log 2> logs\dashboard_%timestamp%.err"

:: Wait for dashboard to initialize
timeout /t 5 /nobreak > nul

:: Start main bot
echo Starting arbitrage bot...
start "Arbitrage Bot" cmd /c "python main.py > logs\bot_%timestamp%.log 2> logs\bot_%timestamp%.err"

:: Display status
echo.
echo ===============================
echo Listonian Arbitrage Bot Status
echo ===============================
echo.
echo Dashboard: Running (check logs\dashboard_%timestamp%.log for details)
echo Bot: Running (check logs\bot_%timestamp%.log for details)
echo.
echo Monitor the logs directory for detailed output.
echo Press Ctrl+C in the respective windows to stop the bot or dashboard.
echo.

:: Keep the window open
pause