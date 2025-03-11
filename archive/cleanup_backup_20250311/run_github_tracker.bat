@echo off
REM GitHub MCP Server Runner for Listonian Arbitrage Bot
REM This script launches the GitHub MCP server for strategy tracking and version control.
REM Version: 1.0.0

echo =======================================================
echo Starting GitHub MCP Server for Arbitrage Strategy Tracking
echo =======================================================

REM Ensure Python environment is activated
call fixed_rebuild_venv.bat >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate Python virtual environment
    exit /b 1
)

REM Check if GitHub credentials are configured
python -c "import os; print('GitHub credentials configured' if os.path.exists('secure/github_credentials.json') else 'GitHub credentials NOT configured')"
if %ERRORLEVEL% neq 0 (
    echo Error: Please run setup_mcp_keys.bat first to configure GitHub credentials
    exit /b 1
)

echo ----------------------------------------
echo Starting GitHub MCP server...
echo ----------------------------------------

REM Launch the GitHub MCP server
python -m mcp_servers.github.server

echo ----------------------------------------
echo GitHub MCP server has been terminated
echo ----------------------------------------

echo To use GitHub integration in your strategies, see examples/github_tracker_example.py