@echo off
echo ===============================================================================
echo ALCHEMY PRICE API DASHBOARD
echo ===============================================================================
echo.
echo This dashboard displays real-time token prices from Alchemy's Price API.
echo It shows prices across multiple exchanges for a variety of tokens.
echo.
echo Before running this dashboard, you need to set up your Alchemy API key:
echo.
echo 1. Get a free API key from https://www.alchemy.com
echo 2. Set it as an environment variable:
echo    setx ALCHEMY_API_KEY "your-api-key-here"
echo.
echo Starting Alchemy Price dashboard...
echo.
echo OPEN THIS URL IN YOUR BROWSER: http://localhost:9097
echo.
echo Press Ctrl+C to stop the server when done.
echo.

python alchemy_price_dashboard.py

echo.
echo Server stopped.
echo ===============================================================================
pause