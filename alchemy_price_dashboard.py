"""
Alchemy Price API Dashboard

Displays real token prices from Alchemy's Price API across multiple tokens.
"""

import os
import sys
import asyncio
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dashboard configuration
PORT = 9097  # Using a different port to avoid conflicts

# Token mappings with symbols, names and Alchemy-compatible addresses
TOKENS = [
    {
        'symbol': 'ETH',
        'name': 'Ethereum',
        'address': 'ethereum'  # Alchemy uses 'ethereum' for ETH
    },
    {
        'symbol': 'WETH',
        'name': 'Wrapped Ether',
        'address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    },
    {
        'symbol': 'USDC',
        'name': 'USD Coin',
        'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
    },
    {
        'symbol': 'USDT',
        'name': 'Tether USD',
        'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    },
    {
        'symbol': 'DAI',
        'name': 'Dai Stablecoin',
        'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F'
    },
    {
        'symbol': 'WBTC',
        'name': 'Wrapped Bitcoin',
        'address': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
    },
    {
        'symbol': 'UNI',
        'name': 'Uniswap',
        'address': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984'
    },
    {
        'symbol': 'AAVE',
        'name': 'Aave',
        'address': '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9'
    },
    {
        'symbol': 'LINK',
        'name': 'Chainlink',
        'address': '0x514910771AF9Ca656af840dff83E8264EcF986CA'
    },
    {
        'symbol': 'MATIC',
        'name': 'Polygon',
        'address': '0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0'
    }
]

# Define the exchange sources to track
EXCHANGES = [
    'uniswapv3',
    'uniswapv2',
    'sushiswap',
    'pancakeswapv2',
    'dodo'
]

class PriceCache:
    """Cache for storing price data."""
    
    def __init__(self):
        self.prices = {}
        self.last_updated = None
    
    def update_prices(self, prices: Dict[str, Any]):
        """Update the price cache with new data."""
        self.prices = prices
        self.last_updated = datetime.now()
    
    def get_prices(self) -> Dict[str, Any]:
        """Get the current price data."""
        return {
            'prices': self.prices,
            'last_updated': self.last_updated.strftime('%Y-%m-%d %H:%M:%S') if self.last_updated else None
        }

# Global price cache instance
price_cache = PriceCache()

def load_config():
    """Load configuration from various sources."""
    # First try to load from .env.production
    load_dotenv(".env.production")
    
    # Check if we have an Alchemy API key from environment
    api_key = os.environ.get('ALCHEMY_API_KEY')
    if api_key:
        logger.info("Using Alchemy API key from .env.production file")
        return {"alchemy": {"api_key": api_key}}
    
    # If not, try to load from config.json
    try:
        with open('configs/config.json', 'r') as f:
            config = json.load(f)
            # Check if the config has network.rpc_url which might contain the Alchemy URL
            if "network" in config and "rpc_url" in config["network"]:
                url = config["network"]["rpc_url"]
                # If this is a secure reference, try to get it from the environment
                if url.startswith("$SECURE:"):
                    env_var = url.replace("$SECURE:", "")
                    url = os.environ.get(env_var, "")
                    
                # Extract API key from Alchemy URL if present
                if "alchemy.com" in url and "/v2/" in url:
                    api_key = url.split("/v2/")[1]
                    logger.info("Extracted Alchemy API key from config.json RPC URL")
                    return {"alchemy": {"api_key": api_key}}
        
        logger.warning("Could not find Alchemy API key in config.json")
    except Exception as e:
        logger.warning(f"Could not load config.json: {e}")
    
    logger.warning("No Alchemy API key found. You'll need to set the ALCHEMY_API_KEY environment variable.")
    return {}

def get_alchemy_api_key(config=None):
    """Get Alchemy API key from config."""
    api_key = config.get('alchemy', {}).get('api_key')
    if not api_key:
        logger.warning("Alchemy API key not found. Please set ALCHEMY_API_KEY environment variable or add it to your config.")
    
    return api_key

def get_token_price(token_address, api_key):
    """
    Get token price in USD using Alchemy's Price API.
    
    Args:
        token_address: Token address or 'ethereum' for ETH
        api_key: Alchemy API key
        
    Returns:
        Dictionary with price data or None if request fails
    """
    url = f"https://api.alchemy.com/v2/{api_key}/alchemy/etherspot/price-entities"
    
    payload = {
        "asset": token_address
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        if data and 'price' in data:
            return data
        else:
            logger.warning(f"No price data returned for {token_address}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting price for {token_address}: {e}")
        return None

def get_token_price_on_exchange(token_address, exchange, api_key):
    """
    Get token price on a specific exchange using Alchemy's Price API.
    
    Args:
        token_address: Token address or 'ethereum' for ETH
        exchange: Exchange name (uniswapv3, sushiswap, etc.)
        api_key: Alchemy API key
        
    Returns:
        Dictionary with price data or None if request fails
    """
    url = f"https://api.alchemy.com/v2/{api_key}/alchemy/etherspot/get-exchange-price"
    
    payload = {
        "source": exchange,
        "destination": "USD",
        "amount": "1",
        "sourceAsset": token_address
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        if data and 'price' in data:
            return data
        else:
            logger.warning(f"No price data returned for {token_address} on {exchange}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting price for {token_address} on {exchange}: {e}")
        return None

async def fetch_token_prices():
    """
    Fetch token prices from Alchemy Price API.
    
    Returns:
        Dictionary with price data
    """
    # Load configuration from environment/config files
    config = load_config()
    
    # Get Alchemy API key
    api_key = get_alchemy_api_key(config)
    if not api_key:
        # Return empty result if no API key
        return {}
    
    result = {}
    
    # First get global prices for all tokens
    for token in TOKENS:
        symbol = token['symbol']
        address = token['address']
        
        price_data = get_token_price(address, api_key)
        if price_data:
            # Store token global price data
            result[symbol] = {
                'symbol': symbol,
                'name': token['name'],
                'price': price_data.get('price', 0),
                'exchanges': {}
            }
        else:
            # Initialize with empty data if API call fails
            result[symbol] = {
                'symbol': symbol,
                'name': token['name'],
                'price': 0,
                'exchanges': {}
            }
    
    # Now get prices for each token on each exchange
    for token in TOKENS:
        symbol = token['symbol']
        address = token['address']
        
        # Skip if token not in results (shouldn't happen)
        if symbol not in result:
            continue
        
        # Get price on each exchange
        for exchange in EXCHANGES:
            exchange_data = get_token_price_on_exchange(address, exchange, api_key)
            
            if exchange_data:
                # Store exchange-specific price
                result[symbol]['exchanges'][exchange] = {
                    'price': exchange_data.get('price', 0),
                    'source': exchange_data.get('source', exchange),
                    'timestamp': exchange_data.get('timestamp', datetime.now().isoformat())
                }
            else:
                # Store empty data if API call fails
                result[symbol]['exchanges'][exchange] = {
                    'price': 0,
                    'source': exchange,
                    'timestamp': None
                }
    
    return result

async def price_update_job():
    """Background job to update prices periodically."""
    while True:
        try:
            logger.info("Updating token prices...")
            prices = await fetch_token_prices()
            price_cache.update_prices(prices)
            logger.info("Prices updated successfully")
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
        
        # Wait before next update
        await asyncio.sleep(30)  # Update every 30 seconds to avoid API rate limits

class AlchemyPriceDashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the Alchemy price dashboard."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_html().encode())
        elif self.path == "/style.css":
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            self.wfile.write(self.get_css().encode())
        elif self.path == "/api/prices":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(price_cache.get_prices()).encode())
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")
    
    def generate_html(self):
        """Generate HTML for the dashboard."""
        # Get price data
        data = price_cache.get_prices()
        prices = data['prices']
        last_updated = data['last_updated']
        
        # Create token rows
        token_rows = ""
        if prices:
            for symbol, token_data in prices.items():
                token_price = token_data.get('price', 0)
                token_name = token_data.get('name', symbol)
                
                # Start token row
                token_rows += f"""
                <div class="token-row">
                    <div class="token-info">
                        <div class="token-symbol">{symbol}</div>
                        <div class="token-name">{token_name}</div>
                        <div class="token-price">${token_price:,.2f}</div>
                    </div>
                    <div class="exchange-prices">
                """
                
                # Add exchange prices
                exchanges = token_data.get('exchanges', {})
                for exchange_name, exchange_data in exchanges.items():
                    price = exchange_data.get('price', 0)
                    
                    # Skip if no price data
                    if price == 0:
                        continue
                    
                    # Format exchange name
                    display_name = exchange_name
                    if exchange_name.lower() == 'uniswapv2':
                        display_name = 'Uniswap V2'
                    elif exchange_name.lower() == 'uniswapv3':
                        display_name = 'Uniswap V3'
                    elif exchange_name.lower() == 'pancakeswapv2':
                        display_name = 'PancakeSwap'
                    
                    token_rows += f"""
                    <div class="exchange-price">
                        <div class="exchange-name">{display_name}</div>
                        <div class="price-value">${price:,.2f}</div>
                    </div>
                    """
                
                # End token row
                token_rows += """
                    </div>
                </div>
                """
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alchemy Price Dashboard</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="30">
    <script>
        // Auto-refresh the data every 30 seconds
        setInterval(function() {{
            fetch('/api/prices')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('last-updated').textContent = data.last_updated;
                    // In a full implementation, we would update the price values here
                }});
        }}, 30000);
    </script>
