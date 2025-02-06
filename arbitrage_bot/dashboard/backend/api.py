from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import random  # For demo data, remove in production
from .auth import auth_manager, get_current_user

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                await self.disconnect(connection)

manager = ConnectionManager()

# Demo data generators (replace with real data in production)
async def generate_predictions():
    return {
        "type": "predictions",
        "predictions": [
            {
                "gasPrice": random.randint(30, 100),
                "confidence": random.random(),
                "probability": random.random(),
                "timestamp": datetime.now().timestamp() * 1000
            }
            for _ in range(3)
        ],
        "timestamp": datetime.now().timestamp() * 1000
    }

async def generate_performance():
    return {
        "type": "performance",
        "performance": [
            {
                "profit": random.uniform(0.1, 1.0),
                "trades": random.randint(10, 100),
                "successRate": random.uniform(70, 95),
                "gasUsed": random.uniform(0.1, 0.5),
                "timestamp": (datetime.now().timestamp() - i * 300) * 1000  # 5-minute intervals
            }
            for i in range(12)  # Last hour of data
        ],
        "timestamp": datetime.now().timestamp() * 1000
    }

async def generate_opportunity():
    tokens = ["WETH", "USDC", "USDT", "DAI", "WBTC"]
    return {
        "type": "opportunity",
        "profit": str(random.uniform(0.001, 0.1)),
        "tokenIn": random.choice(tokens),
        "tokenOut": random.choice(tokens),
        "route": [random.choice(tokens) for _ in range(3)],
        "estimatedGas": random.randint(100000, 500000),
        "timestamp": datetime.now().timestamp() * 1000
    }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send predictions every 5 seconds
            predictions = await generate_predictions()
            await websocket.send_json(predictions)
            await asyncio.sleep(5)

            # Send performance data every 5 seconds
            performance = await generate_performance()
            await websocket.send_json(performance)
            await asyncio.sleep(5)

            # Randomly send opportunities (20% chance every 5 seconds)
            if random.random() < 0.2:
                opportunity = await generate_opportunity()
                await websocket.send_json(opportunity)

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# REST endpoints
@app.get("/api/status")
async def get_status(user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "status": "running",
        "connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/predictions/latest")
async def get_latest_predictions(user: Dict[str, Any] = Depends(get_current_user)):
    predictions = await generate_predictions()
    return predictions

@app.get("/api/performance/summary")
async def get_performance_summary(user: Dict[str, Any] = Depends(get_current_user)):
    performance = await generate_performance()
    return performance

# Initialize auth routes
auth_manager.init_oauth_routes(app)