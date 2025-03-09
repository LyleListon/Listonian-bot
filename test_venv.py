"""
Test using virtual environment.
"""

import os
import sys
import venv
import pytest
import shutil
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def setup_venv():
    """Create and set up virtual environment."""
    try:
        # Create venv directory
        venv_dir = Path("venv_test")
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        
        logger.info(f"Creating virtual environment in {venv_dir}")
        venv.create(venv_dir, with_pip=True)
        
        # Get paths
        if os.name == 'nt':  # Windows
            python_path = venv_dir / "Scripts" / "python.exe"
            pip_path = venv_dir / "Scripts" / "pip.exe"
        else:  # Unix
            python_path = venv_dir / "bin" / "python"
            pip_path = venv_dir / "bin" / "pip"
            
        logger.info(f"Python path: {python_path}")
        logger.info(f"Pip path: {pip_path}")
        
        # Install package in development mode
        cmd = [str(pip_path), "install", "-e", "."]
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        return str(python_path)
    except Exception as e:
        logger.error(f"Failed to set up virtual environment: {e}")
        raise

def run_test(python_path):
    """Run test in virtual environment."""
    try:
        test_code = """
import sys
import logging
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import modules
from arbitrage_bot.core.web3.web3_manager import Web3Manager
from arbitrage_bot.core.distribution.manager import DistributionManager

# Create mock web3 manager
web3_manager = Mock()
web3_manager.get_balance = AsyncMock(return_value=Decimal('1.0'))
web3_manager.wallet_address = "0x1234567890123456789012345678901234567890"
web3_manager.w3 = Mock()
web3_manager.w3.to_wei = lambda x, _: int(float(x) * 10**18)
web3_manager.send_transaction = AsyncMock(return_value="0xmocked_tx_hash")

# Create distribution manager
dist_manager = DistributionManager(web3_manager)

print("Test successful!")
"""
        
        test_file = "venv_test.py"
        with open(test_file, "w") as f:
            f.write(test_code)
            
        cmd = [python_path, test_file]
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_venv():
    """Test package in virtual environment."""
    try:
        python_path = setup_venv()
        run_test(python_path)
        logger.info("Virtual environment test successful")
    except Exception as e:
        logger.error(f"Virtual environment test failed: {e}")
        raise
    finally:
        # Cleanup
        if os.path.exists("venv_test"):
            shutil.rmtree("venv_test")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=DEBUG"])