</head>
<body>
    <div class="header">
        <h1>Real-Time Token Prices</h1>
        <div class="sub-header">Powered by Alchemy Price API</div>
        <div class="last-updated">
            Last Updated: <span id="last-updated">{last_updated or 'Loading...'}</span>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="token-prices">
            {token_rows if prices else '<div class="loading">Loading price data...</div>'}
        </div>
    </div>
    
    <div class="footer">
        <p>Alchemy Price Dashboard | Auto-refreshes every 30 seconds</p>
    </div>
</body>
</html>
"""
    
    def get_css(self):
        """Get CSS styles for the dashboard."""
        return """
        :root {
            --primary-color: #6C5CE7;
            --secondary-color: #2d3436;
            --accent-color: #00cec9;
            --background-color: #f9f9f9;
            --card-background: #ffffff;
            --text-color: #2d3436;
            --light-text: #636e72;
            --border-color: #dfe6e9;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 30px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
        }
        
        .sub-header {
            margin-top: 5px;
            font-size: 1.1em;
            opacity: 0.8;
        }
        
        .last-updated {
            margin-top: 15px;
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .dashboard {
            max-width: 1200px;
            margin: 30px auto;
            padding: 0 20px;
        }
        
        .token-prices {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .token-row {
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        
        .token-info {
            padding: 20px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }
        
        .token-symbol {
            font-size: 1.5em;
            font-weight: bold;
            color: var(--primary-color);
            margin-right: 15px;
            min-width: 80px;
        }
        
        .token-name {
            flex: 1;
            color: var(--light-text);
            font-size: 1.1em;
        }
        
        .token-price {
            font-size: 1.8em;
            font-weight: bold;
            color: var(--secondary-color);
        }
        
        .exchange-prices {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            padding: 20px;
            background-color: #f5f7fa;
        }
        
        .exchange-price {
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .exchange-name {
            font-weight: 500;
            color: var(--light-text);
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        
        .price-value {
            font-size: 1.3em;
            font-weight: bold;
            color: var(--accent-color);
        }
        
        .loading {
            padding: 40px;
            text-align: center;
            font-size: 1.2em;
            color: var(--light-text);
        }
        
        .footer {
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            color: var(--light-text);
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .token-info {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .token-symbol {
                margin-bottom: 5px;
            }
            
            .token-name {
                margin-bottom: 10px;
            }
            
            .exchange-prices {
                grid-template-columns: 1fr;
            }
        }
        """

async def start_server():
    """Start the HTTP server and price update job."""
    # Start the price update job
    asyncio.create_task(price_update_job())
    
    # Start the HTTP server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, AlchemyPriceDashboardHandler)
    
    print(f"Starting Alchemy Price Dashboard on port {PORT}...")
    print(f"Open this URL in your browser: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    
    # Run the server in a separate thread
    import threading
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Keep the main thread running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Server stopped.")
        httpd.shutdown()

def run_server():
    """Run the server."""
    asyncio.run(start_server())

if __name__ == "__main__":
    run_server()