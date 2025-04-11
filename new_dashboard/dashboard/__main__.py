"""Main entry point for the dashboard application."""

import uvicorn
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run the dashboard application."""
    try:
        logger.info("Starting dashboard...")

        # Run the dashboard
        uvicorn.run(
            "new_dashboard.dashboard:create_app()",
            factory=True,
            host="0.0.0.0",
            port=9050,
            reload=False,
            log_level="info",
            access_log=True,
            lifespan="on",
        )
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
