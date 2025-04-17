# MCP Server Setup Guide

This guide will help you properly set up and configure MCP (Model Context Protocol) servers for your Listonian bot project, avoiding common JSON format errors.

## Understanding MCP Configuration Files

There are thre4t
1. `mcp_settings.json` - Main configuration file used by Cline
2. `.roo/mcp.json` - Configuration used by Roo
3. `.augment/mcp_config.json` - Additional configuration

For proper operation, these files should have consistent configurations.

## Proper JSON Format for MCP Servers

Each MCP server configuration should follow this structure:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["path/to/script.py"],
      "env": {
        "ENV_VAR_NAME": "${ENV_VAR_NAME}"
      },
      "description": "Description of what the server does"
    }
  }
}
```

### Key Components:

- **server-name**: A unique identifier for the server (e.g., "brave-search")
- **command**: The command to run the server (usually "python")
- **args**: An array of arguments to pass to the command
- **env**: Environment variables needed by the server
- **description**: A brief description of the server's functionality

## Environment Variables

Environment variables should be defined in your `.env` file with proper formatting:

```
VARIABLE_NAME="value"
```

Note the quotes around the value, which helps prevent parsing issues.

## Adding a New MCP Server

To add a new MCP server:

1. Create your server implementation in the `mcp_servers` directory
2. Update your `.env` file with any required API keys or credentials
3. Add the server configuration to `mcp_settings.json`

Example:

```json
"new-server": {
  "command": "python",
  "args": ["mcp_servers/new_server/run_new_server_mcp.py"],
  "env": {
    "API_KEY": "${API_KEY}"
  },
  "description": "Description of the new server"
}
```

## Troubleshooting JSON Format Errors

If you encounter JSON format errors:

1. Verify all JSON files have proper syntax (commas, brackets, quotes)
2. Ensure environment variables are properly defined in `.env`
3. Check that the server paths in the `args` array are correct
4. Make sure there are no trailing commas in your JSON objects

## Using MCP Servers in Your Code

Once properly configured, you can use your MCP servers with:

```python
<use_mcp_tool>
<server_name>server-name</server_name>
<tool_name>tool-name</tool_name>
<arguments>
{
  "param1": "value1",
  "param2": "value2"
}
</arguments>
</use_mcp_tool>
```

## Current Available Servers

1. **brave-search**: Provides access to the Brave Search API for web searches
2. **crypto-price**: Provides cryptocurrency price data and market information

Each server offers specific tools that can be used in your trading bot to enhance its capabilities.

## Testing MCP Servers

To test if your MCP server is working correctly, you can use the provided test script:

```bash
python test_brave_search_mcp.py
```

This script will:
1. Start the MCP server
2. Send a server_info request to get information about the server
3. Send a tool_call request to perform a web search
4. Display the search results
5. Terminate the server

If the test is successful, you should see search results displayed in the console.

## Troubleshooting

If you encounter issues with MCP servers, try the following:

1. **Configuration Issues**:
   - Run `python test_mcp_config.py` to validate your configuration files
   - Ensure all configuration files (mcp_settings.json, .roo/mcp.json, .augment/mcp_config.json) are consistent
   - Check that all referenced script files exist

2. **Environment Variables**:
   - Make sure your .env file contains all required environment variables
   - Verify that the values are properly formatted with quotes

3. **Connection Issues**:
   - If you get a "Not connected" error when using the MCP tool, try restarting Cline
   - Ensure the MCP server is properly registered with Cline
   - Check if there are any firewall or network issues blocking the connection

4. **Script Errors**:
   - Look for error messages in the console when running the MCP server
   - Check the logs for any exceptions or error messages
   - Verify that all required Python packages are installed

5. **Manual Testing**:
   - Use the test_brave_search_mcp.py script to test the server directly
   - If the test script works but Cline can't connect, the issue might be with Cline's configuration