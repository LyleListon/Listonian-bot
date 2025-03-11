@echo off
REM Glama AI Enhanced Strategy MCP Server Runner for Listonian Arbitrage Bot
REM This script launches the Glama AI MCP server for AI-enhanced arbitrage strategies.
REM Version: 1.0.0

echo =======================================================
echo Starting Glama AI MCP Server for Enhanced Arbitrage Strategies
echo =======================================================

REM Ensure Python environment is activated
call fixed_rebuild_venv.bat >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate Python virtual environment
    exit /b 1
)

REM Check if Glama AI credentials are configured
python -c "import os; print('Glama AI credentials configured' if os.path.exists('secure/glama_ai_credentials.json') else 'Glama AI credentials NOT configured')"
if %ERRORLEVEL% neq 0 (
    echo Error: Please run setup_mcp_keys.bat first to configure Glama AI credentials
    exit /b 1
)

echo ----------------------------------------
echo Starting Glama AI MCP server...
echo ----------------------------------------

REM Launch the Glama AI MCP server
python -m mcp_servers.glama.server

echo ----------------------------------------
echo Glama AI MCP server has been terminated
echo ----------------------------------------

echo To use Glama AI enhanced strategies, see examples/glama_enhanced_strategy.py