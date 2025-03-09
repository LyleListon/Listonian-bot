"""Memory module for storing and managing arbitrage opportunities and trade results."""

from .bank import MemoryBank, create_memory_bank
from .manager import MemoryBankManager, get_memory_bank

__all__ = [
    'MemoryBank',
    'create_memory_bank',
    'MemoryBankManager',
    'get_memory_bank',
]

# Version of the memory module
__version__ = '0.1.0'

# Module level docstring
__doc__ = """
Memory Module
============

The memory module provides functionality for storing and managing arbitrage opportunities
and trade results. It serves as a short-term memory bank for the arbitrage bot, enabling
analysis of historical data and performance tracking.

Components
---------
- MemoryBank: Main component for storing and retrieving opportunities and trade results

Example Usage
------------
```python
from arbitrage_bot.core.memory import create_memory_bank

# Create and initialize memory bank
config = {
    "max_opportunities": 1000,
    "cleanup_interval": 3600,
    "max_age": 86400
}
memory_bank = await create_memory_bank(config)

# Store opportunities
await memory_bank.store_opportunities(opportunities)

# Get statistics
stats = await memory_bank.get_statistics()
```

For more detailed documentation, see the README.md file in the memory module directory.
"""
