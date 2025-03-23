"""Main entry point for the dashboard application."""

import uvicorn
from .app import app

if __name__ == "__main__":
    uvicorn.run(
        "new_dashboard.dashboard.app:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )