"""WebSocket server for real-time dashboard updates."""

import logging
import json
import eventlet
from typing import Dict, Any, Optional
from flask_socketio import SocketIO, emit
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for real-time dashboard updates."""

    def __init__(
        self,
        socketio: SocketIO,
        market_analyzer: Any = None,
        portfolio_tracker: Any = None,
        memory_bank: Any = None,
        storage_hub: Any = None,
        distribution_manager: Any = None,
        execution_manager: Any = None,
        gas_optimizer: Any = None
    ):
        """Initialize WebSocket server."""
        self.socketio = socketio
        self.market_analyzer = market_analyzer
        self.portfolio_tracker = portfolio_tracker
        self.memory_bank = memory_bank
        self.storage_hub = storage_hub
        self.distribution_manager = distribution_manager
        self.execution_manager = execution_manager
        self.gas_optimizer = gas_optimizer
        self.is_running = False
        self.update_interval = 5  # seconds
        logger.debug("WebSocket server initialized")

    def initialize(self) -> bool:
        """Initialize server components."""
        try:
            # Verify all required components
            if not all([
                self.socketio,
                self.market_analyzer,
                self.portfolio_tracker,
                self.memory_bank,
                self.storage_hub,
                self.distribution_manager,
                self.execution_manager,
                self.gas_optimizer
            ]):
                logger.error("Missing required components")
                return False

            # Register event handlers
            self._register_handlers()
            logger.debug("WebSocket server initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize WebSocket server: {e}")
            return False

    def start(self):
        """Start WebSocket server."""
        try:
            self.is_running = True
            eventlet.spawn(self._update_loop)
            logger.debug("WebSocket server started")

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            self.is_running = False
            raise

    def stop(self):
        """Stop WebSocket server."""
        self.is_running = False
        logger.debug("WebSocket server stopped")

    def _register_handlers(self):
        """Register WebSocket event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.debug("Client connected")
            self._send_initial_data()

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.debug("Client disconnected")

        @self.socketio.on('request_update')
        def handle_update_request(data):
            """Handle update request from client."""
            try:
                update_type = data.get('type')
                if update_type == 'market_data':
                    self._send_market_data()
                elif update_type == 'portfolio':
                    self._send_portfolio_data()
                elif update_type == 'memory':
                    self._send_memory_data()
                elif update_type == 'storage':
                    self._send_storage_data()
                elif update_type == 'distribution':
                    self._send_distribution_data()
                elif update_type == 'execution':
                    self._send_execution_data()
                elif update_type == 'gas':
                    self._send_gas_data()
                else:
                    logger.warning(f"Unknown update type requested: {update_type}")
            except Exception as e:
                logger.error(f"Error handling update request: {e}")

    def _update_loop(self):
        """Main update loop for pushing data to clients."""
        while self.is_running:
            try:
                self._send_market_data()
                self._send_portfolio_data()
                self._send_memory_data()
                self._send_storage_data()
                self._send_distribution_data()
                self._send_execution_data()
                self._send_gas_data()
                eventlet.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                eventlet.sleep(1)  # Brief delay before retry

    def _send_initial_data(self):
        """Send initial data to newly connected client."""
        try:
            self._send_market_data()
            self._send_portfolio_data()
            self._send_memory_data()
            self._send_storage_data()
            self._send_distribution_data()
            self._send_execution_data()
            self._send_gas_data()
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")

    def _send_market_data(self):
        """Send market data update."""
        try:
            market_data = self.market_analyzer.get_market_summary()
            self.socketio.emit('market_update', market_data)
        except Exception as e:
            logger.error(f"Error sending market data: {e}")

    def _send_portfolio_data(self):
        """Send portfolio data update."""
        try:
            portfolio_data = self.portfolio_tracker.get_portfolio_summary()
            self.socketio.emit('portfolio_update', portfolio_data)
        except Exception as e:
            logger.error(f"Error sending portfolio data: {e}")

    def _send_memory_data(self):
        """Send memory bank data update."""
        try:
            memory_data = self.memory_bank.get_status()
            self.socketio.emit('memory_update', memory_data)
        except Exception as e:
            logger.error(f"Error sending memory data: {e}")

    def _send_storage_data(self):
        """Send storage hub data update."""
        try:
            storage_data = self.storage_hub.get_status()
            self.socketio.emit('storage_update', storage_data)
        except Exception as e:
            logger.error(f"Error sending storage data: {e}")

    def _send_distribution_data(self):
        """Send distribution data update."""
        try:
            distribution_data = self.distribution_manager.get_metrics()
            self.socketio.emit('distribution_update', distribution_data)
        except Exception as e:
            logger.error(f"Error sending distribution data: {e}")

    def _send_execution_data(self):
        """Send execution data update."""
        try:
            execution_data = self.execution_manager.get_metrics()
            self.socketio.emit('execution_update', execution_data)
        except Exception as e:
            logger.error(f"Error sending execution data: {e}")

    def _send_gas_data(self):
        """Send gas price update."""
        try:
            gas_data = {
                'gas_prices': {
                    'fast': self.gas_optimizer.gas_prices['fast'],
                    'standard': self.gas_optimizer.gas_prices['standard'],
                    'slow': self.gas_optimizer.gas_prices['slow'],
                    'base_fee': self.gas_optimizer.gas_prices['base_fee'],
                    'priority_fee': self.gas_optimizer.gas_prices['priority_fee'],
                    'pending_txs': self.gas_optimizer.gas_prices['pending_txs']
                },
                'metrics': {
                    'historical_prices': self.gas_optimizer.gas_metrics['historical_prices'][-10:]  # Last 10 entries
                }
            }
            self.socketio.emit('gas_update', gas_data)
        except Exception as e:
            logger.error(f"Error sending gas data: {e}")
