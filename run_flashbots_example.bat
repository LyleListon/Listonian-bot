@echo off
echo ========================================================
echo  Flashbots Flash Loan Arbitrage Example
echo ========================================================
echo.

REM Check if PRIVATE_KEY environment variable is set
if "%PRIVATE_KEY%"=="" (
    echo ERROR: PRIVATE_KEY environment variable not set
    echo Please set your private key using:
    echo.
    echo set PRIVATE_KEY=your_private_key
    echo.
    goto end
)

REM Check if ETH_RPC_URL environment variable is set, use default if not
if "%ETH_RPC_URL%"=="" (
    echo WARNING: ETH_RPC_URL environment variable not set
    echo Using default Goerli endpoint. For production, set:
    echo.
    echo set ETH_RPC_URL=your_ethereum_node_url
    echo.
    set ETH_RPC_URL=https://goerli.infura.io/v3/YOUR_INFURA_KEY
)

echo Using Ethereum RPC URL: %ETH_RPC_URL%
echo.
echo Running Flashbots Flash Loan example...
echo.

REM Run the example
python examples/flashbots_flash_loan_example.py

echo.
echo Example execution completed.

:end
pause