"""
Entry point script that ensures eventlet patching happens before any other imports
"""
import logging
from pathlib import Path

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Import and apply eventlet patch first
        from arbitrage_bot.utils.eventlet_patch import eventlet
        
        # Import main after patching
        import main
        
        # Run main directly without mixing eventlet and asyncio
        main.main()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
