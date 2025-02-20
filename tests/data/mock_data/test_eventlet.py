"""Test eventlet functionality."""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_eventlet():
    """Test eventlet installation and patching."""
    try:
        logger.info("Testing eventlet installation...")
        import eventlet
        logger.info("✓ Eventlet imported successfully")
        
        logger.info("Testing eventlet version...")
        logger.info(f"Eventlet version: {eventlet.__version__}")
        
        logger.info("Testing monkey patching...")
        eventlet.monkey_patch(all=True)
        
        # Test green thread functionality first
        logger.info("Testing green thread...")
        def green_thread_test():
            logger.info("Green thread started")
            eventlet.sleep(0.1)
            logger.info("Green thread completed")
            return True
            
        gt = eventlet.spawn(green_thread_test)
        result = gt.wait()
        if not result:
            raise RuntimeError("Green thread test failed")
        logger.info("✓ Green thread test passed")
        
        # Test socket patching
        import socket
        logger.info("Testing socket patching...")
        is_socket_patched = 'eventlet.green.socket' in str(socket.socket)
        logger.info(f"Socket patched: {is_socket_patched}")
        if not is_socket_patched:
            raise RuntimeError("Socket not properly patched")
        logger.info("✓ Socket patching verified")
        
        # Test threading patching
        import threading
        logger.info("Testing threading patching...")
        is_threading_patched = 'eventlet.green.threading' in str(threading.Thread)
        logger.info(f"Threading patched: {is_threading_patched}")
        if not is_threading_patched:
            raise RuntimeError("Threading not properly patched")
        logger.info("✓ Threading patching verified")
        
        # Test time patching
        import time
        logger.info("Testing time patching...")
        start = time.time()
        eventlet.sleep(0.1)
        duration = time.time() - start
        logger.info(f"Sleep duration: {duration:.3f}s")
        if duration < 0.1:
            raise RuntimeError("Time sleep not properly patched")
        logger.info("✓ Time patching verified")
        
        logger.info("✓ All eventlet tests completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Eventlet test failed: {e}")
        return False

if __name__ == "__main__":
    if not test_eventlet():
        sys.exit(1)