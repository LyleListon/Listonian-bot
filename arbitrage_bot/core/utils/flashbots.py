"""Flashbots utility functions."""

import logging
from typing import Dict, Any, List, Optional
from eth_typing import HexStr
# from web3 import Web3 # Unused

logger = logging.getLogger(__name__)


def encode_bundle_data(tx_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encode transaction data for Flashbots bundle.

    Args:
        tx_data: Transaction data including signed transaction

    Returns:
        Dict[str, Any]: Encoded bundle data
    """
    try:
        return {
            "signedTransaction": (
                tx_data["signed_transaction"].hex()
                if isinstance(tx_data["signed_transaction"], bytes)
                else tx_data["signed_transaction"]
            )
        }
    except Exception as e:
        logger.error(f"Failed to encode bundle data: {e}")
        return None


async def simulate_bundle(
    flashbots_client: Any, bundle: List[Dict[str, Any]], block_number: int
) -> Optional[Dict[str, Any]]:
    """
    Simulate a Flashbots bundle.

    Args:
        flashbots_client: Flashbots client instance
        bundle: List of transactions in the bundle
        block_number: Target block number

    Returns:
        Optional[Dict[str, Any]]: Simulation results
    """
    try:
        # Encode bundle transactions
        encoded_bundle = [
            encode_bundle_data(tx) for tx in bundle if encode_bundle_data(tx)
        ]

        if not encoded_bundle:
            logger.error("No valid transactions in bundle")
            return None

        # Simulate bundle
        simulation = await flashbots_client.simulate(
            encoded_bundle, block_number=block_number
        )

        # Check simulation results
        if simulation.get("error"):
            logger.error(f"Bundle simulation failed: {simulation['error']}")
            return None

        return {"success": True, "results": simulation}

    except Exception as e:
        logger.error(f"Bundle simulation failed: {e}")
        return None


async def submit_bundle(
    flashbots_client: Any, bundle: List[Dict[str, Any]], target_block: int
) -> Optional[HexStr]:
    """
    Submit a bundle to Flashbots.

    Args:
        flashbots_client: Flashbots client instance
        bundle: List of transactions in the bundle
        target_block: Target block number

    Returns:
        Optional[HexStr]: Bundle hash if successful
    """
    try:
        # Encode bundle transactions
        encoded_bundle = [
            encode_bundle_data(tx) for tx in bundle if encode_bundle_data(tx)
        ]

        if not encoded_bundle:
            logger.error("No valid transactions in bundle")
            return None

        # Submit bundle
        bundle_hash = await flashbots_client.send_bundle(
            encoded_bundle, target_block_number=target_block
        )

        return bundle_hash

    except Exception as e:
        logger.error(f"Bundle submission failed: {e}")
        return None


async def get_optimal_gas_params(
    web3_manager: Any, min_priority_fee: float, max_priority_fee: float
) -> Optional[Dict[str, int]]:
    """
    Get optimal gas parameters based on network conditions.

    Args:
        web3_manager: Web3Manager instance
        min_priority_fee: Minimum priority fee in GWEI
        max_priority_fee: Maximum priority fee in GWEI

    Returns:
        Optional[Dict[str, int]]: Gas parameters in WEI
    """
    try:
        # Get base fee from latest block
        latest_block = await web3_manager.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]

        # Get network congestion from market analysis
        market_conditions = await web3_manager.use_mcp_tool(
            "market-analysis",
            "assess_market_conditions",
            {"metrics": ["network_congestion"]},
        )

        congestion = market_conditions["metrics"]["network_congestion"]

        # Calculate priority fee based on congestion
        if congestion > 0.8:  # High congestion
            priority_fee = max_priority_fee
        elif congestion > 0.5:  # Medium congestion
            priority_fee = (min_priority_fee + max_priority_fee) / 2
        else:  # Low congestion
            priority_fee = min_priority_fee

        priority_fee_wei = int(priority_fee * 10**9)  # Convert to wei
        max_fee_wei = base_fee + priority_fee_wei

        return {"maxFeePerGas": max_fee_wei, "maxPriorityFeePerGas": priority_fee_wei}

    except Exception as e:
        logger.error(f"Failed to get optimal gas params: {e}")
        return None
