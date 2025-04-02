"""Service for managing metrics data."""

import asyncio
from typing import Dict, Any, Optional, List
from collections import defaultdict
import decimal # Using decimal for potentially better precision with currency
import logging
import statistics
from pathlib import Path
import json
from datetime import datetime
import psutil

from ..core.logging import get_logger
from .memory_service import MemoryService

logger = get_logger("metrics_service")

class MetricsService:
    """Service for managing metrics data."""

    def __init__(self, memory_service: MemoryService):
        """Initialize metrics service.

        Args:
            memory_service: Memory service instance
        """
        logger.info("=== MetricsService.__init__ called ===")
        logger.info("memory_service type: %s", type(memory_service).__name__)
        
        self.memory_service = memory_service
        self._subscribers: List[asyncio.Queue] = []
        self._current_metrics: Dict[str, Any] = {}
        # Initialize with default structure
        self._stats = {
            'metrics': {
 # Note: Structure might differ from metrics.json initially
                'total_profit_eth': 0.0,
                'success_rate': 0.0,
                'total_trades': 0,
                'gas_price': 0.0
, # Average gas price?
                # New Profitability Metrics
                'net_profit_by_pair': {}, # e.g., {"ETH/USDC": 10.5}
                'roi_by_trade_type': {}, # e.g., {"simple": 1.5, "flashloan": 0.8}
                'profit_per_gas': 0.0, # Total Net Profit / Total Gas Cost
                'profit_distribution_by_strategy': {}, # e.g., {"cross_dex": 70.0, "triangular": 30.0}
            },
            'system': {
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0
            },
            'market_data': {
                'prices': {},
                'liquidity': {},
                'spreads': {},
                'analysis': {}
            },
            'system_status': {
                'network_status': 'Unknown',
                'bot_status': 'Initializing',
                'last_update': datetime.utcnow().isoformat()
            },
            'trade_history': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        self._lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._memory_update_task: Optional[asyncio.Task] = None
        self._memory_update_queue: Optional[asyncio.Queue] = None
        self._initialized = False
        
        # Price update tracking
        self._price_history = defaultdict(list)  # Store price history by DEX
        self._price_volatility = {}  # Store calculated volatility by DEX
        self._max_price_history = 100  # Maximum number of price points to keep per DEX

    async def initialize(self):
        """Initialize the metrics service."""
        if self._initialized:
            logger.debug("Metrics service already initialized.")
            return
        logger.info("=== MetricsService.initialize() called ===")

        try:
            # Load initial metrics from memory service state
            await self._load_metrics()

            # Subscribe to memory service updates
            self._memory_update_queue = await self.memory_service.subscribe()
            self._memory_update_task = asyncio.create_task(self._process_memory_updates()) # Start processing updates

            # Start periodic system metrics update task
            self._update_task = asyncio.create_task(self._update_system_metrics_loop())

            self._initialized = True
            logger.info("Metrics service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing metrics service: {e}")
            await self.cleanup()
            raise

    async def cleanup(self):
        """Clean up resources."""
        try:
            # Cancel tasks
            if self._update_task:
                self._update_task.cancel()
                try:
                    await asyncio.wait_for(self._update_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                self._update_task = None

            if self._memory_update_task:
                self._memory_update_task.cancel()
                try:
                    await asyncio.wait_for(self._memory_update_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                self._memory_update_task = None

            # Unsubscribe from memory service
            if self._memory_update_queue:
                await self.memory_service.unsubscribe(self._memory_update_queue)
                self._memory_update_queue = None

            # Clear subscribers
            self._subscribers.clear()

            self._initialized = False
            logger.info("Metrics service shut down")

        except Exception as e:
            logger.error(f"Error during metrics service cleanup: {e}")
            # Don't raise here to allow other cleanup to proceed

    async def _load_metrics(self):
        """Load initial metrics state from MemoryService."""
        try:
            logger.info("Starting to load initial metrics from memory service")
            state = await self.memory_service.get_current_state()
            logger.info(f"Loaded initial state from memory service: {json.dumps(state)}")
            await self._handle_memory_update(state) # Use the handler to populate initial state
            logger.info("Initial metrics loaded from memory service.")
            # Log the current metrics structure after processing
            logger.info(f"Current metrics structure after processing: {json.dumps(self._current_metrics)}")
        except Exception as e:
            logger.error(f"Error loading initial metrics: {e}")
            # Log the actual structure of the metrics file
            try:
                metrics_data = await self.memory_service.file_manager.read_file('metrics')
                logger.info(f"Raw metrics data from file: {json.dumps(metrics_data)}")
            except Exception as file_e:
                logger.error(f"Error reading raw metrics file: {file_e}")
            # Initialize with defaults if loading fails
            async with self._lock:
                 self._current_metrics = self._stats.copy()


    async def _process_memory_updates(self):
        """Process updates received from MemoryService."""
        if not self._memory_update_queue:
            logger.error("Memory update queue not initialized.")
            return

        try:
            while True:
                update = await self._memory_update_queue.get()
                try:
                    await self._handle_memory_update(update)
                except Exception as e:
                    logger.error(f"Error handling memory update: {e}")
                finally:
                     # Ensure task_done is called even if handler fails
                     if hasattr(self._memory_update_queue, 'task_done'):
                         self._memory_update_queue.task_done()
        except asyncio.CancelledError:
            logger.info("Memory update processing task cancelled.")
        except Exception as e:
            logger.error(f"Critical error in memory update processing loop: {e}")


    async def _handle_memory_update(self, update: Dict[str, Any]):
        """Handle state updates received from MemoryService."""
        async with self._lock:
            logger.info(f"--- Handling Memory Update ---")
            logger.info(f"Received update keys: {list(update.keys())}")
            trade_history_received = update.get('trade_history', [])
            logger.info(f"Received trade_history length: {len(trade_history_received)}")
            if trade_history_received:
                logger.info(f"First trade record sample: {trade_history_received[0]}")
            memory_metrics_received = update.get('metrics', {})
            logger.info(f"Received memory_metrics keys: {list(memory_metrics_received.keys())}")

            logger.info(f"Received memory_metrics content: {json.dumps(memory_metrics_received)}")

            logger.info(f"Received memory update: {update.get('timestamp')}")
            # Update metrics based on the 'metrics' key from MemoryService update
            memory_metrics = update.get('metrics', {})

            # Merge bot metrics (profit, trades, success rate, gas)
            # Ensure the 'metrics' key exists in self._stats before updating
            current_metrics_stats = self._stats.setdefault('metrics', {})
            current_metrics_stats.update({
                'total_profit_eth': memory_metrics.get('profitability', {}).get('total_profit', current_metrics_stats.get('total_profit_eth', 0.0)),
                'success_rate': memory_metrics.get('dex_performance', {}).get('success_rates', {}).get('overall', current_metrics_stats.get('success_rate', 0.0)),
                'total_trades': memory_metrics.get('profitability', {}).get('total_trades', current_metrics_stats.get('total_trades', 0)),
                'gas_price': memory_metrics.get('execution', {}).get('gas_by_strategy', {}).get('average', current_metrics_stats.get('gas_price', 0.0))
            })

            # Update market data if present in the update
            if 'market_data' in memory_metrics:
                 self._stats['market_data'] = memory_metrics.get('market_data', self._stats.get('market_data', {}))

            # Update trade history
            self._stats['trade_history'] = update.get('trade_history', self._stats.get('trade_history', []))


            # --- Calculate New Profitability Metrics ---
            trade_history = self._stats.get('trade_history', [])

            # Initialize accumulators for new metrics
            net_profit_by_pair = defaultdict(decimal.Decimal)
            roi_by_trade_type = defaultdict(lambda: {'total_roi': decimal.Decimal(0), 'count': 0})
            profit_by_strategy = defaultdict(decimal.Decimal)
            total_net_profit = decimal.Decimal(0)
            total_gas_cost = decimal.Decimal(0)

            # Process trade history
            for trade in trade_history:
                # Safely extract data using .get() with defaults
                profit = decimal.Decimal(str(trade.get('profit', 0.0))) # Assuming profit is in ETH or similar base unit
                gas_cost = decimal.Decimal(str(trade.get('gas_cost', 0.0))) # Assuming gas_cost is in the same unit
                token_pair = trade.get('token_pair', 'Unknown') # e.g., "ETH/USDC"
                trade_type = trade.get('trade_type', 'unknown') # e.g., "simple", "flashloan"
                strategy_type = trade.get('strategy_type', 'unknown') # e.g., "cross_dex", "triangular"
                initial_investment = decimal.Decimal(str(trade.get('initial_investment', 0.0))) # Amount invested/borrowed

                # Calculate net profit for this trade
                net_profit = profit - gas_cost
                total_net_profit += net_profit
                total_gas_cost += gas_cost

                # 1. Net profit by token pair
                net_profit_by_pair[token_pair] += net_profit

                # 2. ROI by trade type
                if initial_investment > 0:
                    roi = (net_profit / initial_investment) * 100
                    roi_by_trade_type[trade_type]['total_roi'] += roi
                    roi_by_trade_type[trade_type]['count'] += 1

                # 4. Profit by strategy type (for distribution calculation later)
                profit_by_strategy[strategy_type] += net_profit # Using net profit for distribution

            # Calculate final aggregate metrics
            # 3. Profit per gas unit
            profit_per_gas = total_net_profit / total_gas_cost if total_gas_cost > 0 else decimal.Decimal(0)

            # 4. Profit distribution by strategy type
            profit_distribution_by_strategy = {}
            if total_net_profit > 0:
                for strategy, profit_sum in profit_by_strategy.items():
                    distribution = (profit_sum / total_net_profit) * 100
                    profit_distribution_by_strategy[strategy] = float(distribution) # Store as float for JSON

            # Calculate average ROI by trade type
            avg_roi_by_trade_type = {}
            for trade_type, data in roi_by_trade_type.items():
                if data['count'] > 0:
                    avg_roi = data['total_roi'] / data['count']
                    avg_roi_by_trade_type[trade_type] = float(avg_roi) # Store as float for JSON

            # --- Update self._stats['metrics'] with new calculated values ---
            # Ensure the 'metrics' key exists, merging with existing if necessary
            # current_metrics_stats is already defined above
            current_metrics_stats.update({
                # Convert Decimals to float for JSON compatibility before storing
                'net_profit_by_pair': {k: float(v) for k, v in net_profit_by_pair.items()},
                'roi_by_trade_type': avg_roi_by_trade_type,
                'profit_per_gas': float(profit_per_gas),
                'profit_distribution_by_strategy': profit_distribution_by_strategy,
                # Optional: Update total profit to be net profit if desired
                # 'total_profit_eth': float(total_net_profit), # Uncomment if total_profit_eth should be net
            })
            logger.debug(f"Calculated net_profit_by_pair: {dict(net_profit_by_pair)}")
            logger.debug(f"Calculated avg_roi_by_trade_type: {avg_roi_by_trade_type}")
            logger.debug(f"Calculated profit_per_gas: {profit_per_gas}")
            logger.debug(f"Calculated profit_distribution_by_strategy: {profit_distribution_by_strategy}")
            logger.debug(f"--- Finished Handling Memory Update ---")

            # --- End New Metric Calculation ---
            # Update system status (assuming MemoryService doesn't provide this)
            # We might need a separate mechanism if bot status changes
            self._stats['system_status']['last_update'] = datetime.utcnow().isoformat()

            # Update timestamp from the memory service update if available
            self._stats['timestamp'] = update.get('timestamp', datetime.utcnow().isoformat())

            # Update the main metrics dictionary
            self._current_metrics = self._stats.copy() # Ensure we work with a copy

            # Notify subscribers about the change
            await self._notify_subscribers()


    async def _update_system_metrics_loop(self):
        """Background task to periodically update system metrics ONLY."""
        try:
            while True:
                try:
                    async with self._lock:
                        # Update ONLY system metrics
                        self._stats['system'] = {
                            'cpu_usage': psutil.cpu_percent(),
                            'memory_usage': psutil.virtual_memory().percent,
                            'disk_usage': psutil.disk_usage('/').percent
                        }
                        # Update timestamp for this specific update type
                        self._stats['system_status']['last_update'] = datetime.utcnow().isoformat()

                        # Update the main metrics dictionary with the latest system stats
                        self._current_metrics['system'] = self._stats['system']
                        self._current_metrics['system_status'] = self._stats['system_status']
                        self._current_metrics['timestamp'] = self._stats['timestamp'] # Use timestamp from memory update

                        # Notify subscribers
                        await self._notify_subscribers()

                except Exception as e:
                    logger.error(f"Error updating system metrics: {e}")

                # Wait before next update
                await asyncio.sleep(5) # Update system metrics less frequently

        except asyncio.CancelledError:
            logger.info("System metrics update loop cancelled")
            # No need to raise CancelledError here

    async def _notify_subscribers(self):
        """Notify subscribers of metrics updates."""
        if not self._subscribers:
            return

        try:
            # Create a deep copy to prevent modification issues
            metrics_copy = json.loads(json.dumps(self._current_metrics))

            # Send to all subscribers
            active_subscribers = self._subscribers[:] # Iterate over a copy
            for queue in active_subscribers:
                 if queue in self._subscribers: # Check if still subscribed
                    try:
                        # Non-blocking put if queue is full? Or handle differently?
                        await asyncio.wait_for(queue.put(metrics_copy), timeout=1.0)
                    except asyncio.TimeoutError:
                         logger.warning("Subscriber queue full or unresponsive, skipping.")
                    except Exception as e:
                        logger.error(f"Error notifying subscriber: {e}")

        except Exception as e:
            logger.error(f"Error preparing notification for subscribers: {e}")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to metrics updates.

        Returns:
            Queue that will receive metrics updates
        """
        queue = asyncio.Queue(maxsize=10) # Limit queue size
        self._subscribers.append(queue)

        # Send initial metrics
        try:
            async with self._lock:
                 metrics_copy = json.loads(json.dumps(self._current_metrics))
            await queue.put(metrics_copy)
        except Exception as e:
            logger.error(f"Error sending initial metrics to subscriber: {e}")

        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from metrics updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            logger.debug("Subscriber removed.")

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics.

        Returns:
            Current metrics dictionary
        """
        async with self._lock:
            # Return a deep copy
            return json.loads(json.dumps(self._current_metrics))

    async def record_price_update(self, data: Dict[str, Any]):
        """Process and store price update events.
        
        This method:
        1. Stores price updates in the metrics structure
        2. Tracks price volatility over time
        3. Updates the market_data section of the metrics
        4. Integrates with the memory service
        
        Args:
            data: Dictionary containing price update information with keys:
                - dex: The DEX identifier (e.g., 'baseswap_v3')
                - old_price: Previous price value
                - new_price: New price value
        """
        try:
            logger.info(f"Processing price update: {data}")
            
            dex = data.get('dex')
            old_price = data.get('old_price')
            new_price = data.get('new_price')
            
            if not all([dex, old_price is not None, new_price is not None]):
                logger.warning(f"Incomplete price update data: {data}")
                return
                
            # Calculate price change percentage
            if old_price > 0:
                price_change_pct = ((new_price - old_price) / old_price) * 100
            else:
                price_change_pct = 0
                
            timestamp = datetime.utcnow().isoformat()
            
            # Create price update record
            price_record = {
                'timestamp': timestamp,
                'price': new_price,
                'change_pct': price_change_pct
            }
            
            async with self._lock:
                # 1. Store in price history
                self._price_history[dex].append(price_record)
                
                # Limit history size
                if len(self._price_history[dex]) > self._max_price_history:
                    self._price_history[dex] = self._price_history[dex][-self._max_price_history:]
                
                # 2. Calculate volatility (standard deviation of recent price changes)
                if len(self._price_history[dex]) >= 5:  # Need at least 5 data points
                    recent_changes = [record['change_pct'] for record in self._price_history[dex][-10:]]
                    try:
                        volatility = statistics.stdev(recent_changes)
                        self._price_volatility[dex] = volatility
                    except statistics.StatisticsError as e:
                        logger.warning(f"Error calculating volatility for {dex}: {e}")
                        self._price_volatility[dex] = 0
                
                # 3. Update market_data section in metrics
                # Ensure market_data structure exists
                if 'market_data' not in self._stats:
                    self._stats['market_data'] = {'prices': {}, 'liquidity': {}, 'spreads': {}, 'analysis': {}}
                
                # Update prices
                if 'prices' not in self._stats['market_data']:
                    self._stats['market_data']['prices'] = {}
                self._stats['market_data']['prices'][dex] = new_price
                
                # Update analysis with volatility data
                if 'analysis' not in self._stats['market_data']:
                    self._stats['market_data']['analysis'] = {}
                if 'volatility' not in self._stats['market_data']['analysis']:
                    self._stats['market_data']['analysis']['volatility'] = {}
                self._stats['market_data']['analysis']['volatility'][dex] = self._price_volatility.get(dex, 0)
                
                # Add price update to a history section
                if 'price_updates' not in self._stats['market_data']:
                    self._stats['market_data']['price_updates'] = {}
                if dex not in self._stats['market_data']['price_updates']:
                    self._stats['market_data']['price_updates'][dex] = []
                
                # Keep only the last 20 updates in the metrics
                self._stats['market_data']['price_updates'][dex].append(price_record)
                if len(self._stats['market_data']['price_updates'][dex]) > 20:
                    self._stats['market_data']['price_updates'][dex] = self._stats['market_data']['price_updates'][dex][-20:]
                
                # 4. Update the main metrics dictionary
                self._current_metrics['market_data'] = self._stats['market_data']
                
                # 5. Update timestamp
                self._stats['timestamp'] = timestamp
                self._current_metrics['timestamp'] = timestamp
                
                # 6. Notify subscribers about the update
                await self._notify_subscribers()
                
                # 7. Update memory service with the new market data
                await self.memory_service.update_state({
                    'market_data': self._stats['market_data']
                })
                
                logger.info(f"Price update for {dex} processed successfully. New price: {new_price}, Volatility: {self._price_volatility.get(dex, 0):.4f}%")
        except Exception as e:
            logger.error(f"Error processing price update: {e}")

    async def record_opportunity(self, data: Dict[str, Any]):
        """Placeholder for handling opportunity detection events."""
        # TODO: Implement logic if needed (e.g., log opportunities)
        logger.debug(f"Received opportunity event (not processed): {data}")
        pass # Just prevent the AttributeError for now