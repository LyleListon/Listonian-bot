#!/usr/bin/env python
"""
MCP API Key Setup Script

This script helps you configure API keys for MCP servers securely.
It will guide you through the process of setting up the necessary API keys
for GitHub and Glama.ai MCP servers.

Usage:
    python setup_mcp_keys.py

The script will:
1. Check for existing MCP settings
2. Guide you through obtaining API keys if needed
3. Securely store the keys in the MCP settings file
4. Test the connections to verify everything is working
"""

import os
import json
import getpass
import subprocess
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# MCP Settings paths
MCP_SETTINGS_PATHS = [
    # VSCode Roo extension path
    os.path.expanduser("~/AppData/Roaming/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json"),
    # Claude desktop app path
    os.path.expanduser("~/AppData/Roaming/Claude/claude_desktop_config.json"),
]

def find_mcp_settings_file():
    """Find the MCP settings file on the system."""
    for path in MCP_SETTINGS_PATHS:
        if os.path.exists(path):
            logger.info(f"Found MCP settings at: {path}")
            return path
    
    logger.warning("No existing MCP settings file found")
    return None

def read_mcp_settings(settings_path):
    """Read the existing MCP settings."""
    try:
        with open(settings_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.warning(f"Could not read MCP settings at {settings_path}, creating new settings")
        return {"mcpServers": {}}

def write_mcp_settings(settings_path, settings):
    """Write the updated MCP settings."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    
    # Write settings
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)
    
    logger.info(f"Updated MCP settings at: {settings_path}")

def get_openai_api_key():
    """Guide the user to obtain and enter their OpenAI API key."""
    print("\n=== OpenAI API Key Setup ===")
    print("The Glama.ai MCP server requires an OpenAI API key to function.")
    print("If you don't have an API key, you can obtain one by following these steps:")
    print("1. Go to https://platform.openai.com/api-keys")
    print("2. Sign in to your OpenAI account (or create one)")
    print("3. Click 'Create new secret key'")
    print("4. Give your key a name (e.g., 'Listonian Bot')")
    print("5. Copy your API key (it will only be shown once)")
    
    return getpass.getpass("Enter your OpenAI API key (input will be hidden): ")

def get_github_access_token():
    """Guide the user to obtain and enter their GitHub Personal Access Token."""
    print("\n=== GitHub Personal Access Token Setup ===")
    print("The GitHub MCP server requires a Personal Access Token (PAT) to function.")
    print("If you don't have a PAT, you can obtain one by following these steps:")
    print("1. Go to https://github.com/settings/tokens")
    print("2. Click 'Generate new token' (classic)")
    print("3. Give your token a name (e.g., 'Listonian Bot')")
    print("4. Select the following scopes: repo, workflow, read:org")
    print("5. Click 'Generate token' and copy your new PAT (it will only be shown once)")
    
    return getpass.getpass("Enter your GitHub Personal Access Token (input will be hidden): ")

def get_glama_ai_api_key():
    """Guide the user to obtain and enter their Glama.ai API key."""
    print("\n=== Glama.ai API Key Setup ===")
    print("The Glama.ai MCP server requires a Glama.ai API key to function.")
    print("If you don't have an API key, you can obtain one by following these steps:")
    print("1. Go to https://glama.ai/dashboard")
    print("2. Sign in to your Glama.ai account (or create one)")
    print("3. Navigate to API Keys section")
    print("4. Generate a new API key")
    print("5. Copy your API key")
    
    return getpass.getpass("Enter your Glama.ai API key (input will be hidden): ")

def test_github_connection(token):
    """Test the GitHub token by making a simple API request."""
    try:
        import requests
        response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"}
        )
        if response.status_code == 200:
            username = response.json().get("login")
            logger.info(f"GitHub connection successful! Connected as: {username}")
            return True
        else:
            logger.error(f"GitHub connection failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error testing GitHub connection: {str(e)}")
        return False

def update_github_mcp(settings):
    """Update GitHub MCP server settings."""
    print("\n=== GitHub MCP Configuration ===")
    
    if 'github' in settings.get('mcpServers', {}):
        print("GitHub MCP server already configured.")
        update = input("Do you want to update the GitHub MCP settings? (y/n): ").lower() == 'y'
        if not update:
            return settings
    
    token = get_github_access_token()
    if test_github_connection(token):
        if 'mcpServers' not in settings:
            settings['mcpServers'] = {}
        
        settings['mcpServers']['github'] = {
            "command": "docker",
            "args": ["run", "--rm", "-p", "3000:3000", "mcp/github:latest"],
            "env": {
                "GITHUB_TOKEN": token
            },
            "disabled": False,
            "alwaysAllow": []
        }
        
        logger.info("GitHub MCP server configured successfully")
    else:
        logger.error("Failed to configure GitHub MCP server due to connection test failure")
    
    return settings

def update_glama_mcp(settings):
    """Update Glama.ai MCP server settings."""
    print("\n=== Glama.ai MCP Configuration ===")
    
    if 'glama' in settings.get('mcpServers', {}):
        print("Glama.ai MCP server already configured.")
        update = input("Do you want to update the Glama.ai MCP settings? (y/n): ").lower() == 'y'
        if not update:
            return settings
    
    openai_key = get_openai_api_key()
    glama_key = get_glama_ai_api_key()
    
    if 'mcpServers' not in settings:
        settings['mcpServers'] = {}
    
    settings['mcpServers']['glama'] = {
        "command": "docker",
        "args": ["run", "--rm", "-p", "3001:3001", "mcp/glama:latest"],
        "env": {
            "OPENAI_API_KEY": openai_key,
            "GLAMA_API_KEY": glama_key
        },
        "disabled": False,
        "alwaysAllow": []
    }
    
    logger.info("Glama.ai MCP server configured successfully")
    return settings

def main():
    """Main function to set up MCP API keys."""
    print("=== MCP API Key Setup ===")
    print("This script will help you configure API keys for MCP servers.")
    
    # Find MCP settings file
    settings_path = find_mcp_settings_file()
    if not settings_path:
        for path in MCP_SETTINGS_PATHS:
            if input(f"Would you like to create MCP settings at {path}? (y/n): ").lower() == 'y':
                settings_path = path
                break
        
        if not settings_path:
            logger.error("No MCP settings path selected. Exiting.")
            return
    
    # Read existing settings
    settings = read_mcp_settings(settings_path)
    
    # Configure MCP servers
    if input("Do you want to configure the GitHub MCP server? (y/n): ").lower() == 'y':
        settings = update_github_mcp(settings)
    
    if input("Do you want to configure the Glama.ai MCP server? (y/n): ").lower() == 'y':
        settings = update_glama_mcp(settings)
    
    # Write updated settings
    write_mcp_settings(settings_path, settings)
    
    print("\n=== Setup Complete ===")
    print("MCP API keys have been configured successfully.")
    print("You may need to restart your application for the changes to take effect.")
    print("After restart, you can test the MCP servers by running the appropriate batch files:")
    print("- run_github_tracker.bat - For testing GitHub MCP")
    print("- run_glama_enhanced_strategy.bat - For testing Glama.ai MCP")

if __name__ == "__main__":
    main()