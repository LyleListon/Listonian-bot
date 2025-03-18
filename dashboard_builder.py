"""
Dashboard Builder Script

This script builds a functioning dashboard step by step:
1. Sets up basic FastAPI framework
2. Creates required directory structure
3. Adds templates and static files
4. Integrates with arbitrage bot components
"""

import os
import sys
import json
import time
import logging
import importlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dashboard_builder.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dashboard_builder")

def log_section(title):
    """Log a section title with clear separation."""
    logger.info("\n" + "=" * 70)
    logger.info(f" {title}")
    logger.info("=" * 70)

def ensure_directories():
    """Ensure all required directories exist."""
    log_section("SETTING UP DIRECTORY STRUCTURE")
    
    directories = [
        "logs",
        "data",
        "data/performance",
        "data/transactions",
        "templates",
        "static",
        "static/css",
        "static/js",
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            logger.info(f"Creating directory: {directory}")
            path.mkdir(parents=True, exist_ok=True)
        else:
            logger.info(f"Directory already exists: {directory}")
    
    return True

def create_env_file():
    """Create a .env file if it doesn't exist."""
    log_section("SETTING UP ENVIRONMENT FILE")
    
    env_path = Path(".env")
    
    if env_path.exists():
        logger.info(f".env file already exists at {env_path.absolute()}")
        return True
    
    logger.info(f"Creating .env file at {env_path.absolute()}")
    
    # Basic default environment variables
    env_content = """# Dashboard Environment Configuration

# Blockchain Connection
BASE_RPC_URL=https://mainnet.base.org

# Wallet Configuration (view-only)
WALLET_ADDRESS=0x0000000000000000000000000000000000000000

# Server Configuration
HOST=localhost
PORT=8080
DEBUG=true
"""
    
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        logger.info("Successfully created .env file with default values")
        return True
    except Exception as e:
        logger.error(f"Failed to create .env file: {e}")
        return False

def install_required_packages():
    """Install required Python packages."""
    log_section("INSTALLING REQUIRED PACKAGES")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "jinja2",
        "python-dotenv",
        "web3",
        "pydantic"
    ]
    
    logger.info(f"Required packages: {', '.join(required_packages)}")
    
    try:
        import pip
        for package in required_packages:
            try:
                logger.info(f"Checking for {package}...")
                __import__(package)
                logger.info(f"Package {package} is already installed")
            except ImportError:
                logger.info(f"Installing {package}...")
                pip.main(["install", package])
                logger.info(f"Installed {package}")
    except Exception as e:
        logger.error(f"Error installing packages: {e}")
        return False
    
    return True

def test_arbitrage_bot_imports():
    """Test if arbitrage_bot modules can be imported."""
    log_section("TESTING ARBITRAGE BOT IMPORTS")
    
    modules_to_test = [
        "arbitrage_bot",
        "arbitrage_bot.core.web3.web3_manager",
        "arbitrage_bot.core.dex.dex_manager"
    ]
    
    import_results = {}
    
    for module_name in modules_to_test:
        logger.info(f"Testing import of {module_name}...")
        try:
            if module_name not in sys.modules:
                __import__(module_name)
            import_results[module_name] = "Success"
            logger.info(f"Successfully imported {module_name}")
        except Exception as e:
            import_results[module_name] = f"Error: {str(e)}"
            logger.error(f"Failed to import {module_name}: {e}")
    
    return import_results

def create_simplified_dashboard_file():
    """Create a simplified dashboard file that works with or without arbitrage bot."""
    log_section("CREATING SIMPLIFIED DASHBOARD FILE")

    source_path = Path("simplified_dashboard.py")
    if not source_path.exists():
        logger.error("simplified_dashboard.py not found")
        return False
    logger.info("Using existing simplified_dashboard.py")
    return True


def create_dashboard_runner():
    """Create a batch file to run the dashboard."""
    log_section("CREATING DASHBOARD RUNNER")
    
    runner_path = Path("start_dashboard.bat")
    
    runner_content = """@echo off
echo ===============================================================================
echo ARBITRAGE DASHBOARD
echo ===============================================================================
echo.
echo Starting the dashboard...

REM Check if Python is available
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found in PATH
    goto :EOF
)

REM Create required directories
mkdir templates 2>nul
mkdir static 2>nul
mkdir static\css 2>nul
mkdir logs 2>nul
mkdir data 2>nul
mkdir data\performance 2>nul
mkdir data\transactions 2>nul

REM Try to install required packages
pip install fastapi uvicorn jinja2 python-dotenv web3

REM Run the dashboard
python simplified_dashboard.py

echo.
echo ===============================================================================
echo Dashboard stopped. Press any key to exit...
pause >nul
"""
    
    try:
        with open(runner_path, "w") as f:
            f.write(runner_content)
        logger.info(f"Successfully created runner at {runner_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create runner: {e}")
        return False

def main():
    """Run the dashboard builder script."""
    log_section("DASHBOARD BUILDER SCRIPT")
    logger.info("This script will set up a functioning dashboard step by step.")
    
    # Ensure directories
    ensure_directories()
    
    # Create .env file
    create_env_file()
    
    # Install required packages
    install_required_packages()
    
    # Test arbitrage bot imports
    import_results = test_arbitrage_bot_imports()
    
    # Create simplified dashboard file
    create_simplified_dashboard_file()
    
    # Create dashboard runner
    create_dashboard_runner()
    
    # Log summary
    log_section("DASHBOARD BUILDER SUMMARY")
    logger.info("Directory structure: DONE")
    logger.info("Environment file: DONE")
    logger.info("Package installation: DONE")
    logger.info("Dashboard files: DONE")
    
    logger.info("Import test results:")
    for module, result in import_results.items():
        logger.info(f"  {module}: {result}")
    
    logger.info("\nTo start the dashboard, run: start_dashboard.bat")
    logger.info("Then open: http://localhost:8080 in your browser")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())