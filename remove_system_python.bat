@echo off
echo Removing system-wide Python installation...

REM Uninstall pip from system Python
"C:\Program Files\Python312\python.exe" -m pip uninstall pip -y

REM Open Programs and Features to uninstall Python
control appwiz.cpl

echo.
echo Please uninstall Python 3.12 from Programs and Features.
echo After uninstalling, you may need to restart your computer.
echo.
pause