#!/usr/bin/env python
"""Check if the arbitrage bot components are running."""

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
logger = logging.getLogger("check_components")


def check_process_running(name: str, pid: int) -> bool:
    """Check if a process is running.
    
    Args:
        name: Process name.
        pid: Process ID.
        
    Returns:
        True if the process is running, False otherwise.
    """
    try:
        # Check if process exists
        os.kill(pid, 0)
        logger.info(f"Process {name} (PID {pid}) is running")
        return True
    except OSError:
        logger.warning(f"Process {name} (PID {pid}) is not running")
        return False


def check_api_server() -> bool:
    """Check if the API server is running.
    
    Returns:
        True if the API server is running, False otherwise.
    """
    try:
        # Try to connect to the API server
        response = requests.get("http://localhost:8000/api/v1/status", timeout=5)
        
        if response.status_code == 200:
            logger.info(f"API server is running: {response.json()}")
            return True
        else:
            logger.warning(f"API server returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to connect to API server: {e}")
        return False


def check_dashboard_server() -> bool:
    """Check if the dashboard server is running.
    
    Returns:
        True if the dashboard server is running, False otherwise.
    """
    try:
        # Try to connect to the dashboard server
        response = requests.get("http://localhost:8080", timeout=5)
        
        if response.status_code == 200:
            logger.info("Dashboard server is running")
            return True
        else:
            logger.warning(f"Dashboard server returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to connect to dashboard server: {e}")
        return False


def find_python_processes() -> List[Dict[str, Any]]:
    """Find all Python processes.
    
    Returns:
        List of Python processes.
    """
    try:
        # Get list of running Python processes
        if sys.platform == "win32":
            # Windows
            output = subprocess.check_output(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                universal_newlines=True,
            )
            
            # Parse output
            processes = []
            for line in output.strip().split("\n")[1:]:  # Skip header
                if not line:
                    continue
                
                # Remove quotes and split by comma
                parts = line.strip('"').split('","')
                
                if len(parts) >= 2:
                    name = parts[0]
                    pid = int(parts[1])
                    processes.append({"name": name, "pid": pid})
            
            return processes
        else:
            # Unix-like
            output = subprocess.check_output(
                ["ps", "-ef", "|", "grep", "python"],
                universal_newlines=True,
                shell=True,
            )
            
            # Parse output
            processes = []
            for line in output.strip().split("\n"):
                if "grep python" in line:
                    continue
                
                parts = line.split()
                
                if len(parts) >= 2:
                    pid = int(parts[1])
                    name = "python"
                    processes.append({"name": name, "pid": pid})
            
            return processes
    except subprocess.CalledProcessError as e:
        logger.error(f"Error finding Python processes: {e}")
        return []


def main():
    """Main entry point."""
    logger.info("Checking if arbitrage bot components are running")
    
    # Check API server
    api_running = check_api_server()
    
    # Check dashboard server
    dashboard_running = check_dashboard_server()
    
    # Find Python processes
    python_processes = find_python_processes()
    logger.info(f"Found {len(python_processes)} Python processes")
    
    for process in python_processes:
        logger.info(f"Python process: {process}")
    
    # Check if any components are running
    if api_running or dashboard_running or python_processes:
        logger.info("Some components are running")
    else:
        logger.warning("No components are running")


if __name__ == "__main__":
    main()
