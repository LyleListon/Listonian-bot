"""Logging configuration for the dashboard."""

import logging
import sys
from pathlib import Path

def setup_logging(level="INFO"):
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Set up logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S%f"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler
            logging.FileHandler(str(logs_dir / "dashboard.log"))
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)