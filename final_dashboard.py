"""
Arbitrage Dashboard with Base Network Integration
"""

from aiohttp import web
import os
import socketio
import logging
import psutil
import json
import asyncio
from web3 import Web3, AsyncWeb3
from typing import Dict, Any
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
with open('configs/config.json', 'r') as f:
    config = json.load(f)

# Initialize Web3
w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(config['provider_url']))

# Initialize Socket.IO
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False
)

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")

@sio.event
async def request_update(sid, data=None):
    """Handle update request from client."""
    try:
        # Get system metrics
        process = psutil.Process(os.getpid())
        memory_percent = process.memory_percent()

        # Emit system status
        await sio.emit('system_status', {
            'status': 'online',
            'memory_usage': memory_percent,
            'cpu_percent': process.cpu_percent(),
            'active_positions': len(dashboard.active_positions),
            'profit_24h': dashboard.profit_24h
        }, room=sid)

        # Emit blockchain status
        network_data = await get_dashboard_data()
        await sio.emit('blockchain_status', network_data, room=sid)

    except Exception as e:
        logger.error(f"Error handling update request: {e}")
        await sio.emit('error', {'message': str(e)}, room=sid)

@sio.event
async def update_opportunities(sid, data):
    """Handle new opportunities data."""
    try:
        dashboard.opportunities = data.get('opportunities', [])
        await sio.emit('opportunities', {
            'opportunities': dashboard.opportunities
        }, room=sid)
    except Exception as e:
        logger.error(f"Error handling opportunities update: {e}")

@sio.event
async def update_mev_protection(sid, data):
    """Handle MEV protection status update."""
    try:
        dashboard.mev_stats = {
            'active': data.get('active', False),
            'blocked_attacks': data.get('blocked_attacks', 0),
            'risk_level': data.get('risk_level', 'low')
        }
        await sio.emit('mev_protection', dashboard.mev_stats, room=sid)
    except Exception as e:
        logger.error(f"Error handling MEV protection update: {e}")

@sio.event
async def update_profit(sid, data):
    """Handle profit updates."""
    try:
        dashboard.profit_24h = float(data.get('profit_24h', 0))
        dashboard.total_profit = float(data.get('total_profit', 0))
        await sio.emit('profit_update', {
            'profit_24h': dashboard.profit_24h,
            'total_profit': dashboard.total_profit
        }, room=sid)
    except Exception as e:
        logger.error(f"Error handling profit update: {e}")

# Periodic update task
async def periodic_updates():
    """Send periodic updates to all connected clients."""
    while True:
        try:
            # Get system metrics
            process = psutil.Process(os.getpid())
            memory_percent = process.memory_percent()

            # Prepare update data
            status_data = {
                'status': 'online',
                'memory_usage': memory_percent,
                'active_positions': len(dashboard.active_positions),
                'profit_24h': dashboard.profit_24h
            }

            # Emit updates to all clients
            await sio.emit('system_status', status_data)
            await sio.emit('mev_protection', dashboard.mev_stats)
            await sio.emit('opportunities', {'opportunities': dashboard.opportunities})
            await sio.emit('profit_update', {
                'profit_24h': dashboard.profit_24h,
                'total_profit': dashboard.total_profit
            })

        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")

        await asyncio.sleep(5)  # Update every 5 seconds

