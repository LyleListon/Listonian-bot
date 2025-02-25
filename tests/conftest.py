"""Pytest configuration for arbitrage bot tests."""

import os
import sys
from pathlib import Path
import pytest
import asyncio

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "flashbots: mark test as requiring Flashbots"
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create and configure event loop."""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Set default event loop scope
def pytest_addoption(parser):
    parser.addini(
        'asyncio_default_fixture_loop_scope',
        'default scope for event loop fixture',
        default='function'
    )
