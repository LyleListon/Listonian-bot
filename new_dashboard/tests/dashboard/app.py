 import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime

from flask import Flask, render_template
from flask_socketio import SocketIO

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'listonian-arbitrage-bot'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables for mock data
start_time = time.time()
mock_metrics = {
    'gas_price': 25.0,
    'network_status': 'Connected',
    'uptime': 0,
    'performance': {
        'scan_time': 120,
        'cpu_usage': 15.0,
        'memory_usage': 256.0
    }
}

mock_trade_history = []
price_data = {
    'baseswap_v3': 42495201.744674,
    'uniswap_v3': 42498123.123456,
    'sushiswap_v2': 42490567.891234
}

# Routes
@app.route('/')
def index():
    return render_template('test.html')

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    # Start the background task to send updates
    socketio.start_background_task(target=send_updates)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

# Background task to send updates
def send_updates():
    """Send periodic updates to connected clients."""
    while True:
        # Update mock data
        update_mock_data()
        
        # Prepare data to send
        data = {
            'trade_history': mock_trade_history,
            'metrics': mock_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send data to clients
        socketio.emit('update', json.dumps(data))
        
        # Log the update
        logger.debug(f"Sent update: {datetime.now().isoformat()}")
        
        # Wait before sending the next update
        socketio.sleep(1)

def update_mock_data():
    """Update mock data for testing."""
    global mock_metrics, mock_trade_history, price_data, start_time
    
    # Update uptime
    mock_metrics['uptime'] = int(time.time() - start_time)
    
    # Randomly update gas price
    if random.random() < 0.1:
        mock_metrics['gas_price'] = round(random.uniform(20.0, 30.0), 1)
    
    # Randomly update performance metrics
    mock_metrics['performance']['scan_time'] = random.randint(100, 150)
    mock_metrics['performance']['cpu_usage'] = round(random.uniform(10.0, 25.0), 1)
    mock_metrics['performance']['memory_usage'] = round(random.uniform(200.0, 300.0), 1)
    
    # Randomly update price data
    for dex in price_data:
        if random.random() < 0.2:
            old_price = price_data[dex]
            # Small random change
            price_data[dex] += random.uniform(-500, 500)
            logger.debug(f"Received price update event (not processed): {{'dex': '{dex}', 'old_price': {old_price}, 'new_price': {price_data[dex]}}}")
    
    # Randomly add a new trade (5% chance)
    if random.random() < 0.05:
        new_trade = generate_mock_trade()
        mock_trade_history.append(new_trade)
        # Keep only the last 20 trades
        if len(mock_trade_history) > 20:
            mock_trade_history.pop(0)

def generate_mock_trade():
    """Generate a mock trade for testing."""
    dexes = ['Uniswap V3', 'SushiSwap V2', 'BaseSwap V3']
    tokens = ['WETH', 'USDC', 'USDT', 'DAI', 'WBTC']
    
    # Generate random path
    start_token = random.choice(tokens)
    mid_token = random.choice([t for t in tokens if t != start_token])
    end_token = start_token
    
    start_dex = random.choice(dexes)
    end_dex = random.choice([d for d in dexes if d != start_dex])
    
    path = f"{start_token} ({start_dex}) → {mid_token} → {end_token} ({end_dex})"
    
    # Generate random profit values
    profit = round(random.uniform(0.01, 0.5), 4)
    gas_used = random.randint(150000, 300000)
    gas_price = round(random.uniform(20.0, 30.0), 1)
    gas_cost_usd = round(gas_used * gas_price * 0.000000001 * 2000, 4)  # Assuming ETH price of $2000
    net_profit = round(profit - gas_cost_usd, 4)
    
    return {
        'timestamp': int(time.time()),
        'path': path,
        'profit': profit,
        'gas_used': gas_used,
        'gas_price': gas_price,
        'gas_cost_usd': gas_cost_usd,
        'net_profit': net_profit
    }

if __name__ == '__main__':
    # Create static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Start the Socket.IO server
    socketio.run(app, host='0.0.0.0', port=9052, debug=True)