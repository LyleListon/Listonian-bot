@echo off
echo ==========================================
echo VS Code Python Interpreter Fix
echo ==========================================
echo.

echo Checking for venv Python interpreter...
if exist "venv\Scripts\python.exe" (
    echo Found Python interpreter at venv\Scripts\python.exe
) else (
    echo WARNING: venv\Scripts\python.exe does not exist!
    echo A virtual environment might need to be created first.
    echo Consider running memory_efficient_rebuild.bat
    echo.
    pause
    exit /b 1
)

echo.
echo Creating/updating .vscode\settings.json with correct Python path...
if not exist ".vscode" mkdir ".vscode"

(
echo {
echo     "terminal.integrated.defaultProfile.windows": "PowerShell",
echo     "terminal.integrated.shellIntegration.enabled": true,
echo     "python.defaultInterpreterPath": "%cd%\\venv\\Scripts\\python.exe",
echo     "python.terminal.activateEnvironment": true,
echo     "python.terminal.activateEnvInCurrentTerminal": true,
echo     "python.analysis.extraPaths": [
echo         "${workspaceFolder}",
echo         "${workspaceFolder}\\arbitrage_bot"
echo     ]
echo }
) > .vscode\settings.json

echo.
echo VS Code settings updated successfully!
echo.
echo Please:
echo 1. Close VSCode completely (all windows)
echo 2. Reopen VSCode at this folder
echo 3. If still having issues, use Ctrl+Shift+P → "Python: Select Interpreter"
echo    and explicitly select "%cd%\venv\Scripts\python.exe"
echo.
echo NOTE: The Shell Integration might need VSCode to be updated 
echo       or PowerShell to be configured correctly.
echo.
pause
exit /b 0