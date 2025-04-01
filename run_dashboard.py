#!/usr/bin/env python3
"""
Dashboard entry point script.
"""

import uvicorn
import logging
from new_dashboard import app

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable uvicorn access logging
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

if __name__ == "__main__":
    print("\n!!! --- Starting Uvicorn on host 0.0.0.0, port 9050 --- !!!\n")
    uvicorn.run(
        "new_dashboard.dashboard:app", # Keep this format for direct execution
        host="0.0.0.0",
        port=9050,
        reload=False,
        log_level="debug",
        access_log=False,
        use_colors=False
    )