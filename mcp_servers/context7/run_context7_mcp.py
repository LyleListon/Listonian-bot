#!/usr/bin/env python3
"""
Context7 MCP Server Runner
Wraps the NPM-based Context7 MCP server for use with the Listonian bot
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def run_server():
    """Run the Context7 MCP server."""
    try:
        # Get the directory containing this script
        script_dir = Path(__file__).parent.absolute()
        
        # Ensure we have npx available
        try:
            subprocess.run(["npx", "--version"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            logger.error("npx not found. Please install Node.js and npm")
            return 1
        except FileNotFoundError:
            logger.error("npx not found. Please install Node.js and npm")
            return 1
            
        logger.info("Starting Context7 MCP server...")
        
        # Run the Context7 MCP server using npx
        process = subprocess.Popen(
            ["npx", "-y", "@upstash/context7-mcp@latest"],
            cwd=script_dir,
            env=os.environ.copy(),
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
        logger.exception(f"Error running Context7 MCP server: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(run_server())
