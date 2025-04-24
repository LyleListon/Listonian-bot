#!/bin/bash
# MCP Filesystem Helper Script
# This script provides simple commands for interacting with the filesystem MCP server

# Default server command and args
SERVER_CMD="npx"
SERVER_ARGS="-y @modelcontextprotocol/server-filesystem /home/lylepaul78"

# Function to send a request to the MCP server
send_request() {
    local tool_name=$1
    local arguments=$2
    local request="{\"type\":\"tool_call\",\"request_id\":\"req1\",\"tool_name\":\"$tool_name\",\"arguments\":$arguments}"
    
    python mcp_direct.py "$SERVER_CMD" "$SERVER_ARGS" "$request"
}

# Show usage if no arguments provided
if [ $# -lt 1 ]; then
    echo "Usage: ./mcp_fs.sh <command> [arguments]"
    echo ""
    echo "Available commands:"
    echo "  read <path>                  - Read a file"
    echo "  write <path> <content>       - Write to a file"
    echo "  list <path>                  - List directory contents"
    echo "  mkdir <path>                 - Create a directory"
    echo "  search <path> <pattern>      - Search for files"
    echo "  info <path>                  - Get file info"
    echo ""
    echo "Examples:"
    echo "  ./mcp_fs.sh read /path/to/file.txt"
    echo "  ./mcp_fs.sh write /path/to/file.txt \"Hello, world!\""
    echo "  ./mcp_fs.sh list /path/to/directory"
    exit 1
fi

# Parse command and arguments
COMMAND=$1
shift

case $COMMAND in
    read)
        if [ $# -ne 1 ]; then
            echo "Usage: ./mcp_fs.sh read <path>"
            exit 1
        fi
        send_request "read_file" "{\"path\":\"$1\"}"
        ;;
    write)
        if [ $# -ne 2 ]; then
            echo "Usage: ./mcp_fs.sh write <path> <content>"
            exit 1
        fi
        send_request "write_file" "{\"path\":\"$1\",\"content\":\"$2\"}"
        ;;
    list)
        if [ $# -ne 1 ]; then
            echo "Usage: ./mcp_fs.sh list <path>"
            exit 1
        fi
        send_request "list_directory" "{\"path\":\"$1\"}"
        ;;
    mkdir)
        if [ $# -ne 1 ]; then
            echo "Usage: ./mcp_fs.sh mkdir <path>"
            exit 1
        fi
        send_request "create_directory" "{\"path\":\"$1\"}"
        ;;
    search)
        if [ $# -ne 2 ]; then
            echo "Usage: ./mcp_fs.sh search <path> <pattern>"
            exit 1
        fi
        send_request "search_files" "{\"path\":\"$1\",\"pattern\":\"$2\"}"
        ;;
    info)
        if [ $# -ne 1 ]; then
            echo "Usage: ./mcp_fs.sh info <path>"
            exit 1
        fi
        send_request "get_file_info" "{\"path\":\"$1\"}"
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run ./mcp_fs.sh without arguments to see usage"
        exit 1
        ;;
esac