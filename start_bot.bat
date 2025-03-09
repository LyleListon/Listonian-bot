@echo off
echo Starting Arbitrage Bot and Dashboard in LIVE MODE...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3.8 or higher is required
    exit /b 1
)

REM Check if .env.production exists
if not exist .env.production (
    echo Error: .env.production file not found
    echo Please copy .env.production.template and fill in your settings
    exit /b 1
)

REM Check if production config exists
if not exist configs\production_config.json (
    echo Error: configs/production_config.json not found
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Get environment variables as a command string
for /f "tokens=*" %%i in ('python -c "from dotenv import dotenv_values; config = dotenv_values('.env.production'); print(' '.join([f'set {k}={v}' for k, v in config.items() if not k.startswith('#')]))"') do set "ENV_VARS=%%i"

REM Start the bot and dashboard in separate windows with environment variables
start cmd /k "%ENV_VARS% && python production.py"
start cmd /k "%ENV_VARS% && python -m arbitrage_bot.dashboard.run"

echo Bot and dashboard started in LIVE MODE. Press any key to exit this window...
pause
