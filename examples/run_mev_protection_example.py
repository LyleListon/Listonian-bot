#!/usr/bin/env python3
"""
Runner script for the MEV protection example.
"""

import asyncio
import logging
from examples.mev_protection_example import demonstrate_mev_protection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        print("Running MEV Protection Example...")
        print("=================================")
        print("This example demonstrates how to use MEV protection mechanisms")
        print("to protect arbitrage transactions from front-running and sandwich attacks.")
        print()
        
        # Run the demonstration
        asyncio.run(demonstrate_mev_protection())
        
        print()
        print("MEV Protection Example completed successfully!")
        
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        print(f"\nExample failed: {e}")