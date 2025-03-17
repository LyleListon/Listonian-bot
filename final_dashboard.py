"""
Arbitrage Dashboard with Base Network Integration
"""

from aiohttp import web
import logging
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

class DashboardStats:
    """Real-time dashboard statistics."""
    def __init__(self):
        self.block_number = 0
        self.gas_price = 0
        self.network_load = 0.0
        self.dex_stats = {}
        self.last_update = None

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
        </style>
        <script>
            async function updateStats() {
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    
                    // Update network stats
                    if (data.network) {
                        document.getElementById('block-number').textContent = data.network.block_number;
                        document.getElementById('gas-price').textContent = data.network.gas_price;
                        document.getElementById('network-load').textContent = data.network.network_load;
                    }
                    
                    // Update DEX stats
                    if (data.dexes) {
                        const dexContainer = document.getElementById('dex-stats');
                        dexContainer.innerHTML = '';
                        
                        for (const [name, stats] of Object.entries(data.dexes)) {
                            const dexCard = document.createElement('div');
                            dexCard.className = 'dex-info';
                            dexCard.innerHTML = `
                                <h3>${name}</h3>
                                <p>Total Pairs: ${stats.pair_count}</p>
                                <p>WETH-USDC Pool: ${stats.weth_usdc_liquidity ? 'Active' : 'Not Found'}</p>
                            `;
                            dexContainer.appendChild(dexCard);
                        }
                    }
                } catch (error) {
                    console.error('Error updating stats:', error);
                }
            }

            // Update stats every 5 seconds
            setInterval(updateStats, 5000);
            
            // Initial update
            updateStats();
        </script>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h2>Network Status</h2>
                <div>
                    <p>Block Number: <span id="block-number" class="stat-value">-</span></p>
                    <p>Gas Price: <span id="gas-price" class="stat-value">-</span></p>
                    <p>Network Load: <span id="network-load" class="stat-value">-</span></p>
                </div>
            </div>
            
            <div class="card">
                <h2>DEX Status</h2>
                <div id="dex-stats">
                    Loading DEX information...
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
    app.router.add_get('/', handle_index)
    app.router.add_get('/api/stats', handle_stats)
    return app

def main():
    """Run the dashboard server."""
    port = 9095
    logger.info(f"Starting dashboard on http://localhost:{port}")
    web.run_app(init_app(), port=port)

if __name__ == '__main__':
    main()