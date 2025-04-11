"""
Flashbots Interfaces

This module defines the interfaces and data structures for interacting with
Flashbots, including bundle definitions and operation results.
"""

# import asyncio # Unused
# import time # Unused
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, TypedDict

from ...web3.interfaces import Transaction


@dataclass
class FlashbotsBundle:
    """
    Represents a bundle of transactions to be submitted to Flashbots.

    A bundle contains one or more transactions that will be executed atomically
    by miners using Flashbots.
    """

    transactions: List[Transaction]
    """List of transactions to include in the bundle."""

    target_block_number: Optional[int] = None
    """Target block number for the bundle, or None for auto-targeting."""

    blocks_into_future: int = 1
    """Number of blocks into the future to target if target_block_number is None."""

    replacements: Dict[str, str] = field(default_factory=dict)
    """Optional replacements for the bundle."""

    simulation_timestamp: Optional[int] = None
    """Timestamp to use for simulation, or None for current time."""

    # State fields
    signed: bool = False
    """Whether the bundle has been signed."""

    signed_transactions: List[Union[str, bytes]] = field(default_factory=list)
    """List of signed transactions in the bundle."""


@dataclass
class BundleSimulationResult:
    """
    Result of simulating a Flashbots bundle.

    Contains information about the simulation outcome, including whether it was
    successful, any errors encountered, and the simulated state changes.
    """

    success: bool
    """Whether the simulation was successful."""

    error: Optional[str] = None
    """Error message if the simulation failed."""

    state_changes: Dict[str, Any] = field(default_factory=dict)
    """State changes resulting from the simulation."""

    gas_used: Optional[int] = None
    """Gas used by the simulated bundle."""

    gas_price: Optional[int] = None
    """Gas price used for the simulation."""

    eth_sent_to_coinbase: Optional[int] = None
    """ETH sent to the coinbase address."""

    simulation_block: Optional[int] = None
    """Block number used for the simulation."""

    simulation_timestamp: Optional[int] = None
    """Timestamp used for the simulation."""


@dataclass
class BundleSubmissionResult:
    """
    Result of submitting a Flashbots bundle.

    Contains information about the submission outcome, including whether it was
    successful, any errors encountered, and the bundle hash for tracking.
    """

    success: bool
    """Whether the submission was successful."""

    error: Optional[str] = None
    """Error message if the submission failed."""

    bundle_hash: Optional[str] = None
    """Hash of the submitted bundle, used for tracking."""

    relay_response: Dict[str, Any] = field(default_factory=dict)
    """Raw response from the Flashbots relay."""


class BundleStatsResult(TypedDict, total=False):
    """
    Statistics about a submitted Flashbots bundle.

    Contains information about the bundle's status, including whether it was
    included in a block, which block it was included in, and related metrics.
    """

    bundle_hash: str
    """Hash of the bundle."""

    is_included: bool
    """Whether the bundle was included in a block."""

    block_number: Optional[int]
    """Block number where the bundle was included, if any."""

    transaction_hash: Optional[str]
    """Hash of the transaction within the bundle."""

    miner: Optional[str]
    """Address of the miner who included the bundle."""

    gas_used: Optional[int]
    """Gas used by the bundle when executed."""

    gas_price: Optional[int]
    """Effective gas price for the bundle."""

    eth_sent_to_coinbase: Optional[int]
    """ETH sent to the coinbase address."""

    bundle_stats: Dict[str, Any]
    """Additional bundle statistics."""
