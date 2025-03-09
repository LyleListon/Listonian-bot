"""Provider implementations for blockchain interactions."""

from .base import BaseProvider
from .http import HttpProvider

__all__ = [
    'BaseProvider',
    'HttpProvider',
]

# Provider type mapping
PROVIDER_TYPES = {
    'http': HttpProvider,
    'https': HttpProvider,
}

def get_provider(url: str, chain_id: int, retry_count: int = 3) -> BaseProvider:
    """Get appropriate provider based on URL scheme.
    
    Args:
        url: RPC endpoint URL
        chain_id: Network chain ID
        retry_count: Number of retry attempts
        
    Returns:
        BaseProvider: Initialized provider instance
        
    Raises:
        ValueError: If URL scheme is not supported
    """
    scheme = url.split('://')[0].lower()
    provider_class = PROVIDER_TYPES.get(scheme)
    
    if not provider_class:
        raise ValueError(
            f"Unsupported URL scheme: {scheme}. "
            f"Supported schemes: {', '.join(PROVIDER_TYPES.keys())}"
        )
    
    return provider_class(url, chain_id, retry_count)