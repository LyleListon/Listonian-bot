"""Run the dashboard application."""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from arbitrage_bot.dashboard.app import create_app
from arbitrage_bot.dashboard.websocket_server import WebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_websocket_server(socketio, ws_server):
    """Run WebSocket server."""
    await ws_server.start()

def main():
    """Run the dashboard application."""
    try:
        # Create Flask app and SocketIO instance
        app, socketio = create_app()
        
        # Create WebSocket server
        ws_server = WebSocketServer(socketio)
        
        # Get port from environment or use default
        port = int(os.environ.get('DASHBOARD_PORT', 3000))
        
        logger.info(f"Starting dashboard on port {port}...")
        
        # Start WebSocket server in background task
        socketio.start_background_task(run_websocket_server, socketio, ws_server)
        
        # Run the application
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        raise

if __name__ == '__main__':
    main()
