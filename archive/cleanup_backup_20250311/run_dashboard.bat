@echo off
echo Listonian Arbitrage Dashboard
echo ============================
echo.

set PYTHONPATH=%PYTHONPATH%;%CD%
set CONFIG_PATH=configs/production_config.json

echo 1. Run dashboard with production config
echo 2. Run dashboard with test config
echo 3. Exit

choice /C 123 /N /M "Choose an option: "

if errorlevel 3 goto :exit
if errorlevel 2 goto :test
if errorlevel 1 goto :production

:production
echo.
echo Starting dashboard with production configuration...
python -m dashboard.main --config %CONFIG_PATH%
goto :end

:test
echo.
echo Starting dashboard with test configuration...
set CONFIG_PATH=configs/test_config.json
python -m dashboard.main --config %CONFIG_PATH%
goto :end

:exit
echo.
echo Exiting...
goto :end

:end