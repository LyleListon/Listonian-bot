#!/usr/bin/env python3
"""
Dashboard entry point script.
"""

import uvicorn
from dashboard.main import app

if __name__ == "__main__":
    uvicorn.run(
        "dashboard.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="debug"
    )