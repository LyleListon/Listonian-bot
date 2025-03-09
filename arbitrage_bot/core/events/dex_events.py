"""DEX event monitoring and processing for arbitrage opportunities."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union, cast
from decimal import Decimal
from web3 import Web3
from web3.contract import AsyncContract

from arbitrage_bot.core.events.event_emitter import Event, EventEmitter

logger = logging.getLogger(__name__)

@dataclass
class SwapEvent:
    """Standardized representation of a DEX swap event."""
    dex_name: str
    pool_address: str
    token0_address: str
    token1_address: str
    amount0_delta: Decimal
    amount1_delta: Decimal
    price: Decimal  # Price computed from the swap
    block_number: int
    transaction_hash: str
    timestamp: float
    raw_event: Optional[Dict[str, Any]] = None


@dataclass
class LiquidityEvent:
    """Standardized representation of a liquidity change event."""
    dex_name: str
    pool_address: str
    token0_address: str
    token1_address: str
    amount0_delta: Decimal
    amount1_delta: Decimal
    liquidity_delta: Decimal
    block_number: int
    transaction_hash: str
    timestamp: float
    raw_event: Optional[Dict[str, Any]] = None


class DEXEventMonitor:
    """
    Monitors DEX events across multiple exchanges.
    
    Processes on-chain events like swaps, liquidity changes, and other
    relevant blockchain events, converting them to standardized event
    objects and emitting them through the event system.
    """
    
    def __init__(
        self, 
        event_emitter: EventEmitter,
        web3_manager,  # Avoiding circular import
        dex_manager=None,  # Avoiding circular import
        polling_interval: int = 15
    ):
        """
        Initialize DEX event monitor.
        
        Args:
            event_emitter: EventEmitter instance for publishing events
            web3_manager: Web3Manager instance for blockchain interaction
            dex_manager: DexManager instance for accessing DEXs (optional)
            polling_interval: Time between event polling in seconds
        """
        self.event_emitter = event_emitter
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.polling_interval = polling_interval
        
        # Last processed block per DEX
        self._last_block: Dict[str, int] = {}
        
        # Running tasks
        self._tasks: Set[asyncio.Task] = set()
        
        # Control flags
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        
        # Store recently processed tx hashes to avoid duplicates
        self._processed_txs: Set[str] = set()
        self._max_processed_txs = 1000  # Prevent memory growth
        
        # Event cache
        self._swap_events_cache: List[SwapEvent] = []
        self._liquidity_events_cache: List[LiquidityEvent] = []
        self._max_cache_size = 5000  # Limit cache size
        
        # Event signature lookup
        self._event_signatures = {
            # Common event signatures across DEXs
            'Swap': 'Swap(address,address,int256,int256,uint160,uint128,int24)',
            'Mint': 'Mint(address,address,int24,int24,uint128,uint256,uint256)',
            'Burn': 'Burn(address,int24,int24,uint128,uint256,uint256)',
            'Transfer': 'Transfer(address,address,uint256)',
            'Sync': 'Sync(uint112,uint112)',
            'PoolCreated': 'PoolCreated(address,address,uint24,int24,address)'
        }
        
        logger.info("Initialized DEX event monitor")

    async def start(self) -> bool:
        """
        Start monitoring DEX events.
        
        Returns:
            True if started successfully, False otherwise
        """
        async with self._lock:
            if self._running:
                logger.warning("DEX event monitor already running")
                return False
            
            logger.info("Starting DEX event monitor")
            self._running = True
            self._shutdown_event.clear()
            
            # Initialize last blocks if not set
            if not self._last_block and self.dex_manager:
                current_block = await self.web3_manager.w3.eth.block_number
                for dex_name in self.dex_manager.get_enabled_dexes():
                    self._last_block[dex_name] = current_block
            
            # Start monitoring task
            monitoring_task = asyncio.create_task(self._monitor_events())
            self._tasks.add(monitoring_task)
            monitoring_task.add_done_callback(self._tasks.discard)
            
            return True
    
    async def stop(self) -> bool:
        """
        Stop monitoring DEX events.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        async with self._lock:
            if not self._running:
                logger.warning("DEX event monitor not running")
                return False
            
            logger.info("Stopping DEX event monitor")
            self._running = False
            self._shutdown_event.set()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
                self._tasks.clear()
            
            return True
    
    async def _monitor_events(self) -> None:
        """Monitor DEX events periodically."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    if self.dex_manager:
                        # Fetch new events for each DEX
                        for dex_name, dex in self.dex_manager.get_enabled_dexes().items():
                            await self._fetch_dex_events(dex_name, dex)
                    
                    # Process and analyze events
                    await self._process_events()
                    
                    # Prune old processed tx cache
                    if len(self._processed_txs) > self._max_processed_txs:
                        self._processed_txs = set(list(self._processed_txs)[-self._max_processed_txs:])
                    
                    # Wait for next polling interval or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.polling_interval
                        )
                    except asyncio.TimeoutError:
                        # Normal timeout, continue polling
                        pass
                
                except Exception as e:
                    logger.error(f"Error during event monitoring: {e}")
                    # Brief delay to avoid rapid retry on persistent errors
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            logger.info("DEX event monitoring task cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in DEX event monitor: {e}")
    
    async def _fetch_dex_events(self, dex_name: str, dex) -> None:
        """
        Fetch events for a specific DEX.
        
        Args:
            dex_name: Name of the DEX
            dex: DEX instance
        """
        try:
            # Get current block
            current_block = await self.web3_manager.w3.eth.block_number
            from_block = self._last_block.get(dex_name, current_block - 1000)
            
            # Don't fetch too many blocks at once
            max_blocks = 2000
            if current_block - from_block > max_blocks:
                from_block = current_block - max_blocks
            
            # Only proceed if there are new blocks
            if from_block >= current_block:
                return
            
            logger.debug(f"Fetching events for {dex_name} from block {from_block} to {current_block}")
            
            # Get pools to monitor based on DEX type
            if hasattr(dex, '_get_pool_address'):
                # For V3 style DEXs, get active pools
                pools = await self._get_active_pools(dex)
            else:
                # For V2 style DEXs, get factory
                pools = [dex.factory_address] if hasattr(dex, 'factory_address') else []
            
            # No pools to monitor
            if not pools:
                logger.debug(f"No pools to monitor for {dex_name}")
                self._last_block[dex_name] = current_block
                return
            
            # Fetch events for each pool
            for pool_address in pools:
                # Get pool contract
                if pool_address == dex.factory_address:
                    contract = dex.factory
                else:
                    # Get V3 pool contract
                    if hasattr(dex, '_get_pool_contract'):
                        contract = await dex._get_pool_contract(pool_address)
                    else:
                        continue
                
                if not contract:
                    continue
                
                # Fetch swap events
                await self._fetch_swap_events(dex_name, contract, pool_address, from_block, current_block)
                
                # Fetch liquidity events
                await self._fetch_liquidity_events(dex_name, contract, pool_address, from_block, current_block)
            
            # Update last processed block
            self._last_block[dex_name] = current_block
        
        except Exception as e:
            logger.error(f"Error fetching events for {dex_name}: {e}")
    
    async def _get_active_pools(self, dex) -> List[str]:
        """
        Get list of active pool addresses for a DEX.
        
        Args:
            dex: DEX instance
            
        Returns:
            List of pool addresses
        """
        pools = []
        
        # If DEX has token whitelist, use it to get pools
        if hasattr(dex, 'get_supported_tokens'):
            tokens = await dex.get_supported_tokens()
            
            # Get pools for each token pair
            for i, token0 in enumerate(tokens):
                for token1 in tokens[i+1:]:
                    try:
                        if hasattr(dex, '_get_pool_address'):
                            pool_address = await dex._get_pool_address(token0, token1)
                            if pool_address != "0x0000000000000000000000000000000000000000":
                                pools.append(pool_address)
                    except Exception as e:
                        logger.debug(f"Error getting pool for {token0}/{token1}: {e}")
        
        return pools
    
    async def _fetch_swap_events(
        self, 
        dex_name: str, 
        contract: AsyncContract,
        pool_address: str,
        from_block: int,
        to_block: int
    ) -> None:
        """
        Fetch swap events for a specific contract.
        
        Args:
            dex_name: Name of the DEX
            contract: Contract to fetch events from
            pool_address: Address of the pool
            from_block: Start block
            to_block: End block
        """
        try:
            # Check if contract has Swap event
            if not hasattr(contract.events, 'Swap'):
                return
            
            # Get token addresses for the pool
            token0, token1 = await self._get_pool_tokens(contract, pool_address)
            if not token0 or not token1:
                return
            
            # Get event signature
            swap_signature = Web3.keccak(text=self._event_signatures['Swap']).hex()
            
            # Fetch logs
            logs = await self.web3_manager.w3.eth.get_logs({
                'address': pool_address,
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [swap_signature]
            })
            
            # Process swap events
            for log in logs:
                try:
                    # Skip if already processed
                    tx_hash = log.get('transactionHash').hex()
                    if tx_hash in self._processed_txs:
                        continue
                    
                    # Parse log
                    parsed_log = contract.events.Swap().process_log(dict(log))
                    
                    # Get block timestamp
                    block = await self.web3_manager.w3.eth.get_block(log.get('blockNumber'))
                    timestamp = block.get('timestamp', time.time())
                    
                    # Extract values depending on DEX version
                    if 'amount0' in parsed_log['args'] and 'amount1' in parsed_log['args']:
                        # V3 style
                        amount0 = Decimal(str(parsed_log['args']['amount0']))
                        amount1 = Decimal(str(parsed_log['args']['amount1']))
                    elif 'amount0In' in parsed_log['args'] and 'amount0Out' in parsed_log['args']:
                        # V2 style
                        amount0 = Decimal(str(parsed_log['args']['amount0Out'])) - Decimal(str(parsed_log['args']['amount0In']))
                        amount1 = Decimal(str(parsed_log['args']['amount1Out'])) - Decimal(str(parsed_log['args']['amount1In']))
                    else:
                        # Unknown format
                        continue
                    
                    # Calculate price (safe division)
                    price = Decimal('0')
                    if amount0 != 0 and amount1 != 0:
                        price = abs(amount1 / amount0) if amount0 != 0 else 0
                    
                    # Create swap event object
                    swap_event = SwapEvent(
                        dex_name=dex_name,
                        pool_address=pool_address,
                        token0_address=token0,
                        token1_address=token1,
                        amount0_delta=amount0,
                        amount1_delta=amount1,
                        price=price,
                        block_number=log.get('blockNumber'),
                        transaction_hash=tx_hash,
                        timestamp=timestamp,
                        raw_event=parsed_log
                    )
                    
                    # Add to cache
                    self._swap_events_cache.append(swap_event)
                    if len(self._swap_events_cache) > self._max_cache_size:
                        self._swap_events_cache.pop(0)
                    
                    # Mark as processed
                    self._processed_txs.add(tx_hash)
                    
                    # Emit event
                    await self.event_emitter.emit(
                        'dex:swap',
                        swap_event,
                        source=f"dex_monitor:{dex_name}"
                    )
                
                except Exception as e:
                    logger.debug(f"Error processing swap event: {e}")
        
        except Exception as e:
            logger.error(f"Error fetching swap events for {dex_name} pool {pool_address}: {e}")
    
    async def _fetch_liquidity_events(
        self, 
        dex_name: str, 
        contract: AsyncContract,
        pool_address: str,
        from_block: int,
        to_block: int
    ) -> None:
        """
        Fetch liquidity events (Mint, Burn) for a specific contract.
        
        Args:
            dex_name: Name of the DEX
            contract: Contract to fetch events from
            pool_address: Address of the pool
            from_block: Start block
            to_block: End block
        """
        try:
            # Check if contract has liquidity events
            has_mint = hasattr(contract.events, 'Mint')
            has_burn = hasattr(contract.events, 'Burn')
            
            if not has_mint and not has_burn:
                return
            
            # Get token addresses for the pool
            token0, token1 = await self._get_pool_tokens(contract, pool_address)
            if not token0 or not token1:
                return
            
            # Process Mint events
            if has_mint:
                await self._process_mint_events(
                    dex_name, contract, pool_address, token0, token1, from_block, to_block
                )
            
            # Process Burn events
            if has_burn:
                await self._process_burn_events(
                    dex_name, contract, pool_address, token0, token1, from_block, to_block
                )
        
        except Exception as e:
            logger.error(f"Error fetching liquidity events for {dex_name} pool {pool_address}: {e}")
    
    async def _process_mint_events(
        self,
        dex_name: str,
        contract: AsyncContract,
        pool_address: str,
        token0: str,
        token1: str,
        from_block: int,
        to_block: int
    ) -> None:
        """Process Mint events for a pool."""
        try:
            # Get event signature
            mint_signature = Web3.keccak(text=self._event_signatures['Mint']).hex()
            
            # Fetch logs
            logs = await self.web3_manager.w3.eth.get_logs({
                'address': pool_address,
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [mint_signature]
            })
            
            # Process events
            for log in logs:
                try:
                    # Skip if already processed
                    tx_hash = log.get('transactionHash').hex()
                    if tx_hash in self._processed_txs:
                        continue
                    
                    # Parse log
                    parsed_log = contract.events.Mint().process_log(dict(log))
                    
                    # Get block timestamp
                    block = await self.web3_manager.w3.eth.get_block(log.get('blockNumber'))
                    timestamp = block.get('timestamp', time.time())
                    
                    # Extract values
                    amount0 = Decimal(str(parsed_log['args'].get('amount0', 0)))
                    amount1 = Decimal(str(parsed_log['args'].get('amount1', 0)))
                    liquidity = Decimal(str(parsed_log['args'].get('liquidity', 0)))
                    
                    # Create liquidity event
                    liquidity_event = LiquidityEvent(
                        dex_name=dex_name,
                        pool_address=pool_address,
                        token0_address=token0,
                        token1_address=token1,
                        amount0_delta=amount0,
                        amount1_delta=amount1,
                        liquidity_delta=liquidity,
                        block_number=log.get('blockNumber'),
                        transaction_hash=tx_hash,
                        timestamp=timestamp,
                        raw_event=parsed_log
                    )
                    
                    # Add to cache
                    self._liquidity_events_cache.append(liquidity_event)
                    if len(self._liquidity_events_cache) > self._max_cache_size:
                        self._liquidity_events_cache.pop(0)
                    
                    # Mark as processed
                    self._processed_txs.add(tx_hash)
                    
                    # Emit event
                    await self.event_emitter.emit(
                        'dex:liquidity_added',
                        liquidity_event,
                        source=f"dex_monitor:{dex_name}"
                    )
                
                except Exception as e:
                    logger.debug(f"Error processing Mint event: {e}")
        
        except Exception as e:
            logger.error(f"Error processing Mint events for {dex_name} pool {pool_address}: {e}")
    
    async def _process_burn_events(
        self,
        dex_name: str,
        contract: AsyncContract,
        pool_address: str,
        token0: str,
        token1: str,
        from_block: int,
        to_block: int
    ) -> None:
        """Process Burn events for a pool."""
        try:
            # Get event signature
            burn_signature = Web3.keccak(text=self._event_signatures['Burn']).hex()
            
            # Fetch logs
            logs = await self.web3_manager.w3.eth.get_logs({
                'address': pool_address,
                'fromBlock': from_block,
                'toBlock': to_block,
                'topics': [burn_signature]
            })
            
            # Process events
            for log in logs:
                try:
                    # Skip if already processed
                    tx_hash = log.get('transactionHash').hex()
                    if tx_hash in self._processed_txs:
                        continue
                    
                    # Parse log
                    parsed_log = contract.events.Burn().process_log(dict(log))
                    
                    # Get block timestamp
                    block = await self.web3_manager.w3.eth.get_block(log.get('blockNumber'))
                    timestamp = block.get('timestamp', time.time())
                    
                    # Extract values
                    amount0 = -Decimal(str(parsed_log['args'].get('amount0', 0)))  # Negative for liquidity removal
                    amount1 = -Decimal(str(parsed_log['args'].get('amount1', 0)))  # Negative for liquidity removal
                    liquidity = -Decimal(str(parsed_log['args'].get('liquidity', 0)))  # Negative for liquidity removal
                    
                    # Create liquidity event
                    liquidity_event = LiquidityEvent(
                        dex_name=dex_name,
                        pool_address=pool_address,
                        token0_address=token0,
                        token1_address=token1,
                        amount0_delta=amount0,
                        amount1_delta=amount1,
                        liquidity_delta=liquidity,
                        block_number=log.get('blockNumber'),
                        transaction_hash=tx_hash,
                        timestamp=timestamp,
                        raw_event=parsed_log
                    )
                    
                    # Add to cache
                    self._liquidity_events_cache.append(liquidity_event)
                    if len(self._liquidity_events_cache) > self._max_cache_size:
                        self._liquidity_events_cache.pop(0)
                    
                    # Mark as processed
                    self._processed_txs.add(tx_hash)
                    
                    # Emit event
                    await self.event_emitter.emit(
                        'dex:liquidity_removed',
                        liquidity_event,
                        source=f"dex_monitor:{dex_name}"
                    )
                
                except Exception as e:
                    logger.debug(f"Error processing Burn event: {e}")
        
        except Exception as e:
            logger.error(f"Error processing Burn events for {dex_name} pool {pool_address}: {e}")
    
    async def _get_pool_tokens(self, contract: AsyncContract, pool_address: str) -> Tuple[Optional[str], Optional[str]]:
        """Get token0 and token1 addresses for a pool."""
        try:
            # Try to get token0 and token1 from contract
            if hasattr(contract.functions, 'token0') and hasattr(contract.functions, 'token1'):
                token0 = await self.web3_manager.call_contract_function(contract.functions.token0)
                token1 = await self.web3_manager.call_contract_function(contract.functions.token1)
                return Web3.to_checksum_address(token0), Web3.to_checksum_address(token1)
            
            return None, None
        
        except Exception as e:
            logger.debug(f"Error getting tokens for pool {pool_address}: {e}")
            return None, None
    
    async def _process_events(self) -> None:
        """Process and analyze accumulated events."""
        # Analyze large price movements
        await self._analyze_price_movements()
        
        # Analyze liquidity changes
        await self._analyze_liquidity_changes()
    
    async def _analyze_price_movements(self) -> None:
        """
        Analyze recent swap events for significant price movements.
        
        Emits 'arbitrage:opportunity' events when significant price
        discrepancies are detected between DEXs.
        """
        try:
            # Group recent swaps by token pair
            pairs = {}
            recency_threshold = time.time() - 300  # Last 5 minutes
            
            for event in self._swap_events_cache:
                # Skip older events
                if event.timestamp < recency_threshold:
                    continue
                
                # Create token pair key (sorted for consistency)
                tokens = sorted([event.token0_address, event.token1_address])
                pair_key = f"{tokens[0]}_{tokens[1]}"
                
                if pair_key not in pairs:
                    pairs[pair_key] = {}
                
                if event.dex_name not in pairs[pair_key]:
                    pairs[pair_key][event.dex_name] = []
                
                pairs[pair_key][event.dex_name].append(event)
            
            # Analyze price differences between DEXs
            for pair_key, dex_events in pairs.items():
                # Need at least 2 DEXs for comparison
                if len(dex_events) < 2:
                    continue
                
                # Get price data for each DEX
                prices = {}
                for dex_name, events in dex_events.items():
                    if not events:
                        continue
                    
                    # Use latest event
                    latest = max(events, key=lambda e: e.timestamp)
                    prices[dex_name] = latest.price
                
                # Need at least 2 prices for comparison
                if len(prices) < 2:
                    continue
                
                # Find max and min prices
                max_price_dex = max(prices.items(), key=lambda x: x[1])
                min_price_dex = min(prices.items(), key=lambda x: x[1])
                
                # Calculate price difference
                price_diff_pct = ((max_price_dex[1] - min_price_dex[1]) / min_price_dex[1]) * 100
                
                # Emit opportunity event if difference is significant (> 0.5%)
                if price_diff_pct > 0.5:
                    token_addresses = pair_key.split('_')
                    
                    # Emit opportunity event
                    await self.event_emitter.emit(
                        'arbitrage:opportunity',
                        {
                            'token_pair': token_addresses,
                            'price_diff_pct': float(price_diff_pct),
                            'high_price': {
                                'dex': max_price_dex[0],
                                'price': float(max_price_dex[1])
                            },
                            'low_price': {
                                'dex': min_price_dex[0],
                                'price': float(min_price_dex[1])
                            },
                            'timestamp': time.time()
                        },
                        source="dex_monitor:price_analysis",
                        severity="info"
                    )
        
        except Exception as e:
            logger.error(f"Error analyzing price movements: {e}")
    
    async def _analyze_liquidity_changes(self) -> None:
        """
        Analyze recent liquidity events for significant changes.
        
        Emits 'arbitrage:liquidity_change' events when significant
        liquidity changes are detected.
        """
        try:
            # Group recent liquidity events by pool
            pools = {}
            recency_threshold = time.time() - 900  # Last 15 minutes
            
            for event in self._liquidity_events_cache:
                # Skip older events
                if event.timestamp < recency_threshold:
                    continue
                
                # Pool key
                pool_key = f"{event.dex_name}_{event.pool_address}"
                
                if pool_key not in pools:
                    pools[pool_key] = []
                
                pools[pool_key].append(event)
            
            # Analyze liquidity changes
            for pool_key, events in pools.items():
                if not events:
                    continue
                
                # Calculate net liquidity change
                total_change = sum(event.liquidity_delta for event in events)
                
                # Get latest event for pool details
                latest = max(events, key=lambda e: e.timestamp)
                
                # Emit liquidity change event if significant
                if abs(total_change) > 0:
                    await self.event_emitter.emit(
                        'arbitrage:liquidity_change',
                        {
                            'dex_name': latest.dex_name,
                            'pool_address': latest.pool_address,
                            'token0': latest.token0_address,
                            'token1': latest.token1_address,
                            'net_change': float(total_change),
                            'event_count': len(events),
                            'timestamp': time.time()
                        },
                        source="dex_monitor:liquidity_analysis",
                        severity="info"
                    )
        
        except Exception as e:
            logger.error(f"Error analyzing liquidity changes: {e}")
    
    def get_recent_swap_events(
        self,
        token_addresses: Optional[List[str]] = None,
        dex_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[SwapEvent]:
        """
        Get recent swap events, optionally filtered by tokens and DEXs.
        
        Args:
            token_addresses: List of token addresses to filter by (None = all)
            dex_names: List of DEX names to filter by (None = all)
            limit: Maximum number of events to return
            
        Returns:
            List of swap events in reverse chronological order
        """
        # Sort by timestamp (newest first)
        sorted_events = sorted(
            self._swap_events_cache,
            key=lambda e: e.timestamp,
            reverse=True
        )
        
        # Apply filters
        filtered_events = []
        for event in sorted_events:
            # Apply token filter
            if token_addresses and not (
                event.token0_address in token_addresses or
                event.token1_address in token_addresses
            ):
                continue
            
            # Apply DEX filter
            if dex_names and event.dex_name not in dex_names:
                continue
            
            filtered_events.append(event)
            
            # Respect limit
            if len(filtered_events) >= limit:
                break
        
        return filtered_events
    
    def get_recent_liquidity_events(
        self,
        token_addresses: Optional[List[str]] = None,
        dex_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[LiquidityEvent]:
        """
        Get recent liquidity events, optionally filtered by tokens and DEXs.
        
        Args:
            token_addresses: List of token addresses to filter by (None = all)
            dex_names: List of DEX names to filter by (None = all)
            limit: Maximum number of events to return
            
        Returns:
            List of liquidity events in reverse chronological order
        """
        # Sort by timestamp (newest first)
        sorted_events = sorted(
            self._liquidity_events_cache,
            key=lambda e: e.timestamp,
            reverse=True
        )
        
        # Apply filters
        filtered_events = []
        for event in sorted_events:
            # Apply token filter
            if token_addresses and not (
                event.token0_address in token_addresses or
                event.token1_address in token_addresses
            ):
                continue
            
            # Apply DEX filter
            if dex_names and event.dex_name not in dex_names:
                continue
            
            filtered_events.append(event)
            
            # Respect limit
            if len(filtered_events) >= limit:
                break
        
        return filtered_events