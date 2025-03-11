@echo off
setlocal enabledelayedexpansion

echo ===============================================================================
echo                     ARBITRAGE SYSTEM SETUP WIZARD
echo ===============================================================================
echo.
echo This script will automate the setup process for the arbitrage bot system.
echo It will:
echo  - Check Python installation
echo  - Setup a virtual environment
echo  - Install required dependencies
echo  - Create configuration files
echo  - Validate the setup
echo.
echo -------------------------------------------------------------------------------
echo.

REM Check if Python is installed
echo [1/6] Checking Python installation...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo and ensure it's added to your PATH.
    goto end
) else (
    python --version
    echo [SUCCESS] Python is installed.
)
echo.

REM Check pip installation
echo [2/6] Checking pip installation...
python -m pip --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] pip is not installed or not working properly.
    echo.
    echo Installing pip...
    python -m ensurepip --upgrade
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install pip. Please install it manually.
        goto end
    )
)
echo [SUCCESS] pip is installed.
echo.

REM Setup virtual environment
echo [3/6] Setting up virtual environment...
if exist venv (
    echo Virtual environment already exists.
    set /p recreate="Do you want to recreate it? (y/n): "
    if /i "!recreate!"=="y" (
        echo Recreating virtual environment...
        rmdir /s /q venv
        python -m venv venv
    )
) else (
    echo Creating new virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate virtual environment.
    goto end
)
echo [SUCCESS] Virtual environment is setup and activated.
echo.

REM Install dependencies
echo [4/6] Installing dependencies...
echo This may take several minutes depending on your internet connection.
echo.

echo Installing core dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some dependencies failed to install.
    set /p continue="Do you want to continue anyway? (y/n): "
    if /i NOT "!continue!"=="y" goto end
)

echo Installing development dependencies...
pip install -r requirements-dev.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some development dependencies failed to install.
    echo This is not critical for running the system, but may affect development tools.
)

echo Installing additional dependencies for monitoring dashboard...
pip install aiohttp aiofiles pandas matplotlib
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some dashboard dependencies failed to install.
    echo This may affect the monitoring dashboard functionality.
)

echo [SUCCESS] Dependencies installed.
echo.

REM Create configuration directories if they don't exist
echo [5/6] Setting up configuration...
if not exist configs mkdir configs
if not exist monitoring_data mkdir monitoring_data
if not exist logs mkdir logs
if not exist analytics mkdir analytics

REM Create basic configuration file if it doesn't exist
if not exist configs\config.json (
    echo Creating default configuration file...
    echo Creating configs\config.json
    echo {> configs\config.json
    echo   "provider_url": "YOUR_ETHEREUM_NODE_URL",>> configs\config.json
    echo   "chain_id": 1,>> configs\config.json
    echo   "private_key": "YOUR_PRIVATE_KEY",>> configs\config.json
    echo   "wallet_address": "YOUR_WALLET_ADDRESS",>> configs\config.json
    echo   "log_level": "INFO",>> configs\config.json
    echo   "max_paths_to_check": 100,>> configs\config.json
    echo   "min_profit_threshold": 0.001,>> configs\config.json
    echo   "slippage_tolerance": 50,>> configs\config.json
    echo   "gas_limit_buffer": 20,>> configs\config.json
    echo.>> configs\config.json
    echo   "tokens": {>> configs\config.json
    echo     "WETH": {>> configs\config.json
    echo       "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",>> configs\config.json
    echo       "decimals": 18>> configs\config.json
    echo     },>> configs\config.json
    echo     "USDC": {>> configs\config.json
    echo       "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",>> configs\config.json
    echo       "decimals": 6>> configs\config.json
    echo     }>> configs\config.json
    echo   },>> configs\config.json
    echo.>> configs\config.json
    echo   "flash_loans": {>> configs\config.json
    echo     "enabled": true,>> configs\config.json
    echo     "use_flashbots": true,>> configs\config.json
    echo     "min_profit_basis_points": 200,>> configs\config.json
    echo     "max_trade_size": "1",>> configs\config.json
    echo     "slippage_tolerance": 50,>> configs\config.json
    echo     "transaction_timeout": 180,>> configs\config.json
    echo     "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",>> configs\config.json
    echo     "contract_address": {>> configs\config.json
    echo       "mainnet": "YOUR_DEPLOYED_CONTRACT_ADDRESS",>> configs\config.json
    echo       "testnet": "YOUR_TESTNET_CONTRACT_ADDRESS">> configs\config.json
    echo     }>> configs\config.json
    echo   },>> configs\config.json
    echo.>> configs\config.json
    echo   "flashbots": {>> configs\config.json
    echo     "relay_url": "https://relay.flashbots.net",>> configs\config.json
    echo     "auth_signer_key": "YOUR_FLASHBOTS_AUTH_KEY",>> configs\config.json
    echo     "min_profit_threshold": 1000000000000000>> configs\config.json
    echo   },>> configs\config.json
    echo.>> configs\config.json
    echo   "mev_protection": {>> configs\config.json
    echo     "enabled": true,>> configs\config.json
    echo     "use_flashbots": true,>> configs\config.json
    echo     "max_bundle_size": 5,>> configs\config.json
    echo     "max_blocks_ahead": 3,>> configs\config.json
    echo     "min_priority_fee": "1.5",>> configs\config.json
    echo     "max_priority_fee": "3",>> configs\config.json
    echo     "sandwich_detection": true,>> configs\config.json
    echo     "frontrun_detection": true,>> configs\config.json
    echo     "adaptive_gas": true>> configs\config.json
    echo   }>> configs\config.json
    echo }>> configs\config.json

    echo.
    echo Configuration file created. You need to update the following values:
    echo  - provider_url: Your Ethereum node URL
    echo  - private_key: Your wallet private key
    echo  - wallet_address: Your wallet address
    echo  - flash_loans.contract_address: Your deployed contract addresses
    echo  - flashbots.auth_signer_key: Your Flashbots auth key
    echo.
)

