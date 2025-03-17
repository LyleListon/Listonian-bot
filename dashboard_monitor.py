"""
Monitor for the arbitrage bot dashboard with real-time data collection.
"""

import asyncio
import socketio
import json
import sys
import psutil
import logging
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
            reconnection_attempts=5,
            reconnection_delay=1,
            reconnection_delay_max=5
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
        
    def setup_handlers(self):
        """Set up Socket.IO event handlers."""
        @self.sio.event
        def connect():
            logger.info("Connected to dashboard")
            
        @self.sio.event
        def disconnect():
            logger.info("Disconnected from dashboard")
            
        @self.sio.event
        def connect_error(data):
            logger.error(f"Connection error: {data}")
            
        @self.sio.on('request_update')
        def on_request_update(data):
            """Handle manual update requests from the dashboard."""
            self.sio.start_background_task(self.collect_and_emit_data)
    
    async def collect_system_metrics(self) -> Dict:
        """Collect system performance metrics."""
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
    
    async def collect_arbitrage_metrics(self) -> Dict:
        """Collect arbitrage-specific metrics."""
        # This would normally connect to your arbitrage bot's API/socket
        # For now, we'll simulate some data
        return {
            'active_positions': self.active_positions,
            'recent_opportunities': self.opportunities[-10:],  # Last 10 opportunities
            'profit_loss': {
                'total': sum(p['amount'] for p in self.profit_history),
                'last_24h': sum(p['amount'] for p in self.profit_history 
                               if datetime.fromisoformat(p['timestamp']) > datetime.now() - timedelta(days=1)),
                'pending': sum(pos['estimated_profit'] for pos in self.active_positions)
            }
        }
    
    async def collect_mev_metrics(self) -> Dict:
        """Collect MEV protection metrics."""
        recent_events = self.mev_events[-100:]  # Last 100 events
        high_risk = sum(1 for e in recent_events if e['risk_level'] == 'high')
        
        return {
            'active': True,
            'blocked_attacks': len(recent_events),
            'risk_level': 'high' if high_risk > 10 else 'medium' if high_risk > 5 else 'low'
        }
    
    async def collect_and_emit_data(self):
        """Collect all metrics and emit to dashboard."""
        try:
            # Collect all metrics
            system_metrics = await self.collect_system_metrics()
            arbitrage_metrics = await self.collect_arbitrage_metrics()
            mev_metrics = await self.collect_mev_metrics()
            
            # Emit system status
            self.sio.emit('system_status', {
                'status': 'online',
                'memory_usage': system_metrics['memory_usage']['percent'],
                'active_positions': len(arbitrage_metrics['active_positions']),
                'profit_24h': arbitrage_metrics['profit_loss']['last_24h']
            })
            
            # Emit MEV protection stats
            self.sio.emit('mev_protection', mev_metrics)
            
            # Emit opportunities
            self.sio.emit('opportunities', {
                'opportunities': arbitrage_metrics['recent_opportunities']
            })
            
            # Emit profit update
            self.sio.emit('profit_update', {
                'profit': arbitrage_metrics['profit_loss']['total']
            })
            
            # Log successful update
            logger.debug("Successfully emitted dashboard updates")
            
        except Exception as e:
            logger.error(f"Error collecting/emitting data: {e}")
    
    async def monitor_blockchain(self):
        """Monitor blockchain for new opportunities and MEV events."""
        while True:
            try:
                # Simulate finding new opportunities
                new_opportunity = {
                    'token_pair': 'ETH/USDC',
                    'potential_profit': round(0.01 + (datetime.now().microsecond / 1e8), 6),
                    'route': 'Uniswap V3 → Balancer → PancakeSwap',
                    'confidence': 95,
                    'timestamp': datetime.now().isoformat()
                }
                self.opportunities.append(new_opportunity)
                
                # Simulate MEV events
                new_mev_event = {
                    'type': 'sandwich_attempt',
                    'risk_level': 'low' if len(self.mev_events) % 10 != 0 else 'high',
                    'timestamp': datetime.now().isoformat()
                }
                self.mev_events.append(new_mev_event)
                
                # Keep lists at reasonable sizes
                if len(self.opportunities) > 1000:
                    self.opportunities = self.opportunities[-1000:]
                if len(self.mev_events) > 1000:
                    self.mev_events = self.mev_events[-1000:]
                
            except Exception as e:
                logger.error(f"Error in blockchain monitor: {e}")
            
            await asyncio.sleep(2)  # Check every 2 seconds
    
    async def simulate_trading(self):
        """Simulate trading activity for demonstration."""
        while True:
            try:
                # Simulate completing trades
                if self.opportunities and len(self.active_positions) < 5:
                    opp = self.opportunities.pop()
                    position = {
                        'token_pair': opp['token_pair'],
                        'entry_price': 1000,  # Simulated price
                        'size': 1.0,
                        'estimated_profit': opp['potential_profit'],
                        'timestamp': datetime.now().isoformat()
                    }
                    self.active_positions.append(position)
                
                # Simulate closing positions
                if self.active_positions and datetime.now().second % 10 == 0:
                    position = self.active_positions.pop(0)
                    profit = {
                        'amount': position['estimated_profit'],
                        'token_pair': position['token_pair'],
                        'timestamp': datetime.now().isoformat()
                    }
                    self.profit_history.append(profit)
                
                # Keep profit history at a reasonable size
                if len(self.profit_history) > 1000:
                    self.profit_history = self.profit_history[-1000:]
                
            except Exception as e:
                logger.error(f"Error in trading simulator: {e}")
            
            await asyncio.sleep(1)
    
    def connect_to_dashboard(self) -> bool:
        """Connect to the dashboard server."""
        try:
            url = f'http://localhost:{self.dashboard_port}'
            logger.info(f"Connecting to dashboard at {url}...")
            self.sio.connect(
                url,
                socketio_path='socket.io',
                transports=['websocket'],
                wait_timeout=5
            )
            logger.info("Successfully connected to dashboard")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to dashboard: {e}")
            return False
    
    async def periodic_updates(self):
        """Send periodic updates to the dashboard."""
        while True:
            try:
                await self.collect_and_emit_data()
                await asyncio.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Error in periodic updates: {e}")
    
    async def run_async(self):
        """Run the dashboard monitor asynchronously."""
        try:
            tasks = [
                asyncio.create_task(self.monitor_blockchain()),
                asyncio.create_task(self.simulate_trading()),
                asyncio.create_task(self.periodic_updates())
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in monitor: {e}")
    
    def run(self):
        """Run the dashboard monitor."""
        try:
            if not self.connect_to_dashboard():
                logger.error("Could not connect to dashboard")
                return
            
            logger.info("Starting monitor tasks...")
            asyncio.get_event_loop().run_until_complete(self.run_async())
            
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