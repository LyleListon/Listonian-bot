"""
Flashbots Provider Module

This module provides functionality for:
- Flashbots RPC integration
- Bundle submission
- Bundle simulation
- MEV protection
"""

import logging
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, NamedTuple
from eth_account import Account
import binascii
from eth_typing import ChecksumAddress, HexStr
from web3 import Web3
from decimal import Decimal

from ....utils.async_manager import with_retry, AsyncLock
from ..interfaces import Transaction, TransactionReceipt

logger = logging.getLogger(__name__)

class GasEstimate(NamedTuple):
    """Gas price estimate with context."""
    price: int
    base_fee: int
    priority_fee: int
    timestamp: int

class BundleStats(NamedTuple):
    """Statistics for bundle execution."""
    success_rate: float
    avg_profit: int
    total_attempts: int

def standardize_private_key(key: str, key_name: str = "auth_key") -> str:
    """
    Standardize private key format to 0x-prefixed 32-byte hex.

    Args:
        key: Private key in various formats
        key_name: Name of the key for logging

    Returns:
        Standardized key in 0x-prefixed format

    Raises:
        ValueError: If key format is invalid
    """
    try:
        # Strip whitespace and 0x prefix if present
        cleaned_key = key.strip()
        if cleaned_key.startswith('0x'):
            cleaned_key = cleaned_key[2:]

        # Validate hex format
        if len(cleaned_key) != 64 or not all(c in '0123456789abcdefABCDEF' for c in cleaned_key):
            raise ValueError(f"Invalid hex format for {key_name}")

        # Return standardized format
        return f"0x{cleaned_key.lower()}"
    except Exception as e:
        logger.error(f"Failed to standardize {key_name}: {e}")
        raise ValueError(f"Invalid private key format for {key_name}") from e


