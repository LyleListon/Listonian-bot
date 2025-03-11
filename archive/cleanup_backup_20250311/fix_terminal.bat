@echo off
echo ======================================================
echo Terminal Diagnostics and Repair Tool
echo ======================================================
echo.
echo This script will diagnose terminal issues and attempt to fix them.
echo Running from: %~dp0
echo.

echo [Step 1] Verifying PowerShell installation...
where powershell >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell not found in PATH
) else (
    echo PowerShell found in PATH
    for /f "tokens=*" %%a in ('where powershell') do echo Location: %%a
)

echo.
echo [Step 2] Checking PowerShell 7 installation...
where pwsh >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: PowerShell 7 (pwsh.exe) not found in PATH
    echo This may cause issues with VSCode terminal integration
) else (
    echo PowerShell 7 found in PATH
    for /f "tokens=*" %%a in ('where pwsh') do echo Location: %%a
    
    echo.
    echo Checking PowerShell 7 version:
    pwsh -Command "$PSVersionTable.PSVersion" 2>nul
)

echo.
echo [Step 3] Checking Python environment...
echo Python executable:
where python 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Python not found in PATH
) else (
    echo Python version:
    python --version 2>nul
    
    echo.
    echo Python location:
    for /f "tokens=*" %%a in ('where python') do echo %%a
    
    echo.
    echo Checking virtual environment:
    if exist "%~dp0venv\Scripts\python.exe" (
        echo Virtual environment exists at %~dp0venv
    ) else (
        echo WARNING: Virtual environment not found at expected location
        echo Expected: %~dp0venv\Scripts\python.exe
    )
)

echo.
echo [Step 4] Checking VSCode terminal settings...
if exist "C:\Users\listonianapp\AppData\Roaming\Code\User\settings.json" (
    echo VSCode settings file exists
    echo Checking terminal profiles:
    
    powershell -Command "& {$settings = Get-Content 'C:\Users\listonianapp\AppData\Roaming\Code\User\settings.json' -Raw | ConvertFrom-Json; if ($settings.'terminal.integrated.profiles.windows') { Write-Host 'Terminal profiles found'; } else { Write-Host 'WARNING: No terminal profiles configured in settings.json'; }}" 2>nul
) else (
    echo WARNING: VSCode settings file not found
)

echo.
echo [Step 5] Testing terminal functionality...
echo Running basic command test:
echo Command: dir
dir >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Basic 'dir' command failed
) else (
    echo Basic command test passed
)

echo.
echo [Step 6] Attempting to repair terminal settings...
echo Creating PowerShell profile directory if it doesn't exist:
if not exist "C:\Users\listonianapp\Documents\WindowsPowerShell" (
    mkdir "C:\Users\listonianapp\Documents\WindowsPowerShell" 2>nul
    echo Created WindowsPowerShell directory
) else (
    echo WindowsPowerShell directory already exists
)

echo.
echo Setting PowerShell execution policy to RemoteSigned for current user:
powershell -Command "& {Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force; Write-Host 'Execution policy set to RemoteSigned'}" 2>nul

echo.
echo [Step 7] Checking for terminal process conflicts...
echo Listing PowerShell and cmd processes:
powershell -Command "& {Get-Process -Name '*cmd*','*powershell*','*pwsh*' | Format-Table Name, Id, Path -AutoSize}" 2>nul

echo.
echo ======================================================
echo Repair Actions
echo ======================================================
echo.
echo The following actions can help fix terminal issues:
echo.
echo 1) Reset VSCode terminal settings:
echo    - Press Ctrl+Shift+P in VSCode
echo    - Type "Terminal: Select Default Profile"
echo    - Choose "Command Prompt" or "PowerShell"
echo.
echo 2) Try running the terminal as administrator once:
echo    - Right-click on Command Prompt or PowerShell in Start Menu
echo    - Select "Run as administrator"
echo    - Close after successful launch
echo.
echo 3) Ensure PowerShell 7 is properly installed:
echo    - Download from: https://github.com/PowerShell/PowerShell/releases
echo.
echo 4) Update VSCode settings to use correct terminal:
echo.
echo Here's a starting configuration to add to settings.json:
echo.
echo {
echo   "terminal.integrated.defaultProfile.windows": "Command Prompt",
echo   "terminal.integrated.profiles.windows": {
echo     "PowerShell": {
echo       "path": "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
echo       "args": ["-NoLogo"]
echo     },
echo     "Command Prompt": {
echo       "path": "C:\\Windows\\System32\\cmd.exe"
echo     }
echo   }
echo }
echo.
echo ======================================================
echo.
echo Diagnostic report complete.
echo If terminal still doesn't work, please try using Command Prompt:
echo 1) Open a Command Prompt window outside of VS Code
echo 2) Navigate to the project directory: cd %~dp0
echo 3) Run the Python script: python test_path_finder.py
echo.
echo Press any key to exit...
pause >nul