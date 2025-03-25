"""Service for managing metrics data."""

import asyncio
from typing import Dict, Any, Optional, List
import logging
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
        self.memory_service = memory_service
        self._subscribers: List[asyncio.Queue] = []
        self._current_metrics: Dict[str, Any] = {}
        self._stats = {
            'opportunities': {
                'total_found': 0,
                'total_executed': 0,
                'success_count': 0,
                'avg_profit_potential': 0.0,
                'avg_gas_cost': 0.0,
                'best_spread': 0.0,
            },
            'performance': {
                'total_profit': 0.0,
                'total_gas_spent': 0.0,
                'success_rate': 0.0,
                'avg_execution_time': 0.0,
            },
            'market': {
                'last_price_update': None,
                'price_updates_count': 0,
                'price_deviation': 0.0,
            }
        }
        self._lock = asyncio.Lock()
        self._update_task: Optional[asyncio.Task] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the metrics service."""
        if self._initialized:
            return
            
        try:
            # Load initial metrics
            await self._load_metrics()
            
            # Start metrics update task
            self._update_task = asyncio.create_task(self._update_metrics_loop())
            
            self._initialized = True
            logger.info("Metrics service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing metrics service: {e}")
            await self.cleanup()
            raise
            
    async def cleanup(self):
        """Clean up resources."""
        try:
            # Cancel update task
            if self._update_task:
                self._update_task.cancel()
                try:
                    await asyncio.wait_for(self._update_task, timeout=5.0)
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for metrics task to cancel")
                self._update_task = None
            
            # Clear subscribers
            self._subscribers.clear()
            
            self._initialized = False
            logger.info("Metrics service shut down")
            
        except Exception as e:
            logger.error(f"Error during metrics service cleanup: {e}")
            raise
            
    async def _load_metrics(self):
        """Load metrics from memory service."""
        try:
            state = await self.memory_service.get_current_state()
            async with self._lock:
                self._current_metrics = state.get('metrics', {})
                self._stats = state.get('stats', self._stats)
                
        except Exception as e:
            logger.error(f"Error loading metrics: {e}")
            raise
            
    async def _update_metrics_loop(self):
        """Background task to update metrics."""
        try:
            while True:
                try:
                    # Update system metrics
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    
                    async with self._lock:
                        # Update metrics
                        self._current_metrics.update({
                            'timestamp': datetime.utcnow().isoformat(),
                            'system': {
                                'cpu_usage': cpu_percent,
                                'memory_usage': memory.percent,
                                'timestamp': datetime.utcnow().isoformat()
                            },
                            'performance': {
                                'opportunities_found': self._stats['opportunities']['total_found'],
                                'success_rate': (self._stats['opportunities']['success_count'] / max(1, self._stats['opportunities']['total_executed'])) * 100,
                                'avg_profit': self._stats['opportunities']['avg_profit_potential'],
                                'avg_gas': self._stats['opportunities']['avg_gas_cost'],
                                'best_spread': self._stats['opportunities']['best_spread'],
                                'total_profit': self._stats['performance']['total_profit'],
                                'total_gas_spent': self._stats['performance']['total_gas_spent']
                            },
                            'market': {
                                'last_update': self._stats['market']['last_price_update'],
                                'update_count': self._stats['market']['price_updates_count'],
                                'price_deviation': self._stats['market']['price_deviation']
                            }
                        })
                        
                        # Save to memory service
                        await self.memory_service.update_state({
                            'metrics': dict(self._current_metrics),
                            'stats': dict(self._stats)
                        })
                        
                        # Notify subscribers
                        await self._notify_subscribers()
                        
                except Exception as e:
                    logger.error(f"Error updating metrics: {e}")
                    
                # Wait before next update
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Metrics update loop cancelled")
            raise
            
    async def _notify_subscribers(self):
        """Notify subscribers of metrics updates."""
        if not self._subscribers:
            return
            
        try:
            # Create a copy of metrics
            metrics_copy = {
                'metrics': dict(self._current_metrics),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send to all subscribers
            for queue in self._subscribers:
                try:
                    await queue.put(metrics_copy)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")
                    
        except Exception as e:
            logger.error(f"Error in notify subscribers: {e}")
            
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to metrics updates.
        
        Returns:
            Queue that will receive metrics updates
        """
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        
        # Send initial metrics
        try:
            metrics_copy = {
                'metrics': dict(self._current_metrics),
                'timestamp': datetime.utcnow().isoformat()
            }
            await queue.put(metrics_copy)
        except Exception as e:
            logger.error(f"Error sending initial metrics to subscriber: {e}")
            
        return queue
        
    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from metrics updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics.
        
        Returns:
            Current metrics dictionary
        """
        async with self._lock:
            return {
                'metrics': dict(self._current_metrics),
                'timestamp': datetime.utcnow().isoformat()
            }
            
    async def update_metrics(self, updates: Dict[str, Any]):
        """Update metrics.
        
        Args:
            updates: Dictionary of metric updates
        """
        async with self._lock:
            # Update metrics
            self._current_metrics.update(updates)
            
            # Save to memory service
            await self.memory_service.update_state({
                'metrics': dict(self._current_metrics)
            })
            
            # Notify subscribers
            await self._notify_subscribers()
            
    async def record_opportunity(self, opportunity_data: Dict[str, Any]):
        """Record a new arbitrage opportunity.
        
        Args:
            opportunity_data: Dictionary containing opportunity details
        """
        async with self._lock:
            self._stats['opportunities']['total_found'] += 1
            
            # Update average profit potential
            profit = float(opportunity_data.get('profit_potential', 0))
            current_avg = self._stats['opportunities']['avg_profit_potential']
            total = self._stats['opportunities']['total_found']
            self._stats['opportunities']['avg_profit_potential'] = (current_avg * (total - 1) + profit) / total
            
            # Update best spread
            spread = float(opportunity_data.get('spread', 0))
            if spread > self._stats['opportunities']['best_spread']:
                self._stats['opportunities']['best_spread'] = spread
                
            await self._notify_subscribers()
            
    async def record_execution(self, execution_data: Dict[str, Any]):
        """Record an arbitrage execution attempt.
        
        Args:
            execution_data: Dictionary containing execution details
        """
        async with self._lock:
            self._stats['opportunities']['total_executed'] += 1
            
            if execution_data.get('success', False):
                self._stats['opportunities']['success_count'] += 1
                self._stats['performance']['total_profit'] += float(execution_data.get('profit', 0))
            
            # Update average gas cost
            gas_cost = float(execution_data.get('gas_cost', 0))
            self._stats['performance']['total_gas_spent'] += gas_cost
            current_avg = self._stats['opportunities']['avg_gas_cost']
            total = self._stats['opportunities']['total_executed']
            self._stats['opportunities']['avg_gas_cost'] = (current_avg * (total - 1) + gas_cost) / total
            
            # Update execution time stats
            exec_time = float(execution_data.get('execution_time', 0))
            current_avg = self._stats['performance']['avg_execution_time']
            self._stats['performance']['avg_execution_time'] = (current_avg * (total - 1) + exec_time) / total
            
            await self._notify_subscribers()
            
    async def record_price_update(self, price_data: Dict[str, Any]):
        """Record a price update.
        
        Args:
            price_data: Dictionary containing price update details
        """
        async with self._lock:
            self._stats['market']['last_price_update'] = datetime.utcnow().isoformat()
            self._stats['market']['price_updates_count'] += 1
            
            # Calculate price deviation
            if 'old_price' in price_data and 'new_price' in price_data:
                old_price = float(price_data['old_price'])
                new_price = float(price_data['new_price'])
                if old_price > 0:
                    deviation = abs((new_price - old_price) / old_price) * 100
                    self._stats['market']['price_deviation'] = deviation
            
            await self._notify_subscribers()