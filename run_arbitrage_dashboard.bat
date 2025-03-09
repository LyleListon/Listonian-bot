@echo off

REM Open browser automatically when dashboard starts
start "" http://localhost:9097

echo ===============================================================================
echo ARBITRAGE DASHBOARD - OPPORTUNITY TRACKER
echo ===============================================================================
echo This dashboard provides:
echo  - Real-time token prices from Alchemy Price API
echo  - Detailed opportunity tracking for arbitrage trades
echo  - Performance statistics and profit analysis
echo.
echo Loads data from:
echo  - .env.production - For API keys (uses your existing Alchemy key)
echo  - config.json - For token and network configuration
echo.
echo Features:
echo  - Price comparisons across major DEXes
echo  - Opportunity filtering by trading pair, DEX, and profit
echo  - Real-time success/failure tracking
echo.
echo IMPORTANT: 
echo  - If Alchemy API connection fails, the dashboard will use simulated data
echo  - A "SIMULATION MODE" indicator will appear when using simulated data
echo.
echo Opening http://localhost:9097 in your browser...
echo.
echo Press Ctrl+C to stop the server when done.
echo ===============================================================================

python arbitrage_dashboard.py

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