"""
Entry point script that ensures proper eventlet monkey patching.
This script must be run directly, not through python -m.
"""

# Import minimal modules
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def patch_and_verify():
    """Apply and verify eventlet monkey patching."""
    try:
        # Import and patch eventlet before anything else
        import eventlet
        eventlet.monkey_patch(
            os=True,
            select=True,
            socket=True,
            thread=True,
            time=True,
            psycopg=False,
            MySQLdb=False,
            builtins=True
        )
        
        # Verify patching
        import socket
        import threading
        import time
        
        is_socket_patched = 'eventlet.green.socket' in str(socket.socket)
        is_threading_patched = 'eventlet.green.threading' in str(threading.Thread)
        is_time_patched = hasattr(time.sleep, '__module__') and 'eventlet' in time.sleep.__module__
        
        if not all([is_socket_patched, is_threading_patched, is_time_patched]):
            modules_not_patched = []
            if not is_socket_patched:
                modules_not_patched.append('socket')
            if not is_threading_patched:
                modules_not_patched.append('threading')
            if not is_time_patched:
                modules_not_patched.append('time')
            
            raise RuntimeError(f"Modules not properly patched: {', '.join(modules_not_patched)}")
            
        logger.info("✓ All modules successfully patched")
        return True
        
    except Exception as e:
        logger.error(f"Patch verification failed: {e}")
        return False

if __name__ == "__main__":
    try:
        # Apply and verify patching
        if not patch_and_verify():
            logger.error("Failed to verify eventlet monkey patching")
            sys.exit(1)
        
        # Now that patching is verified, import and run the dashboard
        import os
        import json
        from pathlib import Path
        
        # Load config
        config_path = Path(__file__).parent / 'configs' / 'config.json'
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                if 'dashboard' in config:
                    port = config['dashboard'].get('port', 5001)
                    os.environ['DASHBOARD_PORT'] = str(port)
        
        # Import and run dashboard
        from arbitrage_bot.dashboard.run import main
        logger.info("Starting dashboard...")
        main()
        
    except Exception as e:
        logger.error(f"Critical initialization error: {e}")
        sys.exit(1)