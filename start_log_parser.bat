@echo off
echo Starting Log Parser Bridge...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please ensure Python is installed and added to PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

REM Start the Log Parser Bridge
echo Starting Log Parser Bridge...
python scripts/start_log_parser.py

REM Keep window open on error
if errorlevel 1 (
    echo.
    echo Error occurred while running Log Parser Bridge
    pause
)