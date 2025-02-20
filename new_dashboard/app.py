from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arbitrage_bot.core.memory import create_memory_bank

from .routes import router

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)

# Get the absolute path to the static and templates directories
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get('/favicon.ico')
async def favicon():
    """Serve favicon.ico from static directory"""
    return FileResponse(str(static_dir / 'favicon.ico'))

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.memory_bank = None
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs/memory_config.json")
        logging.info(f"Using config path: {self.config_path}")

    async def initialize(self):
        """Initialize the memory bank with configuration"""
        if self.memory_bank is None:
            try:
                if not os.path.exists(self.config_path):
                    raise FileNotFoundError(f"Config file not found: {self.config_path}")
                
                with open(self.config_path) as f:
                    config = json.load(f)
                logging.info(f"Loaded config: {config}")
                
                # Set data directory path
                data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/memory")
                os.makedirs(data_dir, exist_ok=True)
                config['data_dir'] = data_dir
                logging.info(f"Using data directory: {data_dir}")
                
                self.memory_bank = await create_memory_bank(config)
                logging.info("Memory bank created")
                await self.memory_bank.initialize(config)  # Make sure to initialize
                logging.info("Memory bank initialized")
            except Exception as e:
                logging.error(f"Failed to initialize memory bank: {str(e)}", exc_info=True)
                raise
 
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection)
                
    async def broadcast_memory_updates(self):
        """Broadcast memory bank updates to all connected clients"""
        while True:
            try:
                if self.memory_bank is None:
                    await self.initialize()

                # Get latest data from memory bank
                logging.debug("Fetching data from memory bank...")
                
                logging.info(f"Memory bank instance: {self.memory_bank}")
                # Get raw data
                raw_market_data = await self.memory_bank.retrieve("status", "market_data")
                raw_transactions = await self.memory_bank.retrieve("status", "transactions")
                raw_analytics = await self.memory_bank.retrieve("status", "analytics")
                
                logging.info(f"Raw market data: {raw_market_data}")
                logging.info(f"Raw transactions data: {raw_transactions}")
                logging.info(f"Raw analytics data: {raw_analytics}")
                
                # Extract status data
                market_data = raw_market_data.get('data', {}).get('status', {}) if raw_market_data else {}
                transactions = raw_transactions.get('data', {}).get('status', {}) if raw_transactions else {}
                analytics = raw_analytics.get('data', {}).get('status', {}) if raw_analytics else {}
                
                logging.info("Processed data:")
                logging.info(f"Market data: {market_data}")
                logging.info(f"Transactions: {transactions}")
                logging.info(f"Analytics: {analytics}")
                logging.debug(f"Memory bank stats: {await self.memory_bank.get_memory_stats()}")
                
                # Format update message
                update = {
                    "type": "memory_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "market_data": market_data,
                        "transactions": transactions,
                        "analytics": analytics,
                        "memory_stats": {
                            "market_data_size": len(market_data),
                            "transactions_size": len(transactions),
                            "analytics_size": len(analytics)
                        }
                    }
                }
                
                await self.broadcast(update)
                logging.info("Data broadcast complete")
                await asyncio.sleep(1)  # Update every second
                logging.info("Sleeping before next update")
                
            except Exception as e:
                logging.error(f"Error in memory update broadcast: {str(e)}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Start memory updates task
        memory_task = asyncio.create_task(manager.broadcast_memory_updates())
        
        while True:
            try:
                # Handle incoming messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Process client messages here
                if message.get("type") == "config_update":
                    # Handle configuration updates
                    pass
                    
            except WebSocketDisconnect:
                manager.disconnect(websocket)
                memory_task.cancel()
                break
                
    except Exception as e:
        logging.error(f"Error in websocket connection: {str(e)}", exc_info=True)
        manager.disconnect(websocket)
        memory_task.cancel()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}