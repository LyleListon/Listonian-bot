"""
Run DEX Discovery Example

This script runs the DEX discovery example.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from examples.dex_discovery_example import main

if __name__ == "__main__":
    asyncio.run(main())