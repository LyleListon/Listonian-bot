#!/usr/bin/env python3
"""
MCP Filesystem Client

A simple client for communicating with the filesystem MCP server.
"""

import json
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="MCP Filesystem Client")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # read_file command
    read_parser = subparsers.add_parser("read_file", help="Read a file")
    read_parser.add_argument("path", help="Path to the file to read")
    
    # write_file command
    write_parser = subparsers.add_parser("write_file", help="Write to a file")
    write_parser.add_argument("path", help="Path to the file to write")
    write_parser.add_argument("content", help="Content to write to the file")
    
    # list_directory command
    list_parser = subparsers.add_parser("list_directory", help="List directory contents")
    list_parser.add_argument("path", help="Path to the directory to list")
    
    # create_directory command
    mkdir_parser = subparsers.add_parser("create_directory", help="Create a directory")
    mkdir_parser.add_argument("path", help="Path to the directory to create")
    
    # search_files command
    search_parser = subparsers.add_parser("search_files", help="Search for files")
    search_parser.add_argument("path", help="Path to search in")
    search_parser.add_argument("pattern", help="Pattern to search for")
    
    # get_file_info command
    info_parser = subparsers.add_parser("get_file_info", help="Get file info")
    info_parser.add_argument("path", help="Path to the file to get info for")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Start the MCP server process
    process = subprocess.Popen(
        ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/home/lylepaul78"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    try:
        # Prepare the arguments based on the command
        tool_arguments = {}
        if args.command == "read_file":
            tool_arguments = {"path": args.path}
        elif args.command == "write_file":
            tool_arguments = {"path": args.path, "content": args.content}
        elif args.command == "list_directory":
            tool_arguments = {"path": args.path}
        elif args.command == "create_directory":
            tool_arguments = {"path": args.path}
        elif args.command == "search_files":
            tool_arguments = {"path": args.path, "pattern": args.pattern}
        elif args.command == "get_file_info":
            tool_arguments = {"path": args.path}
        
        # Create the request
        request = {
            "type": "tool_call",
            "request_id": "request-1",
            "tool_name": args.command,
            "arguments": tool_arguments
        }
        
        # Send the request
        request_json = json.dumps(request) + "\n"
        process.stdin.write(request_json)
        process.stdin.flush()
        
        # Read the response
        response_line = process.stdout.readline()
        response = json.loads(response_line)
        
        # Process the response
        if response.get("type") == "response":
            content = response.get("content")
            print(json.dumps(content, indent=2))
        else:
            print(f"Error: {response}")
    
    finally:
        # Close the process
        process.terminate()
        process.wait(timeout=5)
        if process.poll() is None:
            process.kill()

if __name__ == "__main__":
    main()