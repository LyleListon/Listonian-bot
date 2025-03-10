"""
Production Setup Script

This script:
1. Installs dependencies
2. Configures environment variables
3. Validates system readiness
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('setup.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_environment(config: Dict[str, Any]) -> bool:
    """Set up environment variables from config."""
    try:
        # Load from .env if exists
        load_dotenv()

        # Set environment variables from config
        os.environ['WALLET_PRIVATE_KEY'] = config['web3']['wallet_key']
        os.environ['FLASHBOTS_AUTH_KEY'] = config['flashbots']['auth_key']

        logger.info("Environment variables set successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to set up environment: {e}")
        return False

def find_abi_files() -> List[str]:
    """Find all required ABI files."""
    abi_dir = Path("abi")
    required_patterns = [
        "*_factory.json",
        "*_pool.json",
        "*_router.json",
        "*_vault.json",
        "*_registry.json"
    ]
    
    found_files = []
    for pattern in required_patterns:
        found_files.extend([f.name for f in abi_dir.glob(pattern)])
    
    return found_files

def check_python_version() -> bool:
    """Check Python version."""
    try:
        version = sys.version_info
        if version.major != 3 or version.minor < 12:
            logger.error("Python 3.12+ is required")
            return False
        logger.info(f"Python version {version.major}.{version.minor} verified")
        return True
    except Exception as e:
        logger.error(f"Failed to check Python version: {e}")
        return False

def check_python_packages() -> bool:
    """Check required Python packages."""
    try:
        import web3
        import eth_account
        import aiohttp
        logger.info("Required Python packages verified")
        return True
    except ImportError as e:
        logger.error(f"Missing required package: {e}")
        return False

async def install_dependencies() -> bool:
    """Install required Python packages."""
    try:
        logger.info("Installing dependencies...")
        subprocess.check_call([
            sys.executable,
            "-m", "pip", "install",
            "-r", "requirements.txt"
        ])
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def validate_config() -> bool:
    """Validate configuration files."""
    try:
        logger.info("Validating configuration...")
        
        # Check production config
        config_path = Path("configs/production.json")
        if not config_path.exists():
            logger.error("Production config not found")
            return False

        # Load and validate config
        with open(config_path) as f:
            config = json.load(f)
            logger.info("Configuration loaded successfully")

        # Check required ABIs
        abi_dir = Path("abi")
        required_abis = find_abi_files()
        missing_abis = []
        for abi in required_abis:
            if not (abi_dir / abi).exists():
                missing_abis.append(abi)
        
        if missing_abis:
            logger.error(f"Missing ABIs: {', '.join(missing_abis)}")
            return False

        # Check custom Flashbots package
        if not Path("arbitrage_bot/core/web3/flashbots").exists():
            logger.error("Custom Flashbots package not found")
            return False

        # Set up environment variables
        if not setup_environment(config):
            logger.error("Failed to set up environment variables")
            return False
        
        logger.info("Configuration validated successfully")
        return True
    
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False

async def main():
    """Run setup process."""
    try:
        # Check Python version
        if not check_python_version():
            logger.error("Python version check failed")
            sys.exit(1)

        # Install dependencies
        if not await install_dependencies():
            sys.exit(1)
        
        # Check Python packages
        if not check_python_packages():
            sys.exit(1)

        # Validate configuration
        if not validate_config():
            sys.exit(1)
        
        logger.info("Setup completed successfully")
        logger.info("Run 'python -m arbitrage_bot.production' to start the system")
    
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())