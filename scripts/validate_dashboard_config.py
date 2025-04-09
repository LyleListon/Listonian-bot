#!/usr/bin/env python3
"""
Dashboard Configuration Validator

This script validates the dashboard configuration and ensures it's properly set up.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard_config_validator")

# Configuration paths
DASHBOARD_CONFIG_PATH = project_root / "new_dashboard" / "config.json"
MAIN_CONFIG_PATH = project_root / "configs" / "config.json"
ENV_FILE_PATH = project_root / ".env"

class ConfigValidator:
    """Validate dashboard configuration."""
    
    def __init__(self):
        """Initialize the validator."""
        self.dashboard_config_path = DASHBOARD_CONFIG_PATH
        self.main_config_path = MAIN_CONFIG_PATH
        self.env_file_path = ENV_FILE_PATH
        
        self.dashboard_config = None
        self.main_config = None
        self.env_vars = {}
        
        self.issues = []
        self.warnings = []
        
    def load_configs(self) -> bool:
        """Load all configuration files."""
        success = True
        
        # Load dashboard config
        if self.dashboard_config_path.exists():
            try:
                with open(self.dashboard_config_path) as f:
                    self.dashboard_config = json.load(f)
                logger.info(f"Loaded dashboard config from {self.dashboard_config_path}")
            except Exception as e:
                logger.error(f"Error loading dashboard config: {e}")
                self.issues.append(f"Failed to load dashboard config: {e}")
                success = False
        else:
            logger.error(f"Dashboard config not found: {self.dashboard_config_path}")
            self.issues.append(f"Dashboard config not found: {self.dashboard_config_path}")
            success = False
        
        # Load main config
        if self.main_config_path.exists():
            try:
                with open(self.main_config_path) as f:
                    self.main_config = json.load(f)
                logger.info(f"Loaded main config from {self.main_config_path}")
            except Exception as e:
                logger.error(f"Error loading main config: {e}")
                self.issues.append(f"Failed to load main config: {e}")
                success = False
        else:
            logger.warning(f"Main config not found: {self.main_config_path}")
            self.warnings.append(f"Main config not found: {self.main_config_path}")
        
        # Load environment variables
        if self.env_file_path.exists():
            try:
                with open(self.env_file_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        
                        key, value = line.split("=", 1)
                        self.env_vars[key.strip()] = value.strip()
                logger.info(f"Loaded environment variables from {self.env_file_path}")
            except Exception as e:
                logger.error(f"Error loading environment variables: {e}")
                self.issues.append(f"Failed to load environment variables: {e}")
                success = False
        else:
            logger.warning(f"Environment file not found: {self.env_file_path}")
            self.warnings.append(f"Environment file not found: {self.env_file_path}")
        
        return success
    
    def validate_dashboard_config(self) -> bool:
        """Validate the dashboard configuration."""
        if not self.dashboard_config:
            return False
        
        # Check required sections
        required_sections = ["dashboard", "arbitrage_bot", "logging"]
        for section in required_sections:
            if section not in self.dashboard_config:
                self.issues.append(f"Missing required section in dashboard config: {section}")
        
        # Check dashboard section
        if "dashboard" in self.dashboard_config:
            dashboard = self.dashboard_config["dashboard"]
            
            # Check required fields
            required_fields = ["port", "host", "memory_bank_path"]
            for field in required_fields:
                if field not in dashboard:
                    self.issues.append(f"Missing required field in dashboard config: dashboard.{field}")
            
            # Check port
            if "port" in dashboard and not isinstance(dashboard["port"], int):
                self.issues.append(f"Invalid port in dashboard config: {dashboard['port']}")
            
            # Check memory bank path
            if "memory_bank_path" in dashboard:
                memory_bank_path = Path(dashboard["memory_bank_path"])
                if not memory_bank_path.is_absolute():
                    memory_bank_path = project_root / memory_bank_path
                
                if not memory_bank_path.exists():
                    self.issues.append(f"Memory bank path does not exist: {memory_bank_path}")
        
        # Check arbitrage_bot section
        if "arbitrage_bot" in self.dashboard_config:
            arbitrage_bot = self.dashboard_config["arbitrage_bot"]
            
            # Check connection
            if "connection" not in arbitrage_bot:
                self.issues.append("Missing connection configuration in arbitrage_bot section")
            elif "type" not in arbitrage_bot["connection"]:
                self.issues.append("Missing connection type in arbitrage_bot.connection")
            elif arbitrage_bot["connection"]["type"] not in ["memory_bank", "api"]:
                self.issues.append(f"Invalid connection type: {arbitrage_bot['connection']['type']}")
        
        # Check logging section
        if "logging" in self.dashboard_config:
            logging_config = self.dashboard_config["logging"]
            
            # Check required fields
            required_fields = ["level", "format"]
            for field in required_fields:
                if field not in logging_config:
                    self.issues.append(f"Missing required field in logging config: logging.{field}")
            
            # Check log level
            if "level" in logging_config and logging_config["level"] not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                self.issues.append(f"Invalid log level: {logging_config['level']}")
        
        return len(self.issues) == 0
    
    def validate_mcp_config(self) -> bool:
        """Validate MCP server configuration."""
        if not self.dashboard_config:
            return False
        
        # Check if MCP servers are configured
        if "mcp_servers" not in self.dashboard_config:
            self.warnings.append("No MCP servers configured in dashboard config")
            return True
        
        mcp_servers = self.dashboard_config["mcp_servers"]
        
        # Check each MCP server
        for server_name, server_config in mcp_servers.items():
            # Check required fields
            required_fields = ["enabled", "url"]
            for field in required_fields:
                if field not in server_config:
                    self.issues.append(f"Missing required field in MCP server config: mcp_servers.{server_name}.{field}")
            
            # Check URL
            if "url" in server_config and not server_config["url"].startswith(("http://", "https://")):
                self.issues.append(f"Invalid URL for MCP server {server_name}: {server_config['url']}")
            
            # Check API key
            if "api_key" in server_config and server_config["api_key"].startswith("${") and server_config["api_key"].endswith("}"):
                env_var = server_config["api_key"][2:-1]
                if env_var not in self.env_vars:
                    self.warnings.append(f"Environment variable {env_var} not found for MCP server {server_name}")
        
        return len(self.issues) == 0
    
    def validate_memory_bank(self) -> bool:
        """Validate memory bank configuration and existence."""
        if not self.dashboard_config:
            return False
        
        # Get memory bank path
        memory_bank_path = None
        if "dashboard" in self.dashboard_config and "memory_bank_path" in self.dashboard_config["dashboard"]:
            memory_bank_path = Path(self.dashboard_config["dashboard"]["memory_bank_path"])
            if not memory_bank_path.is_absolute():
                memory_bank_path = project_root / memory_bank_path
        
        if not memory_bank_path:
            self.issues.append("Memory bank path not configured")
            return False
        
        # Check if memory bank exists
        if not memory_bank_path.exists():
            self.issues.append(f"Memory bank directory does not exist: {memory_bank_path}")
            return False
        
        # Check required subdirectories
        required_dirs = ["trades", "metrics", "state"]
        for dir_name in required_dirs:
            dir_path = memory_bank_path / dir_name
            if not dir_path.exists():
                self.issues.append(f"Memory bank subdirectory does not exist: {dir_path}")
        
        return len(self.issues) == 0
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Validate all configurations."""
        # Load configs
        if not self.load_configs():
            return False, self.issues, self.warnings
        
        # Validate dashboard config
        self.validate_dashboard_config()
        
        # Validate MCP config
        self.validate_mcp_config()
        
        # Validate memory bank
        self.validate_memory_bank()
        
        return len(self.issues) == 0, self.issues, self.warnings

def main():
    """Main entry point."""
    validator = ConfigValidator()
    success, issues, warnings = validator.validate_all()
    
    if success:
        print("Dashboard configuration is valid!")
    else:
        print("Dashboard configuration has issues:")
        for issue in issues:
            print(f"  - {issue}")
    
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
