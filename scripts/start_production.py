#!/usr/bin/env python3
"""
Production Startup Script

This script starts the Listonian Arbitrage Bot in production mode.
It loads environment variables from .env.production, starts the MCP server,
the arbitrage bot, and the dashboard with real data only.
"""

import os
import sys
import logging
import subprocess
import time
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
        logging.FileHandler("logs/production_startup.log"),
    ],
)
logger = logging.getLogger(__name__)

def create_directories():
    """Create necessary directories."""
    try:
        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        logger.info("Created logs directory")

        # Create data directory
        os.makedirs("data", exist_ok=True)
        logger.info("Created data directory")

        return True
    except Exception as e:
        logger.exception(f"Error creating directories: {str(e)}")
        return False

def check_database_connection():
    """Check if the database connection is working."""
    try:
        # Get database URI from environment
        db_uri = os.environ.get("DATABASE_URI", "")

        if not db_uri:
            logger.warning("DATABASE_URI not set, skipping database connection check")
            return True

        # For PostgreSQL, we can use psycopg2 to check the connection
        if db_uri.startswith("postgresql://"):
            try:
                import psycopg2

                # Parse the URI to get connection parameters
                # Format: postgresql://username:password@host:port/dbname
                uri_parts = db_uri.replace("postgresql://", "").split("/")
                dbname = uri_parts[-1]
                connection_parts = uri_parts[0].split("@")
                auth_parts = connection_parts[0].split(":")
                host_parts = connection_parts[1].split(":")

                username = auth_parts[0]
                password = auth_parts[1] if len(auth_parts) > 1 else ""
                host = host_parts[0]
                port = host_parts[1] if len(host_parts) > 1 else "5432"

                # Connect to the database
                conn = psycopg2.connect(
                    dbname=dbname,
                    user=username,
                    password=password,
                    host=host,
                    port=port
                )

                # Close the connection
                conn.close()

                logger.info("Database connection successful")
                return True
            except ImportError:
                logger.warning("psycopg2 not installed, skipping database connection check")
                return True
            except Exception as e:
                logger.error(f"Error connecting to database: {str(e)}")
                return False

        # For other database types, we'll skip the check for now
        logger.warning(f"Unsupported database type: {db_uri.split('://')[0]}, skipping connection check")
        return True

    except Exception as e:
        logger.exception(f"Error checking database connection: {str(e)}")
        return False

def check_rpc_connection():
    """Check if the RPC connection is working."""
    try:
        # Get RPC URL from environment
        rpc_url = os.environ.get("BASE_RPC_URL", "")

        if not rpc_url:
            logger.warning("BASE_RPC_URL not set, skipping RPC connection check")
            return True

        # Use web3.py to check the connection
        try:
            from web3 import Web3

            # Connect to the RPC endpoint
            web3 = Web3(Web3.HTTPProvider(rpc_url))

            # Check if connected
            if web3.is_connected():
                # Get the latest block number to verify the connection
                block_number = web3.eth.block_number
                logger.info(f"RPC connection successful, latest block: {block_number}")
                return True
            else:
                logger.error(f"Failed to connect to RPC endpoint: {rpc_url}")
                return False

        except ImportError:
            logger.warning("web3 not installed, skipping RPC connection check")
            return True
        except Exception as e:
            logger.error(f"Error connecting to RPC endpoint: {str(e)}")
            return False

    except Exception as e:
        logger.exception(f"Error checking RPC connection: {str(e)}")
        return False

def start_mcp_server():
    """Start the MCP server."""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent

        # MCP server script path
        mcp_script = project_root / "run_base_dex_scanner_mcp_with_api.py"

        logger.info(f"Starting MCP server: {mcp_script}")

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

        # Wait for the server to start
        time.sleep(5)

        # Check if the process is still running
        if process.poll() is None:
            logger.info("MCP server is running")
            return process
        else:
            # Process has terminated
            stdout, _ = process.communicate()
            logger.error(f"MCP server failed to start: {stdout}")
            return None

    except Exception as e:
        logger.exception(f"Error starting MCP server: {str(e)}")
        return None

