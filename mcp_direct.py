#!/usr/bin/env python3
"""
Direct MCP Client

A simple client for directly communicating with any MCP server using JSON input.
"""

import json
import sys
import subprocess

def main():
    if len(sys.argv) < 3:
        print("Usage: python mcp_direct.py <server_command> <server_args> <json_request>")
        print("Example: python mcp_direct.py npx '-y @modelcontextprotocol/server-filesystem /home/lylepaul78' '{\"type\":\"tool_call\",\"request_id\":\"req1\",\"tool_name\":\"read_file\",\"arguments\":{\"path\":\"/path/to/file\"}}'")
        return
    
    # Parse command line arguments
    server_command = sys.argv[1]
    server_args = sys.argv[2].split()
    json_request = sys.argv[3]
    
    # Start the MCP server process
    command = [server_command] + server_args
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        # Send the request
        process.stdin.write(json_request + "\n")
        process.stdin.flush()
        
        # Read the response
        response_line = process.stdout.readline()
        try:
            response = json.loads(response_line)
            print(json.dumps(response, indent=2))
        except json.JSONDecodeError:
            print(f"Error decoding JSON response: {response_line}")
    
    finally:
        # Close the process
        process.terminate()
        process.wait(timeout=5)
        if process.poll() is None:
            process.kill()

if __name__ == "__main__":
    main()