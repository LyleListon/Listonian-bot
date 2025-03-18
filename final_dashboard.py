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
import sys
from web3 import Web3, AsyncWeb3
from typing import Dict, Any, Optional, Tuple
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
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
    reconnection=True,
    reconnection_attempts=5
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
                'router': w3.to_checksum_address(dex['router']),
                'version': dex.get('version', 'v2')  # Default to v2 if not specified
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

    async def get_pool_address(self, factory_contract, dex_name: str, token0: str, token1: str) -> Optional[str]:
        """Get pool address based on DEX version."""
        try:
            # Sort tokens to match DEX's internal ordering
            token0, token1 = sorted([token0, token1])
            
            if self.dex_contracts[dex_name]['version'] == 'v2':
                # V2-style getPair
                try:
                    pool_address = await factory_contract.functions.getPair(
                        token0, token1
                    ).call()
                    if pool_address and pool_address != '0x' + '0' * 40:
                        return pool_address
                except Exception as e:
                    logger.error(f"Error getting pair info for {dex_name}: {e}")
                    return None

            elif self.dex_contracts[dex_name]['version'] in ['v3', 'swapbased']:
                # V3-style getPool with fee parameter
                try:
                    # For SwapBased V3, use predefined pool addresses
                    if dex_name == 'swapbased' and 'pools' in config['dexes'][dex_name]:
                        token0_symbol = next((k for k, v in self.tokens.items() if v.lower() == token0.lower()), '')
                        token1_symbol = next((k for k, v in self.tokens.items() if v.lower() == token1.lower()), '')
                        pool_key = f"{token0_symbol}-{token1_symbol}"
                        if pool_key in config['dexes'][dex_name]['pools']:
                            return w3.to_checksum_address(config['dexes'][dex_name]['pools'][pool_key])
                    else:
                        pool_address = await factory_contract.functions.getPool(
                            token0, token1, 3000  # Default fee tier
                        ).call()
                        if pool_address and pool_address != '0x' + '0' * 40:
                            return pool_address
                except Exception as e:
                    logger.error(f"Error getting pool info for {dex_name}: {e}")
                    return None

            elif self.dex_contracts[dex_name]['version'] == 'aerodrome':
                # Aerodrome-style getPool with stable parameter
                try:
                    # Try both stable and volatile pools
                    for stable in [True, False]:
                        pool_address = await factory_contract.functions.getPool(
                            token0, token1, stable
                        ).call()
                        if pool_address and pool_address != '0x' + '0' * 40:
                            return pool_address
                except Exception as e:
                    logger.error(f"Error getting pool info for {dex_name}: {e}")
                    return None

            return None

        except Exception as e:
            logger.error(f"Error getting pool address for {dex_name}: {e}")
            return None

    async def get_pool_data(self, pool_address: str, dex_name: str) -> Optional[dict]:
        """Get pool data based on DEX version."""
        try:
            # Load appropriate ABI
            try:
                with open(f"abi/{dex_name}_v3_pool.json" if self.dex_contracts[dex_name]['version'] in ['v3', 'swapbased'] else f"abi/{dex_name}_pool.json", 'r') as f:
                    pool_abi = json.load(f)
            except FileNotFoundError:
                try:
                    with open(f"abi/{dex_name}_pair.json", 'r') as f:
                        pool_abi = json.load(f)
                except FileNotFoundError:
                    logger.error(f"No pool/pair ABI found for {dex_name}")
                    return None

            pool_contract = w3.eth.contract(
                address=pool_address,
                abi=pool_abi
            )

            if self.dex_contracts[dex_name]['version'] in ['v3', 'swapbased']:
                # V3 pools
                try:
                    # Get pool data based on DEX version
                    if dex_name == 'swapbased':
                        # SwapBased V3 uses different function names
                        current_state = await pool_contract.functions.currentState().call()
                        return {
                            'sqrtPriceX96': current_state[0],
                            'tick': current_state[1],
                            'liquidity': current_state[2]
                        }
                    else:
                        slot0 = await pool_contract.functions.slot0().call()
                        liquidity = await pool_contract.functions.liquidity().call()
                    return {
                        'sqrtPriceX96': slot0[0],
                        'tick': slot0[1],
                        'liquidity': liquidity
                    }
                except Exception as e:
                    logger.error(f"Error getting V3 pool data for {dex_name}: {e}")
                    return None
            else:
                # V2 pairs and Aerodrome pools
                try:
                    reserves = await pool_contract.functions.getReserves().call()
                    return {
                        'reserve0': reserves[0],
                        'reserve1': reserves[1],
                        'timestamp': reserves[2]
                    }
                except Exception as e:
                    logger.error(f"Error getting pool data for {dex_name}: {e}")
                    return None

        except Exception as e:
            logger.error(f"Error getting pool data for {dex_name}: {e}")
            return None

    async def update_dex_stats(self):
        """Update DEX statistics."""
        try:
            for dex_name, contracts in self.dex_contracts.items():
                try:
                    # Load factory ABI
                    with open(f"abi/{dex_name}_factory.json", 'r') as f:
                        factory_abi = json.load(f)

                    factory_contract = w3.eth.contract(
                        address=contracts['factory'],
                        abi=factory_abi
                    )

                    # Get WETH-USDC pool/pair
                    pool_address = await self.get_pool_address(
                        factory_contract,
                        dex_name,
                        self.tokens['WETH'],
                        self.tokens['USDC']
                    )

                    if pool_address:
                        pool_data = await self.get_pool_data(pool_address, dex_name)
                        self.dex_stats[dex_name] = {
                            'weth_usdc_liquidity': True,
                            'pool_data': pool_data
                        }
                    else:
                        self.dex_stats[dex_name] = {
                            'weth_usdc_liquidity': False,
                            'pool_data': None
                        }

                except Exception as e:
                    logger.error(f"Error updating stats for {dex_name}: {e}")
                    self.dex_stats[dex_name] = {
                        'weth_usdc_liquidity': False,
                        'pool_data': None
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
                const socket = io({
                    transports: ['websocket'],
                    reconnection: true,
                    reconnectionAttempts: 5,
                    reconnectionDelay: 1000,
                    reconnectionDelayMax: 5000,
                    timeout: 20000,
                    autoConnect: true
                });

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
                    document.getElementById('total-profit').textContent = `${data.total_profit} ETH`;
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
        await asyncio.sleep(1)  # Give the server a moment to initialize
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        await asyncio.Event().wait()  # run forever
    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
