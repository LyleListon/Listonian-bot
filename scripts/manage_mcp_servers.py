#!/usr/bin/env python3
"""
MCP Server Manager

This script provides a command-line interface to manage MCP servers.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import MCP helper
try:
    from .augment.mcp_helper import (
        load_mcp_config,
        start_mcp_server,
        stop_mcp_server,
        list_mcp_servers,
        stop_all_mcp_servers
    )
except ImportError:
    sys.path.insert(0, str(project_root / ".augment"))
    from mcp_helper import (
        load_mcp_config,
        start_mcp_server,
        stop_mcp_server,
        list_mcp_servers,
        stop_all_mcp_servers
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_manager")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Manage MCP servers")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all MCP servers")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start an MCP server")
    start_parser.add_argument("server", help="Name of the server to start")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop an MCP server")
    stop_parser.add_argument("server", help="Name of the server to stop")
    
    # Start all command
    start_all_parser = subparsers.add_parser("start-all", help="Start all MCP servers")
    
    # Stop all command
    stop_all_parser = subparsers.add_parser("stop-all", help="Stop all MCP servers")
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == "list":
        # List all servers
        servers = list_mcp_servers()
        if not servers:
            print("No MCP servers found")
            return
        
        print("MCP Servers:")
        for server in servers:
            status_color = "\033[92m" if server["status"] == "running" else "\033[91m"
            reset_color = "\033[0m"
            print(f"- {server['name']}: {status_color}{server['status']}{reset_color} (PID: {server['pid']})")
            print(f"  Description: {server['description']}")
        
    elif args.command == "start":
        # Start a server
        if start_mcp_server(args.server):
            print(f"Started MCP server: {args.server}")
        else:
            print(f"Failed to start MCP server: {args.server}")
            sys.exit(1)
    
    elif args.command == "stop":
        # Stop a server
        if stop_mcp_server(args.server):
            print(f"Stopped MCP server: {args.server}")
        else:
            print(f"Failed to stop MCP server: {args.server}")
            sys.exit(1)
    
    elif args.command == "start-all":
        # Start all servers
        config = load_mcp_config()
        if not config or "mcpServers" not in config:
            print("No MCP servers found in configuration")
            return
        
        success = True
        for server_name in config["mcpServers"]:
            print(f"Starting MCP server: {server_name}")
            if not start_mcp_server(server_name):
                print(f"Failed to start MCP server: {server_name}")
                success = False
            time.sleep(2)  # Wait between server starts
        
        if not success:
            sys.exit(1)
    
    elif args.command == "stop-all":
        # Stop all servers
        if stop_all_mcp_servers():
            print("Stopped all MCP servers")
        else:
            print("Failed to stop all MCP servers")
            sys.exit(1)
    
    else:
        # No command specified, show help
        print("Please specify a command. Use --help for more information.")
        sys.exit(1)

if __name__ == "__main__":
    main()
