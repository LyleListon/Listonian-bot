"""MCP Server interaction utilities."""

import logging
from typing import Dict, Any, List, Tuple
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)d)')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional

class MCPServer:
    def __init__(self, name: str, command: str, args: List[str]):
        self.name = name
        self.command = command
        self.args = args
        self.process: Optional[asyncio.subprocess.Process] = None
        
    async def start(self):
        """Start the MCP server process."""
        if not self.process:
            try:
                self.process = await asyncio.create_subprocess_exec(
                    self.command,
                    *self.args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                logger.info(f"Started MCP server {self.name}")
            except Exception as e:
                logger.error(f"Failed to start MCP server {self.name}: {e}")
                raise
            
    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
                logger.info(f"Stopped MCP server {self.name}")
            except:
                pass
            finally:
                self.process = None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                if not self.process:
                    await self.start()
                    # Wait for server to initialize
                    await asyncio.sleep(1)
                
                request = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": 1
                }

                logger.info(f"Sending request to {self.name}: {request}")

                # Write request
                if not self.process or not self.process.stdin:
                    raise Exception("Process not ready")

                self.process.stdin.write(json.dumps(request).encode() + b"\n")
                await self.process.stdin.drain()
                
                # Read response
                if not self.process or not self.process.stdout:
                    raise Exception("Process not ready")

                response = await self.process.stdout.readline()
                if not response:
                    raise Exception("No response from MCP server")

                logger.info(f"Raw response from {self.name}: {response}")

                # Parse response
                try:
                    result = json.loads(response)
                    logger.info(f"Parsed JSON response: {result}")
                    
                    if "error" in result:
                        raise Exception(f"MCP error: {result['error']}")
                    
                    if "result" not in result or "content" not in result["result"]:
                        raise Exception(f"Invalid response format: {result}")
                    
                    content = result["result"]["content"]
                    if not content or not isinstance(content, list) or not content:
                        raise Exception(f"Empty content in response: {result}")
                    
                    if not isinstance(content[0], dict) or "text" not in content[0]:
                        raise Exception(f"Invalid content format: {content[0]}")
                    
                    text = content[0]["text"]
                    logger.info(f"Extracted text content: {text}")
                    
                    if not isinstance(text, str):
                        return text
                    
                    try:
                        data = json.loads(text)
                        logger.info(f"Parsed JSON data: {data}")
                        return data
                    except json.JSONDecodeError:
                        logger.info("Text is not JSON, returning as-is")
                        return text
                        
                except Exception as e:
                    logger.error(f"Error parsing response from {self.name}: {e}")
                    raise

            except Exception as e:
                logger.error(f"Error calling tool {tool_name} on {self.name} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    # Try to restart the server
                    await self.stop()
                    continue
                raise

# Global MCP server instances
mcp_servers: Dict[str, MCPServer] = {
    "crypto-price": MCPServer(
        "crypto-price",
        "node",
        ["C:/Users/listonianapp/Documents/Cline/MCP/crypto-price-server/build/index.js"]
    ),
    "market-analysis": MCPServer(
        "market-analysis",
        "node",
        ["C:/Users/listonianapp/Documents/Cline/MCP/market-analysis-server/build/index.js"]
    )
}

async def use_mcp_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Use an MCP tool.
    
    Args:
        server_name (str): Name of the MCP server
        tool_name (str): Name of the tool to use
        arguments (Dict[str, Any]): Tool arguments
        
    Returns:
        Any: Tool response
    """
    try:
        if server_name not in mcp_servers:
            raise Exception(f"Unknown MCP server: {server_name}")
            
        server = mcp_servers[server_name]
        response = await server.call_tool(tool_name, arguments)
        
        if not response:
            logger.error(f"Empty response from {server_name}")
            return None

        # Add debug logging
        logger.info(f"MCP response from {server_name}: {response}")

        return response
        
    except Exception as e:
        logger.error(f"Failed to use MCP tool {tool_name} on {server_name}: {e}")
        raise
