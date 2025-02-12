"""WebSocket server for real-time data streaming."""

import asyncio
import logging
from typing import Dict, Any, Optional, cast
from datetime import datetime
from web3 import Web3
from web3.types import BlockData
from arbitrage_bot.core.web3.web3_manager import Web3Manager
from arbitrage_bot.core.analytics.analytics_system import create_analytics_system
from arbitrage_bot.core.analysis.market_analyzer import create_market_analyzer
from arbitrage_bot.core.gas.gas_optimizer import create_gas_optimizer

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for streaming real-time data."""

    def __init__(self, socketio):
        """Initialize WebSocket server."""
        self.socketio = socketio
        self.connected_clients = set()
        self.last_update = {
            'state': 0,
            'metrics': 0,
            'market': 0
        }
        
        # Core components
        self.web3_manager = None
        self.analytics_system = None
        self.market_analyzer = None
        self.gas_optimizer = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize core components."""
        try:
            # Initialize Web3 manager
            self.web3_manager = Web3Manager(config)
            
            # Initialize analytics system
            self.analytics_system = await create_analytics_system(config)
            
            # Initialize market analyzer
            self.market_analyzer = await create_market_analyzer(
                web3_manager=self.web3_manager,
                config=config
            )
            
            # Initialize gas optimizer
            self.gas_optimizer = await create_gas_optimizer(
                web3_manager=self.web3_manager,
                config=config
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket server: {e}")
            return False

    async def start(self):
        """Start the WebSocket server."""
        await asyncio.gather(
            self._state_loop(),
            self._metrics_loop(),
            self._market_loop()
        )

    async def _state_loop(self):
        """Stream real-time state data (2s updates)."""
        while True:
            try:
                # Get opportunities
                opportunities = await self.market_analyzer.get_opportunities()
                
                # Get gas data
                gas_analysis = await self.gas_optimizer.analyze_gas_usage()
                optimal_gas = await self.gas_optimizer.get_optimal_gas_price()
                
                # Get latest block
                block = self.web3_manager.get_block()
                block_data = self._get_block_data(block)
                
                # Combine data
                data = {
                    'opportunities': [opp.__dict__ for opp in opportunities],
                    'gas': {
                        'analysis': gas_analysis,
                        'optimal_price': optimal_gas,
                        'current_price': block_data.get('base_fee')
                    },
                    'network': {
                        'status': 'connected' if self.web3_manager.is_connected() else 'disconnected',
                        'block': block_data
                    }
                }
                
                self.socketio.emit('state_update', data, namespace='/')
            except Exception as e:
                logger.error(f"Error in state loop: {e}")
            await asyncio.sleep(2)  # 2 second updates

    async def _metrics_loop(self):
        """Stream performance metrics data (5s updates)."""
        while True:
            try:
                # Get analytics metrics
                analytics = await self.analytics_system.get_metrics()
                
                # Get performance metrics
                performance = await self.market_analyzer.get_performance_metrics()
                
                # Get DEX metrics
                dex_metrics = {}
                for dex_name in self.web3_manager.config['dexes']:
                    if not self.config['dexes'][dex_name].get('enabled', True):
                        continue
                        
                    dex_class = self._get_dex_class(dex_name)
                    if not dex_class:
                        continue
                        
                    dex = dex_class(self.web3_manager, self.config['dexes'][dex_name])
                    await dex.initialize()
                    
                    liquidity = await dex.get_total_liquidity()
                    volume = await dex.get_24h_volume()
                    
                    dex_metrics[dex_name] = {
                        'active': True,
                        'liquidity': float(liquidity) if liquidity else 0,
                        'volume_24h': float(volume) if volume else 0
                    }
                
                # Combine data
                data = {
                    'analytics': analytics,
                    'performance': performance,
                    'dex_metrics': dex_metrics
                }
                
                self.socketio.emit('metrics_update', data, namespace='/')
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
            await asyncio.sleep(5)  # 5 second updates

    async def _market_loop(self):
        """Stream market analysis data (10s updates)."""
        while True:
            try:
                market_data = {}
                
                # Get market conditions for each token
                for token in self.web3_manager.config['tokens']:
                    condition = await self.market_analyzer.get_market_condition(token)
                    if condition:
                        market_data[token] = condition.__dict__
                
                # Get competition analysis
                competition = await self.tx_monitor.get_metrics()
                
                # Get ML analysis
                ml_state = self.ml_system.get_state()
                
                data = {
                    'market_conditions': market_data,
                    'competition': competition,
                    'analysis': ml_state.get('market_state', {})
                }
                
                self.socketio.emit('market_update', data, namespace='/')
            except Exception as e:
                logger.error(f"Error in market loop: {e}")
            await asyncio.sleep(10)  # 10 second updates

    def _get_block_data(self, block: BlockData) -> Dict[str, Any]:
        """Safely extract block data."""
        block_dict = cast(Dict[str, Any], block)
        
        timestamp = block_dict.get('timestamp')
        timestamp_str = datetime.fromtimestamp(timestamp).isoformat() if timestamp else None
        
        base_fee = block_dict.get('baseFeePerGas')
        base_fee_gwei = Web3.from_wei(base_fee, 'gwei') if base_fee else None
        
        return {
            'number': block_dict.get('number'),
            'timestamp': timestamp_str,
            'gas_used': block_dict.get('gasUsed'),
            'gas_limit': block_dict.get('gasLimit'),
            'base_fee': base_fee_gwei,
            'transaction_count': len(block_dict.get('transactions', []))
        }

    def handle_client_connect(self, client_id: str):
        """Handle client connection."""
        self.connected_clients.add(client_id)
        logger.info(f"Client {client_id} connected. Total clients: {len(self.connected_clients)}")

    def handle_client_disconnect(self, client_id: str):
        """Handle client disconnection."""
        self.connected_clients.discard(client_id)
        logger.info(f"Client {client_id} disconnected. Total clients: {len(self.connected_clients)}")

    def broadcast(self, event: str, data: Dict[str, Any]):
        """Broadcast data to all connected clients."""
        for client_id in self.connected_clients:
            self.socketio.emit(event, data, room=client_id)
