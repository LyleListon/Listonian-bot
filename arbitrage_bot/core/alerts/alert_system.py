"""Alert system for monitoring and notifying about important events."""

import logging
import asyncio
from typing import Dict, Any, Optional, Set
from decimal import Decimal

from ..analytics.analytics_system import AnalyticsSystem
from ..web3.web3_manager import Web3Manager
from ..dex.dex_manager import DexManager

logger = logging.getLogger(__name__)

class AlertSystem:
    """System for monitoring and generating alerts."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        dex_manager: DexManager,
        analytics_system: AnalyticsSystem,
        config: Dict[str, Any]
    ):
        """Initialize alert system."""
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.analytics_system = analytics_system
        self.config = config
        self.monitoring = False
        self._tasks = set()  # Set of asyncio.Task
        self._shutdown_event = asyncio.Event()
        logger.info("Alert system initialized")

    async def start_monitoring(self):
        """Start monitoring for alerts."""
        if self.monitoring:
            return

        self.monitoring = True
        self._shutdown_event.clear()

        # Create monitoring tasks
        monitor_task = asyncio.create_task(self._monitor_conditions())
        self._tasks.add(monitor_task)
        monitor_task.add_done_callback(self._tasks.discard)

        logger.info("Alert monitoring started")

    async def stop_monitoring(self):
        """Stop monitoring for alerts."""
        if not self.monitoring:
            return

        # Signal shutdown
        self._shutdown_event.set()
        self.monitoring = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        logger.info("Alert monitoring stopped")

    async def _monitor_conditions(self):
        """Monitor conditions and generate alerts."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Check gas conditions
                    await self._check_gas_condition()

                    # Check balance conditions
                    await self._check_balance_condition()

                    # Check profit conditions
                    await self._check_profit_condition()

                    # Wait before next check
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=60  # Check every minute
                        )
                    except asyncio.TimeoutError:
                        continue

                except Exception as e:
                    logger.error("Error in monitoring loop: %s", str(e))
                    await asyncio.sleep(5)  # Wait before retry

        except asyncio.CancelledError:
            logger.info("Monitoring task cancelled")
        except Exception as e:
            logger.error("Fatal error in monitoring task: %s", str(e))

    async def _check_gas_condition(self):
        """Check gas price conditions."""
        try:
            gas_price = await self.web3_manager.w3.eth.gas_price
            max_gas = self.config.get('gas', {}).get('max_fee', 200)

            if gas_price > max_gas * 10**9:  # Convert to Wei
                logger.warning("High gas price detected: %s gwei", gas_price / 10**9)

        except Exception as e:
            logger.error("Failed to check gas condition: %s", str(e))

    async def _check_balance_condition(self):
        """Check wallet balance conditions."""
        try:
            balance = await self.web3_manager.w3.eth.get_balance(
                self.web3_manager.wallet_address
            )
            min_balance = self.config.get('min_balance_eth', 0.1) * 10**18

            if balance < min_balance:
                logger.warning(
                    "Low wallet balance: %s ETH",
                    balance / 10**18
                )

        except Exception as e:
            logger.error("Failed to check balance condition: %s", str(e))

    async def _check_profit_condition(self):
        """Check profit conditions."""
        try:
            min_profit = self.config.get('min_profit_usd', 0.05)
            
            # Get current profits from analytics
            if hasattr(self.analytics_system, 'get_current_profits'):
                profits = await self.analytics_system.get_current_profits()
                
                if profits and profits < min_profit:
                    logger.warning(
                        "Low profit detected: $%s (minimum: $%s)",
                        profits,
                        min_profit
                    )

        except Exception as e:
            logger.error("Failed to check profit condition: %s", str(e))

async def create_alert_system(
    web3_manager: Web3Manager,
    dex_manager: DexManager,
    analytics_system: AnalyticsSystem,
    config: Dict[str, Any]
) -> AlertSystem:
    """Create and initialize alert system."""
    try:
        system = AlertSystem(
            web3_manager=web3_manager,
            dex_manager=dex_manager,
            analytics_system=analytics_system,
            config=config
        )
        # Start monitoring in a task to avoid blocking
        asyncio.create_task(system.start_monitoring())
        return system
    except Exception as e:
        logger.error("Failed to create alert system: %s", str(e))
        raise
