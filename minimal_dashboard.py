#!/usr/bin/env python
"""
Minimal Dashboard for Arbitrage Bot

This script provides a simple dashboard for monitoring the arbitrage bot.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from flask import Flask, render_template_string, jsonify
from web3 import Web3, HTTPProvider

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "minimal_dashboard.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("minimal_dashboard")

# Create Flask app
app = Flask(__name__)

# Initialize Web3 connection and wallet
web3 = None
wallet_address = None
view_address = None

# Reset start time on each restart
start_time = time.time()

# Basic HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f7f9;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .card {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        .card h2 {
            margin-top: 0;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
            color: #2c3e50;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        .stat-card {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 15px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            font-size: 14px;
            color: #7f8c8d;
        }
        pre {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        .dex-list {
            list-style-type: none;
            padding: 0;
        }
        .dex-item {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .dex-name {
            font-weight: bold;
        }
        .refresh {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 20px;
        }
        .refresh:hover {
            background-color: #2980b9;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #7f8c8d;
            font-size: 12px;
        }
        
        /* Data auto-refresh */
        #last-update {
            margin-top: 10px;
            font-size: 12px;
            color: #7f8c8d;
        }
        .error-notice {
            background-color: #e74c3c;
            color: white;
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .info-notice {
            background-color: #3498db;
            color: white;
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .debug-card {
            background-color: #f39c12;
            color: white;
            text-align: left;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-family: monospace;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Arbitrage Bot Dashboard</h1>
            <p>Monitoring and system status</p>
        </div>
        
        {% if error_message %}
        <div class="error-notice">
            {{ error_message }}
        </div>
        {% endif %}
        
        {% if info_message %}
        <div class="info-notice">
            {{ info_message }}
        </div>
        {% endif %}
        
        {% if debug_info %}
        <div class="debug-card">
            <strong>Debug Information:</strong>
            {{ debug_info }}
        </div>
        {% endif %}
        
        <div class="card">
            <h2>System Status</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value" id="status">{{ status }}</div>
                    <div class="stat-label">Current Status</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="uptime">{{ uptime }}</div>
                    <div class="stat-label">Uptime</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="wallet-balance">{{ wallet_balance }}</div>
                    <div class="stat-label">Wallet Balance</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-profit">{{ total_profit }}</div>
                    <div class="stat-label">Total Profit</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Network Information</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value" id="network">{{ network }}</div>
                    <div class="stat-label">Network</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="gas-price">{{ gas_price }}</div>
                    <div class="stat-label">Gas Price (Gwei)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="block-number">{{ block_number }}</div>
                    <div class="stat-label">Block Number</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="wallet-address">{{ wallet_address_short }}</div>
                    <div class="stat-label">Wallet Address</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Integrated DEXes</h2>
            <ul class="dex-list">
                <li class="dex-item"><span class="dex-name">Uniswap V2</span> - Status: Active</li>
                <li class="dex-item"><span class="dex-name">Sushiswap</span> - Status: Active</li>
                <li class="dex-item"><span class="dex-name">Uniswap V3</span> - Status: Active</li>
                <li class="dex-item"><span class="dex-name">Pancakeswap</span> - Status: Active</li>
                <li class="dex-item"><span class="dex-name">Baseswap</span> - Status: Active</li>
            </ul>
        </div>
        
        <div class="card">
            <h2>Dynamic Allocation Status</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{{ min_percentage }}%</div>
                    <div class="stat-label">Min Percentage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ max_percentage }}%</div>
                    <div class="stat-label">Max Percentage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ concurrent_trades }}</div>
                    <div class="stat-label">Concurrent Trades</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ reserve_percentage }}%</div>
                    <div class="stat-label">Reserve</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Recent Transactions</h2>
            <pre id="transactions">{{ transactions }}</pre>
        </div>
        
        <div class="card">
            <h2>Configuration</h2>
            <pre id="config">{{ config_json }}</pre>
        </div>
        
        <button class="refresh" onclick="refreshData()">Refresh Data</button>
        <div id="last-update">Last updated: {{ current_time }}</div>
    </div>
    
    <div class="footer">
        <p>Arbitrage Bot Dashboard v1.0 | © 2025</p>
    </div>
    
    <script>
        // Auto-refresh data every 30 seconds
        setInterval(refreshData, 15000);
        
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').textContent = data.status;
                    document.getElementById('uptime').textContent = data.uptime;
                    document.getElementById('wallet-balance').textContent = data.wallet_balance;
                    document.getElementById('total-profit').textContent = data.total_profit;
                    document.getElementById('transactions').textContent = data.transactions;
                    document.getElementById('network').textContent = data.network;
                    document.getElementById('gas-price').textContent = data.gas_price;
                    document.getElementById('block-number').textContent = data.block_number;
                    document.getElementById('wallet-address').textContent = data.wallet_address_short;
                    document.getElementById('last-update').textContent = 'Last updated: ' + data.current_time;
                })
                .catch(error => console.error('Error fetching data:', error));
        }
    </script>
</body>
</html>
"""

