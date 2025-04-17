#!/usr/bin/env python3
"""
MCP Configuration Test Script

This script validates your MCP server configuration files and environment variables
to ensure they are properly formatted and consistent across different configuration files.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configuration file paths
MCP_SETTINGS_PATH = "mcp_settings.json"
ROO_MCP_PATH = ".roo/mcp.json"
AUGMENT_MCP_PATH = ".augment/mcp_config.json"
ENV_FILE_PATH = ".env"

def load_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON format error in {file_path}: {str(e)}")
        return None
    except FileNotFoundError:
        print(f"WARNING: File not found: {file_path}")
        return None
    except Exception as e:
        print(f"ERROR: Failed to load {file_path}: {str(e)}")
        return None

def load_env_file(file_path: str) -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        return env_vars
    except Exception as e:
        print(f"ERROR: Failed to load .env file: {str(e)}")
        return {}

def validate_mcp_config(config: Dict[str, Any]) -> List[str]:
    """Validate MCP server configuration format."""
    errors = []
    
    if not isinstance(config, dict):
        errors.append("Configuration must be a JSON object")
        return errors
    
    if "mcpServers" not in config:
        errors.append("Missing 'mcpServers' key in configuration")
        return errors
    
    servers = config["mcpServers"]
    if not isinstance(servers, dict):
        errors.append("'mcpServers' must be a JSON object")
        return errors
    
    for server_name, server_config in servers.items():
        # Check required fields
        if "command" not in server_config:
            errors.append(f"Server '{server_name}' is missing 'command' field")
        
        if "args" not in server_config:
            errors.append(f"Server '{server_name}' is missing 'args' field")
        elif not isinstance(server_config["args"], list):
            errors.append(f"Server '{server_name}': 'args' must be an array")
        
        # Check if script files exist
        if "args" in server_config and isinstance(server_config["args"], list):
            for arg in server_config["args"]:
                if isinstance(arg, str) and arg.endswith(".py") and not os.path.exists(arg):
                    errors.append(f"Server '{server_name}': Script file not found: {arg}")
        
        # Check env variables
        if "env" in server_config:
            if not isinstance(server_config["env"], dict):
                errors.append(f"Server '{server_name}': 'env' must be a JSON object")
    
    return errors

def check_env_variables(config: Dict[str, Any], env_vars: Dict[str, str]) -> List[str]:
    """Check if all referenced environment variables are defined."""
    warnings = []
    
    if "mcpServers" not in config:
        return warnings
    
    for server_name, server_config in config["mcpServers"].items():
        if "env" in server_config:
            for env_var, value in server_config["env"].items():
                # Check for variable references like ${VAR_NAME}
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    var_name = value[2:-1]
                    if var_name not in env_vars:
                        warnings.append(f"Server '{server_name}' references undefined environment variable: {var_name}")
    
    return warnings

def compare_configs(configs: Dict[str, Dict[str, Any]]) -> List[str]:
    """Compare different MCP configuration files for consistency."""
    warnings = []
    
    # Get all server names from all configs
    all_servers = set()
    for config_name, config in configs.items():
        if config and "mcpServers" in config:
            all_servers.update(config["mcpServers"].keys())
    
    # Check for servers defined in one config but not others
    for server_name in all_servers:
        defined_in = []
        for config_name, config in configs.items():
            if config and "mcpServers" in config and server_name in config["mcpServers"]:
                defined_in.append(config_name)
        
        if len(defined_in) < len(configs):
            missing_in = [name for name in configs.keys() if name not in defined_in]
            if missing_in:
                warnings.append(f"Server '{server_name}' is defined in {', '.join(defined_in)} but not in {', '.join(missing_in)}")
    
    return warnings

def main():
    """Main function to validate MCP configuration."""
    print("MCP Configuration Test")
    print("=====================\n")
    
    # Load configuration files
    print("Loading configuration files...")
    mcp_settings = load_json_file(MCP_SETTINGS_PATH)
    roo_mcp = load_json_file(ROO_MCP_PATH)
    augment_mcp = load_json_file(AUGMENT_MCP_PATH)
    env_vars = load_env_file(ENV_FILE_PATH)
    
    configs = {
        "mcp_settings.json": mcp_settings,
        ".roo/mcp.json": roo_mcp,
        ".augment/mcp_config.json": augment_mcp
    }
    
    # Validate each configuration
    all_valid = True
    for name, config in configs.items():
        if config:
            print(f"\nValidating {name}...")
            errors = validate_mcp_config(config)
            if errors:
                all_valid = False
                print(f"❌ Found {len(errors)} errors in {name}:")
                for error in errors:
                    print(f"  - {error}")
            else:
                print(f"✅ {name} format is valid")
                
            # Check environment variables
            warnings = check_env_variables(config, env_vars)
            if warnings:
                print(f"⚠️ Found {len(warnings)} warnings about environment variables:")
                for warning in warnings:
                    print(f"  - {warning}")
    
    # Compare configurations for consistency
    print("\nChecking configuration consistency...")
    consistency_warnings = compare_configs(configs)
    if consistency_warnings:
        print(f"⚠️ Found {len(consistency_warnings)} consistency warnings:")
        for warning in consistency_warnings:
            print(f"  - {warning}")
    else:
        print("✅ All configurations are consistent")
    
    # Final result
    print("\nTest Results:")
    if all_valid:
        print("✅ All MCP configuration files have valid JSON format")
    else:
        print("❌ Some MCP configuration files have JSON format errors")
        print("   Please fix the errors and run this test again")
    
    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())