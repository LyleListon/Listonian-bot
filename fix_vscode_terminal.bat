@echo off
echo ======================================================
echo VSCode Terminal Repair Tool
echo ======================================================
echo.

echo Detecting PowerShell location...
where pwsh >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell 7 (pwsh) not found in PATH.
    echo Please install PowerShell 7 from https://github.com/PowerShell/PowerShell/releases
    goto :error
) else (
    for /f "tokens=*" %%a in ('where pwsh') do set PS7_PATH=%%a
    echo Found PowerShell 7 at: %PS7_PATH%
)

echo.
echo Creating VSCode settings backup...
if exist "C:\Users\listonianapp\AppData\Roaming\Code\User\settings.json" (
    copy "C:\Users\listonianapp\AppData\Roaming\Code\User\settings.json" "C:\Users\listonianapp\AppData\Roaming\Code\User\settings.json.bak" >nul
    echo Backup created at C:\Users\listonianapp\AppData\Roaming\Code\User\settings.json.bak
) else (
    echo WARNING: VSCode settings file not found. A new one will be created.
)

echo.
echo Creating updated VSCode terminal settings...
echo This will update your VSCode settings to use PowerShell 7.

echo {
echo   "terminal.integrated.defaultProfile.windows": "PowerShell",
echo   "terminal.integrated.profiles.windows": {
echo     "PowerShell": {
echo       "source": "PowerShell",
echo       "icon": "terminal-powershell",
echo       "path": "%PS7_PATH%"
echo     },
echo     "Command Prompt": {
echo       "path": "C:\\Windows\\System32\\cmd.exe",
echo       "icon": "terminal-cmd"
echo     }
echo   },
echo   "terminal.integrated.automationShell.windows": "%PS7_PATH%",
echo   "terminal.integrated.fontFamily": "Consolas, 'Courier New', monospace",
echo   "terminal.integrated.env.windows": {
echo     "PSExecutionPolicyPreference": "RemoteSigned"
echo   }
echo } > "%TEMP%\vscode_terminal_settings.json"

echo.
echo Applying these settings to VSCode...
powershell -Command "& {
    $settingsPath = 'C:\Users\listonianapp\AppData\Roaming\Code\User\settings.json'
    $newSettings = Get-Content '%TEMP%\vscode_terminal_settings.json' | ConvertFrom-Json
    
    # Create new settings file if it doesn't exist
    if (-not (Test-Path $settingsPath)) {
        $newSettings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath
        Write-Host 'Created new VSCode settings file'
        exit
    }
    
    # Merge with existing settings
    $existingSettings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    
    # Add or update terminal settings
    $existingSettings.'terminal.integrated.defaultProfile.windows' = $newSettings.'terminal.integrated.defaultProfile.windows'
    $existingSettings.'terminal.integrated.profiles.windows' = $newSettings.'terminal.integrated.profiles.windows'
    $existingSettings.'terminal.integrated.automationShell.windows' = $newSettings.'terminal.integrated.automationShell.windows'
    $existingSettings.'terminal.integrated.env.windows' = $newSettings.'terminal.integrated.env.windows'
    
    # Save updated settings
    $existingSettings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath
    Write-Host 'Updated VSCode settings successfully'
}" 2>nul

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to update VSCode settings.
    goto :error
) else (
    echo VSCode settings updated successfully.
)

echo.
echo Setting PowerShell execution policy...
pwsh -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Failed to set PowerShell execution policy.
) else (
    echo PowerShell execution policy set to RemoteSigned.
)

echo.
echo Creating test script to verify PowerShell is working...
echo function Test-PowerShell {
echo     Write-Host "PowerShell is working correctly!"
echo     Write-Host "PowerShell Version: $($PSVersionTable.PSVersion)"
echo     Write-Host "PowerShell Path: $PSHOME"
echo }
echo.
echo Test-PowerShell
echo.
echo exit > "%TEMP%\test_powershell.ps1"

echo.
echo ======================================================
echo Terminal should now be fixed! Please:
echo ======================================================
echo.
echo 1. Restart VSCode completely
echo 2. Open a new terminal in VSCode (Ctrl+`)
echo 3. If terminal still shows blank, try these commands:
echo    - Select the dropdown next to the plus in the terminal
echo    - Choose "Command Prompt" or "PowerShell"
echo.
echo If VSCode terminal is still not working, you can use this batch file to run the path finder test:
echo.

echo @echo off
echo cd /d %~dp0
echo echo Running path finder test...
echo call venv\Scripts\activate.bat
echo python test_path_finder.py --max-tests 10
echo pause > run_path_test.bat

echo Created run_path_test.bat that you can run from Explorer
echo.
echo Press any key to exit...
pause >nul
exit /b 0

:error
echo.
echo Error occurred. Please see messages above.
echo Press any key to exit...
pause >nul
exit /b 1