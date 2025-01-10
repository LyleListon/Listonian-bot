"""
Main Entry Point for Arbitrage Bot
Coordinates all components and provides clean startup/shutdown
"""

import os
import sys
import asyncio
import logging
import signal
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Configure logging
from arbitrage_bot.utils.config_loader import create_config_loader, ConfigurationError
logger = logging.getLogger('ArbitrageBot')

class ArbitrageBot:
    """Main arbitrage bot class coordinating all components"""
    
    def __init__(self):
        """Initialize basic components"""
        # Load environment variables
        load_dotenv()
        self._validate_environment()
        
        # Initialize config
        self.config_loader = create_config_loader()
        
        # Initialize state
        self.is_running = False
        self.dashboard_process = None
        self.web3_manager = None
        self.arbitrage_executor = None
        self.performance_tracker = None
        self.risk_manager = None
    
    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = ['PRIVATE_KEY', 'BASE_RPC_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    async def initialize(self):
        """Initialize all components asynchronously"""
        try:
            # Import and create component instances after config is loaded
            from arbitrage_bot.core.execution.arbitrage_executor import create_arbitrage_executor
            from arbitrage_bot.core.monitoring.performance_tracker import create_performance_tracker
            from arbitrage_bot.core.strategy.risk_manager import create_risk_manager
            from arbitrage_bot.core.web3.web3_manager import create_web3_manager
            
            # Get config
            config = self.config_loader.get_config()
            
            # Create component instances
            network_config = config.get('network', {})
            provider_url = network_config.get('rpc_url')
            chain_id = network_config.get('chainId')
            
            if not provider_url:
                raise ValueError("RPC URL not configured")
            if not chain_id:
                raise ValueError("Chain ID not configured")
            
            # Initialize Web3 manager first
            self.web3_manager = await create_web3_manager(
                provider_url=provider_url,
                chain_id=chain_id
            )
            if not self.web3_manager.chain_id:
                raise ValueError("Chain ID not available after Web3 initialization")
            
            # Initialize other components
            self.arbitrage_executor = await create_arbitrage_executor(config, self.web3_manager)
            self.performance_tracker = create_performance_tracker(config)
            self.risk_manager = create_risk_manager(config)
            
            logger.info("ArbitrageBot initialized successfully")
        
        except Exception as e:
            logger.error(f"Error initializing ArbitrageBot: {e}")
            raise
    
    async def start(self):
        """Start the arbitrage bot"""
        try:
            logger.info("Starting arbitrage bot...")
            
            # Initialize components
            await self.initialize()
            
            self.is_running = True
            
            # Register signal handlers
            self._register_signal_handlers()
            
            # Start dashboard if enabled
            if self.config_loader.get_config().get('dashboard', {}).get('enabled', True):
                await self._start_dashboard()
            
            # Main arbitrage loop
            await self._run_arbitrage_loop()
        
        except Exception as e:
            logger.error(f"Error starting arbitrage bot: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the arbitrage bot gracefully"""
        try:
            logger.info("Stopping arbitrage bot...")
            self.is_running = False
            
            # Stop dashboard if running
            if self.dashboard_process:
                self.dashboard_process.terminate()
                self.dashboard_process = None
            
            # Perform cleanup
            await self._cleanup()
            
            logger.info("Arbitrage bot stopped successfully")
        
        except Exception as e:
            logger.error(f"Error stopping arbitrage bot: {e}")
            raise
    
    async def _run_arbitrage_loop(self):
        """Main arbitrage execution loop"""
        logger.info("Starting arbitrage loop...")
        
        while self.is_running:
            try:
                # Detect opportunities
                opportunities = await self.arbitrage_executor.detect_opportunities()
                
                if opportunities:
                    logger.info(f"Found {len(opportunities)} opportunities")
                    
                    for opportunity in opportunities:
                        # Validate opportunity with risk manager
                        if not await self.risk_manager.validate_trade(opportunity):
                            continue
                        
                        # Execute trade
                        success = await self.arbitrage_executor.execute_trade(
                            opportunity,
                            self.web3_manager.wallet_address,
                            os.getenv('PRIVATE_KEY')
                        )
                        
                        if success:
                            logger.info("Trade executed successfully")
                        else:
                            logger.warning("Trade execution failed")
                
                # Add delay between iterations
                await asyncio.sleep(
                    self.config_loader.get_config()
                    .get('execution', {})
                    .get('loop_interval', 20)
                )
            
            except Exception as e:
                logger.error(f"Error in arbitrage loop: {e}")
                await asyncio.sleep(5)  # Short delay before retrying
    
    async def _start_dashboard(self):
        """Start the dashboard process"""
        try:
            # Get dashboard port from config
            port = self.config_loader.get_config().get('dashboard', {}).get('port', 5000)
            os.environ['DASHBOARD_PORT'] = str(port)
            
            # Start dashboard as a separate Python process
            dashboard_script = str(Path(__file__).parent / 'arbitrage_bot' / 'dashboard' / 'run.py')
            self.dashboard_process = subprocess.Popen([sys.executable, dashboard_script])
            
            logger.info("Dashboard started successfully")
        
        except Exception as e:
            logger.error(f"Error starting dashboard: {e}")
    
    async def _cleanup(self):
        """Perform cleanup operations"""
        try:
            # Save final performance metrics
            summary = self.performance_tracker.get_performance_summary()
            logger.info(f"Final performance summary: {summary}")
            
            # Close database connections
            # Any other cleanup needed
            
            logger.info("Cleanup completed successfully")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def async_main():
    """Async main entry point"""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create and start bot
        bot = ArbitrageBot()
        await bot.start()
    
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
