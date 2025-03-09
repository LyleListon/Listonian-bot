"""Opportunity tracking system for arbitrage paths and profitability analysis."""

import asyncio
import logging
import time
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Tuple
from decimal import Decimal
from web3 import Web3
from pathlib import Path

from arbitrage_bot.core.events.event_emitter import Event, EventEmitter

logger = logging.getLogger(__name__)

@dataclass
class ArbitrageOpportunity:
    """Representation of a discovered arbitrage opportunity."""
    
    # Core opportunity identifiers
    id: str  # Unique identifier
    timestamp: float  # When opportunity was discovered
    
    # Token information
    input_token: str  # Starting token address
    output_token: str  # Ending token address (usually same as input for circular)
    
    # Route information
    route: List[Dict[str, Any]]  # List of steps in the arbitrage path
    
    # Financial details
    input_amount: int  # Amount in wei
    expected_output: int  # Expected output in wei
    expected_profit: int  # Expected profit in wei
    expected_profit_usd: float = 0.0  # Expected profit in USD
    gas_cost: int = 0  # Estimated gas cost in wei
    gas_price: int = 0  # Gas price in wei
    
    # Execution details
    execution_status: str = "pending"  # pending, executed, failed, rejected
    execution_txhash: Optional[str] = None  # Transaction hash if executed
    execution_timestamp: Optional[float] = None  # When executed
    actual_profit: Optional[int] = None  # Actual profit achieved (if executed)
    execution_gas_used: Optional[int] = None  # Actual gas used (if executed)
    
    # Analysis
    probability: float = 0.0  # Estimated success probability (0-1)
    profitability_score: float = 0.0  # Overall score (higher is better)
    source_system: str = "path_finder"  # System that discovered this opportunity
    
    # Tags for categorization and filtering
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArbitrageOpportunity':
        """Create from dictionary."""
        return cls(**data)
    
    def calculate_profitability_score(self, eth_price_usd: float = 0) -> float:
        """
        Calculate overall profitability score for ranking opportunities.
        
        Args:
            eth_price_usd: Current ETH price in USD for better scoring
            
        Returns:
            Score from 0-100, higher is better
        """
        # Start with base profit factor (profit / input)
        profit_factor = self.expected_profit / max(self.input_amount, 1)
        
        # Multiply by success probability
        weighted_profit = profit_factor * self.probability
        
        # Apply gas efficiency factor
        gas_efficiency = 1.0
        if self.gas_cost > 0:
            # Higher value means more profit per gas unit
            gas_efficiency = min(1.0, self.expected_profit / (self.gas_cost * 2))
        
        # Calculate USD profit if ETH price is available
        if eth_price_usd > 0:
            self.expected_profit_usd = (self.expected_profit / 1e18) * eth_price_usd
        
        # Calculate final score (0-100)
        self.profitability_score = min(100, weighted_profit * gas_efficiency * 10000)
        
        return self.profitability_score


