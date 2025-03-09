@echo off

REM Open browser automatically when dashboard starts
start "" http://localhost:9097

echo ===============================================================================
echo ENHANCED ARBITRAGE DASHBOARD
echo ===============================================================================
echo This dashboard provides:
echo  - Real-time token prices from Alchemy Price API
echo  - Detailed opportunity tracking for arbitrage trades
echo  - Performance statistics and profit analysis
echo  - Wallet activity monitoring with transaction history
echo.
echo Loads data from:
echo  - .env.production - For API keys (uses your existing Alchemy key)
echo  - config.json - For token and network configuration
echo  - Etherscan API for wallet activity (will simulate if not available)
echo.
echo Features:
echo  - Price comparisons across major DEXes
echo  - Opportunity filtering by trading pair, DEX, and profit
echo  - Real-time success/failure tracking
echo  - Wallet balance and transaction monitoring
echo  - Gas usage statistics
echo.
echo IMPORTANT: 
echo  - If Alchemy API connection fails, the dashboard will use simulated data
echo  - A "SIMULATION MODE" indicator will appear when using simulated data
echo  - Wallet transactions may be simulated if API access is unavailable
echo.
echo Opening http://localhost:9097 in your browser...
echo.
echo Press Ctrl+C to stop the server when done.
echo ===============================================================================

python enhanced_arbitrage_dashboard.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred while running the dashboard
    echo Please check that you have Python installed and all required modules
    echo You may need to install dependencies with: pip install requests python-dotenv
    echo.
    pause
) else (
    echo.
    echo Server stopped.
    echo ===============================================================================
)

pause