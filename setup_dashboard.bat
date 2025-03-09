@echo off
echo ========================================================
echo SETTING UP DASHBOARD ENVIRONMENT
echo ========================================================
echo.

echo Installing required packages directly...
pip install fastapi uvicorn jinja2 python-dotenv web3 pydantic

echo.
echo Creating required directories...
mkdir new_dashboard\static 2>nul
mkdir new_dashboard\static\css 2>nul
mkdir new_dashboard\static\js 2>nul
mkdir new_dashboard\templates 2>nul
mkdir logs 2>nul
mkdir data 2>nul
mkdir data\performance 2>nul
mkdir data\transactions 2>nul

echo.
echo Creating basic .env file...
echo BASE_RPC_URL=https://mainnet.base.org > new_dashboard\.env
echo WALLET_ADDRESS=0x0000000000000000000000000000000000000000 >> new_dashboard\.env

echo.
echo Setup complete! Now run the simplified dashboard script.
echo.
echo ========================================================
echo Press any key to start the dashboard...
pause >nul

echo Starting simplified dashboard...
cd new_dashboard
python app.py --debug
cd ..