@echo off
echo ==========================================
echo Python Virtual Environment Rebuild Script
echo ==========================================
echo.

REM Check Python availability
echo Checking Python installation...
where python 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not found in your PATH
    echo Please make sure Python is installed and added to your PATH
    echo Installation guide: https://www.python.org/downloads/
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
    echo This might be due to missing Python venv module
    echo Try installing it with: python -m pip install --user virtualenv
    goto :error
)

REM Activate the environment and install dependencies
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    goto :error
)

echo Installing dependencies...
echo.
echo Installing from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some packages from requirements.txt failed to install
    echo You may need to install them manually later
)

echo.
echo Installing from requirements-dev.txt...
pip install -r requirements-dev.txt
if errorlevel 1 (
    echo WARNING: Some packages from requirements-dev.txt failed to install
    echo You may need to install them manually later
)

echo.
echo Installing project in development mode...
pip install -e .
if errorlevel 1 (
    echo WARNING: Failed to install project in development mode
    echo You may need to do this manually later
)

echo.
echo Creating .vscode/settings.json with correct Python path...
if not exist ".vscode" mkdir ".vscode"
echo {
echo     "terminal.integrated.defaultProfile.windows": "PowerShell",
echo     "terminal.integrated.shellIntegration.enabled": true,
echo     "python.defaultInterpreterPath": "%cd%\\venv\\Scripts\\python.exe",
echo     "python.terminal.activateEnvironment": true,
echo     "python.terminal.activateEnvInCurrentTerminal": true
echo } > .vscode\settings.json

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
echo Please run check_python_installation.bat to diagnose Python issues
echo.
pause
exit /b 1