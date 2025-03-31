#!/usr/bin/env python3
"""
Run script for the advanced analytics example.

This script demonstrates how to run the advanced analytics example.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the example
from examples.advanced_analytics_example import main

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())