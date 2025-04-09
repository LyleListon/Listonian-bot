"""
MCP Helper for Augment Extension

This script provides helper functions for Augment to interact with MCP servers.
"""

import os
import json
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("augment_mcp_helper")

# Global variables
_mcp_processes = {}
_mcp_config = None

def load_mcp_config() -> Dict[str, Any]:
    """Load MCP configuration from .augment/mcp_config.json."""
    global _mcp_config
    
    if _mcp_config is not None:
        return _mcp_config
    
    config_path = Path(".augment/mcp_config.json")
    if not config_path.exists():
        logger.error(f"MCP configuration file not found: {config_path}")
        return {}
    
    try:
        with open(config_path, "r") as f:
            _mcp_config = json.load(f)
        logger.info(f"Loaded MCP configuration from {config_path}")
        return _mcp_config
    except Exception as e:
        logger.error(f"Failed to load MCP configuration: {e}")
        return {}

def start_mcp_server(server_name: str) -> bool:
    """Start an MCP server."""
    global _mcp_processes
    
    # Check if server is already running
    if server_name in _mcp_processes and _mcp_processes[server_name].poll() is None:
        logger.info(f"MCP server {server_name} is already running")
        return True
    
    # Load MCP configuration
    config = load_mcp_config()
    if not config or "mcpServers" not in config or server_name not in config["mcpServers"]:
        logger.error(f"No configuration found for MCP server: {server_name}")
        return False
    
    # Get server configuration
    server_config = config["mcpServers"][server_name]
    
    # Prepare environment variables
    env = os.environ.copy()
    if "env" in server_config:
        for key, value in server_config["env"].items():
            # Replace environment variable placeholders
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                if env_var in os.environ:
                    env[key] = os.environ[env_var]
                else:
                    logger.warning(f"Environment variable {env_var} not found")
            else:
                env[key] = value
    
    # Start the server process
    try:
        command = [server_config["command"]] + server_config["args"]
        logger.info(f"Starting MCP server {server_name}: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        _mcp_processes[server_name] = process
        logger.info(f"MCP server {server_name} started with PID {process.pid}")
        return True
    except Exception as e:
        logger.error(f"Failed to start MCP server {server_name}: {e}")
        return False

def stop_mcp_server(server_name: str) -> bool:
    """Stop an MCP server."""
    global _mcp_processes
    
    if server_name not in _mcp_processes:
        logger.warning(f"MCP server {server_name} is not running")
        return True
    
    try:
        process = _mcp_processes[server_name]
        if process.poll() is None:
            logger.info(f"Stopping MCP server {server_name}")
            process.terminate()
            process.wait(timeout=5)
            
            # Force kill if still running
            if process.poll() is None:
                logger.warning(f"MCP server {server_name} did not terminate gracefully, forcing kill")
                process.kill()
                process.wait(timeout=5)
        
        del _mcp_processes[server_name]
        logger.info(f"MCP server {server_name} stopped")
        return True
    except Exception as e:
        logger.error(f"Failed to stop MCP server {server_name}: {e}")
        return False

def list_mcp_servers() -> List[Dict[str, Any]]:
    """List all MCP servers and their status."""
    global _mcp_processes
    
    config = load_mcp_config()
    if not config or "mcpServers" not in config:
        return []
    
    servers = []
    for name, server_config in config["mcpServers"].items():
        status = "stopped"
        pid = None
        
        if name in _mcp_processes:
            process = _mcp_processes[name]
            if process.poll() is None:
                status = "running"
                pid = process.pid
            else:
                status = "crashed"
                pid = process.pid
        
        servers.append({
            "name": name,
            "status": status,
            "pid": pid,
            "description": server_config.get("description", "")
        })
    
    return servers

def stop_all_mcp_servers() -> bool:
    """Stop all running MCP servers."""
    global _mcp_processes
    
    success = True
    for server_name in list(_mcp_processes.keys()):
        if not stop_mcp_server(server_name):
            success = False
    
    return success

# Register cleanup handler
import atexit
atexit.register(stop_all_mcp_servers)

if __name__ == "__main__":
    # Example usage
    print("MCP Servers:")
    for server in list_mcp_servers():
        print(f"- {server['name']}: {server['status']} (PID: {server['pid']})")
    
    # Start a server
    # start_mcp_server("base-dex-scanner")
