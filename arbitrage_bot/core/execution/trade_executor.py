"""Execute arbitrage trades with flash loans."""

import logging
import asyncio
from typing import Dict, Any, Optional # Removed List, Tuple, Set, cast
from decimal import Decimal
# from web3 import AsyncWeb3, AsyncHTTPProvider # Unused
from web3.contract import Contract
from web3.types import Wei # Removed TxParams
from concurrent.futures import ThreadPoolExecutor
from collections import deque # Removed defaultdict
import time
import lru

from ..models.opportunity import Opportunity
from ..models.enums import OpportunityStatus # Corrected import path
from ..monitoring.transaction_monitor import TransactionMonitor
from ..dex.dex_manager import DexManager # Corrected import path

logger = logging.getLogger(__name__)

# Cache settings
CACHE_TTL = 60  # 60 seconds
BATCH_SIZE = 50  # Process 50 items at a time
MAX_RETRIES = 3  # Maximum number of retries for failed operations
RETRY_DELAY = 1  # Delay between retries in seconds
CACHE_SIZE = 1000  # Maximum number of items in LRU cache
PREFETCH_THRESHOLD = 0.8  # Threshold to trigger prefetch
MAX_BATCH_SIZE = 10  # Maximum number of transactions to process in a batch
BATCH_TIMEOUT = 5  # Maximum time to wait for batch to fill (seconds)


