#!/usr/bin/env python
"""
Dashboard Starter

This script starts the arbitrage system monitoring dashboard.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "dashboard.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("dashboard")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the arbitrage system dashboard")
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="Host to run the dashboard on (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080, 
        help="Port to run the dashboard on (default: 8080)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Run in debug mode"
    )
    parser.add_argument(
        "--config", 
        default="configs/production.json", 
        help="Path to configuration file (default: configs/production.json)"
    )
    return parser.parse_args()

def main():
    """Start the dashboard server."""
    args = parse_arguments()
    
    try:
        logger.info("=" * 70)
        logger.info("STARTING ARBITRAGE SYSTEM DASHBOARD")
        logger.info("=" * 70)
        
        # Add the project directory to the Python path
        project_dir = os.path.dirname(os.path.abspath(__file__))
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        
        # Import dashboard components
        try:
            from arbitrage_bot.dashboard.app import create_app
            from arbitrage_bot.utils.config_loader import load_config
        except ImportError as e:
            logger.error("Failed to import dashboard components: %s", e)
            logger.error("Make sure the arbitrage_bot package is installed")
            return 1
        
        # Load configuration
        logger.info("Loading configuration from %s", args.config)
        config = load_config(args.config)
        
        # Create and configure the dashboard app
        logger.info("Creating dashboard application")
        app = create_app(config)
        
        # Start the dashboard server
        logger.info("Starting dashboard server on %s:%s", args.host, args.port)
        logger.info("Dashboard URL: http://%s:%s", args.host, args.port)
        logger.info("Press Ctrl+C to stop the server")
        
        # Run the app
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Dashboard server stopped by user")
        return 0
    except Exception as e:
        logger.error("Error starting dashboard: %s", e, exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
