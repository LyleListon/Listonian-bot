"""
Memory Bank Module

This module provides persistent storage and retrieval of:
- System metrics
- Trading history
- Performance data
- Configuration state
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

from ..interfaces import TokenPair, ExecutionResult
from ...utils.async_manager import AsyncLock

logger = logging.getLogger(__name__)

class MemoryBank:
    """Manages persistent storage and retrieval of system data."""

    def __init__(self, storage_dir: str = "data/memory_bank"):
        """Initialize the memory bank."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._metrics_lock = AsyncLock()
        self._history_lock = AsyncLock()
        
        # Cache settings
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # 1 minute

    async def initialize(self):
        """Initialize memory bank and load initial data."""
        try:
            # Create required directories
            for subdir in ['metrics', 'history', 'state']:
                (self.storage_dir / subdir).mkdir(exist_ok=True)
            
            # Load initial metrics
            await self._load_metrics()
            
            logger.info("Memory bank initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory bank: {e}")
            raise

    async def update_system_metrics(self, metrics: Dict[str, Any]):
        """Update system metrics."""
        async with self._metrics_lock:
            try:
                # Load current metrics
                current = await self._load_metrics()
                
                # Update with new metrics
                current.update(metrics)
                
                # Add timestamp
                current['last_update'] = datetime.now().isoformat()
                
                # Save metrics
                metrics_file = self.storage_dir / 'metrics' / 'system_metrics.json'
                with open(metrics_file, 'w') as f:
                    json.dump(current, f, indent=2)
                
                # Update cache
                self._metrics_cache = current
                
                logger.debug(f"Updated system metrics: {metrics}")
                
            except Exception as e:
                logger.error(f"Failed to update metrics: {e}")
                raise

    async def store_execution_result(
        self,
        token_pair: TokenPair,
        success: bool,
        profit: int,
        gas_used: int,
        execution_time: float
    ):
        """Store execution result in history."""
        async with self._history_lock:
            try:
                # Create result entry
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'token_pair': str(token_pair),
                    'success': success,
                    'profit': profit,
                    'gas_used': gas_used,
                    'execution_time': execution_time
                }
                
                # Save to history file
                history_file = self.storage_dir / 'history' / 'execution_history.json'
                
                if history_file.exists():
                    with open(history_file) as f:
                        history = json.load(f)
                else:
                    history = []
                
                history.append(result)
                
                # Keep last 1000 entries
                if len(history) > 1000:
                    history = history[-1000:]
                
                with open(history_file, 'w') as f:
                    json.dump(history, f, indent=2)
                
                logger.debug(f"Stored execution result: {result}")
                
            except Exception as e:
                logger.error(f"Failed to store execution result: {e}")
                raise

    async def store_opportunity(
        self,
        token_pair: TokenPair,
        profit_potential: Decimal,
        confidence: float
    ):
        """Store potential arbitrage opportunity."""
        async with self._metrics_lock:
            try:
                opportunity = {
                    'timestamp': datetime.now().isoformat(),
                    'token_pair': str(token_pair),
                    'profit_potential': str(profit_potential),
                    'confidence': confidence
                }
                
                # Save to opportunities file
                opps_file = self.storage_dir / 'metrics' / 'opportunities.json'
                
                if opps_file.exists():
                    with open(opps_file) as f:
                        opportunities = json.load(f)
                else:
                    opportunities = []
                
                opportunities.append(opportunity)
                
                # Keep last 100 opportunities
                if len(opportunities) > 100:
                    opportunities = opportunities[-100:]
                
                with open(opps_file, 'w') as f:
                    json.dump(opportunities, f, indent=2)
                
                logger.debug(f"Stored opportunity: {opportunity}")
                
            except Exception as e:
                logger.error(f"Failed to store opportunity: {e}")
                raise

    async def get_token_metrics(self, token_pair: TokenPair) -> Dict[str, Any]:
        """Get historical metrics for a token pair."""
        try:
            metrics_file = self.storage_dir / 'metrics' / f'token_{str(token_pair)}.json'
            
            if not metrics_file.exists():
                return {
                    'success_rate': 0,
                    'average_profit': 0,
                    'average_gas_cost': 0,
                    'total_executions': 0
                }
            
            with open(metrics_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to get token metrics: {e}")
            return {}

    async def get_next_opportunity(self) -> Optional[Dict[str, Any]]:
        """Get next pending opportunity."""
        try:
            opps_file = self.storage_dir / 'metrics' / 'opportunities.json'
            
            if not opps_file.exists():
                return None
            
            with open(opps_file) as f:
                opportunities = json.load(f)
            
            if not opportunities:
                return None
            
            # Get most recent opportunity
            opportunity = opportunities[-1]
            
            # Remove it from the list
            opportunities = opportunities[:-1]
            
            with open(opps_file, 'w') as f:
                json.dump(opportunities, f, indent=2)
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Failed to get next opportunity: {e}")
            return None

    async def _load_metrics(self) -> Dict[str, Any]:
        """Load system metrics from storage."""
        try:
            metrics_file = self.storage_dir / 'metrics' / 'system_metrics.json'
            
            if not metrics_file.exists():
                return {}
            
            with open(metrics_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            return {}

    async def save_final_state(self):
        """Save final state before shutdown."""
        try:
            # Save current metrics
            await self.update_system_metrics({
                'shutdown_time': datetime.now().isoformat()
            })
            
            logger.info("Final state saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save final state: {e}")
            raise