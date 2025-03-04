@echo off
echo Setting up MCP API Keys for Listonian Arbitrage Bot
echo =================================================
echo.
echo This script will guide you through the process of setting up API keys for:
echo - GitHub MCP server (requires GitHub Personal Access Token)
echo - Glama.ai MCP server (requires OpenAI API key and Glama.ai API key)
echo.
echo IMPORTANT: Your API keys will be stored securely in your MCP settings file.
echo No API keys are shared with external services other than the ones you configure.
echo.
echo Press any key to continue...
pause > nul

python setup_mcp_keys.py

echo.
echo Setup complete. Press any key to exit...
pause > nul