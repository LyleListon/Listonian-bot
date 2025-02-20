"""Shared utilities for DEX implementations."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from web3 import Web3

logger = logging.getLogger(__name__)

# Common token addresses across DEXs
COMMON_TOKENS = {
    'WETH': '0x4200000000000000000000000000000000000006',
    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    'DAI': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb'
}

# Gas cost estimates
GAS_COSTS = {
    'v2': {
        'base_cost': 100000,
        'hop_cost': 50000,
        'buffer': 1.1
    },
    'v3': {
        'base_cost': 150000,
        'hop_cost': 60000,
        'buffer': 1.1
    }
}

def validate_address(address: str) -> bool:
    """
    Validate Ethereum address.
    
    Args:
        address: Address to validate
        
    Returns:
        bool: True if address is valid
    """
    if not isinstance(address, str):
        return False
    if not address.startswith('0x'):
        return False
    try:
        int(address, 16)
        return len(address) == 42
    except ValueError:
        return False

def validate_config(config: Dict[str, Any], required_keys: Dict[str, type]) -> Tuple[bool, Optional[str]]:
    """
    Validate DEX configuration.
    
    Args:
        config: Configuration to validate
        required_keys: Dictionary mapping required keys to expected types
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        # Check required keys
        for key, expected_type in required_keys.items():
            if key not in config:
                return False, f"Missing required config key: {key}"
            if not isinstance(config[key], expected_type):
                return False, (
                    f"Invalid type for {key}. Expected {expected_type.__name__}, "
                    f"got {type(config[key]).__name__}"
                )

        # Validate addresses
        for key in ['router', 'factory']:
            if not validate_address(config[key]):
                return False, f"Invalid address for {key}: {config[key]}"

        # Validate fee
        if not 0 <= config['fee'] <= 10000:
            return False, f"Invalid fee: {config['fee']}. Must be between 0 and 10000"

        return True, None

    except Exception as e:
        return False, f"Validation error: {str(e)}"

def estimate_gas_cost(path: List[str], protocol: str = 'v2') -> int:
    """
    Estimate gas cost for a swap path.
    
    Args:
        path: List of token addresses in the swap path
        protocol: DEX protocol ('v2' or 'v3')
        
    Returns:
        int: Estimated gas cost in wei
    """
    costs = GAS_COSTS[protocol]
    base_cost = costs['base_cost']
    hop_cost = costs['hop_cost']
    buffer = costs['buffer']
    
    # Calculate total cost based on path length
    total_cost = base_cost + (hop_cost * (len(path) - 1))
    
    # Add buffer for safety
    return int(total_cost * buffer)

def calculate_price_impact(
    amount_in: int,
    amount_out: int,
    reserve_in: int,
    reserve_out: int,
    sqrt_price_x96: Optional[int] = None
) -> float:
    """
    Calculate price impact for a trade.
    
    Args:
        amount_in: Input amount in wei
        amount_out: Output amount in wei
        reserve_in: Input token reserve
        reserve_out: Output token reserve
        sqrt_price_x96: V3 sqrt price (optional)
        
    Returns:
        float: Price impact as decimal (0.01 = 1%)
    """
    try:
        # V3 calculation if sqrt_price_x96 provided
        if sqrt_price_x96 is not None:
            price = (sqrt_price_x96 ** 2) / (2 ** 192)
        # V2 calculation
        else:
            price = reserve_out / reserve_in
            
        # Calculate expected output without impact
        expected_out = amount_in * price
        
        # Calculate actual price impact
        impact = (expected_out - amount_out) / expected_out
        
        # Adjust impact based on liquidity depth
        liquidity = min(reserve_in, reserve_out)
        liquidity_factor = min(1, amount_in / liquidity)
        adjusted_impact = impact * liquidity_factor
        
        return float(adjusted_impact)
        
    except Exception as e:
        logger.error(f"Failed to calculate price impact: {e}")
        return 1.0  # Return 100% impact on error (will prevent trade)

def encode_path_for_v3(path: List[str], fee: int) -> bytes:
    """
    Encode path with fees for V3 swap.
    
    Args:
        path: List of token addresses
        fee: Fee in basis points
        
    Returns:
        bytes: Encoded path
    """
    encoded = b''
    for i in range(len(path) - 1):
        encoded += bytes.fromhex(path[i][2:])  # Remove '0x' prefix
        encoded += fee.to_bytes(3, 'big')  # Add fee as 3 bytes
    encoded += bytes.fromhex(path[-1][2:])  # Add final token
    return encoded

def format_amount_with_decimals(amount: int, decimals: int) -> Decimal:
    """
    Format raw amount with decimals.
    
    Args:
        amount: Raw amount in wei
        decimals: Number of decimals
        
    Returns:
        Decimal: Formatted amount
    """
    return Decimal(amount) / Decimal(10 ** decimals)

def get_common_base_tokens() -> List[str]:
    """Get list of common base tokens for routing."""
    return [
        COMMON_TOKENS['WETH'],
        COMMON_TOKENS['USDC'],
        COMMON_TOKENS['DAI']
    ]
