@echo off
echo Removing Windows Store Python app link...

REM Remove Windows Store Python app link
del "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
del "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe"

echo.
echo Windows Store Python app links have been removed.
echo.
pause