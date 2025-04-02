#!/usr/bin/env python3
"""
Run Base DEX Scanner Integration Example

This script provides a convenient way to run the Base DEX Scanner integration example.
It sets up the environment and runs the example script.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/run_base_dex_scanner_example.log"),
    ],
)
logger = logging.getLogger(__name__)

# =====================================================================
# MOCK DATA CONFIGURATION
# =====================================================================
# Set this to False to disable mock data and use real API calls
# In production, this should be set to False
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "false").lower() == "true"

if USE_MOCK_DATA:
    logger.warning("!!! USING MOCK DATA FOR TESTING PURPOSES ONLY !!! Set USE_MOCK_DATA=false to use real data")


async def main():
    """Main entry point for the script."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Add project root to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Import the example module
        from examples.base_dex_scanner_integration_example import main as example_main
        
        # Run the example
        logger.info("Running Base DEX Scanner integration example...")
        
        if USE_MOCK_DATA:
            logger.warning("!!! RUNNING EXAMPLE WITH MOCK DATA - FOR TESTING PURPOSES ONLY !!!")
            logger.warning("!!! RESULTS ARE NOT REAL AND SHOULD NOT BE USED FOR TRADING !!!")
        
        await example_main()
        
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.exception(f"Error running example: {str(e)}")


if __name__ == "__main__":
    # Check if MCP server is configured
    mcp_config_path = Path(__file__).parent / ".roo" / "mcp.json"
    if not mcp_config_path.exists() and not (Path.home() / ".roo" / "mcp.json").exists():
        print(f"MCP configuration file not found at {mcp_config_path}")
        print("Please make sure the Base DEX Scanner MCP server is configured.")
        sys.exit(1)
    
    # Run the example
    asyncio.run(main())