REM Create monitor config
if not exist configs\monitor_config.json (
    echo Creating monitor configuration file...
    echo Creating configs\monitor_config.json
    echo {> configs\monitor_config.json
    echo   "host": "localhost",>> configs\monitor_config.json
    echo   "port": 8080,>> configs\monitor_config.json
    echo   "refresh_interval": 30,>> configs\monitor_config.json
    echo   "data_directory": "monitoring_data",>> configs\monitor_config.json
    echo   "metrics_history_size": 100,>> configs\monitor_config.json
    echo   "charts_enabled": true,>> configs\monitor_config.json
    echo   "alerts_enabled": true,>> configs\monitor_config.json
    echo   "profit_threshold_alert": 0.001,>> configs\monitor_config.json
    echo   "gas_price_threshold_alert": 150,>> configs\monitor_config.json
    echo   "mev_risk_threshold_alert": "high">> configs\monitor_config.json
    echo }>> configs\monitor_config.json
)

echo [SUCCESS] Configuration files created.
echo.

REM Validate installation
echo [6/6] Validating installation...

echo Checking core modules...
python -c "import arbitrage_bot" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Failed to import arbitrage_bot module. 
    echo This may indicate an installation issue.
) else (
    echo Core modules validated.
)

echo Checking dashboard module...
python -c "import dashboard" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Failed to import dashboard module.
    echo This may affect the monitoring dashboard functionality.
) else (
    echo Dashboard module validated.
)

echo.
echo ===============================================================================
echo                     ARBITRAGE SYSTEM SETUP COMPLETE
echo ===============================================================================
echo.
echo Your arbitrage system has been set up successfully!
echo.
echo Next steps:
echo 1. Edit configs\config.json with your actual configuration values
echo 2. Run the system using: powershell -ExecutionPolicy Bypass -File .\run_example.ps1
echo.
echo Optionally:
echo - Read cline_docs\startup_guide_complete.md for detailed instructions
echo - Check cline_docs\arbitrage_integration_guide.md for integration details
echo - See DOCKER_AI_INTEGRATION.md for future AI enhancements
echo.
echo Do you want to update your configuration file now?
set /p configure="Edit config.json now? (y/n): "
if /i "%configure%"=="y" (
    notepad configs\config.json
)

echo.
echo Do you want to launch the system now?
set /p launch="Launch the system now? (y/n): "
if /i "%launch%"=="y" (
    powershell -ExecutionPolicy Bypass -File .\run_example.ps1
)

:end
echo.
echo Press any key to exit...
pause >nul
endlocal