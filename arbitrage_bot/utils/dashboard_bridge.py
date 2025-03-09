"""
Dashboard Bridge Module

This module provides a bridge between the production system and the enhanced dashboard,
enabling real-time metric updates and event tracking.
"""

import logging
import asyncio
import os
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DashboardBridge:
    """Bridge between production system and dashboard"""
    
    def __init__(self):
        """Initialize the dashboard bridge"""
        self.stats_dir = Path('logs')
        self.stats_dir.mkdir(exist_ok=True)
        self.stats_file = self.stats_dir / 'dashboard_stats.json'
        self._lock = asyncio.Lock()
        self._last_update = {}
        self._initialize_stats()
        
    def _initialize_stats(self):
        """Initialize stats with default values"""
        self.stats = {
            'system_status': {
                'start_time': datetime.now().isoformat(),
                'uptime': 0,
                'last_update': datetime.now().isoformat(),
                'mev_risk_level': 'initializing',
                'flash_loans_enabled': True,
                'flashbots_enabled': True
            },
            'performance': {
                'opportunities_found': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'total_profit_eth': 0.0,
                'avg_execution_time': 0.0,
                'gas_saved': 0.0
            },
            'network': {
                'chain_id': 1,
                'gas_price': 0,
                'block_number': 0,
                'connected_nodes': 1,
                'rpc_latency': 0.0
            },
            'dex_stats': {
                'active_dexes': 0,
                'total_pools': 0,
                'monitored_tokens': 0,
                'price_updates': 0
            },
            'flash_loans': {
                'total_borrowed': 0.0,
                'successful_repayments': 0,
                'failed_repayments': 0,
                'avg_loan_size': 0.0
            },
            'mev_protection': {
                'bundles_submitted': 0,
                'bundles_included': 0,
                'frontrun_attempts': 0,
                'sandwich_attacks': 0
            },
            'path_finder': {
                'paths_analyzed': 0,
                'profitable_paths': 0,
                'max_profit_seen': 0.0,
                'avg_path_length': 0.0
            },
            'token_metrics': {},
            'recent_events': []
        }
        self._force_save_stats()
        logger.info("Initialized dashboard stats")
        
    async def update_system_status(self, status: Dict[str, Any]):
        """Update system status metrics"""
        async with self._lock:
            logger.info(f"Updating system status: {status}")
            self.stats['system_status'].update(status)
            self.stats['system_status']['uptime'] = (
                datetime.now() - datetime.fromisoformat(self.stats['system_status']['start_time'])
            ).total_seconds()
            self.stats['system_status']['last_update'] = datetime.now().isoformat()
            self._force_save_stats()
                
    async def update_performance(self, metrics: Dict[str, Any]):
        """Update performance metrics"""
        async with self._lock:
            logger.info(f"Updating performance metrics: {metrics}")
            self.stats['performance'].update(metrics)
            self._force_save_stats()
                
    async def update_network(self, network_info: Dict[str, Any]):
        """Update network statistics"""
        async with self._lock:
            logger.info(f"Updating network info: {network_info}")
            self.stats['network'].update(network_info)
            self._force_save_stats()
                
    async def update_dex_stats(self, dex_info: Dict[str, Any]):
        """Update DEX-related statistics"""
        async with self._lock:
            logger.info(f"Updating DEX stats: {dex_info}")
            self.stats['dex_stats'].update(dex_info)
            self._force_save_stats()
                
    async def update_flash_loans(self, loan_stats: Dict[str, Any]):
        """Update flash loan statistics"""
        async with self._lock:
            logger.info(f"Updating flash loan stats: {loan_stats}")
            self.stats['flash_loans'].update(loan_stats)
            self._force_save_stats()
                
    async def update_mev_protection(self, mev_stats: Dict[str, Any]):
        """Update MEV protection metrics"""
        async with self._lock:
            logger.info(f"Updating MEV protection stats: {mev_stats}")
            self.stats['mev_protection'].update(mev_stats)
            self._force_save_stats()
                
    async def update_path_finder(self, path_stats: Dict[str, Any]):
        """Update path finder statistics"""
        async with self._lock:
            logger.info(f"Updating path finder stats: {path_stats}")
            self.stats['path_finder'].update(path_stats)
            self._force_save_stats()
                
    async def update_token_metrics(self, token_address: str, metrics: Dict[str, Any]):
        """Update metrics for a specific token"""
        async with self._lock:
            if token_address not in self.stats['token_metrics']:
                self.stats['token_metrics'][token_address] = {
                    'price': 0.0,
                    'volume_24h': 0.0,
                    'liquidity': 0.0,
                    'trades': 0,
                    'last_update': ''
                }
            logger.info(f"Updating token metrics for {token_address}: {metrics}")
            self.stats['token_metrics'][token_address].update(metrics)
            self.stats['token_metrics'][token_address]['last_update'] = datetime.now().isoformat()
            self._force_save_stats()
                
    async def add_event(self, event_type: str, description: str, details: Dict[str, Any] = None):
        """Add a new event to recent events"""
        async with self._lock:
            event = {
                'timestamp': datetime.now().isoformat(),
                'type': event_type,
                'description': description,
                'details': details or {}
            }
            logger.info(f"Adding event: {event}")
            self.stats['recent_events'].insert(0, event)
            self.stats['recent_events'] = self.stats['recent_events'][:100]  # Keep last 100 events
            self._force_save_stats()
                
    def _force_save_stats(self):
        """Force save stats to file synchronously"""
        try:
            # Create a copy of stats to avoid modifying during serialization
            stats_copy = json.loads(json.dumps(self.stats, default=str))
            # Force write to file
            with open(self.stats_file, 'w') as f:
                json.dump(stats_copy, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            logger.debug("Stats saved successfully")
        except Exception as e:
            logger.error(f"Failed to save dashboard stats: {e}")

# Global dashboard bridge instance
_dashboard_bridge: Optional[DashboardBridge] = None

def get_dashboard_bridge() -> DashboardBridge:
    """Get the global dashboard bridge instance"""
    global _dashboard_bridge
    if _dashboard_bridge is None:
        _dashboard_bridge = DashboardBridge()
    return _dashboard_bridge