class OpportunityTracker:
    """
    Tracks and analyzes arbitrage opportunities over time.
    
    Records discovered opportunities, their execution status, and analyzes
    patterns to improve future opportunity selection.
    """
    
    def __init__(
        self,
        event_emitter: EventEmitter,
        data_dir: Optional[str] = None,
        max_memory_opportunities: int = 1000,
        auto_persist: bool = True,
        persist_interval: int = 300  # 5 minutes
    ):
        """
        Initialize opportunity tracker.
        
        Args:
            event_emitter: EventEmitter instance for event handling
            data_dir: Directory for persisting opportunity data
            max_memory_opportunities: Maximum opportunities to keep in memory
            auto_persist: Whether to automatically persist opportunities
            persist_interval: How often to persist in seconds
        """
        self.event_emitter = event_emitter
        self.data_dir = data_dir or os.path.join("data", "opportunities")
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Opportunity storage
        self._opportunities: Dict[str, ArbitrageOpportunity] = {}
        self._max_memory_opportunities = max_memory_opportunities
        
        # Statistics and analytics
        self._token_pair_stats: Dict[str, Dict[str, Any]] = {}
        self._dex_pair_stats: Dict[str, Dict[str, Any]] = {}
        
        # For tracking token price history
        self._token_prices: Dict[str, List[Tuple[float, float]]] = {}  # token -> [(timestamp, price)]
        
        # Control flags
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        
        # Auto-persistence
        self._auto_persist = auto_persist
        self._persist_interval = persist_interval
        self._persist_task = None
        
        # Performance metrics
        self._execution_success_rate = 0.0
        self._average_profit = 0
        self._total_profit = 0
        self._opportunity_count = 0
        self._executed_count = 0
        
        logger.info(f"Initialized opportunity tracker with data dir: {self.data_dir}")
    
    async def start(self) -> bool:
        """
        Start the opportunity tracker.
        
        Returns:
            True if started successfully, False otherwise
        """
        async with self._lock:
            if self._running:
                logger.warning("Opportunity tracker already running")
                return False
            
            logger.info("Starting opportunity tracker")
            self._running = True
            self._shutdown_event.clear()
            
            # Load existing opportunities
            await self._load_opportunities()
            
            # Register event handlers
            await self._register_event_handlers()
            
            # Start auto-persist task if enabled
            if self._auto_persist:
                self._persist_task = asyncio.create_task(self._auto_persist_loop())
            
            return True
    
    async def stop(self) -> bool:
        """
        Stop the opportunity tracker.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        async with self._lock:
            if not self._running:
                logger.warning("Opportunity tracker not running")
                return False
            
            logger.info("Stopping opportunity tracker")
            self._running = False
            self._shutdown_event.set()
            
            # Remove event handlers
            await self._unregister_event_handlers()
            
            # Wait for persist task to complete
            if self._persist_task:
                try:
                    await asyncio.wait_for(self._persist_task, timeout=10)
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for persist task to complete")
                self._persist_task = None
            
            # Final persist
            await self.persist_opportunities()
            
            return True
    
    async def _register_event_handlers(self) -> None:
        """Register event handlers for tracking opportunities."""
        # Handler for new opportunities
        await self.event_emitter.on('arbitrage:opportunity', self._handle_opportunity_event)
        
        # Handler for opportunity execution
        await self.event_emitter.on('arbitrage:execution', self._handle_execution_event)
        
        # Handler for token price updates
        await self.event_emitter.on('market:token_price', self._handle_token_price_event)
    
    async def _unregister_event_handlers(self) -> None:
        """Unregister event handlers."""
        # Remove all event handlers
        await self.event_emitter.off('arbitrage:opportunity', self._handle_opportunity_event)
        await self.event_emitter.off('arbitrage:execution', self._handle_execution_event)
        await self.event_emitter.off('market:token_price', self._handle_token_price_event)
    
    async def _handle_opportunity_event(self, event: Event[Any]) -> None:
        """
        Handle new arbitrage opportunity events.
        
        Args:
            event: Event containing opportunity data
        """
        try:
            data = event.data
            
            # Skip if not a valid opportunity
            if not isinstance(data, dict):
                return
            
            # If it's an ArbitrageOpportunity instance, just track it
            if isinstance(data, ArbitrageOpportunity):
                await self.track_opportunity(data)
                return
                
            # Otherwise, build opportunity object from event data
            
            # Generate ID if not provided
            opportunity_id = data.get('id', f"opp_{int(time.time())}_{hash(str(data))}")
            
            # Create opportunity object
            opportunity = ArbitrageOpportunity(
                id=opportunity_id,
                timestamp=data.get('timestamp', time.time()),
                input_token=data.get('input_token', ''),
                output_token=data.get('output_token', ''),
                route=data.get('route', []),
                input_amount=data.get('input_amount', 0),
                expected_output=data.get('expected_output', 0),
                expected_profit=data.get('expected_profit', 0),
                gas_cost=data.get('gas_cost', 0),
                gas_price=data.get('gas_price', 0),
                probability=data.get('probability', 0.0),
                source_system=data.get('source_system', event.source or 'unknown')
            )
            
            # Track the opportunity
            await self.track_opportunity(opportunity)
            
        except Exception as e:
            logger.error(f"Error handling opportunity event: {e}")
    
    async def _handle_execution_event(self, event: Event[Any]) -> None:
        """
        Handle arbitrage execution events.
        
        Args:
            event: Event containing execution data
        """
        try:
            data = event.data
            
            # Skip if not a valid execution event
            if not isinstance(data, dict):
                return
            
            # Get opportunity ID and execution details
            opportunity_id = data.get('opportunity_id')
            if not opportunity_id:
                return
            
            # Update opportunity with execution results
            await self.update_opportunity_execution(
                opportunity_id=opportunity_id,
                status=data.get('status', 'executed'),
                tx_hash=data.get('tx_hash'),
                actual_profit=data.get('actual_profit'),
                gas_used=data.get('gas_used'),
                timestamp=data.get('timestamp', time.time())
            )
            
        except Exception as e:
            logger.error(f"Error handling execution event: {e}")
    
    async def _handle_token_price_event(self, event: Event[Any]) -> None:
        """
        Handle token price update events.
        
        Args:
            event: Event containing token price data
        """
        try:
            data = event.data
            
            # Skip if not a valid price event
            if not isinstance(data, dict):
                return
            
            # Get token address and price
            token_address = data.get('token_address')
            price_usd = data.get('price_usd')
            
            if not token_address or not price_usd:
                return
            
            # Update token price
            if token_address not in self._token_prices:
                self._token_prices[token_address] = []
            
            # Add price data with timestamp
            self._token_prices[token_address].append((time.time(), float(price_usd)))
            
            # Limit history size
            if len(self._token_prices[token_address]) > 1000:
                self._token_prices[token_address] = self._token_prices[token_address][-1000:]
            
        except Exception as e:
            logger.error(f"Error handling token price event: {e}")
    
    async def track_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Track a new arbitrage opportunity.
        
        Args:
            opportunity: Opportunity to track
            
        Returns:
            True if opportunity was tracked successfully
        """
        async with self._lock:
            # Add to tracked opportunities
            self._opportunities[opportunity.id] = opportunity
            
            # Update statistics
            self._update_statistics(opportunity)
            
            # Trim if needed
            if len(self._opportunities) > self._max_memory_opportunities:
                self._trim_opportunities()
            
            # Emit event for other components
            await self.event_emitter.emit(
                'tracker:opportunity_recorded',
                opportunity.to_dict(),
                source="opportunity_tracker"
            )
            
            return True
    
    async def update_opportunity_execution(
        self,
        opportunity_id: str,
        status: str,
        tx_hash: Optional[str] = None,
        actual_profit: Optional[int] = None,
        gas_used: Optional[int] = None,
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Update execution details for an opportunity.
        
        Args:
            opportunity_id: ID of opportunity to update
            status: New execution status (executed, failed, rejected)
            tx_hash: Transaction hash if executed
            actual_profit: Actual profit achieved in wei
            gas_used: Actual gas used
            timestamp: Execution timestamp
            
        Returns:
            True if opportunity was updated
        """
        async with self._lock:
            # Check if opportunity exists
            if opportunity_id not in self._opportunities:
                logger.warning(f"Opportunity {opportunity_id} not found for execution update")
                return False
            
            # Get opportunity
            opportunity = self._opportunities[opportunity_id]
            
            # Update execution details
            opportunity.execution_status = status
            opportunity.execution_txhash = tx_hash
            opportunity.execution_timestamp = timestamp or time.time()
            
            if actual_profit is not None:
                opportunity.actual_profit = actual_profit
            
            if gas_used is not None:
                opportunity.execution_gas_used = gas_used
            
            # Update execution statistics
            self._update_execution_statistics(opportunity)
            
            # Save immediately for executed opportunities
            if status == "executed" and self._auto_persist:
                await self._save_single_opportunity(opportunity)
            
            # Emit event for other components
            await self.event_emitter.emit(
                'tracker:opportunity_executed',
                opportunity.to_dict(),
                source="opportunity_tracker"
            )
            
            return True
    
    def _update_statistics(self, opportunity: ArbitrageOpportunity) -> None:
        """Update statistics with a new opportunity."""
        try:
            # Increment counters
            self._opportunity_count += 1
            
            # Token pair statistics
            token_pair = self._get_token_pair_key(opportunity.input_token, opportunity.output_token)
            if token_pair not in self._token_pair_stats:
                self._token_pair_stats[token_pair] = {
                    "count": 0,
                    "total_profit": 0,
                    "avg_profit": 0,
                    "total_gas": 0,
                    "route_counts": {}
                }
            
            stats = self._token_pair_stats[token_pair]
            stats["count"] += 1
            stats["total_profit"] += opportunity.expected_profit
            stats["avg_profit"] = stats["total_profit"] // stats["count"]
            stats["total_gas"] += opportunity.gas_cost
            
            # Track route patterns
            route_key = self._get_route_key(opportunity.route)
            if route_key not in stats["route_counts"]:
                stats["route_counts"][route_key] = 0
            stats["route_counts"][route_key] += 1
            
            # DEX pair statistics
            for i in range(len(opportunity.route) - 1):
                dex_pair = f"{opportunity.route[i]['dex']}_{opportunity.route[i+1]['dex']}"
                if dex_pair not in self._dex_pair_stats:
                    self._dex_pair_stats[dex_pair] = {
                        "count": 0,
                        "total_profit": 0,
                        "avg_profit": 0
                    }
                
                dex_stats = self._dex_pair_stats[dex_pair]
                dex_stats["count"] += 1
                dex_stats["total_profit"] += opportunity.expected_profit
                dex_stats["avg_profit"] = dex_stats["total_profit"] // dex_stats["count"]
        
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    def _update_execution_statistics(self, opportunity: ArbitrageOpportunity) -> None:
        """Update execution statistics."""
        try:
            # Only count completed executions
            if opportunity.execution_status != "executed":
                return
            
            # Update counters
            self._executed_count += 1
            
            # Update total profit with actual profit
            if opportunity.actual_profit is not None:
                self._total_profit += opportunity.actual_profit
            
            # Recalculate success rate and average profit
            if self._executed_count > 0:
                self._execution_success_rate = self._executed_count / self._opportunity_count
                self._average_profit = self._total_profit // self._executed_count
        
        except Exception as e:
            logger.error(f"Error updating execution statistics: {e}")
    
    def _get_token_pair_key(self, token1: str, token2: str) -> str:
        """Get a consistent key for a token pair (tokens sorted)."""
        tokens = sorted([token1.lower(), token2.lower()])
        return f"{tokens[0]}_{tokens[1]}"
    
    def _get_route_key(self, route: List[Dict[str, Any]]) -> str:
        """Get a route pattern key for statistics."""
        if not route:
            return "empty"
        
        return "_".join([step["dex"] for step in route])
    
    def _trim_opportunities(self) -> None:
        """Trim the opportunity storage to the maximum size."""
        # Keep executed opportunities and most recent
        executed = {}
        pending = {}
        
        for opp_id, opp in self._opportunities.items():
            if opp.execution_status == "executed":
                executed[opp_id] = opp
            else:
                pending[opp_id] = opp
        
        # Keep all executed opportunities if possible
        if len(executed) <= self._max_memory_opportunities:
            # Sort pending by timestamp (newest first)
            sorted_pending = sorted(
                pending.items(),
                key=lambda x: x[1].timestamp,
                reverse=True
            )
            
            # Keep as many as we can
            keep_pending_count = min(
                len(sorted_pending),
                self._max_memory_opportunities - len(executed)
            )
            
            # Update opportunities dict
            self._opportunities = executed.copy()
            for i in range(keep_pending_count):
                opp_id, opp = sorted_pending[i]
                self._opportunities[opp_id] = opp
        else:
            # Just keep newest executed opportunities
            sorted_executed = sorted(
                executed.items(),
                key=lambda x: x[1].execution_timestamp or 0,
                reverse=True
            )
            
            # Update opportunities dict
            self._opportunities = {}
            for i in range(min(len(sorted_executed), self._max_memory_opportunities)):
                opp_id, opp = sorted_executed[i]
                self._opportunities[opp_id] = opp
    
    async def _auto_persist_loop(self) -> None:
        """Loop for automatically persisting opportunities."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Wait for interval or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self._persist_interval
                        )
                    except asyncio.TimeoutError:
                        # Normal timeout, persist
                        pass
                    
                    # Exit if shutdown
                    if self._shutdown_event.is_set():
                        break
                    
                    # Persist opportunities
                    await self.persist_opportunities()
                
                except Exception as e:
                    logger.error(f"Error in persist loop: {e}")
                    await asyncio.sleep(60)  # Wait a minute on error
        
        except asyncio.CancelledError:
            logger.info("Auto-persist task cancelled")
            raise
    
    async def persist_opportunities(self) -> bool:
        """
        Persist opportunities to disk.
        
        Returns:
            True if persisted successfully
        """
        async with self._lock:
            try:
                # Get all opportunities that need persisting
                executed_opportunities = [
                    opp for opp in self._opportunities.values()
                    if opp.execution_status == "executed"
                ]
                
                # Get date for file organization
                today = datetime.now().strftime("%Y-%m-%d")
                persist_dir = os.path.join(self.data_dir, today)
                os.makedirs(persist_dir, exist_ok=True)
                
                # Persist executed opportunities
                for opp in executed_opportunities:
                    await self._save_single_opportunity(opp, persist_dir)
                
                # Save current opportunities snapshot
                snapshot_path = os.path.join(self.data_dir, "current_opportunities.json")
                with open(snapshot_path, 'w') as f:
                    json.dump(
                        {
                            "opportunities": [opp.to_dict() for opp in self._opportunities.values()],
                            "timestamp": time.time(),
                            "stats": {
                                "total_count": self._opportunity_count,
                                "executed_count": self._executed_count,
                                "success_rate": self._execution_success_rate,
                                "average_profit": self._average_profit,
                                "total_profit": self._total_profit
                            }
                        },
                        f,
                        indent=2
                    )
                
                logger.info(f"Persisted {len(executed_opportunities)} executed opportunities")
                return True
            
            except Exception as e:
                logger.error(f"Error persisting opportunities: {e}")
                return False
    
    async def _save_single_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        directory: Optional[str] = None
    ) -> bool:
        """
        Save a single opportunity to disk.
        
        Args:
            opportunity: Opportunity to save
            directory: Directory to save in (default: today's date directory)
            
        Returns:
            True if saved successfully
        """
        try:
            # Get date for file organization
            today = datetime.now().strftime("%Y-%m-%d")
            persist_dir = directory or os.path.join(self.data_dir, today)
            os.makedirs(persist_dir, exist_ok=True)
            
            # Create filename
            filename = f"opportunity_{opportunity.id}.json"
            filepath = os.path.join(persist_dir, filename)
            
            # Save opportunity
            with open(filepath, 'w') as f:
                json.dump(opportunity.to_dict(), f, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving opportunity {opportunity.id}: {e}")
            return False
    
    async def _load_opportunities(self) -> None:
        """Load previously saved opportunities."""
        try:
            # Look for snapshot file
            snapshot_path = os.path.join(self.data_dir, "current_opportunities.json")
            if not os.path.exists(snapshot_path):
                return
            
            # Load snapshot
            with open(snapshot_path, 'r') as f:
                data = json.load(f)
            
            # Load opportunities
            for opp_data in data.get("opportunities", []):
                try:
                    opportunity = ArbitrageOpportunity.from_dict(opp_data)
                    self._opportunities[opportunity.id] = opportunity
                except Exception as e:
                    logger.error(f"Error loading opportunity: {e}")
            
            logger.info(f"Loaded {len(self._opportunities)} opportunities from snapshot")
        
        except Exception as e:
            logger.error(f"Error loading opportunities: {e}")
    
    def get_opportunity(self, opportunity_id: str) -> Optional[ArbitrageOpportunity]:
        """
        Get a specific opportunity by ID.
        
        Args:
            opportunity_id: ID of opportunity to retrieve
            
        Returns:
            Opportunity object or None if not found
        """
        return self._opportunities.get(opportunity_id)
    
    def get_opportunities(
        self,
        count: int = 100,
        status: Optional[str] = None,
        min_profit: Optional[int] = None,
        token_addresses: Optional[List[str]] = None,
        source: Optional[str] = None,
        min_timestamp: Optional[float] = None,
        max_timestamp: Optional[float] = None
    ) -> List[ArbitrageOpportunity]:
        """
        Get opportunities matching filters.
        
        Args:
            count: Maximum opportunities to return
            status: Filter by execution status
            min_profit: Minimum expected profit
            token_addresses: Filter by tokens involved
            source: Filter by source system
            min_timestamp: Minimum discovery timestamp
            max_timestamp: Maximum discovery timestamp
            
        Returns:
            List of opportunities
        """
        # Apply filters
        filtered = []
        for opp in self._opportunities.values():
            # Status filter
            if status and opp.execution_status != status:
                continue
            
            # Profit filter
            if min_profit is not None and opp.expected_profit < min_profit:
                continue
            
            # Token filter
            if token_addresses:
                token_match = False
                for address in token_addresses:
                    if address.lower() in [opp.input_token.lower(), opp.output_token.lower()]:
                        token_match = True
                        break
                    
                    # Check route tokens too
                    for step in opp.route:
                        if (address.lower() == step.get("token_in", "").lower() or
                            address.lower() == step.get("token_out", "").lower()):
                            token_match = True
                            break
                
                if not token_match:
                    continue
            
            # Source filter
            if source and opp.source_system != source:
                continue
            
            # Timestamp filters
            if min_timestamp and opp.timestamp < min_timestamp:
                continue
            if max_timestamp and opp.timestamp > max_timestamp:
                continue
            
            filtered.append(opp)
        
        # Sort by timestamp (newest first)
        filtered.sort(key=lambda o: o.timestamp, reverse=True)
        
        # Return requested count
        return filtered[:count]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get opportunity statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "total_opportunities": self._opportunity_count,
            "executed_opportunities": self._executed_count,
            "execution_success_rate": self._execution_success_rate,
            "average_profit": self._average_profit,
            "total_profit": self._total_profit,
            "tracked_opportunities": len(self._opportunities),
            "token_pairs": len(self._token_pair_stats),
            "top_token_pairs": self._get_top_token_pairs(5),
            "top_dex_pairs": self._get_top_dex_pairs(5)
        }
    
    def _get_top_token_pairs(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get most profitable token pairs."""
        sorted_pairs = sorted(
            self._token_pair_stats.items(),
            key=lambda x: x[1]["avg_profit"],
            reverse=True
        )
        
        result = []
        for i in range(min(count, len(sorted_pairs))):
            pair_key, stats = sorted_pairs[i]
            tokens = pair_key.split('_')
            result.append({
                "token_pair": tokens,
                "count": stats["count"],
                "avg_profit": stats["avg_profit"],
                "total_profit": stats["total_profit"]
            })
        
        return result
    
    def _get_top_dex_pairs(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get most profitable DEX pairs."""
        sorted_pairs = sorted(
            self._dex_pair_stats.items(),
            key=lambda x: x[1]["avg_profit"],
            reverse=True
        )
        
        result = []
        for i in range(min(count, len(sorted_pairs))):
            pair_key, stats = sorted_pairs[i]
            dexes = pair_key.split('_')
            result.append({
                "dex_pair": dexes,
                "count": stats["count"],
                "avg_profit": stats["avg_profit"],
                "total_profit": stats["total_profit"]
            })
        
        return result
    
    def get_token_price_history(
        self,
        token_address: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Tuple[float, float]]:
        """
        Get price history for a token.
        
        Args:
            token_address: Token address
            start_time: Start timestamp (None = all history)
            end_time: End timestamp (None = all history)
            
        Returns:
            List of (timestamp, price) tuples
        """
        if token_address not in self._token_prices:
            return []
        
        history = self._token_prices[token_address]
        
        # Apply time filters
        if start_time or end_time:
            filtered = []
            for timestamp, price in history:
                if start_time and timestamp < start_time:
                    continue
                if end_time and timestamp > end_time:
                    continue
                filtered.append((timestamp, price))
            return filtered
        
        return history.copy()


async def create_opportunity_tracker(
    event_emitter: EventEmitter,
    data_dir: Optional[str] = None
) -> OpportunityTracker:
    """
    Create and initialize an opportunity tracker.
    
    Args:
        event_emitter: EventEmitter instance
        data_dir: Directory for persisting opportunity data
        
    Returns:
        Initialized OpportunityTracker
    """
    tracker = OpportunityTracker(event_emitter, data_dir)
    await tracker.start()
    return tracker