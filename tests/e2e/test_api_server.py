"""End-to-end tests for the API server."""

import os
import time
import subprocess
import signal
import requests
import pytest
from pathlib import Path


@pytest.fixture(scope="module")
def api_server():
    """Start the API server for testing."""
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent.parent
    
    # Set environment variables
    env = os.environ.copy()
    env["ENVIRONMENT"] = "test"
    
    # Start the API server
    process = subprocess.Popen(
        ["python", "bot_api_server.py", "--port", "8001"],
        cwd=root_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for the server to start
    time.sleep(2)
    
    yield process
    
    # Stop the server
    process.send_signal(signal.SIGTERM)
    process.wait()


@pytest.mark.e2e
def test_api_status_endpoint(api_server):
    """Test the status endpoint."""
    # Make a request to the status endpoint
    response = requests.get("http://localhost:8001/api/v1/status")
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "status" in data["data"]
    assert "version" in data["data"]
    assert "components" in data["data"]


@pytest.mark.e2e
def test_api_opportunities_endpoint(api_server):
    """Test the opportunities endpoint."""
    # Make a request to the opportunities endpoint
    response = requests.get(
        "http://localhost:8001/api/v1/opportunities",
        params={"min_profit": 0.1, "limit": 5},
    )
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "opportunities" in data["data"]
    assert "total_count" in data["data"]
    assert "timestamp" in data["data"]


@pytest.mark.e2e
def test_api_config_endpoint(api_server):
    """Test the config endpoint."""
    # Make a request to the config endpoint
    response = requests.get("http://localhost:8001/api/v1/config")
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "trading" in data["data"]
    assert "dexes" in data["data"]
    assert "networks" in data["data"]
    assert "mev_protection" in data["data"]
    assert "flash_loans" in data["data"]
