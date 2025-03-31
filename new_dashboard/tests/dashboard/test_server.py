"""Test server for verifying dashboard functionality."""

import os
from pathlib import Path

# Ensure we're in the correct directory
os.chdir(Path(__file__).parent)

def main():
    """Start the test server."""
    print("Starting test server on http://localhost:9050")
    print("Visit http://localhost:9050/test to view the test page")
    
    import uvicorn
    uvicorn.run(
        "dashboard.app:app",  # Import string for the application
        host="0.0.0.0",
        port=9050,
        log_level="info",
        reload=True,  # Enable auto-reload for development
        reload_dirs=[str(Path(__file__).parent)]  # Watch dashboard directory
    )

if __name__ == "__main__":
    main()