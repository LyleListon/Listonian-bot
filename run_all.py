#!/usr/bin/env python
"""Run all components of the arbitrage bot."""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("run_all")


def run_all(env: str = "test"):
    """Run all components.
    
    Args:
        env: Environment to use.
    """
    logger.info(f"Running all components in {env} environment")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Start MCP server
    logger.info("Starting MCP server")
    mcp_process = subprocess.Popen(
        ["python", "run_mcp_server.py", "--env", env],
        stdout=open("logs/mcp.log", "w"),
        stderr=subprocess.STDOUT,
    )
    
    # Wait for MCP server to start
    time.sleep(2)
    
    # Start bot
    logger.info("Starting bot")
    bot_process = subprocess.Popen(
        ["python", "run_bot.py", "--env", env],
        stdout=open("logs/bot.log", "w"),
        stderr=subprocess.STDOUT,
    )
    
    # Wait for bot to start
    time.sleep(2)
    
    # Start API server
    logger.info("Starting API server")
    api_process = subprocess.Popen(
        ["python", "bot_api_server.py", "--env", env],
        stdout=open("logs/api.log", "w"),
        stderr=subprocess.STDOUT,
    )
    
    # Wait for API server to start
    time.sleep(2)
    
    # Start dashboard server
    logger.info("Starting dashboard server")
    dashboard_process = subprocess.Popen(
        ["python", "run_dashboard.py", "--env", env],
        stdout=open("logs/dashboard.log", "w"),
        stderr=subprocess.STDOUT,
    )
    
    # Wait for dashboard server to start
    time.sleep(2)
    
    # Print URLs
    logger.info("All components started")
    logger.info("API server: http://localhost:8001")
    logger.info("Dashboard: http://localhost:8081")
    
    # Wait for interrupt
    try:
        while True:
            # Check if processes are still running
            if mcp_process.poll() is not None:
                logger.error(f"MCP server process terminated with code {mcp_process.returncode}")
                break
            
            if bot_process.poll() is not None:
                logger.error(f"Bot process terminated with code {bot_process.returncode}")
                break
            
            if api_process.poll() is not None:
                logger.error(f"API server process terminated with code {api_process.returncode}")
                break
            
            if dashboard_process.poll() is not None:
                logger.error(f"Dashboard server process terminated with code {dashboard_process.returncode}")
                break
            
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    
    # Stop all processes
    logger.info("Stopping all processes")
    
    for process in [dashboard_process, api_process, bot_process, mcp_process]:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5.0)
    
    logger.info("All processes stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run all components of the arbitrage bot")
    parser.add_argument(
        "--env",
        type=str,
        default="test",
        help="Environment to use (development, production, test)",
    )
    args = parser.parse_args()
    
    run_all(args.env)


if __name__ == "__main__":
    main()
