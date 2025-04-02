#!/usr/bin/env python3
"""
Update MCP Port Configuration

This script updates the MCP port configuration in all relevant files.
"""

import os
import re
import sys

# Configuration
OLD_PORT = "8000"
NEW_PORT = "9050"
FILES_TO_UPDATE = [
    "arbitrage_bot/integration/base_dex_scanner_mcp.py",
    "run_base_dex_scanner_mcp.py",
    "run_base_dex_scanner_example.py",
    "examples/base_dex_scanner_integration_example.py"
]

def update_file(file_path):
    """Update port configuration in a file."""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace port in URLs
    updated_content = content.replace(f"localhost:{OLD_PORT}", f"localhost:{NEW_PORT}")
    updated_content = updated_content.replace(f"127.0.0.1:{OLD_PORT}", f"127.0.0.1:{NEW_PORT}")
    
    # Replace port in configuration variables
    pattern = r'(MCP_SERVER_PORT\s*=\s*)(\d+)'
    if re.search(pattern, updated_content):
        updated_content = re.sub(pattern, r'\g<1>' + NEW_PORT, updated_content)
    
    # Write updated content back to file
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated {file_path}")
    return True

def main():
    """Main entry point."""
    print(f"Updating MCP port from {OLD_PORT} to {NEW_PORT}...")
    
    success_count = 0
    for file_path in FILES_TO_UPDATE:
        if update_file(file_path):
            success_count += 1
    
    print(f"Updated {success_count} of {len(FILES_TO_UPDATE)} files.")

if __name__ == "__main__":
    main()