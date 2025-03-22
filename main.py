w""
Enhanced Arbitrage Bot Main Module

This module orchestrates the enhanced arbitrage system with:
- Parallel price monitoring
- Multi-path arbitrage execution
- Advanced risk management
- Performance monitoring
"""

import asyncio
import logging
import signal
from typing import Dict, List, Optional
from decimal import Decimal
from web3 import Web3

from arbitrage_bot.core.market.enhanced_market_analyzer import EnhancedMarketAnalyzer
from arbitrage_bot.core.market.price_validator import PriceValidator
from arbitrage_bot.core.unified_flash_loan_manager import EnhancedFlashLoanManager
from arbitrage_bot.core.execution.arbitrage_executor import EnhancedArbitrageExecutor
from arbitrage_bot.core.web3.web3_manager import Web3Manager
from arbitrage_bot.core.web3.flashbots.flashbots_provider import FlashbotsProvider, create_flashbots_provider
from arbitrage_bot.core.memory.memory_bank import MemoryBank
from arbitrage_bot.core.ml.model_interface import MLSystem
from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.utils.secure_env import SecureEnvironment

logger = logging.getLogger(__name__)

class ArbitrageBot:
    """Enhanced arbitrage bot with advanced monitoring and execution."""

    def __init__(self):
        """Initialize the arbitrage bot."""
        self.running = False
        self._shutdown_event = asyncio.Event()
        self._components_initialized = False
        
        # Component instances will be set in initialize()
        self.web3_manager = None
        self.flashbots_provider = None
        self.memory_bank = None
        self.ml_system = None
        self.market_analyzer = None
        self.price_validator = None
        self.flash_loan_manager = None
        self.arbitrage_executor = None

    async def initialize(self):
        """Initialize all system components."""
        try:
            logger.info("Initializing arbitrage bot components...")
            
            # Load configuration
            config = load_config()
            secure_env = SecureEnvironment()
            
            # Initialize Web3
            self.web3_manager = Web3Manager(
                rpc_url=config['web3']['rpc_url'],
                chain_id=config['web3']['chain_id']
            )
            await self.web3_manager.initialize()
            
            # Initialize Flashbots
            self.flashbots_provider = await create_flashbots_provider(
                web3_manager=self.web3_manager,
                relay_url=config['flashbots']['relay_url'],
                auth_key=config['flashbots']['auth_key']
            )
            
            # Initialize Memory Bank
            self.memory_bank = MemoryBank()
            await self.memory_bank.initialize()
            
            # Initialize ML System
            self.ml_system = MLSystem()
            await self.ml_system.initialize()
            
            # Initialize Price Validator
            self.price_validator = PriceValidator(
                web3=self.web3_manager.w3,
                memory_bank=self.memory_bank
            )
            
            # Initialize Market Analyzer
            self.market_analyzer = EnhancedMarketAnalyzer(
                web3=self.web3_manager.w3,
                ml_system=self.ml_system,
                memory_bank=self.memory_bank,
                price_validator=self.price_validator
            )
            
            # Initialize Flash Loan Manager
            self.flash_loan_manager = EnhancedFlashLoanManager(
                web3=self.web3_manager.w3,
                flashbots_provider=self.flashbots_provider,
                memory_bank=self.memory_bank
            )
            
            # Initialize Arbitrage Executor
            self.arbitrage_executor = EnhancedArbitrageExecutor(
                web3=self.web3_manager.w3,
                market_analyzer=self.market_analyzer,
                flash_loan_manager=self.flash_loan_manager,
                flashbots_provider=self.flashbots_provider,
                memory_bank=self.memory_bank
            )
            
            self._components_initialized = True
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    async def start(self):
        """Start the arbitrage bot."""
        if not self._components_initialized:
            await self.initialize()
        
        self.running = True
        logger.info("Starting arbitrage bot...")
        
        # Register signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)
        
        try:
            # Start monitoring and execution tasks
            monitoring_task = asyncio.create_task(self._monitor_opportunities())
            execution_task = asyncio.create_task(self._execute_opportunities())
            metrics_task = asyncio.create_task(self._update_metrics())
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Cancel running tasks
            monitoring_task.cancel()
            execution_task.cancel()
            metrics_task.cancel()
            
            try:
                await asyncio.gather(
                    monitoring_task,
                    execution_task,
                    metrics_task,
                    return_exceptions=True
                )
            except asyncio.CancelledError:
                pass
            
        finally:
            self.running = False
            await self._cleanup()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_event.set()

    async def _monitor_opportunities(self):
        """Monitor for arbitrage opportunities."""
        while self.running:
            try:
                # Get active token pairs
                token_pairs = await self.memory_bank.get_active_token_pairs()
                
                # Find best opportunity
                best_pair, prices, score = await self.market_analyzer.find_best_opportunity(
                    token_pairs
                )
                
                if score.profit_potential > 0:
                    # Store opportunity in memory bank
                    await self.memory_bank.store_opportunity(
                        token_pair=best_pair,
                        profit_potential=score.profit_potential,
                        confidence=score.confidence
                    )
                
                await asyncio.sleep(1)  # Adjust based on network conditions
                
            except Exception as e:
                logger.error(f"Error in opportunity monitoring: {e}")
                await asyncio.sleep(5)  # Longer sleep on error

    async def _execute_opportunities(self):
        """Execute identified opportunities."""
        while self.running:
            try:
                # Get pending opportunity
                opportunity = await self.memory_bank.get_next_opportunity()
                if not opportunity:
                    await asyncio.sleep(1)
                    continue
                
                # Execute opportunity
                result = await self.arbitrage_executor.execute_opportunity(
                    token_pair=opportunity.token_pair,
                    opportunity=opportunity.score
                )
                
                # Update execution metrics
                await self.memory_bank.update_execution_metrics(result)
                
                if not result.success:
                    logger.warning(f"Execution failed: {result.error}")
                
            except Exception as e:
                logger.error(f"Error in opportunity execution: {e}")
                await asyncio.sleep(5)

    async def _update_metrics(self):
        """Update system metrics periodically."""
        while self.running:
            try:
                # Get execution stats
                stats = await self.arbitrage_executor.get_execution_stats()
                
                # Get current state
                state = await self.arbitrage_executor.get_current_state()
                
                # Update memory bank
                await self.memory_bank.update_system_metrics(stats, state)
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(5)

    async def _cleanup(self):
        """Cleanup resources on shutdown."""
        logger.info("Cleaning up resources...")
        
        try:
            # Close Flashbots provider
            if self.flashbots_provider:
                await self.flashbots_provider.close()
            
            # Close Web3 connection
            if self.web3_manager:
                await self.web3_manager.close()
            
            # Save final metrics
            if self.memory_bank:
                await self.memory_bank.save_final_state()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start bot
    bot = ArbitrageBot()
    
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
