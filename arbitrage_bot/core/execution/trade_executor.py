"""Execute arbitrage trades with flash loans."""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set, cast
from decimal import Decimal
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.contract import Contract
from web3.types import TxParams, Wei
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
import time
import lru

from ..models.opportunity import Opportunity, OpportunityStatus
from ..monitoring.transaction_monitor import TransactionMonitor
from ..dex.dex_manager import DEXManager

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
        dex_manager: DEXManager,
        config: Dict[str, Any],
        transaction_monitor: Optional[TransactionMonitor] = None
    ):
        """Initialize trade executor."""
        self.w3 = web3_manager
        self.flash_loan = flash_loan_contract
        self.dex_manager = dex_manager
        self.config = config
        self.transaction_monitor = transaction_monitor
        self.min_profit = Decimal(str(config["trading"]["min_profit_usd"]))
        self.max_slippage = Decimal(str(config["trading"]["safety"]["protection_limits"]["max_slippage_percent"])) / 100
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
            key = f"{opportunity.buy_dex}:{opportunity.sell_dex}:{opportunity.token_pair}"
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
                if (len(self._tx_batch) >= MAX_BATCH_SIZE or 
                    current_time - self._last_tx_batch >= BATCH_TIMEOUT):
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
                task = asyncio.create_task(self._execute_single_opportunity(opportunity))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error processing transaction batch: {e}")

    async def _execute_single_opportunity(self, opportunity: Opportunity) -> bool:
        """Execute a single opportunity."""
        try:
            async with self._execution_lock:
                # Run validation checks and prepare loan parameters concurrently
                validation_task = asyncio.create_task(self._validate_opportunity(opportunity))
                loan_params_task = asyncio.create_task(self._prepare_loan_parameters(opportunity))
                
                # Wait for validation results with retries
                for attempt in range(MAX_RETRIES):
                    try:
                        is_valid = await validation_task
                        if not is_valid:
                            logger.info(f"Opportunity no longer profitable: {opportunity.token_pair}")
                            opportunity.status = OpportunityStatus.EXPIRED
                            return False
                        break
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        logger.error(f"Validation failed after {MAX_RETRIES} attempts: {e}")
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
                        logger.error(f"Failed to get loan parameters after {MAX_RETRIES} attempts: {e}")
                        opportunity.status = OpportunityStatus.FAILED
                        return False
                
                # Get gas estimates and check profitability concurrently
                gas_task = asyncio.create_task(self._estimate_execution_gas(
                    loan_token, loan_amount, params
                ))
                gas_price_task = asyncio.create_task(self.w3.w3.eth.gas_price)
                
                gas_estimate, gas_price = await asyncio.gather(gas_task, gas_price_task)
                gas_cost = Decimal(str(gas_estimate)) * Decimal(str(gas_price))
                
                if opportunity.net_profit <= gas_cost * self.gas_buffer:
                    logger.info(f"Opportunity not profitable after gas costs: {opportunity.token_pair}")
                    opportunity.status = OpportunityStatus.EXPIRED
                    return False
                
                # Execute flash loan transaction with retries
                for attempt in range(MAX_RETRIES):
                    try:
                        # Execute flash loan transaction
                        tx_hash = await self._execute_flash_loan(
                            loan_token,
                            loan_amount,
                            params,
                            gas_estimate,
                            Wei(gas_price)
                        )
                        
                        # Monitor transaction and update metrics concurrently
                        monitor_task = asyncio.create_task(self._monitor_transaction(opportunity, tx_hash))
                        metrics_task = asyncio.create_task(self._update_profit_metrics(opportunity, tx_hash))
                        
                        success = await monitor_task
                        if success:
                            await metrics_task
                            opportunity.status = OpportunityStatus.COMPLETED
                            return True
                        else:
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(RETRY_DELAY)
                                continue
                            opportunity.status = OpportunityStatus.FAILED
                            return False
                            
                    except Exception as e:
                        logger.error(f"Error executing trade (attempt {attempt + 1}): {e}")
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        opportunity.status = OpportunityStatus.FAILED
                        return False

        except Exception as e:
            logger.error(f"Error executing opportunity: {str(e)}", exc_info=True)
            opportunity.status = OpportunityStatus.FAILED
            return False

    async def _validate_opportunity(self, opportunity: Opportunity) -> bool:
        """Validate opportunity is still profitable."""
        try:
            # Check validation cache
            cache_key = f"validation_{opportunity.token_pair}"
            validation = await self._get_cached_data(
                cache_key,
                self._validation_cache,
                self._validation_cache_times
            )
            if validation is not None:
                return validation
            
            # Get current prices concurrently
            prices = await self._get_current_prices(opportunity)
            
            # Calculate profit in thread pool
            loop = asyncio.get_event_loop()
            actual_profit = await loop.run_in_executor(
                self.executor,
                self._calculate_actual_profit,
                opportunity,
                prices
            )
            
            result = actual_profit >= self.min_profit
            
            # Update cache
            await self._update_cache(
                cache_key,
                result,
                self._validation_cache,
                self._validation_cache_times
            )
            
            return result

        except Exception as e:
            logger.error(f"Error validating opportunity: {str(e)}")
            return False

    async def _get_current_prices(self, opportunity: Opportunity) -> Dict[str, float]:
        """Get current prices from DEXes concurrently."""
        try:
            tokens = opportunity.token_pair.split('/')
            token0_addr = self.config['tokens'][tokens[0]]['address']
            token1_addr = self.config['tokens'][tokens[1]]['address']
            
            # Get quotes concurrently
            buy_task = asyncio.create_task(self._get_dex_quote(
                opportunity.buy_dex,
                int(opportunity.buy_amount),
                [token0_addr, token1_addr],
                'buy'
            ))
            
            sell_task = asyncio.create_task(self._get_dex_quote(
                opportunity.sell_dex,
                int(opportunity.sell_amount),
                [token1_addr, token0_addr],
                'sell'
            ))
            
            buy_quote, sell_quote = await asyncio.gather(buy_task, sell_task)
            
            prices = {}
            if buy_quote:
                prices['buy'] = float(buy_quote['amount_out']) / float(opportunity.buy_amount)
            if sell_quote:
                prices['sell'] = float(opportunity.sell_amount) / float(sell_quote['amount_in'])
            
            return prices

        except Exception as e:
            logger.error(f"Error getting current prices: {str(e)}")
            return {}

    async def _get_dex_quote(
        self,
        dex_name: str,
        amount: int,
        path: List[str],
        side: str
    ) -> Optional[Dict[str, Any]]:
        """Get quote from DEX with caching."""
        try:
            # Check cache first
            cache_key = f"{dex_name}:{amount}:{':'.join(path)}:{side}"
            quote = await self._get_cached_data(
                cache_key,
                self._quote_cache,
                self._quote_cache_times
            )
            if quote:
                return quote
            
            # Get DEX instance from cache
            dex_key = dex_name.split('_')[0]
            dex = self._dex_cache.get(dex_key)
            if not dex:
                dex = self.dex_manager.get_dex(dex_key)
                if dex:
                    self._dex_cache[dex_key] = dex
                else:
                    return None
            
            # Get quote with retries
            for attempt in range(MAX_RETRIES):
                try:
                    quote = await dex.get_quote_with_impact(amount, path)
                    if quote:
                        # Update cache
                        await self._update_cache(
                            cache_key,
                            quote,
                            self._quote_cache,
                            self._quote_cache_times
                        )
                        return quote
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to get quote after {MAX_RETRIES} attempts: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting {side} quote from {dex_name}: {str(e)}")
            return None

    def _calculate_actual_profit(
        self,
        opportunity: Opportunity,
        current_prices: Dict[str, float]
    ) -> Decimal:
        """Calculate actual profit based on current prices (CPU-bound)."""
        try:
            if not current_prices or 'buy' not in current_prices or 'sell' not in current_prices:
                return Decimal('0')

            buy_price = Decimal(str(current_prices['buy']))
            sell_price = Decimal(str(current_prices['sell']))
            amount = Decimal(str(opportunity.buy_amount))

            # Calculate profit
            cost = amount * buy_price
            revenue = amount * sell_price
            profit = revenue - cost

            return profit

        except Exception as e:
            logger.error(f"Error calculating actual profit: {str(e)}")
            return Decimal('0')

    async def _prepare_loan_parameters(
        self,
        opportunity: Opportunity
    ) -> Tuple[str, int, bytes]:
        """Prepare flash loan parameters concurrently."""
        try:
            # Check loan cache
            cache_key = f"loan_{opportunity.token_pair}"
            params = await self._get_cached_data(
                cache_key,
                self._loan_cache,
                self._loan_cache_times
            )
            if params:
                return params
            
            # Get loan token and calculate amount
            loan_token = self._get_loan_token(opportunity)
            loan_amount = self._calculate_optimal_amount(opportunity)
            
            # Prepare trade paths
            dex_paths, amounts, is_v3 = self._prepare_trade_path(opportunity)
            
            # Encode parameters in thread pool
            loop = asyncio.get_event_loop()
            encoded_params = await loop.run_in_executor(
                self.executor,
                self._encode_parameters,
                dex_paths,
                amounts,
                is_v3
            )
            
            result = (loan_token, loan_amount, encoded_params)
            
            # Update cache
            await self._update_cache(
                cache_key,
                result,
                self._loan_cache,
                self._loan_cache_times
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error preparing loan parameters: {str(e)}")
            raise

    def _encode_parameters(
        self,
        dex_paths: List[str],
        amounts: List[int],
        is_v3: List[bool]
    ) -> bytes:
        """Encode parameters for flash loan (CPU-bound)."""
        return self.w3.w3.eth.contract(abi=[]).encodeParameters(
            ['address[]', 'uint256[]', 'bool[]'],
            [dex_paths, amounts, is_v3]
        )

    def _get_loan_token(self, opportunity: Opportunity) -> str:
        """Get the token to use for flash loan."""
        # Prefer stable tokens for flash loans
        token0, token1 = opportunity.token_pair.split('/')
        if token0 in ['USDC', 'DAI', 'USDT']:
            return self.config['tokens'][token0]['address']
        elif token1 in ['USDC', 'DAI', 'USDT']:
            return self.config['tokens'][token1]['address']
        else:
            # Default to WETH if no stables
            return self.config['tokens']['WETH']['address']

    def _calculate_optimal_amount(self, opportunity: Opportunity) -> int:
        """Calculate optimal flash loan amount."""
        # Start with maximum profitable amount
        max_amount = int(opportunity.buy_amount)
        
        # Consider pool liquidity limits
        if opportunity.market_conditions:
            liquidity_limit = int(opportunity.market_conditions.get('max_trade_size', max_amount))
            optimal_amount = min(max_amount, liquidity_limit)
            return optimal_amount
            
        return max_amount

    def _prepare_trade_path(self, opportunity: Opportunity) -> Tuple[List[str], List[int], List[bool]]:
        """Prepare trade path parameters for flash loan."""
        if opportunity.route_type == "triangular":
            return self._prepare_triangular_path(opportunity)
        else:
            return self._prepare_direct_path(opportunity)

    def _prepare_direct_path(self, opportunity: Opportunity) -> Tuple[List[str], List[int], List[bool]]:
        """Prepare direct trade path."""
        dex_paths = [
            self.config['dexes'][opportunity.buy_dex.split('_')[0]]['router'],
            self.config['dexes'][opportunity.sell_dex.split('_')[0]]['router']
        ]
        
        amounts = [
            int(opportunity.buy_amount),
            int(opportunity.sell_amount)
        ]
        
        is_v3 = [
            '_v3' in opportunity.buy_dex.lower(),
            '_v3' in opportunity.sell_dex.lower()
        ]
        
        return dex_paths, amounts, is_v3

    def _prepare_triangular_path(self, opportunity: Opportunity) -> Tuple[List[str], List[int], List[bool]]:
        """Prepare triangular trade path."""
        if not opportunity.intermediate_dex:
            raise ValueError("Missing intermediate DEX for triangular arbitrage")

        dex_paths = [
            self.config['dexes'][opportunity.buy_dex.split('_')[0]]['router'],
            self.config['dexes'][opportunity.intermediate_dex.split('_')[0]]['router'],
            self.config['dexes'][opportunity.sell_dex.split('_')[0]]['router']
        ]
        
        # Calculate intermediate amounts based on ratios
        amounts = [
            int(opportunity.buy_amount),
            int(opportunity.buy_amount * (1 + opportunity.profit_percent/2)),
            int(opportunity.sell_amount)
        ]
        
        is_v3 = [
            '_v3' in opportunity.buy_dex.lower(),
            '_v3' in opportunity.intermediate_dex.lower(),
            '_v3' in opportunity.sell_dex.lower()
        ]
        
        return dex_paths, amounts, is_v3

    async def _estimate_execution_gas(
        self,
        loan_token: str,
        loan_amount: int,
        params: bytes
    ) -> int:
        """Estimate gas for flash loan execution."""
        try:
            # Check cache first
            cache_key = f"{loan_token}:{loan_amount}:{params.hex()}"
            gas = await self._get_cached_data(
                cache_key,
                self._gas_cache,
                self._gas_cache_times
            )
            if gas is not None:
                return gas
            
            # Run gas estimation in thread pool with retries
            for attempt in range(MAX_RETRIES):
                try:
                    loop = asyncio.get_event_loop()
                    gas = await loop.run_in_executor(
                        self.executor,
                        self._estimate_gas,
                        loan_token,
                        loan_amount,
                        params
                    )
                    
                    # Update cache
                    await self._update_cache(
                        cache_key,
                        gas,
                        self._gas_cache,
                        self._gas_cache_times
                    )
                    
                    return cast(int, gas)
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to estimate gas after {MAX_RETRIES} attempts: {e}")
                    return 500000  # Conservative fallback
            
            return 500000  # Conservative fallback
            
        except Exception as e:
            logger.error(f"Error estimating gas: {str(e)}")
            return 500000  # Conservative fallback

    def _estimate_gas(
        self,
        loan_token: str,
        loan_amount: int,
        params: bytes
    ) -> int:
        """Estimate gas (CPU-bound)."""
        return self.flash_loan.functions.executeFlashLoan(
            loan_token,
            loan_amount,
            params
        ).estimate_gas({'from': self.w3.w3.eth.default_account})

    async def _execute_flash_loan(
        self,
        loan_token: str,
        loan_amount: int,
        params: bytes,
        gas_estimate: int,
        gas_price: Wei
    ) -> str:
        """Execute flash loan transaction."""
        # Get transaction parameters concurrently
        nonce_task = asyncio.create_task(self._get_nonce())
        chain_id_task = asyncio.create_task(self.w3.w3.eth.chain_id)
        
        nonce, chain_id = await asyncio.gather(nonce_task, chain_id_task)
        
        tx_params: TxParams = {
            'from': self.w3.w3.eth.default_account,
            'gas': Wei(int(gas_estimate * self.gas_buffer)),
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': chain_id
        }
        
        # Build and sign transaction in thread pool
        loop = asyncio.get_event_loop()
        signed_tx = await loop.run_in_executor(
            self.executor,
            self._build_and_sign_transaction,
            loan_token,
            loan_amount,
            params,
            tx_params
        )
        
        # Send transaction with retries
        for attempt in range(MAX_RETRIES):
            try:
                tx_hash = await self.w3.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                return tx_hash.hex()
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                logger.error(f"Failed to send transaction after {MAX_RETRIES} attempts: {e}")
                raise

    async def _get_nonce(self) -> int:
        """Get nonce with caching."""
        try:
            # Check cache first
            cache_key = 'nonce'
            nonce = await self._get_cached_data(
                cache_key,
                self._nonce_cache,
                self._nonce_cache_times
            )
            if nonce is not None:
                return nonce
            
            # Get new nonce with retries
            for attempt in range(MAX_RETRIES):
                try:
                    nonce = await self.w3.w3.eth.get_transaction_count(
                        self.w3.w3.eth.default_account
                    )
                    
                    # Update cache
                    await self._update_cache(
                        cache_key,
                        nonce,
                        self._nonce_cache,
                        self._nonce_cache_times
                    )
                    
                    return nonce
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY)
                        continue
                    logger.error(f"Failed to get nonce after {MAX_RETRIES} attempts: {e}")
                    raise
            
            raise Exception("Failed to get nonce")
            
        except Exception as e:
            logger.error(f"Error getting nonce: {e}")
            raise

    def _build_and_sign_transaction(
        self,
        loan_token: str,
        loan_amount: int,
        params: bytes,
        tx_params: TxParams
    ):
        """Build and sign transaction (CPU-bound)."""
        tx = self.flash_loan.functions.executeFlashLoan(
            loan_token,
            loan_amount,
            params
        ).build_transaction(tx_params)
        
        return self.w3.w3.eth.account.sign_transaction(tx, self.config['private_key'])

    async def _monitor_transaction(
        self,
        opportunity: Opportunity,
        tx_hash: str
    ) -> bool:
        """Monitor transaction status."""
        if not self.transaction_monitor:
            return True
            
        # Monitor transaction with retries
        for attempt in range(MAX_RETRIES):
            try:
                receipt = await self.transaction_monitor._check_transaction_success({
                    'hash': tx_hash
                })
                return bool(receipt)
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                logger.error(f"Failed to monitor transaction after {MAX_RETRIES} attempts: {e}")
                return False

    async def _update_profit_metrics(self, opportunity: Opportunity, tx_hash: str) -> None:
        """Update profit metrics after successful trade."""
        try:
            # Get receipt and process event concurrently
            receipt_task = asyncio.create_task(self.w3.w3.eth.get_transaction_receipt(tx_hash))
            
            receipt = await receipt_task
            
            # Process event in thread pool
            loop = asyncio.get_event_loop()
            event = await loop.run_in_executor(
                self.executor,
                lambda: self.flash_loan.events.FlashLoanExecuted().process_receipt(receipt)[0]
            )
            
            actual_profit = float(event.args.profit)
            opportunity.net_profit = actual_profit
            
            logger.info(f"Trade completed - Actual profit: ${actual_profit}")
            
        except Exception as e:
            logger.error(f"Error updating profit metrics: {str(e)}")

    async def _get_cached_data(
        self,
        key: str,
        cache: Dict[str, Any],
        cache_times: Dict[str, float]
    ) -> Optional[Any]:
        """Get data from cache if not expired."""
        try:
            current_time = time.time()
            
            async with self._cache_lock:
                if key in cache:
                    last_update = cache_times.get(key, 0)
                    if current_time - last_update < self.cache_ttl:
                        return cache[key]
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None

    async def _update_cache(
        self,
        key: str,
        data: Any,
        cache: Dict[str, Any],
        cache_times: Dict[str, float]
    ) -> None:
        """Update cache with new data."""
        try:
            async with self._cache_lock:
                cache[key] = data
                cache_times[key] = time.time()
        except Exception as e:
            logger.error(f"Error updating cache: {e}")

    async def _periodic_cache_cleanup(self) -> None:
        """Periodically clean up caches."""
        try:
            while True:
                await self._cleanup_caches()
                await asyncio.sleep(self.cache_ttl / 2)  # Clean up every half TTL
        except Exception as e:
            logger.error(f"Error in periodic cache cleanup: {e}")

    async def _cleanup_caches(self) -> None:
        """Clean up expired cache entries."""
        try:
            current_time = time.time()
            
            async with self._cache_lock:
                # Clean up DEX cache
                expired_dexes = [
                    key for key, last_update in self._dex_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_dexes:
                    del self._dex_cache[key]
                    del self._dex_cache_times[key]
                
                # Clean up quote cache
                expired_quotes = [
                    key for key, last_update in self._quote_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_quotes:
                    del self._quote_cache[key]
                    del self._quote_cache_times[key]
                
                # Clean up gas cache
                expired_gas = [
                    key for key, last_update in self._gas_cache_times.items()
                    if current_time - last_update > self.cache_ttl
                ]
                for key in expired_gas:
                    del self._gas_cache[key]
                    del self._gas_cache_times[key]
