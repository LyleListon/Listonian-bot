#!/usr/bin/env python3
"""
Production Runner Script

This script runs the Listonian Arbitrage Bot in production mode with the user's credentials.
It stops any running MCP servers, loads the environment variables from .env.production,
starts the MCP server with the production configuration, and tests the connections.
"""

import os
import sys
import logging
import subprocess
import time
import signal
import psutil
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the environment loader
from scripts.load_env import load_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def stop_running_servers():
    """Stop any running MCP servers."""
    try:
        logger.info("Stopping any running MCP servers...")
        
        # Find processes running the MCP server
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check if this is a Python process running the MCP server
                if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'run_base_dex_scanner_mcp' in cmdline:
                        logger.info(f"Found MCP server process: PID {proc.info['pid']}")
                        
                        # Kill the process
                        os.kill(proc.info['pid'], signal.SIGTERM)
                        logger.info(f"Sent SIGTERM to PID {proc.info['pid']}")
                        
                        # Wait for the process to terminate
                        try:
                            psutil.Process(proc.info['pid']).wait(timeout=5)
                            logger.info(f"Process {proc.info['pid']} terminated")
                        except psutil.TimeoutExpired:
                            # If the process doesn't terminate, force kill it
                            os.kill(proc.info['pid'], signal.SIGKILL)
                            logger.info(f"Sent SIGKILL to PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Wait a moment to ensure all processes are stopped
        time.sleep(2)
        
        logger.info("All MCP server processes stopped")
        return True
    
    except Exception as e:
        logger.exception(f"Error stopping MCP servers: {str(e)}")
        return False

def test_blockchain_connection():
    """Test the connection to the blockchain."""
    try:
        logger.info("Testing blockchain connection...")
        
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        
        # Test script path
        test_script = project_root / "scripts" / "test_blockchain_connection.py"
        
        # Run the test script
        result = subprocess.run(
            [sys.executable, str(test_script)],
            capture_output=True,
            text=True
        )
        
        # Check if the test was successful
        if result.returncode == 0:
            logger.info("Blockchain connection test passed")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"Blockchain connection test failed: {result.returncode}")
            logger.error(result.stdout)
            logger.error(result.stderr)
            return False
    
    except Exception as e:
        logger.exception(f"Error testing blockchain connection: {str(e)}")
        return False

def start_mcp_server():
    """Start the MCP server with production configuration."""
    try:
        logger.info("Starting MCP server with production configuration...")
        
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        
        # MCP server script path
        mcp_script = project_root / "run_base_dex_scanner_mcp_with_api.py"
        
        # Start the MCP server as a subprocess
        process = subprocess.Popen(
            [sys.executable, str(mcp_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Log the process ID
        logger.info(f"MCP server started with PID: {process.pid}")
        
        # Wait for the server to become responsive by polling the root endpoint
        start_time = time.time()
        timeout_seconds = 30
        poll_interval_seconds = 1
        server_ready = False
        mcp_url = f"http://{os.environ.get('MCP_SERVER_HOST', 'localhost')}:{os.environ.get('MCP_SERVER_PORT', '9050')}/"

        logger.info(f"Waiting up to {timeout_seconds} seconds for MCP server at {mcp_url} to respond...")
        while time.time() - start_time < timeout_seconds:
            # Check if the process terminated prematurely
            if process.poll() is not None:
                logger.error("MCP server process terminated unexpectedly during startup.")
                stdout, _ = process.communicate()
                logger.error(f"MCP server output: {stdout}")
                return None

            try:
                response = requests.get(mcp_url, timeout=poll_interval_seconds)
                if response.status_code == 200:
                    logger.info("MCP server responded successfully.")
                    server_ready = True
                    break
                else:
                    logger.debug(f"MCP server responded with status {response.status_code}, retrying...")
            except requests.exceptions.ConnectionError:
                logger.debug("MCP server not yet responding, retrying...")
            except requests.exceptions.Timeout:
                logger.debug("MCP server connection timed out, retrying...")
            except Exception as e:
                logger.warning(f"Unexpected error polling MCP server: {e}")

            time.sleep(poll_interval_seconds)

        if server_ready:
            logger.info("MCP server is running and responsive.")
            return process
        else:
            logger.error(f"MCP server did not become responsive within {timeout_seconds} seconds.")
            process.terminate()
            try:
                stdout, _ = process.communicate(timeout=5)
                logger.error(f"MCP server output upon termination: {stdout}")
            except subprocess.TimeoutExpired:
                logger.error("MCP server did not terminate gracefully, killing.")
                process.kill()
            return None
    
    except Exception as e:
        logger.exception(f"Error starting MCP server: {str(e)}")
        return None

def test_mcp_server():
    """Test the MCP server."""
    try:
        logger.info("Testing MCP server...")
        
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        
        # Test script path
        test_script = project_root / "scripts" / "test_production.py"
        
        # Run the test script
        result = subprocess.run(
            [sys.executable, str(test_script)],
            capture_output=True,
            text=True
        )
        
        # Check if the test was successful
        if result.returncode == 0:
            logger.info("MCP server test passed")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"MCP server test failed: {result.returncode}")
            logger.error(result.stdout)
            logger.error(result.stderr)
            return False
    
    except Exception as e:
        logger.exception(f"Error testing MCP server: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    try:
        logger.info("Starting Listonian Arbitrage Bot in production mode")
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Load environment variables from .env.production
        if not load_env(".env.production"):
            logger.error("Failed to load environment variables")
            return 1
        
        # Stop any running MCP servers
        if not stop_running_servers():
            logger.error("Failed to stop running MCP servers")
            return 1
        
        # Test blockchain connection
        if not test_blockchain_connection():
            logger.error("Blockchain connection test failed")
            return 1
        
        # Start MCP server
        mcp_process = start_mcp_server()
        if not mcp_process:
            logger.error("Failed to start MCP server")
            return 1
        
        # Test MCP server
        logger.info("Testing MCP server...")
        if not test_mcp_server():
            logger.error("MCP server test failed")
            
            # Stop the MCP server
            mcp_process.terminate()
            mcp_process.wait()
            
            return 1
        
        logger.info("Listonian Arbitrage Bot is now running in production mode")
        logger.info("Press Ctrl+C to stop")
        
        # Keep the script running to maintain the MCP server
        try:
            while True:
                # Check if the MCP server is still running
                if mcp_process.poll() is not None:
                    logger.error("MCP server has terminated unexpectedly")
                    return 1
                
                # Sleep for a while
                time.sleep(10)
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
            
            # Terminate the MCP server
            mcp_process.terminate()
            mcp_process.wait()
            
            logger.info("MCP server terminated")
        
        return 0
    
    except Exception as e:
        logger.exception(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())