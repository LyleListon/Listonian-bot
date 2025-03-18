"""
Python environment validation.

This module verifies:
1. Python version
2. Installation path
3. Required packages
4. Virtual environment
"""

import os
import sys
import logging
import platform
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_python_version() -> bool:
    """Check Python version meets requirements."""
    required_version = (3, 12)
    current_version = sys.version_info[:2]
    
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"Python implementation: {platform.python_implementation()}")
    logger.info(f"Python build: {platform.python_build()}")
    
    if current_version < required_version:
        logger.error(f"Python {required_version[0]}.{required_version[1]}+ is required")
        return False
    return True

def check_virtual_env() -> bool:
    """Check if running in a virtual environment."""
    in_venv = sys.prefix != sys.base_prefix
    logger.info(f"Virtual environment: {'Active' if in_venv else 'Not active'}")
    logger.info(f"Virtual environment path: {sys.prefix}")
    return in_venv

def check_python_path() -> bool:
    """Check Python path configuration."""
    logger.info("Python path:")
    for path in sys.path:
        logger.info(f"  {path}")
    
    # Check if current directory is in path
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        logger.warning(f"Current directory not in Python path: {cwd}")
        return False
    return True

def check_required_packages() -> bool:
    """Check required package installations."""
    required_packages = [
        'web3',
        'fastapi',
        'uvicorn',
        'pytest',
        'pytest-asyncio',
        'aiohttp',
        'pydantic'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"Package {package} is installed")
        except ImportError:
            logger.error(f"Package {package} is missing")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def main() -> int:
    """Run all environment checks."""
    logger.info("=" * 70)
    logger.info("PYTHON ENVIRONMENT VALIDATION")
    logger.info("=" * 70)
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_env),
        ("Python Path", check_python_path),
        ("Required Packages", check_required_packages)
    ]
    
    all_passed = True
    for name, check in checks:
        logger.info(f"\nRunning {name} check...")
        try:
            if not check():
                all_passed = False
                logger.error(f"{name} check failed")
        except Exception as e:
            all_passed = False
            logger.error(f"{name} check error: {e}")
    
    if all_passed:
        logger.info("\nAll environment checks passed")
        return 0
    else:
        logger.error("\nSome environment checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())