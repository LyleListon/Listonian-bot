#!/usr/bin/env python3
"""
Base DEX Scanner MCP Server Wrapper

This script serves as a wrapper for the Base DEX Scanner MCP server,
ensuring that environment variables are properly set.
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/base_dex_scanner_mcp_wrapper.log"),
    ],
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the wrapper script."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Set environment variables
        env = os.environ.copy()
        
        # Set ENVIRONMENT to development by default for MCP server
        # This allows using mock data for demonstration purposes
        env["ENVIRONMENT"] = "development"
        
        # Set USE_MOCK_DATA to true for demonstration purposes
        # In production, this would be overridden by the safety mechanism
        env["USE_MOCK_DATA"] = "true"
        
        logger.info("Starting Base DEX Scanner MCP server with environment variables:")
        logger.info(f"ENVIRONMENT={env['ENVIRONMENT']}")
        logger.info(f"USE_MOCK_DATA={env['USE_MOCK_DATA']}")
        
        # Run the MCP server
        server_script = os.path.join("Listonian-bot", "run_base_dex_scanner_mcp_with_api.py")
        
        # Check if the script exists
        if not os.path.exists(server_script):
            logger.error(f"Server script not found: {server_script}")
            return 1
            
        logger.info(f"Running server script: {server_script}")
        
        # Run the server script with the environment variables
        process = subprocess.Popen(
            [sys.executable, server_script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Log the output
        for line in process.stdout:
            print(line, end="")
            
        # Wait for the process to complete
        return_code = process.wait()
        
        logger.info(f"Server process exited with code {return_code}")
        return return_code
        
    except Exception as e:
        logger.exception(f"Error running wrapper script: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())