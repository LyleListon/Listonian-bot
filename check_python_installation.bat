@echo off
echo ==========================================
echo Python Installation Diagnostic
echo ==========================================
echo.

echo Checking for Python installations:
echo.

echo Looking for Python 3.12...
where python
echo.

echo Python version information:
python --version
echo.

echo Checking PATH environment variable:
echo %PATH%
echo.

echo Checking current directory:
cd
echo.

echo Environment diagnostic complete.
echo.
pause