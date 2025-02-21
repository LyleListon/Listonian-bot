"""Balance manager for tracking and updating token balances."""

import logging
import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal
from web3 import Web3

from .web3.web3_manager import Web3Manager
from .dex.dex_manager import DexManager

logger = logging.getLogger(__name__)

class BalanceManager:
    """Manages token balances and updates."""

    _instance = None

    def __init__(
        self,
        web3_manager: Web3Manager,
        dex_manager: DexManager,
        config: Dict[str, Any]
    ):
        """Initialize balance manager."""
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.config = config
        self.balances = {}
        self.running = False
        self._tasks = set()  # Set of asyncio.Task
        self._shutdown_event = asyncio.Event()
        logger.info("Creating new BalanceManager instance")

    @classmethod
    async def get_instance(
        cls,
        web3_manager: Optional[Web3Manager] = None,
        dex_manager: Optional[DexManager] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> 'BalanceManager':
        """Get or create singleton instance."""
        if not cls._instance:
            if not all([web3_manager, dex_manager, config]):
                raise ValueError("Required parameters missing for initialization")
            cls._instance = cls(web3_manager, dex_manager, config)
            logger.info("BalanceManager instance created successfully")
            # Start balance updates in a task to avoid blocking
            asyncio.create_task(cls._instance.start())
        return cls._instance

    async def start(self):
        """Start balance updates."""
        if self.running:
            return

        self.running = True
        self._shutdown_event.clear()

        # Create update task
        update_task = asyncio.create_task(self._periodic_updates())
        self._tasks.add(update_task)
        update_task.add_done_callback(self._tasks.discard)

        logger.info("Balance manager started")

    async def stop(self):
        """Stop balance updates."""
        if not self.running:
            return

        # Signal shutdown
        self._shutdown_event.set()
        self.running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        logger.info("Balance manager stopped")

    async def _periodic_updates(self):
        """Periodically update balances."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    await self._update_balances()

                    # Wait before next update
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=60  # Update every minute
                        )
                    except asyncio.TimeoutError:
                        continue

                except Exception as e:
                    logger.error("Error in update loop: %s", str(e))
                    await asyncio.sleep(5)  # Wait before retry

        except asyncio.CancelledError:
            logger.info("Update task cancelled")
        except Exception as e:
            logger.error("Fatal error in update task: %s", str(e))

    async def _update_balances(self):
        """Update token balances."""
        try:
            # Update ETH balance
            eth_balance = await self.web3_manager.w3.eth.get_balance(
                self.web3_manager.wallet_address
            )
            self.balances['ETH'] = eth_balance

            # Update token balances
            for token_symbol, token_data in self.config.get('tokens', {}).items():
                if token_symbol == 'ETH':
                    continue

                try:
                    token_address = Web3.to_checksum_address(token_data['address'])
                    token_contract = self.web3_manager.get_token_contract(token_address)
                    
                    if token_contract:
                        balance = await self.web3_manager.call_contract_function(
                            token_contract.functions.balanceOf,
                            self.web3_manager.wallet_address
                        )
                        self.balances[token_symbol] = balance

                except Exception as e:
                    logger.error("Failed to update balance for %s: %s", token_symbol, str(e))

        except Exception as e:
            logger.error("Error updating balances: %s", str(e))

    def get_balance(self, token_symbol: str) -> Optional[int]:
        """Get balance for a token."""
        return self.balances.get(token_symbol)

    def get_all_balances(self) -> Dict[str, int]:
        """Get all token balances."""
        return self.balances.copy()

    async def check_balance(self, token_symbol: str, amount: int) -> bool:
        """Check if balance is sufficient for amount."""
        try:
            balance = self.get_balance(token_symbol)
            if balance is None:
                return False
            return balance >= amount
        except Exception as e:
            logger.error("Failed to check balance: %s", str(e))
            return False

    async def get_formatted_balance(self, token_symbol: str) -> Optional[Decimal]:
        """Get formatted balance with decimals."""
        try:
            balance = self.get_balance(token_symbol)
            if balance is None:
                return None

            token_data = self.config.get('tokens', {}).get(token_symbol)
            if not token_data:
                return None

            decimals = token_data.get('decimals', 18)
            return Decimal(balance) / Decimal(10 ** decimals)

        except Exception as e:
            logger.error("Failed to get formatted balance: %s", str(e))
            return None
