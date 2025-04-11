"""
Listonian Arbitrage Bot - Base DEX Trading Executor

This module provides the trading execution component for the Base DEX Scanner MCP integration.
It takes the arbitrage opportunities discovered by the scanner and executes trades to capture profits.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from decimal import Decimal
from web3 import Web3
from web3.providers.async_base import AsyncBaseProvider
from web3.types import TxParams, Wei

from eth_utils import to_checksum_address

from ..core.arbitrage.models import ArbitrageOpportunity
from ..core.flashbots.flashbots_provider import FlashbotsProvider
from .base_dex_scanner_mcp import BaseDexScannerMCP, BaseDexScannerSource, USE_MOCK_DATA

logger = logging.getLogger(__name__)

# =====================================================================
# MOCK DATA CONFIGURATION
# =====================================================================
# Set this to False to disable mock data and use real API calls
# In production, this should be set to False
USE_MOCK_TRADING = os.environ.get("USE_MOCK_TRADING", "false").lower() == "true"

if USE_MOCK_TRADING:
    logger.warning(
        "!!! USING MOCK TRADING FOR TESTING PURPOSES ONLY !!! Set USE_MOCK_TRADING=false to use real trading"
    )

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


class BaseDexTradingExecutor:
    """Trading executor for Base DEX arbitrage opportunities."""

    def __init__(
        self,
        private_key: str,
        rpc_url: str = "https://mainnet.base.org",
        flashbots_relay_url: str = "https://relay.flashbots.net",
        wallet_address: Optional[str] = None,
        min_profit_usd: float = 10.0,
        max_slippage: float = 0.005,  # 0.5%
        gas_price_buffer: float = 1.1,  # 10% buffer
        server_name: str = "base-dex-scanner",
    ):
        """Initialize the trading executor.

        Args:
            private_key: Private key for transaction signing
            rpc_url: Base RPC URL
            wallet_address: Wallet address (derived from private key if not provided)
            flashbots_relay_url: Flashbots relay URL
            min_profit_usd: Minimum profit in USD to execute a trade
            max_slippage: Maximum slippage allowed
            gas_price_buffer: Buffer for gas price estimation
            server_name: Name of the MCP server
        """
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.wallet_address = wallet_address
        self.flashbots_relay_url = flashbots_relay_url
        self.min_profit_usd = Decimal(str(min_profit_usd))
        self.max_slippage = Decimal(str(max_slippage))
        self.gas_price_buffer = Decimal(str(gas_price_buffer))
        self.server_name = server_name

        self.scanner = BaseDexScannerMCP(server_name=server_name)
        self.source = BaseDexScannerSource(server_name=server_name)
        self.flashbots_provider = None
        self.web3 = None
        self.token_contracts = {}
        self.router_contracts = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._stats = {
            "opportunities_found": 0,
            "trades_executed": 0,
            "total_profit_usd": 0.0,
            "failed_trades": 0,
            "start_time": None,
            "last_trade_time": None,
        }

        # Configuration for DEX routers and ABIs
        self.config = {"dex_routers": {}, "dex_router_abis": {}}

        # Show warning if using mock data
        if USE_MOCK_TRADING:
            logger.warning(
                "!!! BaseDexTradingExecutor USING MOCK TRADING FOR TESTING PURPOSES ONLY !!!"
            )

    async def initialize(self) -> bool:
        """Initialize the trading executor.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Initialize Web3
            # Use HTTP provider for now, as AsyncHTTPProvider might not be available in all web3.py versions
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))

            # Derive wallet address if not provided
            if not self.wallet_address:
                account = self.web3.eth.account.from_key(self.private_key)
                self.wallet_address = account.address
                logger.info(f"Derived wallet address: {self.wallet_address}")
            else:
                # Ensure wallet address is checksummed
                self.wallet_address = to_checksum_address(self.wallet_address)

            # Initialize Flashbots provider
            self.flashbots_provider = FlashbotsProvider(
                web3=self.web3,
                config={
                    "relay_url": self.flashbots_relay_url,
                    "private_key": self.private_key,
                    "chain_id": 8453,  # Base chain ID
                },
                account=self.web3.eth.account.from_key(self.private_key),
            )

            # Initialize the source
            source_initialized = await self.source.initialize()
            if not source_initialized:
                logger.error("Failed to initialize Base DEX Scanner source")
                return False

            # Load token and router contracts as needed

            logger.info("Base DEX Trading Executor initialized")
            return True
        except Exception as e:
            logger.exception(f"Error initializing trading executor: {str(e)}")
            return False

    async def start(self) -> None:
        """Start the trading executor."""
        async with self._lock:
            if self._running:
                logger.warning("Trading executor is already running")
                return

            self._running = True
            self._stats["start_time"] = datetime.now()

            logger.info("Starting Base DEX Trading Executor")

            # Start the trading loop in a separate task
            asyncio.create_task(self._trading_loop())

    async def stop(self) -> None:
        """Stop the trading executor."""
        async with self._lock:
            if not self._running:
                logger.warning("Trading executor is not running")
                return

            self._running = False
            logger.info("Stopping Base DEX Trading Executor")

    async def get_stats(self) -> Dict[str, Any]:
        """Get trading statistics.

        Returns:
            Trading statistics
        """
        async with self._lock:
            stats = self._stats.copy()

            # Calculate runtime
            if stats["start_time"]:
                runtime = datetime.now() - stats["start_time"]
                stats["runtime_seconds"] = runtime.total_seconds()
                stats["runtime_formatted"] = str(runtime).split(".")[0]  # HH:MM:SS

            # Calculate average profit
            if stats["trades_executed"] > 0:
                stats["avg_profit_usd"] = (
                    stats["total_profit_usd"] / stats["trades_executed"]
                )
            else:
                stats["avg_profit_usd"] = 0.0

            return stats

    async def _trading_loop(self) -> None:
        """Main trading loop."""
        while self._running:
            try:
                # Detect arbitrage opportunities
                opportunities = await self.source.detect_arbitrage_opportunities()

                async with self._lock:
                    self._stats["opportunities_found"] += len(opportunities)

                # Filter profitable opportunities
                profitable_opportunities = [
                    opp
                    for opp in opportunities
                    if hasattr(opp, "is_profitable")
                    and opp.is_profitable
                    and Decimal(str(opp.net_profit_usd)) >= self.min_profit_usd
                ]

                logger.info(
                    f"Found {len(profitable_opportunities)} profitable arbitrage opportunities"
                )

                # Execute trades for profitable opportunities
                for opp in profitable_opportunities:
                    if not self._running:
                        break

                    try:
                        # Execute the trade
                        result = await self._execute_trade(opp)

                        if result["success"]:
                            async with self._lock:
                                self._stats["trades_executed"] += 1
                                self._stats["total_profit_usd"] += float(
                                    result["profit_usd"]
                                )
                                self._stats["last_trade_time"] = datetime.now()

                            logger.info(
                                f"Successfully executed trade with profit: ${result['profit_usd']:.2f}"
                            )
                        else:
                            async with self._lock:
                                self._stats["failed_trades"] += 1

                            logger.warning(
                                f"Failed to execute trade: {result['error']}"
                            )

                    except Exception as e:
                        logger.exception(f"Error executing trade: {str(e)}")
                        async with self._lock:
                            self._stats["failed_trades"] += 1

                # Sleep before next iteration
                await asyncio.sleep(5)

            except Exception as e:
                logger.exception(f"Error in trading loop: {str(e)}")
                await asyncio.sleep(10)  # Longer sleep on error

    async def _execute_trade(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Execute a trade for an arbitrage opportunity.

        Args:
            opportunity: Arbitrage opportunity to execute

        Returns:
            Trade result
        """
        try:
            # Log opportunity details
            logger.info(
                f"Executing trade for opportunity: {getattr(opportunity, 'id', 'unknown')}"
            )

            # Validate opportunity
            if not await self._validate_opportunity(opportunity):
                return {
                    "success": False,
                    "error": "Opportunity validation failed",
                }

            # Get current block and gas price
            current_block = self.web3.eth.block_number
            gas_price = self.web3.eth.gas_price

            # Create transactions for the arbitrage path
            transactions = await self._create_transactions(opportunity, gas_price)
            if not transactions:
                return {
                    "success": False,
                    "error": "Failed to create transactions",
                }

            # Create bundle
            bundle = {
                "transactions": transactions,
                "target_block": current_block + 1,
                "gas_price": gas_price,
            }

            # Simulate the bundle
            simulation_result = await self._simulate_bundle(bundle)

            # Check if simulation was successful
            if not simulation_result["success"]:
                return {
                    "success": False,
                    "error": f"Bundle simulation failed: {simulation_result.get('error', 'unknown error')}",
                }

            # Verify profit from simulation
            expected_profit = getattr(opportunity, "expected_profit_wei", 0)
            simulated_profit = simulation_result.get("profit_wei", 0)

            if simulated_profit < expected_profit:
                return {
                    "success": False,
                    "error": f"Simulated profit ({simulated_profit}) less than expected ({expected_profit})",
                }

            # Submit the bundle
            submission_result = await self._submit_bundle(bundle)

            # Check if submission was successful
            if not submission_result["success"]:
                return {
                    "success": False,
                    "error": f"Bundle submission failed: {submission_result.get('error', 'unknown error')}",
                }

            # Wait for bundle to be included
            bundle_hash = submission_result["bundle_hash"]
            inclusion_result = await self._wait_for_inclusion(bundle_hash)

            # Check if bundle was included
            if not inclusion_result["included"]:
                return {
                    "success": False,
                    "error": f"Bundle not included: {inclusion_result.get('status', 'unknown status')}",
                }

            # Calculate actual profit
            actual_profit_wei = inclusion_result.get("profit_wei", 0)
            output_price_usd = getattr(opportunity, "output_price_usd", 0)
            actual_profit_usd = (
                Decimal(str(actual_profit_wei))
                * Decimal(str(output_price_usd))
                / Decimal("1e18")
            )

            return {
                "success": True,
                "transaction_hash": inclusion_result.get("transaction_hash"),
                "block_number": inclusion_result.get("block_number"),
                "profit_wei": actual_profit_wei,
                "profit_usd": float(actual_profit_usd),
                "gas_used": inclusion_result.get("gas_used"),
                "gas_price": inclusion_result.get("gas_price"),
            }

        except Exception as e:
            logger.exception(f"Error executing trade: {str(e)}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _validate_opportunity(self, opportunity: ArbitrageOpportunity) -> bool:
        """Validate an arbitrage opportunity.

        Args:
            opportunity: Arbitrage opportunity to validate

        Returns:
            True if opportunity is valid, False otherwise
        """
        try:
            # Check if opportunity is profitable
            if not getattr(opportunity, "is_profitable", False):
                logger.warning("Opportunity is not profitable")
                return False

            # Check if profit meets minimum threshold
            net_profit_usd = Decimal(str(getattr(opportunity, "net_profit_usd", 0)))
            if net_profit_usd < self.min_profit_usd:
                logger.warning(
                    f"Profit ({net_profit_usd}) below minimum threshold ({self.min_profit_usd})"
                )
                return False

            # Additional validation as needed

            return True
        except Exception as e:
            logger.exception(f"Error validating opportunity: {str(e)}")
            return False

    async def _create_transactions(
        self, opportunity: ArbitrageOpportunity, gas_price: int
    ) -> List[Dict[str, Any]]:
        """Create transactions for an arbitrage opportunity.

        Args:
            opportunity: Arbitrage opportunity
            gas_price: Current gas price

        Returns:
            List of transactions
        """
        try:
            if USE_MOCK_TRADING:
                # =====================================================================
                # !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
                # =====================================================================
                logger.warning(
                    "!!! MOCK TRANSACTION CREATION - FOR TESTING PURPOSES ONLY !!!"
                )

                # This is a simplified implementation for testing
                # In a real implementation, we would:
                # 1. Create transactions for the arbitrage path
                # 2. Optimize gas usage
                # 3. Add slippage protection
                # 4. Add balance verification

                # Mock transaction
                tx = {
                    "from": self.wallet_address,
                    "to": self.wallet_address,  # Self-transfer as placeholder
                    "value": 0,
                    "gas": 100000,
                    "gasPrice": gas_price,
                    "nonce": self.web3.eth.get_transaction_count(self.wallet_address),
                    "data": "0x",  # Empty data
                }

                return [tx]
            else:
                # =====================================================================
                # REAL TRANSACTION CREATION - PRODUCTION CODE
                # =====================================================================
                logger.info(
                    f"Creating real transactions for arbitrage opportunity: {getattr(opportunity, 'id', 'unknown')}"
                )

                # Get path details
                path = getattr(opportunity, "path", [])
                if len(path) < 2:
                    logger.error("Invalid arbitrage path: must have at least 2 steps")
                    return []

                # Get token details
                token_in = getattr(opportunity, "token_in", None)
                token_out = getattr(opportunity, "token_out", None)
                input_amount = getattr(opportunity, "input_amount", None)

                if not token_in or not token_out or not input_amount:
                    logger.error("Missing token details in opportunity")
                    return []

                # Get current nonce
                nonce = self.web3.eth.get_transaction_count(self.wallet_address)

                # Create transactions
                transactions = []

                # 1. Create transaction for first step (buy)
                buy_step = path[0]
                buy_dex = buy_step.get("dex")
                buy_pool = buy_step.get("pool")

                if not buy_dex or not buy_pool:
                    logger.error("Invalid buy step in arbitrage path")
                    return []

                # Get router contract for buy DEX
                buy_router = self._get_router_contract(buy_dex)
                if not buy_router:
                    logger.error(f"Router contract not found for DEX: {buy_dex}")
                    return []

                # Create swap transaction
                buy_tx = {
                    "from": self.wallet_address,
                    "to": buy_router.address,
                    "value": 0,  # No ETH sent directly
                    "gas": 300000,  # Estimate
                    "gasPrice": gas_price,
                    "nonce": nonce,
                    "data": self._create_swap_data(
                        router=buy_router,
                        token_in=token_in,
                        token_out=token_out,
                        amount_in=input_amount.amount,
                        min_amount_out=input_amount.amount * (1 - self.max_slippage),
                        path=[buy_pool],
                    ),
                }

                transactions.append(buy_tx)
                nonce += 1

                # Add more transactions for multi-step arbitrage if needed
                # For now, we're implementing a simple two-step arbitrage

                # Apply gas optimization
                for tx in transactions:
                    tx["gas"] = int(tx["gas"] * self.gas_price_buffer)

                logger.info(
                    f"Created {len(transactions)} transactions for arbitrage opportunity"
                )
                return transactions
        except Exception as e:
            logger.exception(f"Error creating transactions: {str(e)}")
            return []

    def _get_router_contract(self, dex_name: str) -> Optional[Any]:
        """Get the router contract for a DEX.

        Args:
            dex_name: Name of the DEX

        Returns:
            Router contract or None if not found
        """
        try:
            # Get router address from configuration
            router_address = self.config.get("dex_routers", {}).get(dex_name)
            if not router_address:
                logger.error(f"Router address not found for DEX: {dex_name}")
                return None

            # Ensure address is checksummed
            router_address = self.web3.to_checksum_address(router_address)

            # Get router ABI from configuration
            router_abi = self.config.get("dex_router_abis", {}).get(dex_name)
            if not router_abi:
                logger.error(f"Router ABI not found for DEX: {dex_name}")
                return None

            # Create contract
            return self.web3.eth.contract(address=router_address, abi=router_abi)
        except Exception as e:
            logger.exception(f"Error getting router contract for {dex_name}: {str(e)}")
            return None

    def _create_swap_data(
        self,
        router: Any,
        token_in: str,
        token_out: str,
        amount_in: float,
        min_amount_out: float,
        path: List[str],
    ) -> str:
        """Create swap transaction data.

        Args:
            router: Router contract
            token_in: Input token symbol
            token_out: Output token symbol
            amount_in: Input amount
            min_amount_out: Minimum output amount
            path: Swap path

        Returns:
            Transaction data
        """
        # This is a simplified implementation
        # In a real implementation, we would:
        # 1. Get token addresses from symbols
        # 2. Create swap function call based on DEX type
        return "0x"  # Placeholder

    async def _simulate_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a bundle.

        Args:
            bundle: Bundle to simulate

        Returns:
            Simulation result
        """
        try:
            if USE_MOCK_TRADING:
                # =====================================================================
                # !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
                # =====================================================================
                logger.warning(
                    "!!! MOCK BUNDLE SIMULATION - FOR TESTING PURPOSES ONLY !!!"
                )

                # Mock simulation result
                return {
                    "success": True,
                    "profit_wei": 1000000000000000000,  # 1 ETH
                    "gas_used": 200000,
                }
            else:
                # =====================================================================
                # REAL BUNDLE SIMULATION - PRODUCTION CODE
                # =====================================================================
                logger.info("Simulating bundle with Flashbots provider...")

                # Check if Flashbots provider is initialized
                if not self.flashbots_provider:
                    logger.error("Flashbots provider not initialized")
                    return {
                        "success": False,
                        "error": "Flashbots provider not initialized",
                    }

                # Check if Flashbots provider is ready
                if not await self.flashbots_provider.is_initialized():
                    try:
                        await self.flashbots_provider.initialize()
                    except Exception as e:
                        logger.error(
                            f"Failed to initialize Flashbots provider: {str(e)}"
                        )
                        return {
                            "success": False,
                            "error": f"Failed to initialize Flashbots provider: {str(e)}",
                        }

                # Extract transactions from bundle
                transactions = bundle.get("transactions", [])
                if not transactions:
                    logger.error("No transactions in bundle")
                    return {"success": False, "error": "No transactions in bundle"}

                # Get current block number
                try:
                    block_number = await self.flashbots_provider.get_block_number()
                except Exception as e:
                    logger.error(f"Failed to get block number: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to get block number: {str(e)}",
                    }

                # Simulate bundle
                try:
                    simulation_result = await self.flashbots_provider.simulate_bundle(
                        transactions=transactions, block_number=block_number
                    )

                    # Process simulation result
                    if simulation_result and "result" in simulation_result:
                        result = simulation_result["result"]
                        return {
                            "success": True,
                            "profit_wei": result.get("value", 0),
                            "gas_used": result.get("gasUsed", 0),
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Invalid simulation result: {simulation_result}",
                        }

                except Exception as e:
                    logger.error(f"Failed to simulate bundle: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to simulate bundle: {str(e)}",
                    }
        except Exception as e:
            logger.exception(f"Error simulating bundle: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _submit_bundle(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a bundle to Flashbots.

        Args:
            bundle: Bundle to submit

        Returns:
            Submission result
        """
        try:
            if USE_MOCK_TRADING:
                # =====================================================================
                # !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
                # =====================================================================
                logger.warning(
                    "!!! MOCK BUNDLE SUBMISSION - FOR TESTING PURPOSES ONLY !!!"
                )

                # Mock submission result
                return {
                    "success": True,
                    "bundle_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                }
            else:
                # =====================================================================
                # REAL BUNDLE SUBMISSION - PRODUCTION CODE
                # =====================================================================
                logger.info("Submitting bundle to Flashbots")

                # Check if Flashbots provider is initialized
                if not self.flashbots_provider:
                    logger.error("Flashbots provider not initialized")
                    return {
                        "success": False,
                        "error": "Flashbots provider not initialized",
                    }

                # Check if Flashbots provider is ready
                if not await self.flashbots_provider.is_initialized():
                    try:
                        await self.flashbots_provider.initialize()
                    except Exception as e:
                        logger.error(
                            f"Failed to initialize Flashbots provider: {str(e)}"
                        )
                        return {
                            "success": False,
                            "error": f"Failed to initialize Flashbots provider: {str(e)}",
                        }

                # Extract transactions from bundle
                transactions = bundle.get("transactions", [])
                if not transactions:
                    logger.error("No transactions in bundle")
                    return {"success": False, "error": "No transactions in bundle"}

                # Get target block number
                target_block = bundle.get("target_block")
                if not target_block:
                    target_block = await self.flashbots_provider.get_block_number() + 1

                # Submit bundle
                try:
                    bundle_hash = await self.flashbots_provider.send_bundle(
                        transactions=transactions, target_block_number=target_block
                    )

                    logger.info(f"Bundle submitted with hash: {bundle_hash}")
                    return {"success": True, "bundle_hash": bundle_hash}

                except Exception as e:
                    logger.error(f"Failed to submit bundle: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to submit bundle: {str(e)}",
                    }
        except Exception as e:
            logger.exception(f"Error submitting bundle: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _wait_for_inclusion(self, bundle_hash: str) -> Dict[str, Any]:
        """Wait for a bundle to be included in a block.

        Args:
            bundle_hash: Bundle hash

        Returns:
            Inclusion result
        """
        try:
            if USE_MOCK_TRADING:
                # =====================================================================
                # !!! MOCK DATA - FOR TESTING PURPOSES ONLY !!!
                # =====================================================================
                logger.warning(
                    "!!! MOCK BUNDLE INCLUSION - FOR TESTING PURPOSES ONLY !!!"
                )

                # Mock inclusion result
                return {
                    "included": True,
                    "transaction_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                    "block_number": self.web3.eth.block_number,
                    "profit_wei": 1000000000000000000,  # 1 ETH
                    "gas_used": 200000,
                    "gas_price": self.web3.eth.gas_price,
                    "status": "included",
                }
            else:
                # =====================================================================
                # REAL BUNDLE INCLUSION - PRODUCTION CODE
                # =====================================================================
                logger.info(f"Waiting for bundle {bundle_hash} to be included")

                # Check if Flashbots provider is initialized
                if not self.flashbots_provider:
                    logger.error("Flashbots provider not initialized")
                    return {
                        "included": False,
                        "status": "error",
                        "error": "Flashbots provider not initialized",
                    }

                # Check if Flashbots provider is ready
                if not await self.flashbots_provider.is_initialized():
                    try:
                        await self.flashbots_provider.initialize()
                    except Exception as e:
                        logger.error(
                            f"Failed to initialize Flashbots provider: {str(e)}"
                        )
                        return {
                            "included": False,
                            "status": "error",
                            "error": f"Failed to initialize Flashbots provider: {str(e)}",
                        }

                # Wait for bundle to be included
                try:
                    inclusion_result = await self.flashbots_provider.wait_for_bundle(
                        bundle_hash
                    )

                    if inclusion_result and inclusion_result.get("included"):
                        logger.info(
                            f"Bundle {bundle_hash} included in block {inclusion_result.get('block_number')}"
                        )
                        return {
                            "included": True,
                            "transaction_hash": inclusion_result.get(
                                "transaction_hash"
                            ),
                            "block_number": inclusion_result.get("block_number"),
                            "profit_wei": inclusion_result.get("value", 0),
                            "gas_used": inclusion_result.get("gasUsed", 0),
                            "gas_price": inclusion_result.get("effectiveGasPrice", 0),
                            "status": "included",
                        }
                    else:
                        logger.warning(
                            f"Bundle {bundle_hash} not included: {inclusion_result}"
                        )
                        return {
                            "included": False,
                            "status": "not_included",
                            "error": "Bundle not included",
                        }

                except Exception as e:
                    logger.error(f"Failed to wait for bundle inclusion: {str(e)}")
                    return {
                        "included": False,
                        "status": "error",
                        "error": f"Failed to wait for bundle inclusion: {str(e)}",
                    }
        except Exception as e:
            logger.exception(f"Error waiting for inclusion: {str(e)}")
            return {"included": False, "status": "failed", "error": str(e)}


# Example usage
async def main():
    """Example usage of the Base DEX Trading Executor.

    !!! THIS IS A MOCK EXAMPLE FOR TESTING PURPOSES ONLY !!!
    """
    logger.warning("!!! MOCK EXAMPLE - FOR TESTING PURPOSES ONLY !!!")

    # Create the executor
    executor = BaseDexTradingExecutor(
        private_key="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",  # Mock private key
        wallet_address="0x1234567890123456789012345678901234567890",  # Mock wallet address
        min_profit_usd=10.0,
    )

    # Initialize the executor
    await executor.initialize()

    # Start the executor
    await executor.start()

    # Run for a while
    await asyncio.sleep(60)

    # Get statistics
    stats = await executor.get_stats()
    print(f"Trading Statistics:")
    print(f"  Opportunities Found: {stats['opportunities_found']}")
    print(f"  Trades Executed: {stats['trades_executed']}")
    print(f"  Total Profit: ${stats['total_profit_usd']:.2f}")
    print(f"  Failed Trades: {stats['failed_trades']}")
    print(f"  Runtime: {stats.get('runtime_formatted', 'N/A')}")

    # Stop the executor
    await executor.stop()


if __name__ == "__main__":
    asyncio.run(main())
