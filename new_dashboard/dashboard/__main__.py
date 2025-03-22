"""Main entry point for the dashboard application."""

import uvicorn
import os
from pathlib import Path

def main():
    """Run the dashboard application."""
    # Ensure we're in the correct directory
    os.chdir(Path(__file__).parent.parent)
    
    # Run the FastAPI application
    uvicorn.run(
        "dashboard.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
        log_level="info"
    )

if __name__ == "__main__":
    main()