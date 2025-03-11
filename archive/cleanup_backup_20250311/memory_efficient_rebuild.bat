@echo off
echo ==========================================
echo Memory-Efficient Python Environment Setup
echo ==========================================
echo.

REM Check Python availability
echo Checking Python installation...
where python 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not found in your PATH
    echo Please make sure Python is installed and added to your PATH
    goto :error
)

REM Get Python version
for /f "tokens=*" %%a in ('python --version 2^>^&1') do (
    echo Found: %%a
)
echo.

REM Check project directory
echo Current directory: %cd%
if not "%cd%"=="d:\Listonian-bot" (
    echo WARNING: You should run this script from d:\Listonian-bot
)
echo.

REM Remove existing venv if it exists
if exist "venv" (
    echo Removing existing virtual environment...
    rmdir /s /q "venv"
    if errorlevel 1 (
        echo ERROR: Failed to remove existing venv
        goto :error
    )
)

REM Create new venv in the project directory
echo Creating new virtual environment in %cd%\venv...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo Make sure you have the venv module installed with:
    echo python -m pip install --user virtualenv
    goto :error
)

REM Activate the environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    goto :error
)

REM Install pip dependencies in smaller batches to avoid memory issues
echo Installing basic dependencies first...
pip install --no-cache-dir wheel setuptools pip --upgrade

echo Installing core dependencies...
pip install --no-cache-dir cryptography web3 python-dotenv pyyaml jsonschema

echo Installing networking dependencies...
pip install --no-cache-dir aiohttp aiohttp-cors aiohttp-sse aiohttp-jinja2 jinja2 websockets requests

echo Installing data processing dependencies...
pip install --no-cache-dir joblib

echo Installing database dependencies...
pip install --no-cache-dir sqlalchemy lru-dict redis aioredis

echo Installing monitoring dependencies...
pip install --no-cache-dir prometheus_client

echo Installing ML dependencies (may take a while)...
pip install --no-cache-dir numpy
pip install --no-cache-dir pandas
pip install --no-cache-dir scikit-learn

echo Installing development dependencies...
pip install --no-cache-dir pytest pytest-asyncio pytest-cov pytest-mock

echo Installing project in development mode...
pip install -e .

echo.
echo Creating .vscode/settings.json with correct Python path...
if not exist ".vscode" mkdir ".vscode"
(
echo {
echo     "terminal.integrated.defaultProfile.windows": "PowerShell",
echo     "terminal.integrated.shellIntegration.enabled": true,
echo     "python.defaultInterpreterPath": "%cd%\\venv\\Scripts\\python.exe",
echo     "python.terminal.activateEnvironment": true,
echo     "python.terminal.activateEnvInCurrentTerminal": true
echo }
) > .vscode\settings.json

echo.
echo ==========================================
echo Virtual environment rebuilt successfully!
echo ==========================================
echo.
echo Please:
echo 1. Close VSCode completely
echo 2. Reopen VSCode
echo 3. Select the Python interpreter at %cd%\venv\Scripts\python.exe
echo    (Ctrl+Shift+P → "Python: Select Interpreter")
echo.
pause
exit /b 0

:error
echo.
echo ==========================================
echo ERRORS OCCURRED DURING SETUP
echo ==========================================
echo.
echo Please check your Python installation with check_python_installation.bat
echo.
pause
exit /b 1