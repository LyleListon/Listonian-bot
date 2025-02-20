"""Run the dashboard application."""

# Import eventlet patch first to ensure monkey patching is done before any other imports
import eventlet
eventlet.monkey_patch(all=True)  # Use all=True to ensure complete patching

import os
import sys
import json
import logging
from pathlib import Path
from .app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def verify_monkey_patch():
    """Verify that eventlet monkey patching was successful."""
    try:
        import socket
        import threading
        import time
        
        # Verify socket patching
        is_socket_patched = 'eventlet.green.socket' in str(socket.socket)
        logger.info(f"Socket patched: {is_socket_patched}")
        
        # Verify threading patching
        is_threading_patched = 'eventlet.green.threading' in str(threading.Thread)
        logger.info(f"Threading patched: {is_threading_patched}")
        
        # Verify time patching
        is_time_patched = hasattr(time.sleep, '__module__') and 'eventlet' in time.sleep.__module__
        logger.info(f"Time patched: {is_time_patched}")
        
        if not all([is_socket_patched, is_threading_patched, is_time_patched]):
            raise RuntimeError("Not all modules properly patched")
            
        logger.info("✓ Eventlet monkey patching verified")
        return True
        
    except Exception as e:
        logger.error(f"Monkey patching verification failed: {e}")
        logger.error("Critical: Essential monkey patching verification failed")
        return False

def main():
    """Run the dashboard application."""
    try:
        # Verify monkey patching
        if not verify_monkey_patch():
            sys.exit(1)

        # Load config
        config_path = Path(__file__).parent.parent.parent / 'configs' / 'config.json'
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                if 'dashboard' in config:
                    port = config['dashboard'].get('port', 5001)
                    os.environ['DASHBOARD_PORT'] = str(port)

        # Create app and socketio
        app, socketio = create_app()
        
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

if __name__ == '__main__':
    main()
