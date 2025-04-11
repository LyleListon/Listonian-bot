"""Core error classes."""


class Web3Error(Exception):
    """Base exception class for Web3-related errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
