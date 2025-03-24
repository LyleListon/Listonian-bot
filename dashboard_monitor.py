"""
Monitor for the arbitrage bot dashboard with real-time data collection.
"""

import asyncio
import socketio
import json
import sys
import psutil
import logging
import aiohttp
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta
from web3 import Web3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DashboardMonitor:
    """Monitor for the arbitrage bot dashboard."""
    
    def __init__(self, dashboard_port: int = 9095):
        """Initialize dashboard monitor."""
        self.dashboard_port = dashboard_port
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            reconnection=True,
            reconnection_attempts=10,  # Increased attempts
            reconnection_delay=1,
            reconnection_delay_max=5,
            request_timeout=30
        )
        self.setup_handlers()
        
        # Initialize data storage
        self.active_positions: List[Dict] = []
        self.opportunities: List[Dict] = []
        self.profit_history: List[Dict] = []
        self.mev_events: List[Dict] = []
        
        # Initialize performance tracking
        self.last_memory_check = datetime.now()
        self.memory_check_interval = timedelta(seconds=5)
        self.connected = False
        self.reconnecting = False
        
    def setup_handlers(self):
        """Set up Socket.IO event handlers."""
        @self.sio.event
        def connect():
            logger.info("Connected to dashboard")
            self.connected = True
            self.reconnecting = False
            
        @self.sio.event
        def disconnect():
            logger.info("Disconnected from dashboard")
            self.connected = False
            
        @self.sio.event
        def connect_error(data):
            logger.error(f"Connection error: {data}")
            if not self.reconnecting:
                self.reconnecting = True
                asyncio.create_task(self.handle_reconnection())
            
        @self.sio.on('request_update')
        def on_request_update(data):
            """Handle manual update requests from the dashboard."""
            if self.connected:
                asyncio.create_task(self.collect_and_emit_data())
    
    async def wait_for_dashboard(self, timeout: int = 30) -> bool:
        """Wait for dashboard to become available."""
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f'http://localhost:{self.dashboard_port}') as response:
                        if response.status == 200:
                            return True
            except aiohttp.ClientError:
                pass
            await asyncio.sleep(1)
        return False

    async def handle_reconnection(self):
        """Handle reconnection attempts with exponential backoff."""
        attempt = 0
        max_attempts = 10
        base_delay = 1

        while attempt < max_attempts and not self.connected:
            delay = min(base_delay * (2 ** attempt), 30)  # Cap at 30 seconds
            logger.info(f"Attempting reconnection in {delay} seconds (attempt {attempt + 1}/{max_attempts})")
            await asyncio.sleep(delay)
            
            try:
                if await self.wait_for_dashboard(timeout=5):
                    self.connect_to_dashboard()
                    if self.connected:
                        break
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
            
            attempt += 1

        if not self.connected:
            logger.error("Failed to reconnect after maximum attempts")
            self.reconnecting = False

    async def collect_system_metrics(self) -> Dict:
        """Collect system performance metrics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'memory_usage': {
                    'rss': memory_info.rss / 1024 / 1024,  # MB
                    'vms': memory_info.vms / 1024 / 1024,  # MB
                    'percent': process.memory_percent()
                },
                'threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'connections': len(process.connections())
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    async def collect_arbitrage_metrics(self) -> Dict:
        """Collect arbitrage-specific metrics."""
        try:
            return {
                'active_positions': self.active_positions,
                'recent_opportunities': self.opportunities[-10:],
                'profit_loss': {
                    'total': sum(p['amount'] for p in self.profit_history),
                    'last_24h': sum(p['amount'] for p in self.profit_history 
                                  if datetime.fromisoformat(p['timestamp']) > datetime.now() - timedelta(days=1)),
                    'pending': sum(pos['estimated_profit'] for pos in self.active_positions)
                }
            }
        except Exception as e:
            logger.error(f"Error collecting arbitrage metrics: {e}")
            return {}
    
    async def collect_mev_metrics(self) -> Dict:
        """Collect MEV protection metrics."""
        try:
            recent_events = self.mev_events[-100:]
            high_risk = sum(1 for e in recent_events if e['risk_level'] == 'high')
            
            return {
                'active': True,
                'blocked_attacks': len(recent_events),
                'risk_level': 'high' if high_risk > 10 else 'medium' if high_risk > 5 else 'low'
            }
        except Exception as e:
            logger.error(f"Error collecting MEV metrics: {e}")
            return {}
    
    async def collect_and_emit_data(self):
        """Collect all metrics and emit to dashboard."""
        if not self.connected:
            return

        try:
            system_metrics = await self.collect_system_metrics()
            arbitrage_metrics = await self.collect_arbitrage_metrics()
            mev_metrics = await self.collect_mev_metrics()
            
            if system_metrics and arbitrage_metrics:
                self.sio.emit('system_status', {
                    'status': 'online',
                    'memory_usage': system_metrics['memory_usage']['percent'],
                    'active_positions': len(arbitrage_metrics['active_positions']),
                    'profit_24h': arbitrage_metrics['profit_loss']['last_24h']
                })
            
            if mev_metrics:
                self.sio.emit('mev_protection', mev_metrics)
            
            if arbitrage_metrics:
                self.sio.emit('opportunities', {
                    'opportunities': arbitrage_metrics['recent_opportunities']
                })
                
                self.sio.emit('profit_update', {
                    'profit': arbitrage_metrics['profit_loss']['total']
                })
            
        except Exception as e:
            logger.error(f"Error collecting/emitting data: {e}")
    
    def connect_to_dashboard(self) -> bool:
        """Connect to the dashboard server."""
        try:
            url = f'http://localhost:{self.dashboard_port}'
            logger.info(f"Connecting to dashboard at {url}...")
            
            self.sio.connect(
                url,
                socketio_path='socket.io',
                transports=['websocket', 'polling'],  # Allow fallback to polling
                wait_timeout=10,
                wait=True  # Wait for connection before returning
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to dashboard: {e}")
            return False
    
    async def run_async(self):
        """Run the dashboard monitor asynchronously."""
        try:
            # Wait for dashboard to be available
            if not await self.wait_for_dashboard():
                logger.error("Dashboard not available")
                return

            # Connect to dashboard
            if not self.connect_to_dashboard():
                logger.error("Could not connect to dashboard")
                return

            # Start monitoring tasks
            tasks = [
                asyncio.create_task(self.monitor_blockchain()),
                asyncio.create_task(self.simulate_trading()),
                asyncio.create_task(self.periodic_updates())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Error in monitor: {e}")
        finally:
            if self.sio.connected:
                self.sio.disconnect()
    
    def run(self):
        """Run the dashboard monitor."""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("Stopping monitor...")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            if self.sio.connected:
                self.sio.disconnect()

if __name__ == '__main__':
    monitor = DashboardMonitor()
    monitor.run()