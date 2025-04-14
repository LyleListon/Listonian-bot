#!/usr/bin/env python
"""Test the dashboard server."""

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
logger = logging.getLogger("test_dashboard")

def test_dashboard(host="127.0.0.1", port=8081):
    """Test the dashboard server.

    Args:
        host: Dashboard server host.
        port: Dashboard server port.
    """
    base_url = f"http://{host}:{port}"

    # Test endpoints
    endpoints = [
        "/",
        "/index.html",
        "/css/styles.css",
        "/js/app.js",
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
    parser = argparse.ArgumentParser(description="Test dashboard server")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard server host")
    parser.add_argument("--port", type=int, default=8081, help="Dashboard server port")
    args = parser.parse_args()

    test_dashboard(args.host, args.port)

if __name__ == "__main__":
    main()
