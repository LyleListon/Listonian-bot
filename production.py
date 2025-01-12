"""
Production entry point for Arbitrage Bot
Uses production configuration and environment
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ProductionBot')

# Import main bot class
from main import ArbitrageBot

async def async_main():
    """Async production entry point"""
    try:
        # Ensure logs directory exists
        Path('logs').mkdir(exist_ok=True)
        
        # Load environment
        load_dotenv('.env')
        
        # Validate critical environment variables
        required_vars = [
            'WEB3_PROVIDER_URI',
            'PRIVATE_KEY',
            'WALLET_ADDRESS',
            'NETWORK_NAME',
            'CHAIN_ID'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
            
        # Map environment variables
        os.environ['BASE_RPC_URL'] = os.getenv('WEB3_PROVIDER_URI')
        
        # Create and start bot
        logger.info("Starting bot in production mode...")
        bot = ArbitrageBot()
        await bot.start()
        
    except Exception as e:
        logger.error(f"Production startup error: {e}")
        sys.exit(1)

def main():
    """Production main entry point"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