class FlashbotsProvider:
    """Provides Flashbots integration functionality."""

    def __init__(
        self,
        w3: Web3,
        relay_url: str,
        auth_key: Optional[str] = None,
        chain_id: int = 8453  # Base mainnet
    ):
        """
        Initialize Flashbots provider.

        Args:
            w3: Web3 instance
            relay_url: Flashbots relay URL
            auth_key: Optional authentication key
            chain_id: Chain ID
        """
        self.w3 = w3
        self.relay_url = relay_url.rstrip('/')  # Ensure no trailing slash
        self.chain_id = chain_id

        # Set up authentication
        self.auth_signer = None
        if auth_key:
            # Handle secure reference
            raw_key = auth_key
            if auth_key.startswith('$SECURE:'):
                from arbitrage_bot.utils.secure_env import SecureEnvironment
                secure_env = SecureEnvironment()
                # Get raw private key without re-encrypting
                raw_key = secure_env.secure_load(auth_key[8:])  # Remove '$SECURE:' prefix
                if not raw_key:
                    raise ValueError(f"Failed to load auth key from secure storage")
            auth_key = standardize_private_key(raw_key, "auth_key")
            self.auth_signer = Account.from_key(auth_key)

        # Initialize locks for thread safety
        self._simulation_lock = AsyncLock()
        self._bundle_lock = AsyncLock()
        self._gas_cache_lock = AsyncLock()

        # Bundle optimization settings
        self.max_simulations = 5
        self.min_profit = Web3.to_wei(0.01, 'ether')  # 0.01 ETH minimum profit
        self.max_gas_price = Web3.to_wei(500, 'gwei')  # 500 gwei max gas price

        # Cache settings
        self._gas_price_cache: Dict[int, GasEstimate] = {}  # block -> estimate
        self._bundle_stats: Dict[str, BundleStats] = {}  # bundle hash prefix -> stats
        self._cache_ttl = 120  # 2 minutes

        logger.info(
            f"Flashbots provider initialized for chain {chain_id} "
            f"with auth signer {self.auth_signer.address if self.auth_signer else 'None'}"
        )

    def _get_bundle_key(self, transactions: List[Transaction]) -> str:
        """Get cache key for bundle stats."""
        tx_hashes = [tx.hash for tx in transactions]
        combined = ''.join(tx_hashes)
        return self.w3.keccak(text=combined).hex()[:10]

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _estimate_gas_price(self) -> GasEstimate:
        """Estimate optimal gas price based on recent blocks."""
        base_fee = await self.w3.eth.get_block('latest')
        priority_fee = await self.w3.eth.max_priority_fee

        async with self._gas_cache_lock:
            # Check cache
            block_number = base_fee['number']
            cached = self._gas_price_cache.get(block_number)
            if cached:
                return cached

            # Calculate new estimate
            estimate = GasEstimate(
                price=base_fee['baseFeePerGas'] + priority_fee,
                base_fee=base_fee['baseFeePerGas'],
                priority_fee=priority_fee,
                timestamp=base_fee['timestamp']
            )

            # Update cache
            self._gas_price_cache[block_number] = estimate

            # Clean old entries
            current_time = int(time.time())
            self._gas_price_cache = {
                k: v for k, v in self._gas_price_cache.items()
                if current_time - v.timestamp < self._cache_ttl
            }

            return estimate

    @with_retry(max_attempts=3, base_delay=1.0)
    async def simulate_bundle(
        self,
        transactions: List[Transaction],
 
        state_overrides: Optional[Dict[str, Any]] = None,
        block_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simulate transaction bundle.

        Args:
            transactions: List of transactions
            state_overrides: Optional state overrides for simulation
            block_number: Optional block number to simulate at

        Returns:
            Simulation results

        Raises:
            ValueError: If no transactions provided
        """
        if not transactions:
            raise ValueError("No transactions provided")

        async with self._simulation_lock:
            # Get current block if none provided
            if block_number is None:
                block_number = await self.w3.eth.block_number

            # Convert transactions to dict format
            tx_dicts = [tx.to_dict() for tx in transactions]

            # Get block info
            block = await self.w3.eth.get_block(block_number)
            block_timestamp = block["timestamp"]
            prev_block = await self.w3.eth.get_block(block_number - 1)
            base_fee = prev_block["baseFeePerGas"]

            # Add simulation parameters
            params = {
                "txs": tx_dicts,
                "blockNumber": hex(block_number),
                "timestamp": hex(block_timestamp),
                "stateBlockNumber": hex(block_number - 1),  # Use previous block state
                "gasLimit": hex(30000000),  # Block gas limit
                "coinbase": "0x0000000000000000000000000000000000000000"
,
                "baseFee": hex(base_fee),
                "extraData": "0x",
                "stateOverrides": state_overrides or {}
            }

            logger.debug(f"Simulating bundle with params: {params}")

            # Make RPC call
            response = await self.w3.eth.provider.make_request(
                "eth_callBundle",
                [{
                    "txs": params["txs"],
                    "blockNumber": params["blockNumber"],
                    "stateBlockNumber": params["stateBlockNumber"],
                    "timestamp": params["timestamp"]
                }]
            )

            # Extract result from response
            result = response.get("result")
            if not result:
                raise ValueError(f"Invalid response from Flashbots: {response}")

            # Decode and enhance result
            logger.debug(f"Raw simulation result: {result}")
            sim_result = self.w3.eth.abi.decode_abi(
                ["tuple(bool success, string error, uint256 gasUsed, uint256 effectiveGasPrice, uint256 mevValue)"],
                result
            )[0]

            return {
                "success": sim_result[0],
                "error": sim_result[1] if not sim_result[0] else "",
                "gasUsed": sim_result[2],
                "effectiveGasPrice": sim_result[3],
                "mevValue": sim_result[4],
                "baseFee": base_fee,
                "totalCost": (sim_result[2] * sim_result[3]) + (sim_result[2] * base_fee),
                "profitability": sim_result[4] - (sim_result[2] * sim_result[3])
            }

    async def _optimize_bundle(
        self,
        transactions: List[Transaction],
        target_block: Optional[int] = None,
        state_overrides: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Transaction], Dict[str, Any]]:
        """
        Optimize transaction bundle for maximum profit.

        Args:
            transactions: List of transactions
            target_block: Optional target block number
            state_overrides: Optional state overrides for simulation

        Returns:
            Tuple of (optimized transactions, simulation results)
        """
        best_profit = -float('inf')
        best_bundle = None
        best_results = None

        # Get base gas price
        gas_estimate = await self._estimate_gas_price()
        base_gas_price = gas_estimate.price

        # Dynamic gas variations based on network conditions
        congestion = gas_estimate.price / gas_estimate.base_fee
        variations = [
            1.0,  # Base price
            1.1,  # +10%
            0.9,  # -10%
        ]

        if congestion > 1.5:  # High congestion
            variations.extend([
                1.2,  # +20%
                1.3,  # +30%
                1.4   # +40%
            ])
        elif congestion < 0.8:  # Low congestion
            variations.extend([
                0.8,  # -20%
                0.7   # -30%
            ])

        # Calculate gas price variations
        gas_variations = [
            int(base_gas_price * v) for v in variations
        ]

        # Create modified transaction sets
        modified_tx_sets = []
        for gas_price in gas_variations:
            if gas_price > self.max_gas_price:
                continue

            # Update gas prices in transactions
            modified_txs = []
            for tx in transactions:
                tx_dict = tx.to_dict()
                tx_dict['gasPrice'] = hex(gas_price)
                modified_txs.append(Transaction(tx_dict))
            modified_tx_sets.append(modified_txs)

        # Simulate bundles in parallel
        simulation_tasks = [
            self.simulate_bundle(txs, state_overrides, target_block)
            for txs in modified_tx_sets
        ]

        # Wait for all simulations
        all_results = await asyncio.gather(*simulation_tasks, return_exceptions=True)

        # Process results
        for txs, results in zip(modified_tx_sets, all_results):
            if isinstance(results, Exception):
                logger.warning(f"Bundle simulation failed: {results}")
                continue

            if results['success'] and results['profitability'] > best_profit:
                best_profit = results['profitability']
                best_bundle = txs
                best_results = results
                break  # Stop if we find a profitable bundle

        if best_bundle is None:
            raise ValueError("Failed to optimize bundle: no profitable configuration found")

        return best_bundle, best_results

    async def _validate_bundle_profit(
        self,
        transactions: List[Transaction],
        simulation_result: Dict[str, Any]
    ) -> bool:
        """
        Validate bundle profitability.

        Args:
            transactions: List of transactions
            simulation_result: Simulation results

        Returns:
            True if profitable, False otherwise
        """
        if not simulation_result['success']:
            return False

        # Calculate net profit
        gas_cost = simulation_result['gasUsed'] * simulation_result['effectiveGasPrice']
        net_profit = simulation_result['mevValue'] - gas_cost

        # Get historical stats
        bundle_key = self._get_bundle_key(transactions)
        stats = self._bundle_stats.get(bundle_key)

        # Adjust minimum profit based on historical performance
        min_profit = self.min_profit
        if stats:
            if stats.success_rate < 0.5:  # Low success rate
                min_profit = int(min_profit * 1.5)  # Require 50% more profit
            elif stats.success_rate > 0.8:  # High success rate
                min_profit = int(min_profit * 0.8)  # Allow 20% less profit

        # Validate against minimum profit threshold
        if net_profit < min_profit:
            logger.warning(f"Bundle profit {net_profit} below minimum threshold {min_profit}")
            return False

        logger.info(f"Bundle validated with expected profit {net_profit} wei")
        return True

    @with_retry(max_attempts=3, base_delay=1.0)
    async def send_bundle(
        self,
        transactions: List[Transaction],
        target_block: Optional[int] = None,
 
        state_overrides: Optional[Dict[str, Any]] = None,
        min_timestamp: Optional[int] = None
    ) -> HexStr:
        """
        Send transaction bundle to Flashbots.

        Args:
            transactions: List of transactions
            target_block: Optional target block number
            state_overrides: Optional state overrides for simulation
            min_timestamp: Optional minimum timestamp

        Returns:
            Bundle hash

        Raises:
            ValueError: If no transactions provided or no auth signer configured
        """
        if not transactions:
            raise ValueError("No transactions provided")

        if not self.auth_signer:
            raise ValueError("No auth signer configured")

        async with self._bundle_lock:
            # Get current block if no target provided
            if target_block is None:
                target_block = await self.w3.eth.block_number + 1

            # Optimize bundle
            optimized_txs, sim_results = await self._optimize_bundle(
                transactions,
                target_block
,
                state_overrides
            )

            # Validate profitability
            if not await self._validate_bundle_profit(transactions, sim_results):
                raise ValueError("Bundle not profitable enough to execute")

            # Convert transactions to dict format
            tx_dicts = [tx.to_dict() for tx in optimized_txs]

            # Add bundle parameters
            params = {
                "txs": tx_dicts,
                "blockNumber": hex(target_block),
                "minTimestamp": hex(min_timestamp) if min_timestamp else hex(0),
                "maxTimestamp": hex(min_timestamp + 180) if min_timestamp else hex(0),  # 3 minute window
                "revertingTxHashes": []  # Hashes of transactions that are allowed to revert
            }

            # Sign bundle
            message = self.w3.keccak(
                self.w3.eth.abi.encode_abi(
                    ["tuple(bytes[] txs, bytes32 blockNumber, bytes32 minTimestamp, bytes32 maxTimestamp, bytes32[] revertingTxHashes)"],
                    [params]
                )
            )

            signature = self.auth_signer.sign_message(message)

            # Make RPC call with enhanced parameters
            response = await self.w3.eth.provider.make_request(
                "eth_sendBundle",
                [{
                    "txs": params["txs"],
                    "blockNumber": params["blockNumber"],
                    "minTimestamp": params["minTimestamp"],
                    "maxTimestamp": params["maxTimestamp"],
                    "revertingTxHashes": params["revertingTxHashes"],
                    "signature": signature.hex()
                }]
            )

            # Update bundle stats
            bundle_key = self._get_bundle_key(transactions)
            current_stats = self._bundle_stats.get(bundle_key, BundleStats(0, 0, 0))

            if response.get("result"):
                # Success
                new_success_rate = (
                    (current_stats.success_rate * current_stats.total_attempts + 1) /
                    (current_stats.total_attempts + 1)
                )
                new_avg_profit = (
                    (current_stats.avg_profit * current_stats.total_attempts + sim_results['profitability']) /
                    (current_stats.total_attempts + 1)
                )
                self._bundle_stats[bundle_key] = BundleStats(
                    new_success_rate, new_avg_profit, current_stats.total_attempts + 1
                )

            # Log bundle submission
            logger.info(f"Submitted optimized bundle to block {target_block} "
                       f"with estimated profit {sim_results['profitability']} wei")

            # Return bundle hash
            result = response.get("result")
            if not result:
                raise ValueError(f"Invalid response from Flashbots: {response}")
            return HexStr(result)

    async def close(self):
        """Clean up resources."""
        # Clear caches
        self._gas_price_cache.clear()
        self._bundle_stats.clear()

async def create_flashbots_provider(
    web3_manager: Any,
    relay_url: str,
    auth_key: Optional[str] = None
) -> FlashbotsProvider:
    """
    Create a new Flashbots provider.

    Args:
        web3_manager: Web3Manager instance
        relay_url: Flashbots relay URL
        auth_key: Optional authentication key

    Returns:
        FlashbotsProvider instance
    """
    return FlashbotsProvider(
        w3=web3_manager.w3,
        relay_url=relay_url,
        auth_key=auth_key,
        chain_id=web3_manager.chain_id
    )
