#!/usr/bin/env python
"""Test the API server endpoints."""

import argparse
import logging
import requests
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_api")

def test_api_endpoint(host="127.0.0.1", port=8001):
    """Test the API server endpoints.

    Args:
        host: API server host.
        port: API server port.
    """
    base_url = f"http://{host}:{port}"

    # Test endpoints
    endpoints = [
        "/api/v1/status",
        "/api/status",  # Try both versions
        "/status",      # Try direct endpoint
    ]

    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        logger.info(f"Testing endpoint: {url}")

        try:
            response = requests.get(url, timeout=5)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}...")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to {url}: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test API server endpoints")
    parser.add_argument("--host", default="127.0.0.1", help="API server host")
    parser.add_argument("--port", type=int, default=8001, help="API server port")
    args = parser.parse_args()

    test_api_endpoint(args.host, args.port)

if __name__ == "__main__":
    main()
