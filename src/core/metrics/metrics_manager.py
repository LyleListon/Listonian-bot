"""Metrics management and aggregation system."""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .portfolio_tracker import PortfolioTracker
from ..web3.web3_manager import Web3Manager
from ...utils.database import Database

logger = logging.getLogger(__name__)

class MetricsManager:
    """Manages and aggregates various system metrics."""

    def __init__(
        self,
        config: Dict[str, Any],
        db: Optional[Database] = None
    ):
        """
        Initialize metrics manager.

        Args:
            config: Configuration dictionary
            db: Optional Database instance
        """
        def convert_to_string(value: Any) -> Any:
            """Convert values to strings recursively."""
            if isinstance(value, dict):
                return {k: convert_to_string(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert_to_string(item) for item in value]
            elif value is None:
                return ""
            else:
                return str(value)

        # Convert all config values to strings
        self.config = convert_to_string(config)
        self.db = db if db else Database()
        
        # Initialize metrics containers with default values and type hints
        def init_metrics_container(defaults: Dict[str, Any]) -> Dict[str, Any]:
            def convert_value(v: Any) -> str:
                if isinstance(v, dict):
                    return {k: convert_value(val) for k, val in v.items()}
                elif isinstance(v, list):
                    return [convert_value(x) for x in v]
                elif v is None:
                    return ""
                elif isinstance(v, (int, float)):
                    return str(float(v))
                elif isinstance(v, bool):
                    return str(v).lower()
                else:
                    return str(v)
            return {k: convert_value(v) for k, v in defaults.items()}

        # Initialize all metrics containers with string values
        self.system_metrics: Dict[str, Any] = init_metrics_container({
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage': 0,
            'network_io': {'bytes_sent': 0, 'bytes_recv': 0},
            'timestamp': datetime.now().isoformat()
        })
        
        self.performance_metrics: Dict[str, Any] = init_metrics_container({
            'total_trades': 0,
            'success_rate': 0,
            'total_profit_usd': 0,
            'active_opportunities': 0
        })
        
        self.gas_metrics: Dict[str, Any] = init_metrics_container({
            'current_gas_price': 0,
            'average_gas_used': 0,
            'total_gas_spent': 0
        })
        
        self.network_metrics: Dict[str, Any] = init_metrics_container({
            'block_number': 0,
            'network_id': 8453,
            'peer_count': 0
        })
        
        def convert_to_string(value: Any) -> str:
            """Convert any value to string."""
            if value is None:
                return ""
            elif isinstance(value, (int, float)):
                return str(float(value))
            else:
                return str(value)

        # Convert config values to strings
        metrics_config = config.get('metrics', {})
        self.update_interval = int(convert_to_string(metrics_config.get('update_interval', 60)))
        self.history_window = int(convert_to_string(metrics_config.get('history_window', 24 * 60 * 60)))
        
        # Initialize tracking with string values
        self.start_time = datetime.now()
        self._running = "false"  # Initialize as string
        self._update_task = None
        self.initialized = "false"  # Initialize as string

    async def initialize(self) -> bool:
        """Initialize metrics tracking."""
        try:
            # Load historical data
            await self._load_historical_data()
            
            def convert_to_string(value: Any) -> str:
                """Convert any value to string."""
                if value is None:
                    return ""
                elif isinstance(value, (int, float)):
                    return str(float(value))
                elif isinstance(value, bool):
                    return str(value).lower()
                else:
                    return str(value)

            # Start metrics update loop
            self._running = "true"  # Set as string
            self._update_task = asyncio.create_task(self._update_loop())
            self.initialized = "true"  # Set as string
            
            logger.info("Metrics manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize metrics manager: {e}")
            return False

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return self.system_metrics.copy()

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_metrics.copy()

    async def get_gas_metrics(self) -> Dict[str, Any]:
        """Get current gas metrics."""
        return self.gas_metrics.copy()

    async def get_network_metrics(self) -> Dict[str, Any]:
        """Get current network metrics."""
        return self.network_metrics.copy()

    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        return {
            'system': self.system_metrics,
            'performance': self.performance_metrics,
            'gas': self.gas_metrics,
            'network': self.network_metrics,
            'timestamp': datetime.now().isoformat()
        }

    async def update_metrics(
        self,
        category: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Update metrics for a specific category.

        Args:
            category: Metrics category
            metrics: New metrics data

        Returns:
            bool: True if update successful
        """
        try:
            # Convert all values to strings recursively
            def convert_metrics(data: Any) -> Any:
                if isinstance(data, dict):
                    return {k: convert_metrics(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [convert_metrics(x) for x in data]
                elif data is None:
                    return ""
                elif isinstance(data, (int, float)):
                    return str(float(data))
                elif isinstance(data, bool):
                    return str(data).lower()
                else:
                    return str(data)

            converted_metrics = convert_metrics(metrics)

            if category == 'system':
                self.system_metrics.update(converted_metrics)
            elif category == 'performance':
                self.performance_metrics.update(converted_metrics)
            elif category == 'gas':
                self.gas_metrics.update(converted_metrics)
            elif category == 'network':
                self.network_metrics.update(converted_metrics)
            else:
                logger.warning(f"Unknown metrics category: {category}")
                return False
                
            # Save to database
            await self._save_metrics_snapshot()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
            return False

    async def get_historical_metrics(
        self,
        category: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical metrics data.

        Args:
            category: Metrics category
            start_time: Start time for historical data
            end_time: End time for historical data

        Returns:
            List[Dict[str, Any]]: Historical metrics data
        """
        try:
            if not start_time:
                start_time = self.start_time
            if not end_time:
                end_time = datetime.now()
                
            query = {
                "category": category,
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }
            
            metrics = await self.db.get_metrics(query)
            return sorted(metrics, key=lambda x: x['timestamp'])
            
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return []

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            def convert_to_string(value: Any) -> str:
                """Convert any value to string."""
                if value is None:
                    return ""
                elif isinstance(value, (int, float)):
                    return str(float(value))
                elif isinstance(value, bool):
                    return str(value).lower()
                else:
                    return str(value)

            self._running = "false"  # Set as string
            if self._update_task:
                self._update_task.cancel()
                try:
                    await self._update_task
                except asyncio.CancelledError:
                    pass
                
            logger.info("Metrics manager cleaned up")
            
        except Exception as e:
            logger.error(f"Error during metrics manager cleanup: {e}")

    async def _update_loop(self) -> None:
        """Background metrics update loop."""
        while self._running == "true":  # Check string value
            try:
                # Update system metrics
                await self._update_system_metrics()
                
                # Save snapshot
                await self._save_metrics_snapshot()
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                self._running = "false"  # Set string value
                break
            except Exception as e:
                logger.error(f"Error in metrics update loop: {e}")
                await asyncio.sleep(self.update_interval)

    async def _update_system_metrics(self) -> None:
        """Update system-level metrics."""
        try:
            import psutil
            
            # System metrics with string conversion
            network_io = psutil.net_io_counters()._asdict()
            network_io = {k: str(v) for k, v in network_io.items()}
            
            self.system_metrics.update({
                'cpu_percent': str(psutil.cpu_percent()),
                'memory_percent': str(psutil.virtual_memory().percent),
                'disk_usage': str(psutil.disk_usage('/').percent),
                'network_io': network_io,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")

    async def _save_metrics_snapshot(self) -> None:
        """Save current metrics to database."""
        try:
            # Ensure all metric containers have default values
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'system': self.system_metrics if self.system_metrics is not None else {},
                'performance': self.performance_metrics if self.performance_metrics is not None else {},
                'gas': self.gas_metrics if self.gas_metrics is not None else {},
                'network': self.network_metrics if self.network_metrics is not None else {}
            }
            
            # Convert any None values to empty strings in nested dictionaries
            def sanitize_dict(d):
                if isinstance(d, dict):
                    return {k: sanitize_dict(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [sanitize_dict(x) for x in d]
                elif d is None:
                    return ""
                elif isinstance(d, (int, float)):
                    return str(float(d))
                elif isinstance(d, bool):
                    return str(d).lower()
                else:
                    return str(d)
            
            snapshot = {k: sanitize_dict(v) if isinstance(v, dict) else v 
                       for k, v in snapshot.items()}
            
            await self.db.save_metrics(snapshot)
            
        except Exception as e:
            logger.error(f"Failed to save metrics snapshot: {e}")

    async def _load_historical_data(self) -> None:
        """Load historical metrics data."""
        try:
            # Get recent metrics
            start_time = datetime.now() - timedelta(seconds=self.history_window)
            metrics = await self.get_historical_metrics('all', start_time)
            
            if metrics:
                # Convert metrics to strings using sanitize_dict
                def convert_to_strings(d):
                    if isinstance(d, dict):
                        return {k: convert_to_strings(v) for k, v in d.items()}
                    elif isinstance(d, list):
                        return [convert_to_strings(x) for x in d]
                    elif d is None:
                        return ""
                    else:
                        return str(d)

                # Use most recent snapshot with string conversion
                latest = metrics[-1]
                self.system_metrics = convert_to_strings(latest.get('system', {}))
                self.performance_metrics = convert_to_strings(latest.get('performance', {}))
                self.gas_metrics = convert_to_strings(latest.get('gas', {}))
                self.network_metrics = convert_to_strings(latest.get('network', {}))
                
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")


async def create_metrics_manager(
    config: Dict[str, Any],
    db: Optional[Database] = None
) -> Optional[MetricsManager]:
    """
    Create metrics manager instance.

    Args:
        config: Configuration dictionary
        db: Optional Database instance

    Returns:
        Optional[MetricsManager]: Metrics manager instance
    """
    try:
        manager = MetricsManager(config=config, db=db)
        if await manager.initialize():
            return manager
        return None
    except Exception as e:
        logger.error(f"Failed to create metrics manager: {e}")
        return None