class DashboardStats:
    """Real-time dashboard statistics."""
    def __init__(self):
        self.block_number = 0
        self.gas_price = 0
        self.network_load = 0.0
        self.dex_stats = {}
        self.last_update = None
        self.active_positions = []
        self.profit_24h = 0.0
        self.total_profit = 0.0
        self.opportunities = []
        self.mev_stats = {'active': False, 'blocked_attacks': 0, 'risk_level': 'low'}
        self.update_task = None

        # Contract addresses
        self.dex_contracts = {
            name: {
                'factory': w3.to_checksum_address(dex['factory']),
                'router': w3.to_checksum_address(dex['router'])
            }
            for name, dex in config['dexes'].items()
            if dex.get('enabled', True)
        }

        # Token addresses
        self.tokens = {
            symbol: w3.to_checksum_address(address)
            for symbol, address in config['tokens'].items()
        }

    async def update_network_stats(self):
        """Update network statistics."""
        try:
            # Get latest block and gas price
            block = await w3.eth.get_block('latest')
            gas_price = await w3.eth.gas_price

            self.block_number = block.number
            self.gas_price = gas_price
            self.network_load = min(1.0, len(block.transactions) / 300)  # Rough estimate based on block fullness

            logger.info(f"Updated network stats - Block: {self.block_number}, Gas: {gas_price / 1e9:.1f} Gwei")
            return True

        except Exception as e:
            logger.error(f"Error updating network stats: {e}")
            return False

    async def update_dex_stats(self):
        """Update DEX statistics."""
        try:
            for dex_name, contracts in self.dex_contracts.items():
                factory_contract = w3.eth.contract(
                    address=contracts['factory'],
                    abi=self.load_abi(f"abi/{dex_name}_factory.json")
                )

                # Get basic DEX stats
                pair_count = await factory_contract.functions.allPairsLength().call()
                
                # Get WETH-USDC pair info if it exists
                try:
                    pair_address = await factory_contract.functions.getPair(
                        self.tokens['WETH'],
                        self.tokens['USDC']
                    ).call()
                    
                    if pair_address and pair_address != '0x' + '0' * 40:
                        pair_contract = w3.eth.contract(
                            address=pair_address,
                            abi=self.load_abi(f"abi/{dex_name}_pair.json")
                        )
                        reserves = await pair_contract.functions.getReserves().call()
                        
                        self.dex_stats[dex_name] = {
                            'pair_count': pair_count,
                            'weth_usdc_liquidity': True,
                            'reserves': reserves
                        }
                    else:
                        self.dex_stats[dex_name] = {
                            'pair_count': pair_count,
                            'weth_usdc_liquidity': False,
                            'reserves': None
                        }
                except Exception as e:
                    logger.error(f"Error getting pair info for {dex_name}: {e}")
                    self.dex_stats[dex_name] = {
                        'pair_count': pair_count,
                        'weth_usdc_liquidity': False,
                        'reserves': None
                    }

            return True

        except Exception as e:
            logger.error(f"Error updating DEX stats: {e}")
            return False

    def load_abi(self, path: str) -> list:
        """Load contract ABI from file."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading ABI from {path}: {e}")
            return []

# Initialize dashboard
dashboard = DashboardStats()

async def get_dashboard_data():
    """Get current dashboard data."""
    await dashboard.update_network_stats()
    await dashboard.update_dex_stats()

    return {
        'network': {
            'block_number': dashboard.block_number,
            'gas_price': f"{dashboard.gas_price / 1e9:.1f} Gwei",
            'network_load': f"{dashboard.network_load * 100:.1f}%"
        },
        'dexes': dashboard.dex_stats
    }

async def handle_stats(request):
    """Handle stats API requests."""
    try:
        data = await get_dashboard_data()
        return web.Response(
            text=json.dumps(data),
            content_type='application/json'
        )
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return web.Response(
            text=json.dumps({
                'error': str(e)
            }),
            status=500,
            content_type='application/json'
        )

async def handle_index(request):
    """Handle root path request."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Base Network Arbitrage Dashboard</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f0f2f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
            }
            .card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .card h2 {
                color: #1a73e8;
                margin-top: 0;
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                color: #0d904f;
            }
            .dex-info {
                margin-top: 10px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
            }
            .profit-info {
                margin-top: 10px;
                padding: 10px;
                background: #e8f5e9;
                border-radius: 4px;
            }
            .opportunity-info {
                margin-top: 10px;
                padding: 10px;
                background: #e3f2fd;
                border-radius: 4px;
            }
        </style>
        <script>
            document.addEventListener('DOMContentLoaded', () => {
                const socket = io();

                socket.on('connect', () => {
                    console.log('Connected to server');
                    document.getElementById('connection-status').textContent = 'Connected';
                });

                socket.on('disconnect', () => {
                    console.log('Disconnected from server');
                    document.getElementById('connection-status').textContent = 'Disconnected';
                });

                socket.on('system_status', (data) => {
                    document.getElementById('memory-usage').textContent = `${data.memory_usage.toFixed(2)}%`;
                    document.getElementById('active-positions').textContent = data.active_positions;
                    document.getElementById('profit-24h').textContent = `${data.profit_24h} ETH`;
                });

                socket.on('mev_protection', (data) => {
                    document.getElementById('mev-status').textContent = data.active ? 'Active' : 'Inactive';
                    document.getElementById('blocked-attacks').textContent = data.blocked_attacks;
                    document.getElementById('risk-level').textContent = data.risk_level;
                });

                socket.on('opportunities', (data) => {
                    const container = document.getElementById('opportunities');
                    container.innerHTML = '';
                    data.opportunities.forEach(opp => {
                        const div = document.createElement('div');
                        div.className = 'opportunity-info';
                        div.innerHTML = `
                            <p><strong>${opp.token_pair}</strong></p>
                            <p>Potential Profit: ${opp.potential_profit} ETH</p>
                            <p>Route: ${opp.route}</p>
                            <p>Confidence: ${opp.confidence}%</p>
                        `;
                        container.appendChild(div);
                    });
                });

                socket.on('profit_update', (data) => {
                    document.getElementById('total-profit').textContent = `${data.profit} ETH`;
                });

                // Request initial update
                socket.emit('request_update');

                // Setup periodic update requests
                setInterval(() => {
                    socket.emit('request_update');
                }, 5000);
            });

            function formatTimestamp(timestamp) {
                try {
                    const date = new Date(timestamp);
                    return date.toLocaleString();
                } catch (e) {
                    return timestamp;
                }
            }
        </script>
    </head>
    <body>
        <h1>Base Network Arbitrage Dashboard</h1>
        <p>Status: <span id="connection-status">Connecting...</span></p>
        
        <div class="container">
            <div class="card">
                <h2>System Status</h2>
                <div>
                    <p>Memory Usage: <span id="memory-usage" class="stat-value">-</span></p>
                    <p>Active Positions: <span id="active-positions" class="stat-value">-</span></p>
                    <p>24h Profit: <span id="profit-24h" class="stat-value">-</span></p>
                </div>
            </div>
            
            <div class="card">
                <h2>MEV Protection</h2>
                <div>
                    <p>Status: <span id="mev-status" class="stat-value">-</span></p>
                    <p>Blocked Attacks: <span id="blocked-attacks" class="stat-value">-</span></p>
                    <p>Risk Level: <span id="risk-level" class="stat-value">-</span></p>
                </div>
            </div>

            <div class="card">
                <h2>Profit Overview</h2>
                <div class="profit-info">
                    <p>Total Profit: <span id="total-profit" class="stat-value">-</span></p>
                </div>
            </div>

            <div class="card">
                <h2>Recent Opportunities</h2>
                <div id="opportunities">
                    Loading opportunities...
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def init_app():
    """Initialize the application."""
    app = web.Application()
    
    # Attach Socket.IO
    sio.attach(app)
    
    # Start periodic updates
    asyncio.create_task(periodic_updates())
    
    # Add routes
    app.router.add_get('/', handle_index)
    app.router.add_get('/api/stats', handle_stats)
    
    return app

async def main():
    """Run the dashboard server."""
    port = 9095
    logger.info(f"Starting dashboard on http://localhost:{port}")
    
    try:
        app = await init_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        await asyncio.Event().wait()  # run forever
    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())