"""DEX utility functions"""

import logging
from typing import List, Tuple, Optional
from eth_abi import decode

logger = logging.getLogger(__name__)


def encode_path_for_pancake(token_in: str, token_out: str, fee: int) -> bytes:
    """Encode path for PancakeSwap v3"""
    try:
        # Remove '0x' prefix if present
        token_in = token_in[2:] if token_in.startswith("0x") else token_in
        token_out = token_out[2:] if token_out.startswith("0x") else token_out

        # Convert fee to hex and pad to 3 bytes
        fee_hex = hex(fee)[2:].zfill(6)

        # Concatenate path: <token_in><fee><token_out>
        # Each address is 20 bytes, fee is 3 bytes
        path = token_in + fee_hex + token_out

        # Add '0x' prefix and return
        return bytes.fromhex(path)

    except Exception as e:
        logger.error(f"Error encoding path: {str(e)}")
        raise


def decode_quote_result(result: bytes) -> Optional[int]:
    """Decode quote result from PancakeSwap v3"""
    try:
        # Decode result tuple (uint256 amountOut, uint160[] sqrtPriceX96AfterList, uint32[] initializedTicksCrossedList, uint256 gasEstimate)
        decoded = decode(["uint256", "uint160[]", "uint32[]", "uint256"], result)

        # Return just the amountOut (first element)
        return decoded[0] if decoded else None

    except Exception as e:
        logger.error(f"Error decoding quote result: {str(e)}")
        return None
