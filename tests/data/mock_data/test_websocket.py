import eventlet
eventlet.monkey_patch()

import os
import sys
from flask import Flask, send_file
from flask_socketio import SocketIO
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@app.route('/')
def index():
    return send_file('test_websocket.html')

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    # Send test data
    socketio.emit('memory_update', {
        'type': 'memory_update',
        'data': {
            'memory_stats': {
                'market_data_size': 100,
                'transactions_size': 50,
                'analytics_size': 25
            }
        },
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5001))
    print(f"Starting WebSocket test server on port {port}")
    print(f"Visit http://localhost:{port} to view the test page")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)