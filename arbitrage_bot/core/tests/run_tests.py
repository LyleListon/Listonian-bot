"""Test runner script for arbitrage bot."""

import os
import sys
import pytest
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def run_tests():
    """Run test suite."""
    try:
        # Get project root directory
        test_dir = Path(__file__).parent
        project_root = test_dir.parent.parent.parent  # Go up to project root
        
        # Change to project root
        os.chdir(project_root)
        
        # Add project root to Python path
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Run pytest
        args = [
            str(test_dir),  # Test directory
            "-v",  # Verbose output
            "--capture=no",  # Show print statements
            "-p", "no:warnings",  # Disable warning capture
            "--asyncio-mode=auto",  # Enable asyncio mode
            "--import-mode=importlib",  # Use importlib for imports
        ]

        # Add coverage if available
        try:
            import pytest_cov
            args.extend([
                "--cov=arbitrage_bot",
                "--cov-report=term-missing",
                "--cov-report=html:coverage_html"
            ])
        except ImportError:
            logger.warning("pytest-cov not installed, skipping coverage report")

        logger.info(f"Running tests from {project_root}")
        logger.info(f"Test directory: {test_dir}")
        logger.info(f"Python path: {sys.path[0]}")
        
        result = pytest.main(args)

        if result == 0:
            logger.info("All tests passed!")
        else:
            logger.error("Some tests failed!")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