class TradeExecutor:
    """Executes arbitrage trades using flash loans."""

    def __init__(
        self,
        web3_manager,
        flash_loan_contract: Contract,
        dex_manager: DexManager,
        config: Dict[str, Any],
        transaction_monitor: Optional[TransactionMonitor] = None,
    ):
        """Initialize trade executor."""
        self.w3 = web3_manager
        self.flash_loan = flash_loan_contract
        self.dex_manager = dex_manager
        self.config = config
        self.transaction_monitor = transaction_monitor
        self.min_profit = Decimal(str(config["trading"]["min_profit_usd"]))
        self.max_slippage = (
            Decimal(
                str(
                    config["trading"]["safety"]["protection_limits"][
                        "max_slippage_percent"
                    ]
                )
            )
            / 100
        )
        self.gas_buffer = Decimal("1.1")  # 10% buffer for gas estimates

        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Cache settings
        self.cache_ttl = CACHE_TTL
        self.batch_size = BATCH_SIZE

        # LRU caches for frequently accessed data
        self._dex_cache = lru.LRU(CACHE_SIZE)
        self._quote_cache = lru.LRU(CACHE_SIZE)
        self._gas_cache = lru.LRU(CACHE_SIZE)
        self._nonce_cache = lru.LRU(CACHE_SIZE)
        self._tx_cache = lru.LRU(CACHE_SIZE)
        self._validation_cache = lru.LRU(CACHE_SIZE)
        self._loan_cache = lru.LRU(CACHE_SIZE)

        # Cache timestamps
        self._dex_cache_times = {}
        self._quote_cache_times = {}
        self._gas_cache_times = {}
        self._nonce_cache_times = {}
        self._tx_cache_times = {}
        self._validation_cache_times = {}
        self._loan_cache_times = {}

        # Locks for thread safety
        self._execution_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
        self._gas_lock = asyncio.Lock()
        self._nonce_lock = asyncio.Lock()
        self._tx_lock = asyncio.Lock()
        self._validation_lock = asyncio.Lock()
        self._loan_lock = asyncio.Lock()
        self._batch_lock = asyncio.Lock()

        # Transaction batching
        self._tx_batch = []
        self._last_tx_batch = time.time()

        # Recent transactions for deduplication
        self._recent_transactions = deque(maxlen=1000)

        # Prefetch settings
        self._prefetch_size = 100  # Number of items to prefetch
        self._prefetch_threshold = PREFETCH_THRESHOLD

        # Start periodic tasks
        self._cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())
        self._batch_task = asyncio.create_task(self._periodic_tx_batch())
        self._prefetch_task = asyncio.create_task(self._periodic_prefetch())

    async def execute_opportunity(self, opportunity: Opportunity) -> bool:
        """Execute an arbitrage opportunity using flash loans."""
        try:
            # Skip if recently processed
            key = (
                f"{opportunity.buy_dex}:{opportunity.sell_dex}:{opportunity.token_pair}"
            )
            if key in self._recent_transactions:
                logger.debug(f"Skipping recently processed opportunity: {key}")
                return False

            # Add to recent transactions
            self._recent_transactions.append(key)

            # Add to batch
            async with self._batch_lock:
                self._tx_batch.append(opportunity)

                # Process batch if full or timeout reached
                current_time = time.time()
                if (
                    len(self._tx_batch) >= MAX_BATCH_SIZE
                    or current_time - self._last_tx_batch >= BATCH_TIMEOUT
                ):
                    await self._process_tx_batch()

            return True

        except Exception as e:
            logger.error(f"Error queueing opportunity: {str(e)}", exc_info=True)
            opportunity.status = OpportunityStatus.FAILED
            return False

    async def _process_tx_batch(self) -> None:
        """Process transaction batch."""
        try:
            async with self._batch_lock:
                if not self._tx_batch:
                    return

                # Get batch
                batch = self._tx_batch[:MAX_BATCH_SIZE]
                self._tx_batch = self._tx_batch[MAX_BATCH_SIZE:]
                self._last_tx_batch = time.time()

            # Process opportunities concurrently
            tasks = []
            for opportunity in batch:
                task = asyncio.create_task(
                    self._execute_single_opportunity(opportunity)
                )
                tasks.append(task)

            await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error processing transaction batch: {e}")

    async def _execute_single_opportunity(self, opportunity: Opportunity) -> bool:
        """Execute a single opportunity."""
        try:
            async with self._execution_lock:
                # Run validation checks and prepare loan parameters concurrently
                validation_task = asyncio.create_task(
                    self._validate_opportunity(opportunity)
                )
                loan_params_task = asyncio.create_task(
                    self._prepare_loan_parameters(opportunity)
                )

                # Wait for validation results with retries
                for attempt in range(MAX_RETRIES):
                    try:
                        is_valid = await validation_task
                        if not is_valid:
                            logger.info(
                                f"Opportunity no longer profitable: {opportunity.token_pair}"
                            )
                            opportunity.status = OpportunityStatus.INVALID # Map EXPIRED to INVALID
                            return False
                        break
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        logger.error(
                            f"Validation failed after {MAX_RETRIES} attempts: {e}"
                        )
                        opportunity.status = OpportunityStatus.FAILED
                        return False

                # Get loan parameters with retries
                for attempt in range(MAX_RETRIES):
                    try:
                        loan_token, loan_amount, params = await loan_params_task
                        break
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        logger.error(
                            f"Failed to get loan parameters after {MAX_RETRIES} attempts: {e}"
                        )
                        opportunity.status = OpportunityStatus.FAILED
                        return False

                # Get gas estimates and check profitability concurrently
                gas_task = asyncio.create_task(
                    self._estimate_execution_gas(loan_token, loan_amount, params)
                )
                gas_price_task = asyncio.create_task(self.w3.w3.eth.gas_price)

                gas_estimate, gas_price = await asyncio.gather(gas_task, gas_price_task)
                gas_cost = Decimal(str(gas_estimate)) * Decimal(str(gas_price))

                if opportunity.net_profit <= gas_cost * self.gas_buffer:
                    logger.info(
                        f"Opportunity not profitable after gas costs: {opportunity.token_pair}"
                    )
                    opportunity.status = OpportunityStatus.INVALID # Map EXPIRED to INVALID
                    return False

                # Check and approve tokens before executing flash loan
                tokens = opportunity.token_pair.split("/")
                token0_addr = self.config["tokens"][tokens[0]]["address"]
                token1_addr = self.config["tokens"][tokens[1]]["address"]

                # Get DEX instances
                buy_dex = self.dex_manager.get_dex(opportunity.buy_dex.split("_")[0])
                sell_dex = self.dex_manager.get_dex(opportunity.sell_dex.split("_")[0])

                if not buy_dex or not sell_dex:
                    logger.error("Failed to get DEX instances")
                    opportunity.status = OpportunityStatus.FAILED
                    return False

                # Approve tokens for both DEXes
                approval_tasks = []
                for token_addr in [token0_addr, token1_addr]:
                    for dex in [buy_dex, sell_dex]:
                        approval_tasks.append(
                            dex.check_and_approve_token(token_addr, loan_amount)
                        )

                approval_results = await asyncio.gather(*approval_tasks)
                if not all(approval_results):
                    logger.error("Failed to approve tokens for trading")
                    opportunity.status = OpportunityStatus.FAILED
                    return False

                # Execute flash loan after approvals
                for attempt in range(MAX_RETRIES):
                    try:
                        # Execute flash loan transaction
                        tx_hash = await self._execute_flash_loan(
                            loan_token,
                            loan_amount,
                            params,
                            gas_estimate,
                            Wei(gas_price),
                        )

                        # Monitor transaction and update metrics concurrently
                        monitor_task = asyncio.create_task(
                            self._monitor_transaction(opportunity, tx_hash)
                        )
                        metrics_task = asyncio.create_task(
                            self._update_profit_metrics(opportunity, tx_hash)
                        )

                        success = await monitor_task
                        if success:
                            await metrics_task
                            opportunity.status = OpportunityStatus.EXECUTED # Map COMPLETED to EXECUTED
                            return True
                        else:
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            opportunity.status = OpportunityStatus.FAILED
                            return False

                    except Exception as e:
                        logger.error(
                            f"Error executing trade (attempt {attempt + 1}): {e}"
                        )
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        opportunity.status = OpportunityStatus.FAILED
                        return False

        except Exception as e:
            logger.error(f"Error executing opportunity: {str(e)}", exc_info=True)
            opportunity.status = OpportunityStatus.FAILED
            return False
