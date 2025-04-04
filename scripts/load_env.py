#!/usr/bin/env python3
"""
Environment Loader

This script loads environment variables from a .env file.
It's used to set up the production environment for the Listonian Arbitrage Bot.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/env_loader.log"),
    ],
)
logger = logging.getLogger(__name__)

def load_env(env_file=".env.production"):
    """Load environment variables from a .env file."""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        env_path = project_root / env_file
        
        logger.info(f"Loading environment variables from {env_path}")
        
        # Check if the file exists
        if not env_path.exists():
            logger.error(f"Environment file not found: {env_path}")
            return False
        
        # Load environment variables
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Parse key-value pairs
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Set environment variable
                    os.environ[key] = value
                    logger.info(f"Set environment variable: {key}")
        
        logger.info("Environment variables loaded successfully")
        return True
    
    except Exception as e:
        logger.exception(f"Error loading environment variables: {str(e)}")
        return False

if __name__ == "__main__":
    # Get the environment file from command line arguments
    env_file = ".env.production"
    if len(sys.argv) > 1:
        env_file = sys.argv[1]
    
    # Load environment variables
    success = load_env(env_file)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)