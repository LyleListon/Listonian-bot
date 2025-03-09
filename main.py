"""
Main Entry Point for Arbitrage Bot
Coordinates all components and provides clean startup/shutdown
"""

import os
import sys
import logging
import signal
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Import logging configuration
from arbitrage_bot.utils.logger_config import (
    setup_logging,
    log_metric,
    log_opportunity,
    log_execution,
    log_system_metrics
)

# Configure logging
from arbitrage_bot.utils.config_loader import (
    create_config_loader,
    ConfigurationError,
    InitializationError,
    resolve_secure_values
)
from arbitrage_bot.utils.secure_env import init_secure_environment

logger = logging.getLogger('ArbitrageBot')

class GasOptimizerError(InitializationError):
    """Error raised when gas optimizer initialization fails."""
    pass

class ArbitrageBot:
    """Main arbitrage bot class coordinating all components"""
    
    class DashboardError(Exception):
        """Error raised when dashboard operations fail."""
        pass
        
    class ArbitrageExecutionError(Exception):
        """Error raised when arbitrage execution fails."""
        pass
    
    def __init__(self):
        """Initialize basic components"""
        # Set up logging first
        setup_logging(logging.INFO)
        
        # Load environment variables
        load_dotenv('.env.production')
        self._validate_environment()

        # Initialize secure environment
        init_secure_environment()
        
        # Initialize config
        self.config_loader = create_config_loader()
        
        # Initialize state
        self.is_running = False
        self.dashboard_process = None
        self.web3_manager = None
        self.arbitrage_executor = None
        self.performance_tracker = None
        
        # Initialize asyncio event for shutdown
        self.shutdown_event = asyncio.Event()
    
    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = ['PRIVATE_KEY', 'BASE_RPC_URL', 'WALLET_ADDRESS']
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = "Missing required environment variables: " + ", ".join(missing_vars)
            raise ValueError(error_msg)
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Import required components
            from arbitrage_bot.core.web3.web3_manager import create_web3_manager
            from arbitrage_bot.core.market_analyzer import create_market_analyzer
            from arbitrage_bot.core.ml.ml_system import create_ml_system
            from arbitrage_bot.core.analytics.analytics_system import create_analytics_system
            from arbitrage_bot.core.monitoring.transaction_monitor import create_transaction_monitor
            from arbitrage_bot.core.execution.arbitrage_executor import create_arbitrage_executor
            from arbitrage_bot.core.metrics.portfolio_tracker import create_portfolio_tracker
            from arbitrage_bot.core.dex.dex_manager import create_dex_manager
            from arbitrage_bot.core.gas.gas_optimizer import create_gas_optimizer
            from arbitrage_bot.core.memory import get_memory_bank
            from arbitrage_bot.core.unified_balance_manager import UnifiedBalanceManager
            from arbitrage_bot.core.unified_flash_loan_manager import create_unified_flash_loan_manager
            from arbitrage_bot.core.alerts.alert_system import create_alert_system
            
            # Get config
            config = self.config_loader.get_config()

            # Resolve secure values in config
            config = resolve_secure_values(config)
            logger.info("Resolved secure values in config")
            
            # Initialize Web3 manager first
            logger.info("Initializing Web3 manager...")
            self.web3_manager = await create_web3_manager(
                provider_url=os.getenv('BASE_RPC_URL'),
                chain_id=config['network']['chainId'],
                private_key=os.getenv('PRIVATE_KEY')
            )
            logger.info("Web3 manager created")
            
            # Initialize DEX manager
            logger.info("Initializing DEX manager...")
            self.dex_manager = await create_dex_manager(self.web3_manager, config)
            logger.info("DEX manager initialized")
            
            # Initialize market analyzer with DEX manager
            self.market_analyzer = create_market_analyzer(dex_manager=self.dex_manager)
            logger.info("Market analyzer initialized with DEX manager")
            
            # Initialize ML system
            self.ml_system = await create_ml_system(None, self.market_analyzer, config)
            
            # Initialize portfolio tracker (serves as performance tracker)
            self.portfolio_tracker = await create_portfolio_tracker(
                web3_manager=self.web3_manager,
                wallet_address=self.web3_manager.wallet_address,
                config=config
            )
            self.performance_tracker = self.portfolio_tracker
            
            # Initialize gas optimizer
            logger.info("Initializing gas optimizer...")
            self.gas_optimizer = await create_gas_optimizer(
                dex_manager=self.dex_manager,
                web3_manager=self.web3_manager
            )
            if not await self.gas_optimizer.initialize():
                raise GasOptimizerError("Gas optimizer initialization failed")
            logger.info("Gas optimizer initialized")
            
            # Initialize analytics system
            self.analytics_system = await create_analytics_system(config)
            self.analytics_system.web3_manager = self.web3_manager
            self.analytics_system.wallet_address = self.web3_manager.wallet_address
            
            # Set dex_manager in analytics system
            self.analytics_system.set_dex_manager(self.dex_manager)
            
            # Set analytics in ML system
            self.ml_system.analytics = self.analytics_system
            
            # Initialize memory bank
            self.memory_bank = get_memory_bank()
            
            # Initialize transaction monitor
            logger.info("Initializing transaction monitor...")
            self.tx_monitor = await create_transaction_monitor(
                self.web3_manager, self.analytics_system, self.ml_system, self.dex_manager)
            logger.info("Transaction monitor initialized")
            
            # Initialize balance manager
            logger.info("Initializing balance manager...")
            self.balance_manager = await UnifiedBalanceManager.get_instance(
                web3_manager=self.web3_manager,
                dex_manager=self.dex_manager,
                config=config
            )
            logger.info("Balance manager initialized")
            
            # Initialize alert system
            self.alert_system = await create_alert_system(
                web3_manager=self.web3_manager,
                dex_manager=self.dex_manager,
                analytics_system=self.analytics_system,
                config=config
            )

            # Initialize flash loan manager
            self.flash_loan_manager = await create_unified_flash_loan_manager(
                web3_manager=self.web3_manager,
                config=config
            )
            
            # Finally, initialize arbitrage executor with all components
            logger.info("Initializing arbitrage executor...")
            self.arbitrage_executor = await create_arbitrage_executor(
                web3_manager=self.web3_manager,
                dex_manager=self.dex_manager,
                gas_optimizer=self.gas_optimizer,
                tx_monitor=self.tx_monitor,
                market_analyzer=self.market_analyzer,
                analytics_system=self.analytics_system,
                ml_system=self.ml_system,
                memory_bank=self.memory_bank,
                flash_loan_manager=self.flash_loan_manager,
                balance_manager=self.balance_manager,
                config=config
            )
            
            logger.info("ArbitrageBot initialized successfully")
            return True
        
        except (ConfigurationError, GasOptimizerError, InitializationError) as e:
            logger.error("Initialization error: %s", str(e))
            raise

    async def start(self):
        """Start the arbitrage bot"""
        try:
            logger.info("Starting arbitrage bot...")
            
            # Initialize components
            if not await self.initialize():
                raise InitializationError("Failed to initialize components")
            
            self.is_running = True
            
            # Register signal handlers
            self._register_signal_handlers()
            
            # Start dashboard if enabled
            if self.config_loader.get_config().get('dashboard', {}).get('enabled', True):
                # Set dashboard WebSocket port
                websocket_port = 8771
                os.environ['DASHBOARD_WEBSOCKET_PORT'] = str(websocket_port)
                
                # Set analytics system reference
                os.environ['ANALYTICS_SYSTEM_ID'] = str(id(self.analytics_system))
                await self._start_dashboard()
            
            # Main arbitrage loop
            await self._run_arbitrage_loop()
        
        except (ConfigurationError, GasOptimizerError, InitializationError, self.DashboardError) as e:
            logger.error("Failed to start arbitrage bot: %s", str(e))
            await self.stop()
    
    async def stop(self):
        """Stop the arbitrage bot gracefully"""
        try:
            logger.info("Stopping arbitrage bot...")
            self.is_running = False
            self.shutdown_event.set()
            
            # Stop dashboard if running
            if self.dashboard_process:
                self.dashboard_process.terminate()
                self.dashboard_process = None
            
            # Perform cleanup
            await self._cleanup()
            
            logger.info("Arbitrage bot stopped successfully")
        
        except (self.DashboardError, IOError) as e:
            logger.error("Error during bot shutdown: %s", str(e))
            raise
    
    async def _run_arbitrage_loop(self):
        """Main arbitrage execution loop"""
        logger.info("Starting arbitrage loop...")
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Get opportunities from market analyzer
                opportunities = await self.market_analyzer.get_opportunities()
                if opportunities:
                    sorted_opportunities = sorted(opportunities, key=lambda x: x.profit_margin, reverse=True)
                    for opportunity in sorted_opportunities:
                        # Log opportunity before execution
                        log_opportunity({
                            'token_id': opportunity.token_id,
                            'token_address': opportunity.token_address,
                            'buy_dex': opportunity.buy_dex,
                            'sell_dex': opportunity.sell_dex,
                            'buy_price': float(opportunity.buy_price),
                            'sell_price': float(opportunity.sell_price),
                            'profit_margin': float(opportunity.profit_margin),
                            'timestamp': opportunity.timestamp
                        })
                        
                        # Execute opportunity
                        success = await self.arbitrage_executor.execute_opportunity(opportunity)
                        
                        # Log execution result
                        if success and hasattr(opportunity, 'tx_hash'):
                            log_execution(
                                tx_hash=opportunity.tx_hash,
                                status='success',
                                profit=float(opportunity.profit_margin),
                                gas_cost=getattr(opportunity, 'gas_cost', 0)
                            )
                
                # Add delay between iterations and log metrics every 60 seconds
                current_time = asyncio.get_event_loop().time()
                if not hasattr(self, '_last_metrics_time') or current_time - self._last_metrics_time >= 60:
                    import psutil
                    process = psutil.Process()
                    log_system_metrics(
                        memory_usage=process.memory_info().rss / 1024 / 1024,  # Convert to MB
                        cpu_usage=process.cpu_percent(),
                        thread_count=process.num_threads(),
                        active_approvals=len(self.arbitrage_executor._pending_approvals)
                    )
                    self._last_metrics_time = current_time

                await asyncio.sleep(
                    self.config_loader.get_config()
                    .get('execution', {})
                    .get('loop_interval', 0.1)  # Reduced to 0.1s for faster response
                )
            
            except (self.ArbitrageExecutionError, IOError, TimeoutError) as e:
                logger.error("Arbitrage execution failed: %s", str(e))
                await asyncio.sleep(5)  # Brief delay before retry
    
    async def _start_dashboard(self):
        """Start the dashboard process"""
        try:
            # Get dashboard port from config
            port = self.config_loader.get_config().get('dashboard', {}).get('port', 5000)
            os.environ['DASHBOARD_PORT'] = str(port)
            
            # Start dashboard as a separate Python process
            dashboard_script = str(Path(__file__).parent / 'arbitrage_bot' / 'dashboard' / 'run.py')
            
            # Start dashboard process
            self.dashboard_process = subprocess.Popen([sys.executable, dashboard_script])
            
            logger.info("Dashboard started successfully")
        
        except (FileNotFoundError, subprocess.SubprocessError, OSError) as e:
            raise self.DashboardError("Failed to start dashboard: %s" % str(e)) from e
    
    async def _cleanup(self):
        """Perform cleanup operations"""
        try:
            # Save final performance metrics
            if self.performance_tracker:
                summary = await self.performance_tracker.get_performance_summary()
                logger.info("Final performance summary: %s", str(summary))
                
                # Log final metrics
                for metric, value in summary.items():
                    log_metric("final_" + metric, value)
            
            # Close database connections
            # Any other cleanup needed
            
            logger.info("Cleanup completed successfully")
        
        except IOError as e:
            logger.error("Cleanup operation failed: %s", str(e))
            raise
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        loop = asyncio.get_running_loop()
        
        def signal_handler(signum, frame):
            logger.info("Received signal %s", str(signum))
            loop.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

async def async_main():
    """Async main entry point"""
    try:
        # Create and start bot
        bot = ArbitrageBot()
        await bot.start()
    
    except ConfigurationError as e:
        logger.error("Configuration error: %s", str(e))
        sys.exit(1)
    except (ArbitrageBot.ArbitrageExecutionError, ArbitrageBot.DashboardError, IOError) as e:
        logger.error("Critical error: %s", str(e))
        sys.exit(1)

def main():
    """Synchronous entry point that runs the async main"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Critical error: %s", str(e), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
