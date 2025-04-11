"""Execution management module."""

import logging
# import asyncio # Unused
from typing import Any, Optional # Removed Dict
from decimal import Decimal
from web3 import Web3
from .config import ExecutionConfig

logger = logging.getLogger(__name__)


class ExecutionManager:
    """Manages execution of trades."""

    def __init__(
        self,
        config: ExecutionConfig,
        web3: Web3,
        distribution_manager: Any,
        memory_bank: Any,
    ):
        """Initialize execution manager."""
        self.config = config
        self.web3 = web3
        self.distribution_manager = distribution_manager
        self.memory_bank = memory_bank
        self.initialized = False
        self._pending_txs = {}
        self._nonce = None
        self._last_block = None

    def initialize(self) -> bool:
        """Initialize the execution manager."""
        try:
            # Initialize tracking dictionaries
            self._pending_txs = {}

            # Get current nonce
            self._nonce = self.web3.eth.get_transaction_count(
                self.web3.eth.default_account
            )

            # Get current block
            self._last_block = self.web3.eth.block_number

            self.initialized = True
            logger.info("Execution manager initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize execution manager: {e}")
            return False

    async def execute_trade(
        self,
        dex_name: str,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        path: list,
    ) -> Optional[str]:
        """Execute a trade on a DEX."""
        try:
            if not self.initialized:
                raise RuntimeError("Execution manager not initialized")

            # Check if trade size within allocation
            allocation = self.distribution_manager.get_dex_allocation(dex_name)
            if not allocation or Decimal(str(amount_in)) > allocation:
                logger.warning(f"Trade size exceeds allocation for {dex_name}")
                return None

            # Get gas price within limits
            gas_price = await self._get_optimal_gas_price()
            if not gas_price:
                logger.warning("Could not get optimal gas price")
                return None

            # Build transaction
            tx = {
                "from": self.web3.eth.default_account,
                "nonce": self._get_next_nonce(),
                "gas": self.config.gas_limit,
                "gasPrice": gas_price,
                "value": 0,
            }

            # Add trade parameters
            tx.update(
                {
                    "to": path[0],
                    "data": self._encode_trade_data(
                        token_in, token_out, amount_in, min_amount_out, path
                    ),
                }
            )

            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(
                tx, private_key=self.web3.eth.account.default_account.privateKey
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

            # Track pending transaction
            self._pending_txs[tx_hash.hex()] = {
                "nonce": tx["nonce"],
                "gas_price": gas_price,
                "timestamp": self.web3.eth.get_block("latest").timestamp,
            }

            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return None

    async def _get_optimal_gas_price(self) -> Optional[int]:
        """Get optimal gas price within limits."""
        try:
            # Get current gas price
            gas_price = self.web3.eth.gas_price

            # Apply multiplier based on pending transactions
            pending_multiplier = 1 + (
                len(self._pending_txs) * 0.1
            )  # 10% increase per pending tx
            gas_price = int(gas_price * pending_multiplier)

            # Ensure within limits
            max_gas_price_wei = self.web3.to_wei(self.config.max_gas_price, "gwei")
            return min(gas_price, max_gas_price_wei)

        except Exception as e:
            logger.error(f"Error getting optimal gas price: {e}")
            return None

    def _get_next_nonce(self) -> int:
        """Get next nonce value."""
        if self._nonce is None:
            self._nonce = self.web3.eth.get_transaction_count(
                self.web3.eth.default_account
            )
        self._nonce += 1
        return self._nonce - 1

    def _encode_trade_data(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_amount_out: int,
        path: list,
    ) -> bytes:
        """Encode trade data for transaction."""
        try:
            # Get contract ABI from memory bank
            abi = self.memory_bank.get_contract_abi("UniswapV2Router02")
            contract = self.web3.eth.contract(address=path[0], abi=abi)

            # Encode swap function call
            return contract.encodeABI(
                fn_name="swapExactTokensForTokens",
                args=[
                    amount_in,
                    min_amount_out,
                    path,
                    self.web3.eth.default_account,
                    self.web3.eth.get_block("latest").timestamp
                    + 60,  # 1 minute deadline
                ],
            )

        except Exception as e:
            logger.error(f"Error encoding trade data: {e}")
            raise
