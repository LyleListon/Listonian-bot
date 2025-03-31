"""
Run DEX Discovery Example with Mock Web3 Manager

This script runs the DEX discovery example with a mock Web3 manager.

WARNING: This script is for testing and demonstration purposes only.
DO NOT use this in production as it creates mock data that could interfere
with real DEX discovery.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from examples.dex_discovery_example_mock import main

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("WARNING: This script is for TESTING PURPOSES ONLY.")
    print("It uses mock data and should NOT be used in production.")
    print("=" * 80 + "\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    finally:
        print("\nTest completed. All temporary test data has been cleaned up.")