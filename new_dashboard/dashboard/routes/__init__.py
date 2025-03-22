"""API routes for the dashboard."""

from fastapi import APIRouter

from .metrics import router as metrics_router
from .system import router as system_router
from .websocket import router as websocket_router

# Create a combined router for all API routes
api_router = APIRouter()

# Include all route modules
api_router.include_router(metrics_router, prefix="/api/metrics", tags=["metrics"])
api_router.include_router(system_router, prefix="/api/system", tags=["system"])

# Export all routers
__all__ = [
    'api_router',
    'metrics_router',
    'system_router',
    'websocket_router'
]
