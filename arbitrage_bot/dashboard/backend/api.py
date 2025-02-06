"""FastAPI backend for arbitrage monitoring dashboard."""

import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
import json
from dataclasses import asdict

from ...core.arbitrage.detector import AggressiveArbitrageDetector
from ...core.ml.models.manager import ModelManager
from ...core.data_collection.coordinator import DataCollectionCoordinator

app = FastAPI(title="Arbitrage Dashboard API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global references
detector: Optional[AggressiveArbitrageDetector] = None
model_manager: Optional[ModelManager] = None
data_coordinator: Optional[DataCollectionCoordinator] = None
active_websockets: List[WebSocket] = []

async def broadcast_updates():
    """Broadcast updates to all connected clients."""
    while True:
        try:
            if detector and active_websockets:
                # Get current state
                update = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'detector': await get_detector_status(),
                    'predictions': await get_predictions(),
                    'performance': await get_performance_metrics()
                }
                
                # Broadcast to all clients
                for websocket in active_websockets:
                    try:
                        await websocket.send_json(update)
                    except Exception as e:
                        logging.error(f"Error sending to websocket: {e}")
                        active_websockets.remove(websocket)
                        
            await asyncio.sleep(1)  # Update every second
            
        except Exception as e:
            logging.error(f"Error in broadcast loop: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Start broadcast task on startup."""
    asyncio.create_task(broadcast_updates())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        active_websockets.remove(websocket)

@app.get("/api/status")
async def get_detector_status() -> Dict[str, Any]:
    """Get current detector status."""
    if not detector:
        return {"error": "Detector not initialized"}
        
    status = detector.get_status()
    
    # Format opportunities
    opportunities = []
    for opp in detector.opportunities:
        opportunities.append({
            'path': opp.path,
            'expected_profit': float(opp.expected_profit),
            'confidence': float(opp.confidence),
            'gas_cost': float(opp.gas_cost),
            'position_size': float(opp.position_size),
            'risk_score': float(opp.risk_score),
            'timestamp': opp.timestamp.isoformat()
        })
        
    return {
        'opportunities': opportunities,
        'active_trades': len(detector.active_trades),
        'performance': status['performance'],
        'risk_metrics': status['risk_metrics']
    }

@app.get("/api/predictions")
async def get_predictions() -> Dict[str, Any]:
    """Get current ML predictions."""
    if not model_manager:
        return {"error": "Model manager not initialized"}
        
    try:
        # Get predictions
        gas_prediction = await model_manager.predict_gas_price()
        liquidity_prediction = await model_manager.predict_liquidity()
        
        return {
            'gas': {
                'price': float(gas_prediction['predicted_price']),
                'uncertainty': float(gas_prediction['uncertainty']),
                'confidence': float(gas_prediction['confidence'])
            },
            'liquidity': {
                'total': float(liquidity_prediction['liquidity']['total']),
                'volume': float(liquidity_prediction['liquidity']['volume']),
                'impact': float(liquidity_prediction['liquidity']['impact']),
                'uncertainty': float(liquidity_prediction['uncertainty']),
                'confidence': float(liquidity_prediction['confidence'])
            }
        }
        
    except Exception as e:
        logging.error(f"Error getting predictions: {e}")
        return {"error": str(e)}

@app.get("/api/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get detailed performance metrics."""
    if not detector:
        return {"error": "Detector not initialized"}
        
    try:
        stats = detector.performance_stats
        risk_metrics = detector.get_status()['risk_metrics']
        
        return {
            'trades': {
                'total': stats['trades_executed'],
                'successful': stats['successful_trades'],
                'win_rate': stats['successful_trades'] / max(stats['trades_executed'], 1),
                'average_profit': stats['total_profit'] / max(stats['trades_executed'], 1)
            },
            'profit_loss': {
                'total_profit': float(stats['total_profit']),
                'total_loss': float(stats['total_loss']),
                'net_profit': float(stats['total_profit'] - stats['total_loss'])
            },
            'risk': {
                'drawdown': float(risk_metrics['drawdown']),
                'exposure': float(risk_metrics['exposure']),
                'sharpe_ratio': float(risk_metrics['sharpe_ratio']),
                'volatility': float(risk_metrics['volatility'])
            }
        }
        
    except Exception as e:
        logging.error(f"Error getting performance metrics: {e}")
        return {"error": str(e)}

@app.get("/api/historical/{metric}")
async def get_historical_data(
    metric: str,
    hours: int = 24
) -> Dict[str, Any]:
    """Get historical data for specified metric."""
    if not data_coordinator:
        return {"error": "Data coordinator not initialized"}
        
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get historical data
        data = await data_coordinator.get_recent_data(
            collector='all',
            minutes=hours * 60
        )
        
        # Format response based on metric
        if metric == 'gas_price':
            return {
                'timestamps': [d['timestamp'] for d in data],
                'values': [d.get('base_fee', 0) for d in data]
            }
        elif metric == 'liquidity':
            return {
                'timestamps': [d['timestamp'] for d in data],
                'values': [d.get('liquidity', {}).get('total', 0) for d in data]
            }
        else:
            return {"error": f"Unknown metric: {metric}"}
            
    except Exception as e:
        logging.error(f"Error getting historical data: {e}")
        return {"error": str(e)}

@app.post("/api/initialize")
async def initialize_components(
    detector_instance: AggressiveArbitrageDetector,
    model_manager_instance: ModelManager,
    data_coordinator_instance: DataCollectionCoordinator
):
    """Initialize dashboard with system components."""
    global detector, model_manager, data_coordinator
    
    detector = detector_instance
    model_manager = model_manager_instance
    data_coordinator = data_coordinator_instance
    
    return {"status": "initialized"}

@app.get("/api/system/health")
async def get_system_health() -> Dict[str, Any]:
    """Get system health metrics."""
    return {
        'detector': detector is not None,
        'model_manager': model_manager is not None,
        'data_coordinator': data_coordinator is not None,
        'websocket_connections': len(active_websockets),
        'timestamp': datetime.utcnow().isoformat()
    }