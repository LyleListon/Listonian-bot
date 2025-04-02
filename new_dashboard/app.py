eee
Re-export the FastAPI app from dashboard/app.py.

This file exists to provide a consistent import path for Uvicorn.
"""

from new_dashboard.dashboard.app import app

# Re-export the app
__all__ = ['app']