"""Flash loan execution manager."""

from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging
import asyncio
from web3.types import TxReceipt

from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)

class FlashLoanManager:
    """Manages flash loan operations for arbitrage execution."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize flash loan manager."""
        self.web3_manager = web3_manager
        self.config = config
        self.contract = None
        self.initialized = False

        # Validate required config
        required_fields = ['balancer_vault', 'flash_loan_contract']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")

    async def initialize(self) -> bool:
        """Initialize flash loan contract and approvals."""
        try:
            # Load contract ABI
            contract_abi = self.web3_manager.load_abi('BaseFlashLoanArbitrage')
            
            # Initialize contract
            self.contract = self.web3_manager.w3.eth.contract(
                address=self.config['flash_loan_contract'],
                abi=contract_abi
            )

            # Set DEX routers
            await self._set_dex_routers()

            # Verify contract is deployed
            code = await self.web3_manager.w3.eth.get_code(self.config['flash_loan_contract'])
            if len(code) <= 2:  # Empty or just '0x'
                raise ValueError(f"No contract deployed at {self.config['flash_loan_contract']}")

            self.initialized = True
            logger.info("Flash loan manager initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize flash loan manager: {e}")
            return False

    async def _set_dex_routers(self):
        """Set router addresses for supported DEXes."""
        try:
            # Set BaseSwap router
            if 'baseswap' in self.config['dexes']:
                tx = await self._retry_async(
                    lambda: self.contract.functions.setBaseswapRouter(
                        self.config['dexes']['baseswap']['router']
                    ).build_transaction({
                        'from': self.web3_manager.account.address,
                        'gas': 200000,
                        'nonce': await self.web3_manager.w3.eth.get_transaction_count(
                            self.web3_manager.account.address
                        )
                    })
                )
                await self.web3_manager.send_transaction_async(tx)

            # Set PancakeSwap router
            if 'pancakeswap' in self.config['dexes']:
                tx = await self._retry_async(
                    lambda: self.contract.functions.setPancakeswapRouter(
                        self.config['dexes']['pancakeswap']['router']
                    ).build_transaction({
                        'from': self.web3_manager.account.address,
                        'gas': 200000,
                        'nonce': await self.web3_manager.w3.eth.get_transaction_count(
                            self.web3_manager.account.address
                        )
                    })
                )
                await self.web3_manager.send_transaction_async(tx)

        except Exception as e:
            logger.error(f"Failed to set DEX routers: {e}")
            raise

    async def approve_token(self, token_address: str, amount: int) -> bool:
        """Approve token spending for flash loan contract."""
        try:
            tx_data = await self._retry_async(
                lambda: self.contract.functions.approveToken(
                    token_address,
                    amount
                ).build_transaction({
                    'from': self.web3_manager.account.address,
                    'gas': 100000,
                    'nonce': await self.web3_manager.w3.eth.get_transaction_count(
                        self.web3_manager.account.address
                    )
                })
            )
            
            tx_hash = await self.web3_manager.send_transaction_async(tx_data)
            await self.web3_manager.w3.eth.wait_for_transaction_receipt(tx_hash)
            return True

        except Exception as e:
            logger.error(f"Failed to approve token {token_address}: {e}")
            return False

    async def execute_arbitrage(
        self,
        token_in: str,
        token_out: str,
        amount: int,
        buy_dex: str,
        sell_dex: str,
        min_profit: int
    ) -> Optional[TxReceipt]:
        """Execute arbitrage using flash loan."""
        try:
            if not self.initialized:
                raise ValueError("Flash loan manager not initialized")

            # Get nonce asynchronously
            nonce = await self.web3_manager.get_transaction_count_async(
                self.web3_manager.account.address
            )

            # Build transaction
            tx = await self._retry_async(
                lambda: self.contract.functions.executeArbitrage(
                    token_in,
                    token_out,
                    amount,
                    buy_dex,
                    sell_dex,
                    min_profit
                ).build_transaction({
                    'from': self.web3_manager.account.address,
                    'gas': 500000,  # Flash loans need more gas
                    'nonce': nonce
                })
            )

            # Send transaction and get receipt
            receipt = await self.web3_manager.send_transaction_async(tx)

            # Log transaction
            logger.info(
                f"Flash loan arbitrage executed: {tx_hash.hex()}\n"
                f"Token in: {token_in}\n"
                f"Token out: {token_out}\n"
                f"Amount: {amount}\n"
                f"Buy DEX: {buy_dex}\n"
                f"Sell DEX: {sell_dex}\n"
                f"Min profit: {min_profit}"
            )

            return receipt

        except Exception as e:
            logger.error(f"Failed to execute flash loan arbitrage: {e}")
            return None

    async def _retry_async(self, func, retries: int = 3, delay: float = 1.0):
        """Retry async function with exponential backoff."""
        last_error = None
        for i in range(retries):
            try:
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                else:
                    return result
            except Exception as e:
                last_error = e
                if i < retries - 1:
                    await asyncio.sleep(delay * (2 ** i))
                continue
        raise last_error