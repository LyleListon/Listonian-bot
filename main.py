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
    
    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = ['PRIVATE_KEY', 'BASE_RPC_URL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    async def initialize(self):
        """Initialize all components asynchronously"""
        try:
            # Import required components
            from arbitrage_bot.core.web3.web3_manager import create_web3_manager
            from arbitrage_bot.core.analysis.market_analyzer import create_market_analyzer
            from arbitrage_bot.core.ml.ml_system import create_ml_system
            from arbitrage_bot.core.analytics.analytics_system import create_analytics_system
            from arbitrage_bot.core.monitoring.transaction_monitor import create_transaction_monitor
            from arbitrage_bot.core.execution.arbitrage_executor import create_arbitrage_executor
            from arbitrage_bot.core.metrics.portfolio_tracker import create_portfolio_tracker
            from arbitrage_bot.core.dex.dex_manager import create_dex_manager
            from arbitrage_bot.core.gas.gas_optimizer import create_gas_optimizer
            from arbitrage_bot.core.memory import get_memory_bank
            
            # Get config
            config = self.config_loader.get_config()
            
            # Set environment variables for Web3 manager
            os.environ['BASE_RPC_URL'] = config['network']['rpc_url']
            os.environ['CHAIN_ID'] = str(config['network']['chainId'])
            
            # Initialize Web3 manager first
            self.web3_manager = await create_web3_manager(config)
            
            # Initialize market analyzer
            self.market_analyzer = await create_market_analyzer(
                self.web3_manager,
                config
            )
            
            # Initialize ML system
            self.ml_system = await create_ml_system(
                None,  # Analytics will be set after creation
                self.market_analyzer,
                config
            )
            
            # Initialize portfolio tracker (serves as performance tracker)
            self.portfolio_tracker = await create_portfolio_tracker(
                web3_manager=self.web3_manager,
                wallet_address=self.web3_manager.wallet_address,
                config=config
            )
            self.performance_tracker = self.portfolio_tracker  # Use portfolio tracker for performance tracking
            
            # Initialize DEX manager
            self.dex_manager = await create_dex_manager(
                self.web3_manager,
                config
            )
            
            # Initialize gas optimizer
            self.gas_optimizer = await create_gas_optimizer(
                dex_manager=self.dex_manager,
                web3_manager=self.web3_manager
            )
            if not await self.gas_optimizer.initialize():
                raise Exception("Failed to initialize gas optimizer")
            
            # Initialize analytics system
            self.analytics_system = await create_analytics_system(config)
            
            # Set dex_manager in analytics system
            await self.analytics_system.set_dex_manager(self.dex_manager)
            
            # Set analytics in ML system
            self.ml_system.analytics = self.analytics_system
            
            # Initialize memory bank
            self.memory_bank = await get_memory_bank()
            
            # Initialize transaction monitor
            self.tx_monitor = await create_transaction_monitor(
                self.web3_manager,
                self.analytics_system,
                self.ml_system,
                self.dex_manager
            )
            
            # Initialize alert system
            from arbitrage_bot.core.alerts.alert_system import create_alert_system
            self.alert_system = await create_alert_system(
                self.analytics_system,
                self.tx_monitor,
                self.market_analyzer,
                config
            )
            
            # Finally, initialize arbitrage executor with all components
            self.arbitrage_executor = await create_arbitrage_executor(
                web3_manager=self.web3_manager,
                dex_manager=self.dex_manager,
                gas_optimizer=self.gas_optimizer,
                tx_monitor=self.tx_monitor,
                market_analyzer=self.market_analyzer,
                analytics_system=self.analytics_system,  # Pass analytics system
                ml_system=self.ml_system,  # Pass ML system
                memory_bank=self.memory_bank,  # Pass memory bank
                config=config
            )
            
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
                # Set dashboard WebSocket port
                os.environ['DASHBOARD_WEBSOCKET_PORT'] = '8771'
                # Set analytics system reference
                os.environ['ANALYTICS_SYSTEM_ID'] = str(id(self.analytics_system))
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
                # Detect and execute opportunities
                opportunities = await self.arbitrage_executor.detect_opportunities()
                if opportunities:
                    for opportunity in opportunities:
                        await self.arbitrage_executor.execute_opportunity(opportunity)
                
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
            
            # Create and connect Web3 manager before starting dashboard
            await self.web3_manager.connect()
            
            # Start dashboard process
            self.dashboard_process = subprocess.Popen([sys.executable, dashboard_script])
            
            logger.info("Dashboard started successfully")
        
        except Exception as e:
            logger.error(f"Error starting dashboard: {e}")
    
    async def _cleanup(self):
        """Perform cleanup operations"""
        try:
            # Save final performance metrics
            if self.performance_tracker:
                summary = await self.performance_tracker.get_performance_summary()
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
