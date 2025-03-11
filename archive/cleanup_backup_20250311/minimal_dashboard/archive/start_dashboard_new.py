"""
Start the dashboard application with proper eventlet monkey patching.
"""

# IMPORTANT: Monkey patch must happen before any other imports
import eventlet
eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)

# Now we can safely import the rest
import os
import sys
import json
import logging
from pathlib import Path
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def verify_monkey_patch():
    """Verify that eventlet monkey patching was successful."""
    try:
        logger.info(f"Socket module location: {socket.__file__}")
        logger.info(f"Socket module attributes: {dir(socket.socket)}")
        return 'eventlet' in str(socket.socket)
    except Exception as e:
        logger.error(f"Failed to verify monkey patch: {e}")
        return False

if __name__ == "__main__":
    try:
        # Verify monkey patching worked
        if not verify_monkey_patch():
            logger.error("Monkey patching verification failed")
            sys.exit(1)
        
        logger.info("Monkey patching verified successfully")
        
        # Import Flask app only after monkey patching is verified
        from arbitrage_bot.dashboard.app import create_app
        from arbitrage_bot.core.memory.bank import create_memory_bank
        from arbitrage_bot.core.storage.factory import create_storage_hub
        from arbitrage_bot.utils.config_loader import resolve_secure_values
        
        # Load config
        config_path = Path(__file__).parent / 'configs' / 'config.json'
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                if 'dashboard' in config:
                    port = config['dashboard'].get('port', 5001)
                    os.environ['DASHBOARD_PORT'] = str(port)

        # Resolve secure values
        config = resolve_secure_values(config)
        logger.info("Resolved secure values in config")

        # Initialize components with delays between each
        memory_bank = create_memory_bank()
        eventlet.sleep(2)  # Wait between initializations

        # Set up storage path
        storage_path = os.path.join(os.path.dirname(__file__), 'data', 'storage')
        os.makedirs(storage_path, exist_ok=True)
        storage_hub = create_storage_hub(base_path=storage_path, memory_bank=memory_bank)
        eventlet.sleep(2)  # Wait between initializations

        # Create app and socketio with pre-initialized components
        app, socketio = create_app(memory_bank=memory_bank, storage_hub=storage_hub)
        
        # Get port from environment or use default
        port = int(os.getenv('DASHBOARD_PORT', '5001'))
        
        # Start server
        logger.info(f"Starting dashboard on port {port}...")
        logger.info(f"Access the dashboard at http://localhost:{port}")
        
        # Run with eventlet
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            log_output=True
        )

    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        sys.exit(1)