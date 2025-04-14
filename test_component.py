#!/usr/bin/env python
"""Test a specific component with detailed output."""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
import requests
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_component")


def test_component(component: str, env: str = "test") -> bool:
    """Test a specific component.
    
    Args:
        component: Component to test (mcp, bot, api, dashboard).
        env: Environment to use.
        
    Returns:
        True if the test passed, False otherwise.
    """
    logger.info(f"Testing {component}")
    
    # Get command for component
    if component == "mcp":
        command = ["python", "run_mcp_server.py", "--env", env]
    elif component == "bot":
        command = ["python", "run_bot.py", "--env", env]
    elif component == "api":
        command = ["python", "bot_api_server.py", "--env", env]
    elif component == "dashboard":
        command = ["python", "run_dashboard.py", "--env", env]
    else:
        logger.error(f"Unknown component: {component}")
        return False
    
    try:
        # Start component
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        
        logger.info(f"Started {component} with PID {process.pid}")
        
        # Wait for component to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"{component} process terminated with code {process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            return False
        
        logger.info(f"{component} is running")
        
        # Check if component is responding
        if component == "api":
            try:
                response = requests.get("http://localhost:8000/api/v1/status", timeout=5)
                logger.info(f"API response: {response.status_code}")
                logger.info(f"API response body: {response.text}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to connect to API: {e}")
        elif component == "dashboard":
            try:
                response = requests.get("http://localhost:8080", timeout=5)
                logger.info(f"Dashboard response: {response.status_code}")
                logger.info(f"Dashboard response body: {response.text[:200]}...")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to connect to dashboard: {e}")
        
        # Wait for user input
        input(f"Press Enter to stop {component}...")
        
        # Kill process
        process.terminate()
        process.wait(timeout=5.0)
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing {component}: {e}")
        return False


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test a specific component")
    parser.add_argument(
        "component",
        choices=["mcp", "bot", "api", "dashboard"],
        help="Component to test",
    )
    parser.add_argument(
        "--env",
        type=str,
        default="test",
        help="Environment to use (development, production, test)",
    )
    args = parser.parse_args()
    
    # Test component
    success = test_component(args.component, args.env)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
