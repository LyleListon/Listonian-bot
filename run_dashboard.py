#!/usr/bin/env python3
"""
Dashboard entry point script.
"""

import uvicorn
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get dashboard port from environment or use default
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", 9050))

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable uvicorn access logging
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

if __name__ == "__main__":
    logger = logging.getLogger("dashboard_startup")
    logger.info(f"\n!!! --- Starting Uvicorn on host 0.0.0.0, port {DASHBOARD_PORT} --- !!!\n")
    logger.info("Attempting to start dashboard with app path: new_dashboard.dashboard:app")

    try:
        uvicorn.run(
            "new_dashboard.dashboard:app",  # Keep this format for direct execution
            host="0.0.0.0",
            port=DASHBOARD_PORT,
            reload=False,
            log_level="debug",
            access_log=False,
            use_colors=False
        )
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        raise