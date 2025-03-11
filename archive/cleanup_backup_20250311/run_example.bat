@echo off
echo ================================================================
echo Arbitrage System Example Launcher
echo ================================================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python not found. Please install Python and try again.
    goto end
)

REM If an argument is provided, use it as the example to run
if "%~1"=="" (
    echo Available examples:
    echo.
    echo 1. Complete Arbitrage Example
    echo 2. Flash Loan Example
    echo 3. MEV Protection Example
    echo 4. Monitoring Dashboard
    echo 5. Run Tests
    echo.
    set /p choice="Enter your choice (1-5): "
) else (
    set choice=%1
)

echo.
echo ================================================================

if "%choice%"=="1" (
    echo Running Complete Arbitrage Example...
    echo.
    python complete_arbitrage_example.py
    goto end
)

if "%choice%"=="2" (
    echo Running Flash Loan Example...
    echo.
    python flash_loan_example.py
    goto end
)

if "%choice%"=="3" (
    echo Running MEV Protection Example...
    echo.
    python mev_protection_example.py
    goto end
)

if "%choice%"=="4" (
    echo Starting Monitoring Dashboard...
    echo The dashboard will be available at http://localhost:8080
    echo.
    if not exist "monitoring_data" mkdir "monitoring_data"
    start "" http://localhost:8080
    python -m dashboard.arbitrage_monitor
    goto end
)

if "%choice%"=="5" (
    echo Running Tests...
    echo.
    pytest tests/flashbots_flash_loan_test.py -v
    goto end
)

echo Invalid choice. Please try again.

:end
echo.
echo ================================================================
echo Press any key to exit...
pause >nul