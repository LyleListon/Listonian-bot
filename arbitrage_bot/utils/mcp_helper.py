"""MCP (Model Context Protocol) helper utilities."""

import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path
import subprocess
from ..utils.config_loader import load_config
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)

# Cache for MCP clients
_mcp_clients: Dict[str, Any] = {}


class MockClient:
    """Mock MCP client for testing."""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.connected = True

    def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock tool calls with predefined responses."""
        if tool_name == "get_prices":
            return {"data": {"bitcoin": 50000.0, "ethereum": 3000.0}}
        elif tool_name == "analyze_opportunities":
            return {
                "data": {"success_rate": 0.85, "avg_profit": 0.02, "risk_score": 0.3}
            }
        return {"data": {}}

    def access_resource(self, uri: str) -> Dict[str, Any]:
        """Mock resource access."""
        return {"data": {}}

    def close(self):
        """Close mock connection."""
        self.connected = False


def get_mcp_client(server_name: str) -> Any:
    """
    Get MCP client for specified server.

    Args:
        server_name (str): Name of MCP server to connect to

    Returns:
        Any: MCP client instance
    """
    global _mcp_clients

    if server_name in _mcp_clients:
        return _mcp_clients[server_name]

    try:
        # Try loading from Claude.app MCP settings first
        mcp_settings_path = Path(r"c:\Users\listonianapp\AppData\Roaming\Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\cline_mcp_settings.json")
        if mcp_settings_path.exists():
            try:
                with open(mcp_settings_path, 'r') as f:
                    mcp_settings = json.load(f)
                if "mcpServers" in mcp_settings and server_name in mcp_settings["mcpServers"]:
                    server_config = mcp_settings["mcpServers"][server_name]
                    # Create MCP client using server config
                    # Start the MCP server process
                    process = subprocess.Popen(
                        [server_config['command']] + server_config['args'],
                        env=server_config.get('env', {}),
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        text=True
                    )
                    client = MCPClient(process)
                    _mcp_clients[server_name] = client
                    logger.info(f"Created MCP client for {server_name} from Claude.app settings")
                    return client
            except Exception as e:
                logger.error(f"Failed to load Claude.app MCP settings: {e}")

        # Fallback to config.json
        config = load_config()
        if "mcp" not in config or server_name not in config["mcp"]:
            raise ValueError(f"No configuration found for MCP server: {server_name}")

        # Create client based on server type
        if server_name == "crypto-price":
            client = create_crypto_price_client(server_config)
        elif server_name == "market-analysis":
            client = create_market_analysis_client(server_config)
        else:
            raise ValueError(f"Unknown MCP server type: {server_name}")

        _mcp_clients[server_name] = client
        logger.info(f"Created MCP client for {server_name}")
        return client

    except Exception as e:
        logger.error(f"Failed to create MCP client for {server_name}: {e}")
        raise


def create_crypto_price_client(config: Dict[str, Any]) -> Any:
    """
    Create crypto price MCP client.

    Args:
        config (Dict[str, Any]): Server configuration

    Returns:
        Any: Crypto price client instance
    """
    try:
        client = MockClient(name="crypto-price-client", version="0.1.0")
        return client
    except Exception as e:
        logger.error(f"Failed to create crypto price client: {e}")
        raise


def create_market_analysis_client(config: Dict[str, Any]) -> Any:
    """
    Create market analysis MCP client.

    Args:
        config (Dict[str, Any]): Server configuration

    Returns:
        Any: Market analysis client instance
    """
    try:
        client = MockClient(name="market-analysis-client", version="0.1.0")
        return client
    except Exception as e:
        logger.error(f"Failed to create market analysis client: {e}")
        raise


def close_mcp_clients():
    """Close all MCP client connections."""
    global _mcp_clients

    for name, client in _mcp_clients.items():
        try:
            client.close()
            logger.info(f"Closed MCP client for {name}")
        except Exception as e:
            logger.error(f"Error closing MCP client for {name}: {e}")

    _mcp_clients = {}


def call_mcp_tool(
    server_name: str, tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Call MCP tool with arguments.

    Args:
        server_name (str): Name of MCP server
        tool_name (str): Name of tool to call
        arguments (Dict[str, Any]): Tool arguments

    Returns:
        Dict[str, Any]: Tool response
    """
    try:
        client = get_mcp_client(server_name)
        response = client.call_tool(tool_name, arguments)
        return response
    except Exception as e:
        logger.error(f"Failed to call MCP tool {tool_name} on {server_name}: {e}")
        raise


def access_mcp_resource(server_name: str, uri: str) -> Dict[str, Any]:
    """
    Access MCP resource.

    Args:
        server_name (str): Name of MCP server
        uri (str): Resource URI

    Returns:
        Dict[str, Any]: Resource data
    """
    try:
        client = get_mcp_client(server_name)
        response = client.access_resource(uri)
        return response
    except Exception as e:
        logger.error(f"Failed to access MCP resource {uri} on {server_name}: {e}")
        raise