error_message = None
info_message = None
debug_info = None

def load_config():
    """Load configuration from file."""
    try:
        with open("configs/production.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        return {}

def initialize_web3():
    """Initialize Web3 connection from config."""
    global web3, wallet_address, view_address, error_message, info_message, debug_info
    
    try:
        config = load_config()
        provider_url = config.get('provider_url', '')
        private_key = config.get('private_key', '')
        
        # Check if we have a view address to display (even if wallet isn't usable)
        view_address = config.get('view_address')
        
        # Debug info
        debug_info = "Using view address: " + (view_address or "None") + "\n"
        
        # Check if we have proper values
        if 'YOUR_API_KEY' in provider_url or not provider_url:
            error_message = "ERROR: No valid provider URL configured. Please update configs/production.json."
            return
            
        debug_info += "Provider URL: " + provider_url[:30] + "...\n"
        
        # Connect to Ethereum node
        web3 = Web3(HTTPProvider(provider_url))
        
        # Check connection
        if not web3.isConnected():
            error_message = "ERROR: Failed to connect to Ethereum node. Please check your provider URL."
            return
        
        debug_info += "Connected to Web3: " + str(web3.isConnected()) + "\n"
        debug_info += "Checking Web3 connection: Network ID: " + str(web3.net.version) + "\n"
        
        # Connect wallet if private key provided    
        if private_key and private_key != 'YOUR_PRIVATE_KEY_HERE':
            try:
                account = web3.eth.account.from_key(private_key)
                wallet_address = account.address
                debug_info += "Wallet address from private key: " + wallet_address + "\n"
                logger.info("Web3 initialized with wallet. Connected to network: %s", get_network_name())
            except Exception as e:
                error_message = f"ERROR: Invalid private key format. Please check your private key."
                logger.error("Failed to initialize wallet: %s", e)
                debug_info += "Wallet error: " + str(e) + "\n"
                # Still continue if we have a view address
                if view_address:
                    info_message = "Using view-only address for balance display. Transactions will not be possible."
        else:
            if view_address:
                info_message = "Using view-only address for balance display. Transactions will not be possible."
                debug_info += "Using view address only. No private key.\n"
            else:
                error_message = "ERROR: No valid private key or view address configured. Please update configs/production.json."
                debug_info += "No private key or view address configured.\n"
            
    except Exception as e:
        error_message = f"ERROR: Failed to initialize Web3 connection: {str(e)}"
        logger.error("Failed to initialize Web3: %s", e)
        debug_info += "Web3 initialization error: " + str(e) + "\n"

def get_network_name():
    """Get the name of the connected network."""
    if not web3 or not web3.isConnected():
        return "Not Connected"
    
    try:
        chain_id = web3.eth.chain_id
        networks = {
            1: "Ethereum Mainnet",
            3: "Ropsten Testnet",
            4: "Rinkeby Testnet",
            5: "Goerli Testnet",
            42: "Kovan Testnet",
            56: "Binance Smart Chain",
            137: "Polygon Mainnet",
            42161: "Arbitrum",
            10: "Optimism",
            8453: "Base"
        }
        return networks.get(chain_id, f"Unknown Network (Chain ID: {chain_id})")
    except Exception as e:
        logger.error("Failed to get network name: %s", e)
        return "Unknown"

def get_wallet_balance():
    """Get wallet balance in ETH."""
    global debug_info
    
    # Use view address if available, fall back to wallet address
    address_to_check = view_address or wallet_address
    
    if not web3 or not web3.isConnected() or not address_to_check:
        debug_info += "Cannot get balance: " + str(bool(web3)) + ", " + str(bool(web3.isConnected() if web3 else False)) + ", " + str(bool(address_to_check)) + "\n"
        return "Not Available"
    
    try:
        debug_info += "Checking balance for: " + address_to_check + "\n"
        balance_wei = web3.eth.get_balance(Web3.to_checksum_address(address_to_check))
        debug_info += "Balance in wei: " + str(balance_wei) + "\n"
        balance_eth = web3.from_wei(balance_wei, 'ether')
        debug_info += "Balance in ETH: " + str(balance_eth) + "\n"
        return f"{balance_eth:.4f} ETH"
    except Exception as e:
        logger.error("Failed to get wallet balance: %s", e)
        debug_info += "Balance error: " + str(e) + "\n"
        return "Error"

def get_gas_price():
    """Get current gas price in Gwei."""
    if not web3 or not web3.isConnected():
        return "Not Available"
    
    try:
        gas_price_wei = web3.eth.gas_price
        gas_price_gwei = web3.from_wei(gas_price_wei, 'gwei')
        return f"{gas_price_gwei:.2f}"
    except Exception as e:
        logger.error("Failed to get gas price: %s", e)
        return "Error"

def get_block_number():
    """Get latest block number."""
    if not web3 or not web3.isConnected():
        return "Not Available"
    
    try:
        return str(web3.eth.block_number)
    except Exception as e:
        logger.error("Failed to get block number: %s", e)
        return "Error"

def get_recent_transactions():
    """Get recent transactions."""
    address_to_check = wallet_address or view_address
    
    if not web3 or not web3.isConnected() or not address_to_check:
        return "Not Available"
    
    try:
        # Basic implementation - can be expanded with more transaction data
        return "Transaction data can be integrated with Etherscan API or local transaction tracking."
    except Exception as e:
        logger.error("Failed to get transactions: %s", e)
        return "Error"

def get_total_profit():
    """Get total profit."""
    # In a real implementation, this would fetch data from storage
    return "Not Tracked"

@app.route('/')
def index():
    """Render dashboard index page."""
    config = load_config()
    
    # Format uptime
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    # Get Web3 data
    wallet_balance = get_wallet_balance()
    network = get_network_name()
    gas_price = get_gas_price()
    block_number = get_block_number()
    transactions = get_recent_transactions()
    total_profit = get_total_profit()
    
    # Format wallet/view address for display
    display_address = view_address or wallet_address
    wallet_address_short = display_address[:6] + "..." + display_address[-4:] if display_address else "Not Available"
    
    # Get dynamic allocation values
    dynamic_allocation = config.get('dynamic_allocation', {})
    min_percentage = dynamic_allocation.get('min_percentage', "N/A")
    max_percentage = dynamic_allocation.get('max_percentage', "N/A")
    concurrent_trades = dynamic_allocation.get('concurrent_trades', "N/A")
    reserve_percentage = dynamic_allocation.get('reserve_percentage', "N/A")
    
    # Set status based on Web3 connection
    status = "Running" if web3 and web3.isConnected() else "Not Connected"
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        status=status,
        uptime=uptime,
        wallet_balance=wallet_balance,
        total_profit=total_profit,
        min_percentage=min_percentage,
        max_percentage=max_percentage,
        concurrent_trades=concurrent_trades,
        reserve_percentage=reserve_percentage,
        config_json=json.dumps(config, indent=2),
        current_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        network=network,
        gas_price=gas_price,
        block_number=block_number,
        wallet_address_short=wallet_address_short,
        transactions=transactions,
        error_message=error_message,
        info_message=info_message,
        debug_info=debug_info
    )

