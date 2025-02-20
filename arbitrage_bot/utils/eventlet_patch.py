"""Initialize eventlet monkey patching."""

import sys
import logging

import asyncio

logger = logging.getLogger(__name__)

def apply_patches():
    """Apply eventlet monkey patches in the correct order."""
    try:
        # Import eventlet
        import eventlet
        
        # Apply patches in specific order
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
        
        # Initialize event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("✓ Event loop initialized")
        
        # Import modules after patching
        import socket
        import time
        import select
        import threading
        import builtins
        
        # Log patching status
        logger.info("✓ Eventlet patches applied")
        
        # Basic verification without raising errors
        is_socket_patched = 'eventlet.green.socket' in str(socket.socket)
        is_time_patched = hasattr(time.sleep, '__module__') and 'eventlet' in time.sleep.__module__
        is_select_patched = hasattr(select.select, '__module__') and 'eventlet' in select.select.__module__
        
        if not is_socket_patched:
            logger.warning("Socket module may not be fully patched")
        if not is_time_patched:
            logger.warning("Time module may not be fully patched")
        if not is_select_patched:
            logger.warning("Select module may not be fully patched")
            
        return eventlet
        
    except Exception as e:
        logger.error(f"Failed to apply eventlet patches: {e}")
        # Continue without patching rather than raising an error
        import eventlet
        return eventlet

# Apply patches immediately and export eventlet
eventlet = apply_patches()