def start_bot():
    """Start the arbitrage bot."""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent

        # Bot script path
        bot_script = project_root / "run_bot.py"

        logger.info(f"Starting arbitrage bot: {bot_script}")

        # Set environment variables
        env = os.environ.copy()
        env['USE_REAL_DATA_ONLY'] = 'true'
        env['PRODUCTION_MODE'] = 'true'

        # Start the bot as a subprocess
        process = subprocess.Popen(
            [sys.executable, str(bot_script)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Log the process ID
        logger.info(f"Arbitrage bot started with PID: {process.pid}")

        # Wait for the bot to start
        time.sleep(5)

        # Check if the process is still running
        if process.poll() is None:
            logger.info("Arbitrage bot is running")
            return process
        else:
            # Process has terminated
            stdout, _ = process.communicate()
            logger.error(f"Arbitrage bot failed to start: {stdout}")
            return None

    except Exception as e:
        logger.exception(f"Error starting arbitrage bot: {str(e)}")
        return None

def start_dashboard():
    """Start the dashboard."""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent

        # Dashboard script path
        dashboard_script = project_root / "run_dashboard.py"

        logger.info(f"Starting dashboard: {dashboard_script}")

        # Set environment variables
        env = os.environ.copy()
        env['USE_REAL_DATA_ONLY'] = 'true'
        env['PRODUCTION_MODE'] = 'true'

        # Start the dashboard as a subprocess
        process = subprocess.Popen(
            [sys.executable, str(dashboard_script)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Log the process ID
        logger.info(f"Dashboard started with PID: {process.pid}")

        # Wait for the dashboard to start
        time.sleep(5)

        # Check if the process is still running
        if process.poll() is None:
            logger.info("Dashboard is running")
            return process
        else:
            # Process has terminated
            stdout, _ = process.communicate()
            logger.error(f"Dashboard failed to start: {stdout}")
            return None

    except Exception as e:
        logger.exception(f"Error starting dashboard: {str(e)}")
        return None

def main():
    """Main entry point for the script."""
    try:
        logger.info("Starting Listonian Arbitrage Bot in production mode (REAL DATA ONLY)")

        # Set real data only flag
        os.environ['USE_REAL_DATA_ONLY'] = 'true'
        os.environ['PRODUCTION_MODE'] = 'true'

        # Load environment variables
        if not load_env(".env.production"):
            logger.error("Failed to load environment variables")
            return 1

        # Create necessary directories
        if not create_directories():
            logger.error("Failed to create directories")
            return 1

        # Check database connection
        if not check_database_connection():
            logger.error("Failed to connect to database")
            return 1

        # Check RPC connection
        if not check_rpc_connection():
            logger.error("Failed to connect to RPC endpoint")
            return 1

        # Start MCP server
        mcp_process = start_mcp_server()
        if not mcp_process:
            logger.error("Failed to start MCP server")
            return 1

        # Start arbitrage bot
        bot_process = start_bot()
        if not bot_process:
            logger.error("Failed to start arbitrage bot")
            # Terminate MCP server
            mcp_process.terminate()
            mcp_process.wait()
            return 1

        # Start dashboard
        dashboard_process = start_dashboard()
        if not dashboard_process:
            logger.error("Failed to start dashboard")
            # Terminate MCP server and bot
            mcp_process.terminate()
            mcp_process.wait()
            bot_process.terminate()
            bot_process.wait()
            return 1

        logger.info("Listonian Arbitrage Bot started successfully in production mode")
        logger.info(f"Dashboard available at: http://localhost:9050")

        # Keep the script running to maintain all processes
        try:
            while True:
                # Check if any process has terminated
                if mcp_process.poll() is not None:
                    logger.error("MCP server has terminated unexpectedly")
                    return 1

                if bot_process.poll() is not None:
                    logger.error("Arbitrage bot has terminated unexpectedly")
                    return 1

                if dashboard_process.poll() is not None:
                    logger.error("Dashboard has terminated unexpectedly")
                    return 1

                # Sleep for a while
                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")

            # Terminate all processes
            dashboard_process.terminate()
            dashboard_process.wait()
            logger.info("Dashboard terminated")

            bot_process.terminate()
            bot_process.wait()
            logger.info("Arbitrage bot terminated")

            mcp_process.terminate()
            mcp_process.wait()
            logger.info("MCP server terminated")

        return 0

    except Exception as e:
        logger.exception(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())