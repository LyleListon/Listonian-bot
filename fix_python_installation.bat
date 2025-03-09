@echo off
echo ===============================================================================
echo                      Python Installation Fix Script
echo ===============================================================================

echo Step 1: Remove system-wide Python installation
call remove_system_python.bat

echo.
echo Step 2: Update Python PATH settings
call update_python_path.bat

echo.
echo All steps completed. Please restart your computer for changes to take full effect.
echo After restart, only the user-specific Python installation will be available.
echo.
pause