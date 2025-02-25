@echo off
echo Running Python Diagnostic...
echo.

REM Try to run using the venv Python first
IF EXIST "D:\Listonian-bot\venv\Scripts\python.exe" (
    echo Using venv Python...
    "D:\Listonian-bot\venv\Scripts\python.exe" check_python.py
    echo.
    pause
) ELSE (
    echo Venv Python not found, trying system Python...
    python check_python.py
    echo.
    pause
)