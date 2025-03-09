"""Utility functions for DEX contract interactions."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from web3.contract import Contract
from web3.types import ChecksumAddress

from ...blockchain import Web3Manager

logger = logging.getLogger(__name__)

# ABI cache to avoid repeated file reads
_abi_cache: Dict[str, Dict[str, Any]] = {}


def load_abi(name: str) -> Dict[str, Any]:
    """Load ABI from file.
    
    Args:
        name: Name of ABI file (without .json extension)
        
    Returns:
        Parsed ABI dictionary
        
    Raises:
        FileNotFoundError: If ABI file doesn't exist
        JSONDecodeError: If ABI file is invalid
    """
    if name in _abi_cache:
        return _abi_cache[name]

    # Look in standard locations
    paths = [
        Path(f"abi/{name}.json"),
        Path(f"src/core/dex/abis/{name}.json"),
        Path(f"contracts/abis/{name}.json")
    ]
    
    for path in paths:
        if path.exists():
            try:
                with open(path) as f:
                    abi = json.load(f)
                _abi_cache[name] = abi
                return abi
            except json.JSONDecodeError as e:
                logger.error(f"Invalid ABI file {path}: {e}")
                raise
                
    raise FileNotFoundError(
        f"ABI file not found for {name}. "
        f"Searched paths: {', '.join(str(p) for p in paths)}"
    )


def get_contract(
    web3: Web3Manager,
    address: ChecksumAddress,
    name: str
) -> Contract:
    """Get contract instance with caching.
    
    Args:
        web3: Web3 manager instance
        address: Contract address
        name: Contract name for ABI lookup
        
    Returns:
        Contract instance
        
    Raises:
        FileNotFoundError: If ABI file doesn't exist
        ValueError: If contract creation fails
    """
    try:
        abi = load_abi(name)
        return web3.provider.web3.eth.contract(
            address=address,
            abi=abi
        )
    except Exception as e:
        logger.error(f"Failed to create contract {name} at {address}: {e}")
        raise ValueError(f"Contract creation failed: {e}")


async def verify_contract(
    web3: Web3Manager,
    address: ChecksumAddress,
    name: str,
    expected_methods: Optional[list] = None
) -> bool:
    """Verify contract exists and has expected methods.
    
    Args:
        web3: Web3 manager instance
        address: Contract address
        name: Contract name for ABI lookup
        expected_methods: List of method names to verify
        
    Returns:
        True if contract is valid
        
    Raises:
        ValueError: If contract verification fails
    """
    try:
        # Check contract exists
        code = await web3.provider.web3.eth.get_code(address)
        if code == b'':
            raise ValueError(f"No contract at address {address}")
            
        # Get contract
        contract = get_contract(web3, address, name)
        
        # Verify methods if specified
        if expected_methods:
            for method in expected_methods:
                if not hasattr(contract.functions, method):
                    raise ValueError(
                        f"Contract missing required method: {method}"
                    )
                    
        return True
        
    except Exception as e:
        logger.error(f"Contract verification failed: {e}")
        raise ValueError(f"Invalid contract: {e}")


def encode_path(
    *addresses: ChecksumAddress,
    fees: Optional[list] = None
) -> bytes:
    """Encode path for router contracts.
    
    Args:
        *addresses: Token addresses in path
        fees: Optional list of fees between tokens
        
    Returns:
        Encoded path bytes
        
    Example:
        encode_path(token0, token1, fees=[3000])
        encode_path(token0, token1, token2, fees=[3000, 500])
    """
    if not addresses:
        raise ValueError("No addresses provided")
        
    if fees and len(fees) != len(addresses) - 1:
        raise ValueError(
            f"Expected {len(addresses)-1} fees, got {len(fees)}"
        )
        
    if not fees:
        # Simple path encoding
        return b''.join(addr.encode() for addr in addresses)
        
    # Encode path with fees
    path = b''
    for i, addr in enumerate(addresses):
        path += addr.encode()
        if i < len(fees):
            # Encode fee as 3 bytes
            fee_bytes = fees[i].to_bytes(3, 'big')
            path += fee_bytes
            
    return path