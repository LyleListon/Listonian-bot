@echo off
echo ===== Starting Arbitrage Bot System =====

echo.
echo Step 1: Checking .env file...
if not exist .env (
    echo Error: .env file not found
    echo Creating a sample .env file...
    (
        echo # Base Network RPC URL (Required)
        echo BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY
        echo.
        echo # Wallet Configuration (Required)
        echo PRIVATE_KEY=YOUR_PRIVATE_KEY
        echo WALLET_ADDRESS=YOUR_WALLET_ADDRESS
        echo PROFIT_RECIPIENT=YOUR_WALLET_ADDRESS
        echo.
        echo # Flashbots Configuration (Required)
        echo FLASHBOTS_AUTH_KEY=YOUR_FLASHBOTS_KEY
        echo.
        echo # API Keys (Required)
        echo ALCHEMY_API_KEY=YOUR_API_KEY
        echo.
        echo # Optional Configuration
        echo LOG_LEVEL=INFO
        echo DASHBOARD_ENABLED=true
        echo DASHBOARD_PORT=9050
        echo.
        echo # Memory Bank Path for Dashboard
        echo MEMORY_BANK_PATH=./memory-bank
    ) > .env
    echo Sample .env file created. Please edit it with your actual values.
    notepad .env
    echo Please restart this script after editing the .env file.
    pause
    exit /b 1
)

echo .env file found

echo.
echo Step 2: Fixing memory bank data...
python fix_memory_bank.py
if %ERRORLEVEL% NEQ 0 (
    echo Error fixing memory bank data
    pause
    exit /b 1
)

echo.
echo Step 3: Starting dashboard...
start "Dashboard" cmd /c "python run_dashboard.py"
echo Dashboard started in a new window

echo.
echo Step 4: Starting arbitrage bot...
start "Arbitrage Bot" cmd /c "python run_bot.py"
echo Arbitrage bot started in a new window

echo.
echo Step 5: Opening dashboard in browser...
timeout /t 5 /nobreak
start http://localhost:9050

echo.
echo ===== System started successfully =====
echo Dashboard URL: http://localhost:9050
echo.
echo Press any key to exit this window (components will continue running)
pause > nul
