@echo off
echo Listonian Arbitrage Bot
echo =====================
echo.

set CONFIG_PATH=configs/production_config.json

echo 1. Run with new arbitrage system architecture
echo 2. Run with legacy arbitrage system
echo 3. Exit

choice /C 123 /N /M "Choose an option: "

if errorlevel 3 goto :exit
if errorlevel 2 goto :legacy
if errorlevel 1 goto :new

:new
echo.
echo Starting arbitrage system with new architecture...
python -m arbitrage_bot.production --config %CONFIG_PATH%
goto :end

:legacy
echo.
echo Starting arbitrage system with legacy architecture...
python -m arbitrage_bot.production --config %CONFIG_PATH% --legacy
goto :end

:exit
echo.
echo Exiting...
goto :end

:end