"""
Start the dashboard application with proper eventlet monkey patching.
"""

# Import essential modules first
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

try:
    # Import and initialize eventlet patching
    from arbitrage_bot.utils.eventlet_patch import verify_patch
    logger.info("Verifying eventlet patching...")
    
    if not verify_patch():
        logger.error("Failed to verify eventlet monkey patching")
        sys.exit(1)
    
    # Now that patching is verified, import other modules
    import os
    import json
    from pathlib import Path
    from arbitrage_bot.dashboard.run import main

    if __name__ == "__main__":
        try:
            # Load config
            config_path = Path(__file__).parent / 'configs' / 'config.json'
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                    if 'dashboard' in config:
                        port = config['dashboard'].get('port', 5001)
                        os.environ['DASHBOARD_PORT'] = str(port)

            # Start dashboard
            logger.info("Starting dashboard...")
            main()

        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            sys.exit(1)

except Exception as e:
    logger.error(f"Critical initialization error: {e}")
    sys.exit(1)