@app.route('/api/status')
def api_status():
    """API endpoint for dashboard status."""
    # Format uptime
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    # Get Web3 data
    wallet_balance = get_wallet_balance()
    network = get_network_name()
    gas_price = get_gas_price()
    block_number = get_block_number()
    transactions = get_recent_transactions()
    total_profit = get_total_profit()
    
    # Format wallet/view address for display
    display_address = view_address or wallet_address
    wallet_address_short = display_address[:6] + "..." + display_address[-4:] if display_address else "Not Available"
    
    # Set status based on Web3 connection
    status = "Running" if web3 and web3.isConnected() else "Not Connected"
    
    return jsonify({
        'status': status,
        'uptime': uptime,
        'wallet_balance': wallet_balance,
        'total_profit': total_profit,
        'transactions': transactions,
        'current_time': time.strftime("%Y-%m-%d %H:%M:%S"),
        'network': network,
        'gas_price': gas_price,
        'block_number': block_number,
        'wallet_address_short': wallet_address_short,
        'error_message': error_message,
        'info_message': info_message,
        'debug_info': debug_info
    })

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the minimal arbitrage system dashboard")
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="Host to run the dashboard on (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=5000, 
        help="Port to run the dashboard on (default: 5000)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Run in debug mode"
    )
    return parser.parse_args()

def main():
    """Start the dashboard server."""
    global start_time
    start_time = time.time()  # Reset start time on each run
    
    args = parse_arguments()
    
    try:
        logger.info("=" * 70)
        logger.info("STARTING ARBITRAGE SYSTEM DASHBOARD")
        logger.info("=" * 70)
        
        # Initialize Web3
        initialize_web3()
        
        # Start the dashboard
        logger.info("Starting dashboard server on %s:%s", args.host, args.port)
        logger.info("Dashboard URL: http://%s:%s", args.host, args.port)
        logger.info("Press Ctrl+C to stop the server")
        
        # Run the app
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Dashboard server stopped by user")
        return 0
    except Exception as e:
        logger.error("Error starting dashboard: %s", e, exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())