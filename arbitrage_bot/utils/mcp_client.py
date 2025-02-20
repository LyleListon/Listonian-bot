"""MCP client implementation."""

import json
import logging
from typing import Dict, Any, Optional
from subprocess import Popen, PIPE

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for communicating with MCP servers."""
    
    def __init__(self, process: Popen):
        """Initialize MCP client."""
        self.process = process
        self.request_id = 0

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server."""
        try:
            # Create request
            request = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "callTool",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            self.request_id += 1

            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Read response
            response_str = self.process.stdout.readline()
            response = json.loads(response_str)

            if "error" in response:
                raise Exception(response["error"]["message"])

            return response["result"]

        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            raise

    def access_resource(self, uri: str) -> Dict[str, Any]:
        """Access a resource on the MCP server."""
        try:
            # Create request
            request = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "accessResource",
                "params": {
                    "uri": uri
                }
            }
            self.request_id += 1

            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()

            # Read response
            response_str = self.process.stdout.readline()
            response = json.loads(response_str)

            if "error" in response:
                raise Exception(response["error"]["message"])

            return response["result"]

        except Exception as e:
            logger.error(f"Error accessing MCP resource {uri}: {e}")
            raise

    def close(self):
        """Close the MCP client connection."""
        try:
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.terminate()
            self.process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error closing MCP client: {e}")
            # Force kill if graceful shutdown fails
            self.process.kill()
