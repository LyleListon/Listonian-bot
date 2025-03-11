@echo off
setlocal enabledelayedexpansion
echo Updating Python PATH settings...

REM Remove system Python from PATH
set "OLD_PATH=%PATH%"
set "SYSTEM_PYTHON_PATH=C:\Program Files\Python312;C:\Program Files\Python312\Scripts"
set "NEW_PATH="

REM Build new PATH without system Python
for %%p in ("%OLD_PATH:;=";"%") do (
    set "p=%%~p"
    if not "!p!"=="%SYSTEM_PYTHON_PATH%" (
        if defined NEW_PATH (
            set "NEW_PATH=!NEW_PATH!;!p!"
        ) else (
            set "NEW_PATH=!p!"
        )
    )
)

REM Update user PATH
setx PATH "%NEW_PATH%"

echo.
echo Python PATH has been updated to remove system-wide installation.
echo Please restart your terminal for changes to take effect.
echo.
endlocal
pause