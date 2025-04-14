#!/usr/bin/env python
"""Test each component individually."""

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
logger = logging.getLogger("test_standalone")


def test_mcp_server() -> bool:
    """Test the MCP server.
    
    Returns:
        True if the test passed, False otherwise.
    """
    logger.info("Testing MCP server")
    
    try:
        # Start MCP server
        process = subprocess.Popen(
            ["python", "run_mcp_server.py", "--env", "test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        
        # Wait for server to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"MCP server process terminated with code {process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            return False
        
        logger.info("MCP server is running")
        
        # Kill process
        process.terminate()
        process.wait(timeout=5.0)
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing MCP server: {e}")
        return False


def test_bot() -> bool:
    """Test the bot.
    
    Returns:
        True if the test passed, False otherwise.
    """
    logger.info("Testing bot")
    
    try:
        # Start bot
        process = subprocess.Popen(
            ["python", "run_bot.py", "--env", "test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        
        # Wait for bot to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"Bot process terminated with code {process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            return False
        
        logger.info("Bot is running")
        
        # Kill process
        process.terminate()
        process.wait(timeout=5.0)
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing bot: {e}")
        return False


def test_api_server() -> bool:
    """Test the API server.
    
    Returns:
        True if the test passed, False otherwise.
    """
    logger.info("Testing API server")
    
    try:
        # Start API server
        process = subprocess.Popen(
            ["python", "bot_api_server.py", "--env", "test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        
        # Wait for server to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"API server process terminated with code {process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            return False
        
        # Try to connect to the API server
        try:
            response = requests.get("http://localhost:8000/api/v1/status", timeout=5)
            
            if response.status_code == 200:
                logger.info(f"API server is running: {response.json()}")
            else:
                logger.warning(f"API server returned status code {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to connect to API server: {e}")
            return False
        
        # Kill process
        process.terminate()
        process.wait(timeout=5.0)
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing API server: {e}")
        return False


def test_dashboard_server() -> bool:
    """Test the dashboard server.
    
    Returns:
        True if the test passed, False otherwise.
    """
    logger.info("Testing dashboard server")
    
    try:
        # Start dashboard server
        process = subprocess.Popen(
            ["python", "run_dashboard.py", "--env", "test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        
        # Wait for server to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"Dashboard server process terminated with code {process.returncode}")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            return False
        
        # Try to connect to the dashboard server
        try:
            response = requests.get("http://localhost:8080", timeout=5)
            
            if response.status_code == 200:
                logger.info("Dashboard server is running")
            else:
                logger.warning(f"Dashboard server returned status code {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to connect to dashboard server: {e}")
            return False
        
        # Kill process
        process.terminate()
        process.wait(timeout=5.0)
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing dashboard server: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("Testing each component individually")
    
    # Test MCP server
    mcp_server_passed = test_mcp_server()
    
    # Test bot
    bot_passed = test_bot()
    
    # Test API server
    api_server_passed = test_api_server()
    
    # Test dashboard server
    dashboard_server_passed = test_dashboard_server()
    
    # Print results
    logger.info("Test results:")
    logger.info(f"  MCP server: {'PASSED' if mcp_server_passed else 'FAILED'}")
    logger.info(f"  Bot: {'PASSED' if bot_passed else 'FAILED'}")
    logger.info(f"  API server: {'PASSED' if api_server_passed else 'FAILED'}")
    logger.info(f"  Dashboard server: {'PASSED' if dashboard_server_passed else 'FAILED'}")
    
    # Check if all tests passed
    if mcp_server_passed and bot_passed and api_server_passed and dashboard_server_passed:
        logger.info("All tests PASSED")
        return 0
    else:
        logger.warning("Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
