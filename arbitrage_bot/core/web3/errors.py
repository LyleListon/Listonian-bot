"""
Web3 Error Module

This module provides error classes for Web3 operations.
"""

from typing import Dict, Any


class Web3Error(Exception):
    """Base class for Web3 errors with context."""

    def __init__(self, message: str, error_type: str, context: Dict[str, Any]):
        self.message = message
        self.error_type = error_type
        self.context = context
        super().__init__(f"{error_type}: {message}")
