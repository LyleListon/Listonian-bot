@echo off
echo Running Multi-Path Arbitrage Example...
echo.

rem Set environment variables (replace with appropriate values)
set ETH_RPC_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY
set PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE

rem Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found, using system Python
)

rem Run the example
python examples/multi_path_arbitrage_example.py

rem Deactivate virtual environment if activated
if exist venv\Scripts\activate.bat (
    call venv\Scripts\deactivate.bat
)

echo.
echo Example execution complete.
pause