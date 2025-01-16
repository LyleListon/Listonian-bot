 #!/usr/bin/env python3
"""Production entry point for arbitrage bot."""

import os
import sys
import json
import asyncio
import logging
import signal
from pathlib import Path
from typing import Dict, Any, Optional
from web3 import Web3

from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.web3.web3_manager import Web3Manager
from arbitrage_bot.core.process.manager import ProcessManager
from arbitrage_bot.core.analysis.market_analyzer import MarketAnalyzer
from arbitrage_bot.core.execution.arbitrage_executor import ArbitrageExecutor, create_arbitrage_executor
from arbitrage_bot.core.optimization.performance import PerformanceOptimizer
from arbitrage_bot.dashboard.run import main as start_dashboard
from arbitrage_bot.core.dex_manager import DEXManager

# Configure logging
instance_id = os.environ.get("INSTANCE_ID", "main")
log_dir = Path(f"logs/instances/{instance_id}")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ArbitrageBot')

class ArbitrageBot:
    """Main arbitrage bot class."""
    
    def __init__(self, config: Dict[str, Any], instance_id: str):
        """Initialize arbitrage bot."""
        self.config = config
        self.instance_id = instance_id
        self.running = False
        self.tasks = []
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(config["network"]["rpc_url"]))
        
        # Initialize components
        self.market_analyzer = None
        self.arbitrage_executor = None
        self.process_manager = None
        self.performance_optimizer = None
        
    async def initialize(self):
        """Initialize bot components."""
        try:
            # Initialize DEX manager
            self.dex_manager = DEXManager(self.w3, self.config)
            self.dexes = await self.dex_manager.initialize_all()
            
            # Initialize components
            self.performance_optimizer = PerformanceOptimizer(self.config)
            
            # Set up Web3Manager with wallet from config
            os.environ['WALLET_ADDRESS'] = self.config['wallet']['wallet_address']
            os.environ['PRIVATE_KEY'] = self.config['wallet']['private_key']
            os.environ['BASE_RPC_URL'] = self.config['network']['rpc_url']
            os.environ['CHAIN_ID'] = str(self.config['network']['chainId'])
            web3_manager = Web3Manager(provider_url=self.config['network']['rpc_url'])
            await web3_manager.connect()
            
            self.market_analyzer = MarketAnalyzer(
                web3_manager=web3_manager,
                config=self.config
            )
            
            # Create arbitrage executor
            self.arbitrage_executor = await create_arbitrage_executor(
                web3_manager=web3_manager,
                dex_manager=self.dex_manager,
                min_profit_usd=self.config.get("arbitrage", {}).get("min_profit_usd", 0.05),
                max_price_impact=self.config.get("arbitrage", {}).get("max_price_impact", 0.01),
                slippage_tolerance=self.config.get("arbitrage", {}).get("slippage_tolerance", 0.001),
                market_analyzer=self.market_analyzer
            )
            
            # Set task priorities
            priorities = self.config.get("optimization", {}).get("task_priorities", {})
            
            # Start dashboard if ports provided
            dashboard_port = os.environ.get("DASHBOARD_PORT")
            websocket_port = os.environ.get("DASHBOARD_WEBSOCKET_PORT")
            
            if dashboard_port and websocket_port:
                # Set environment variables for dashboard
                os.environ['DASHBOARD_PORT'] = str(dashboard_port)
                os.environ['DASHBOARD_WEBSOCKET_PORT'] = str(websocket_port)
                
                # Start dashboard
                self.tasks.append(
                    asyncio.create_task(start_dashboard())
                )
                
            logger.info("Bot initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            return False
            
    async def start(self):
        """Start bot operation."""
        try:
            if not await self.initialize():
                return
                
            self.running = True
            
            # Get task priorities
            priorities = self.config.get("optimization", {}).get("task_priorities", {})
            
            # Start performance optimization
            optimizer_task = asyncio.create_task(
                self.performance_optimizer.optimize_resources()
            )
            optimizer_task.set_name("performance_optimization")
            setattr(optimizer_task, "priority", priorities.get("monitoring", 70))
            self.performance_optimizer.track_task(optimizer_task)
            self.tasks.append(optimizer_task)
            
            # Start market analysis
            analysis_task = asyncio.create_task(
                self.market_analyzer.start_monitoring()
            )
            analysis_task.set_name("market_analysis")
            setattr(analysis_task, "priority", priorities.get("market_analysis", 100))
            self.performance_optimizer.track_task(analysis_task)
            self.tasks.append(analysis_task)
            
            # Start arbitrage execution
            execution_task = asyncio.create_task(
                self.arbitrage_executor.start_execution()
            )
            execution_task.set_name("arbitrage_execution")
            setattr(execution_task, "priority", priorities.get("arbitrage_execution", 90))
            self.performance_optimizer.track_task(execution_task)
            self.tasks.append(execution_task)
            
            # Start heartbeat
            heartbeat_task = asyncio.create_task(
                self._send_heartbeat()
            )
            heartbeat_task.set_name("heartbeat")
            setattr(heartbeat_task, "priority", priorities.get("monitoring", 70))
            self.performance_optimizer.track_task(heartbeat_task)
            self.tasks.append(heartbeat_task)
            
            logger.info(f"Bot instance {self.instance_id} started")
            
            # Wait for shutdown while monitoring performance
            while self.running:
                stats = self.performance_optimizer.get_optimization_stats()
                logger.info(f"Performance stats: {stats}")
                await asyncio.sleep(
                    self.config.get("optimization", {})
                    .get("metrics", {})
                    .get("update_interval", 1)
                )
            
        except Exception as e:
            logger.error(f"Error in bot operation: {e}")
            
        finally:
            await self.stop()
            
    async def stop(self):
        """Stop bot operation."""
        try:
            self.running = False
            
            # Cancel all tasks
            for task in self.tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            logger.info(f"Bot instance {self.instance_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            
    async def _send_heartbeat(self):
        """Send heartbeat to process manager."""
        while self.running:
            try:
                # Load process manager config
                process_config = self.config.get("process", {})
                heartbeat_interval = process_config.get("heartbeat_timeout", 30) / 2
                
                # Create temporary process manager for heartbeat
                process_manager = ProcessManager(self.config)
                await process_manager.heartbeat(self.instance_id)
                
                await asyncio.sleep(heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                await asyncio.sleep(5)
                
    async def _wait_for_shutdown(self):
        """Wait for shutdown signal."""
        while self.running:
            await asyncio.sleep(1)
            
def handle_signal(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    asyncio.get_event_loop().stop()
    
async def main():
    """Main entry point."""
    try:
        # Load configuration
        config = load_config()
        
        # Get instance ID from environment
        instance_id = os.environ.get("INSTANCE_ID", "main")
        
        # Create and start bot
        bot = ArbitrageBot(config, instance_id)
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
        
        # Start bot
        await bot.start()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    asyncio.run(main())
