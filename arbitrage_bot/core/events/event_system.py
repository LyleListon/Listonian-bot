"""Integrated event system for arbitrage bot components."""

import asyncio
import logging
import time
import os
from typing import Dict, List, Optional, Any, Union, Set

from arbitrage_bot.core.events.event_emitter import EventEmitter, Event
from arbitrage_bot.core.events.dex_events import DEXEventMonitor, SwapEvent, LiquidityEvent
from arbitrage_bot.core.events.opportunity_tracker import OpportunityTracker, ArbitrageOpportunity
from arbitrage_bot.core.events.transaction_monitor import TransactionLifecycleMonitor, TransactionRecord, TransactionStatus

logger = logging.getLogger(__name__)

class EventSystem:
    """
    Central event system for the arbitrage bot.
    
    Integrates all event-related components and provides a unified
    interface for event emission, subscription, and monitoring.
    """
    
    def __init__(
        self,
        web3_manager=None,  # Avoiding circular import
        dex_manager=None,   # Avoiding circular import
        data_dir: Optional[str] = None
    ):
        """
        Initialize event system.
        
        Args:
            web3_manager: Web3Manager instance for blockchain interaction
            dex_manager: DexManager instance for DEX access
            data_dir: Base directory for data storage
        """
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.data_dir = data_dir or os.path.join('data', 'events')
        
        # Create event directories
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize event emitter
        self.event_emitter = EventEmitter()
        
        # Initialize subsystems to None (will be created during start)
        self.dex_monitor: Optional[DEXEventMonitor] = None
        self.opportunity_tracker: Optional[OpportunityTracker] = None
        self.transaction_monitor: Optional[TransactionLifecycleMonitor] = None
        
        # Control flags
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        
        # For storing active event subscriptions
        self._subscriptions: Dict[str, Set[int]] = {}
        self._subscription_callbacks: Dict[int, Any] = {}
        self._next_subscription_id = 1
        
        logger.info("Initialized event system")
    
    async def start(self) -> bool:
        """
        Start the event system and all components.
        
        Returns:
            True if started successfully
        """
        async with self._lock:
            if self._running:
                logger.warning("Event system already running")
                return False
            
            logger.info("Starting event system")
            self._running = True
            self._shutdown_event.clear()
            
            # Initialize components if needed
            if self.web3_manager:
                if not self.dex_monitor:
                    self.dex_monitor = DEXEventMonitor(
                        event_emitter=self.event_emitter,
                        web3_manager=self.web3_manager,
                        dex_manager=self.dex_manager
                    )
                
                if not self.transaction_monitor:
                    self.transaction_monitor = TransactionLifecycleMonitor(
                        event_emitter=self.event_emitter,
                        web3_manager=self.web3_manager
                    )
            
            if not self.opportunity_tracker:
                opportunity_dir = os.path.join(self.data_dir, 'opportunities')
                self.opportunity_tracker = OpportunityTracker(
                    event_emitter=self.event_emitter,
                    data_dir=opportunity_dir
                )
            
            # Start components
            success = True
            
            if self.dex_monitor:
                success = success and await self.dex_monitor.start()
            
            if self.opportunity_tracker:
                success = success and await self.opportunity_tracker.start()
            
            if self.transaction_monitor:
                success = success and await self.transaction_monitor.start()
            
            # Register global event handlers
            await self._register_event_handlers()
            
            return success
    
    async def stop(self) -> bool:
        """
        Stop the event system and all components.
        
        Returns:
            True if stopped successfully
        """
        async with self._lock:
            if not self._running:
                logger.warning("Event system not running")
                return False
            
            logger.info("Stopping event system")
            self._running = False
            self._shutdown_event.set()
            
            # Stop components
            success = True
            
            if self.dex_monitor:
                success = success and await self.dex_monitor.stop()
            
            if self.opportunity_tracker:
                success = success and await self.opportunity_tracker.stop()
            
            if self.transaction_monitor:
                success = success and await self.transaction_monitor.stop()
            
            # Unregister event handlers
            await self._unregister_event_handlers()
            
            # Clear subscriptions
            self._subscriptions.clear()
            self._subscription_callbacks.clear()
            
            return success
    
    async def _register_event_handlers(self) -> None:
        """Register global event handlers."""
        # Register wildcard handler for subscription routing
        await self.event_emitter.on('*', self._route_event_to_subscribers)
    
    async def _unregister_event_handlers(self) -> None:
        """Unregister global event handlers."""
        await self.event_emitter.off('*', self._route_event_to_subscribers)
    
    async def _route_event_to_subscribers(self, event: Event[Any]) -> None:
        """
        Route events to subscribers.
        
        Args:
            event: Event to route
        """
        # Get subscriptions for this event
        subscriber_ids = self._subscriptions.get(event.name, set())
        
        # Also check for wildcard subscribers
        wildcard_ids = self._subscriptions.get('*', set())
        all_subscribers = subscriber_ids.union(wildcard_ids)
        
        # Invoke callbacks
        for sub_id in all_subscribers:
            callback = self._subscription_callbacks.get(sub_id)
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in subscription callback {sub_id}: {e}")
    
    async def emit(
        self,
        event_name: str,
        data: Any,
        source: Optional[str] = None,
        severity: str = "info"
    ) -> None:
        """
        Emit an event into the event system.
        
        Args:
            event_name: Event name/type
            data: Event payload
            source: Event source
            severity: Event severity
        """
        await self.event_emitter.emit(event_name, data, source=source, severity=severity)
    
    async def subscribe(
        self,
        event_name: str,
        callback: Any
    ) -> int:
        """
        Subscribe to events.
        
        Args:
            event_name: Event name to subscribe to (or '*' for all)
            callback: Function or coroutine to call with events
            
        Returns:
            Subscription ID for later unsubscription
        """
        async with self._lock:
            # Get next subscription ID
            sub_id = self._next_subscription_id
            self._next_subscription_id += 1
            
            # Register subscription
            if event_name not in self._subscriptions:
                self._subscriptions[event_name] = set()
            
            self._subscriptions[event_name].add(sub_id)
            self._subscription_callbacks[sub_id] = callback
            
            return sub_id
    
    async def unsubscribe(self, subscription_id: int) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: Subscription ID to unsubscribe
            
        Returns:
            True if unsubscribed successfully
        """
        async with self._lock:
            if subscription_id not in self._subscription_callbacks:
                return False
            
            # Remove from all event subscriptions
            for event_name, subs in self._subscriptions.items():
                if subscription_id in subs:
                    subs.remove(subscription_id)
            
            # Remove callback
            del self._subscription_callbacks[subscription_id]
            
            return True
    
    async def wait_for_event(
        self,
        event_name: str,
        timeout: Optional[float] = None,
        predicate=None
    ) -> Optional[Event[Any]]:
        """
        Wait for a specific event to occur.
        
        Args:
            event_name: Event name to wait for
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
            predicate: Optional function to filter events
            
        Returns:
            The event that occurred, or None if timeout
        """
        event_future = asyncio.Future()
        
        async def event_handler(event: Event[Any]) -> None:
            if predicate and not predicate(event):
                return
            if not event_future.done():
                event_future.set_result(event)
        
        # Subscribe to event
        sub_id = await self.subscribe(event_name, event_handler)
        
        try:
            # Wait for event with timeout
            if timeout is not None:
                return await asyncio.wait_for(event_future, timeout)
            else:
                return await event_future
        except asyncio.TimeoutError:
            return None
        finally:
            # Unsubscribe
            await self.unsubscribe(sub_id)
    
    # Convenience methods for common event emissions
    
    async def emit_opportunity(self, opportunity: ArbitrageOpportunity) -> None:
        """
        Emit an arbitrage opportunity event.
        
        Args:
            opportunity: Opportunity to emit
        """
        await self.emit(
            'arbitrage:opportunity',
            opportunity,
            source='arbitrage_bot',
            severity='info'
        )
    
    async def emit_transaction_submitted(
        self,
        tx_hash: str,
        from_address: str,
        to_address: str,
        value: int = 0,
        gas_price: int = 0,
        gas_limit: int = 0,
        opportunity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a transaction submission event.
        
        Args:
            tx_hash: Transaction hash
            from_address: Sender address
            to_address: Recipient address
            value: ETH value in wei
            gas_price: Gas price in wei
            gas_limit: Gas limit
            opportunity_id: Associated opportunity ID
            metadata: Additional metadata
        """
        await self.emit(
            'transaction:submitted',
            {
                'tx_hash': tx_hash,
                'from': from_address,
                'to': to_address,
                'value': value,
                'gas_price': gas_price,
                'gas': gas_limit,
                'opportunity_id': opportunity_id,
                'metadata': metadata or {},
                'timestamp': time.time()
            },
            source='arbitrage_bot',
            severity='info'
        )
    
    async def emit_bundle_submitted(
        self,
        bundle_id: str,
        tx_hashes: List[str],
        target_block: int,
        opportunity_id: Optional[str] = None
    ) -> None:
        """
        Emit a Flashbots bundle submission event.
        
        Args:
            bundle_id: Bundle ID
            tx_hashes: Transaction hashes in the bundle
            target_block: Target block number
            opportunity_id: Associated opportunity ID
        """
        await self.emit(
            'flashbots:bundle_submitted',
            {
                'bundle_id': bundle_id,
                'tx_hashes': tx_hashes,
                'target_block': target_block,
                'opportunity_id': opportunity_id,
                'timestamp': time.time()
            },
            source='arbitrage_bot',
            severity='info'
        )
    
    async def emit_execution_result(
        self,
        opportunity_id: str,
        tx_hash: str,
        status: str,
        actual_profit: Optional[int] = None,
        gas_used: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Emit an execution result event.
        
        Args:
            opportunity_id: Associated opportunity ID
            tx_hash: Transaction hash
            status: Execution status
            actual_profit: Actual profit achieved
            gas_used: Gas used by transaction
            error: Error message if failed
        """
        await self.emit(
            'arbitrage:execution',
            {
                'opportunity_id': opportunity_id,
                'tx_hash': tx_hash,
                'status': status,
                'actual_profit': actual_profit,
                'gas_used': gas_used,
                'error': error,
                'timestamp': time.time()
            },
            source='arbitrage_bot',
            severity='info' if status == 'executed' else 'error'
        )
    
    # Methods to access system components
    
    def get_recent_swap_events(
        self,
        token_addresses: Optional[List[str]] = None,
        dex_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[SwapEvent]:
        """
        Get recent swap events.
        
        Args:
            token_addresses: Filter by token addresses
            dex_names: Filter by DEX names
            limit: Maximum events to return
            
        Returns:
            List of swap events
        """
        if not self.dex_monitor:
            return []
        
        return self.dex_monitor.get_recent_swap_events(
            token_addresses=token_addresses,
            dex_names=dex_names,
            limit=limit
        )
    
    def get_recent_liquidity_events(
        self,
        token_addresses: Optional[List[str]] = None,
        dex_names: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[LiquidityEvent]:
        """
        Get recent liquidity events.
        
        Args:
            token_addresses: Filter by token addresses
            dex_names: Filter by DEX names
            limit: Maximum events to return
            
        Returns:
            List of liquidity events
        """
        if not self.dex_monitor:
            return []
        
        return self.dex_monitor.get_recent_liquidity_events(
            token_addresses=token_addresses,
            dex_names=dex_names,
            limit=limit
        )
    
    def get_transaction(self, tx_hash: str) -> Optional[TransactionRecord]:
        """
        Get transaction record by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction record or None if not found
        """
        if not self.transaction_monitor:
            return None
            
        return self.transaction_monitor.get_transaction(tx_hash)
    
    def get_opportunity(self, opportunity_id: str) -> Optional[ArbitrageOpportunity]:
        """
        Get opportunity by ID.
        
        Args:
            opportunity_id: Opportunity ID
            
        Returns:
            Opportunity or None if not found
        """
        if not self.opportunity_tracker:
            return None
            
        return self.opportunity_tracker.get_opportunity(opportunity_id)
    
    def get_opportunities(
        self,
        count: int = 100,
        status: Optional[str] = None,
        min_profit: Optional[int] = None,
        token_addresses: Optional[List[str]] = None
    ) -> List[ArbitrageOpportunity]:
        """
        Get arbitrage opportunities.
        
        Args:
            count: Maximum opportunities to return
            status: Filter by execution status
            min_profit: Minimum profit threshold
            token_addresses: Filter by tokens involved
            
        Returns:
            List of opportunities
        """
        if not self.opportunity_tracker:
            return []
            
        return self.opportunity_tracker.get_opportunities(
            count=count,
            status=status,
            min_profit=min_profit,
            token_addresses=token_addresses
        )
    
    def get_event_stats(self) -> Dict[str, Any]:
        """
        Get event system statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            "subscriptions": {
                "total": sum(len(subs) for subs in self._subscriptions.values()),
                "by_event": {name: len(subs) for name, subs in self._subscriptions.items()}
            }
        }
        
        # Add component stats
        if self.dex_monitor:
            stats["dex_monitor"] = {
                "running": self.dex_monitor._running,
                "swap_events_cache_size": len(self.dex_monitor._swap_events_cache),
                "liquidity_events_cache_size": len(self.dex_monitor._liquidity_events_cache)
            }
            
        if self.opportunity_tracker:
            stats["opportunity_tracker"] = self.opportunity_tracker.get_stats()
            
        if self.transaction_monitor:
            stats["transaction_monitor"] = self.transaction_monitor.get_stats()
        
        return stats


async def create_event_system(
    web3_manager=None,
    dex_manager=None,
    data_dir: Optional[str] = None
) -> EventSystem:
    """
    Create and initialize a complete event system.
    
    Args:
        web3_manager: Web3Manager instance
        dex_manager: DexManager instance
        data_dir: Data directory
        
    Returns:
        Initialized EventSystem
    """
    # Create event system
    system = EventSystem(
        web3_manager=web3_manager,
        dex_manager=dex_manager,
        data_dir=data_dir
    )
    
    # Start the system
    await system.start()
    
    return system