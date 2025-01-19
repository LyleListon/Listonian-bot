@echo off
echo Starting Dashboard...

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

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Get environment variables as a command string
for /f "tokens=*" %%i in ('python -c "from dotenv import dotenv_values; config = dotenv_values('.env.production'); print(' '.join([f'set {k}={v}' for k, v in config.items() if not k.startswith('#')]))"') do set "ENV_VARS=%%i"

REM Set additional environment variables
set DASHBOARD_PORT=5000
set DASHBOARD_WEBSOCKET_PORT=8771
set PYTHONPATH=%PYTHONPATH%;%CD%

REM Start the dashboard with Hypercorn
%ENV_VARS% && python -m hypercorn arbitrage_bot.dashboard.run:app --bind 0.0.0.0:5000 --worker-class asyncio --debug --access-logfile - --error-logfile - --reload --keep-alive 120

echo Dashboard started. Press Ctrl+C to exit...
