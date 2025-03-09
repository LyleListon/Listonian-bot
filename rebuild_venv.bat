@echo off
echo Rebuilding Python virtual environment...
echo.

REM Remove existing venv if it exists
IF EXIST "D:\Listonian-bot\venv" (
    echo Removing existing virtual environment...
    rmdir /s /q "D:\Listonian-bot\venv"
)

echo Creating new virtual environment...
python -m venv venv

echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

echo.
echo Virtual environment rebuilt successfully!
echo Please restart VS Code to apply changes.
echo.
pause