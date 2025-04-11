"----------------" "SwapBased DEX implementation." ""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from web3 import Web3
from eth_typing import HexStr
from web3.contract import AsyncContract
from .base_dex import BaseDEX
from ..web3.web3_manager import Web3Manager
from ..utils.flashbots import (
    encode_bundle_data,
    simulate_bundle,
    submit_bundle,
    get_optimal_gas_params,
)

logger = logging.getLogger(__name__)


class SwapBasedDEX(BaseDEX):
    """SwapBased DEX implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize SwapBased DEX."""
        # Add Flashbots configuration
        self.flashbots_enabled = config.get("flashbots", {}).get("enabled", True)
        self.max_bundle_size = config.get("flashbots", {}).get("max_bundle_size", 5)
        self.max_blocks_ahead = config.get("flashbots", {}).get("max_blocks_ahead", 3)
        self.min_priority_fee = float(
            config.get("flashbots", {}).get("min_priority_fee", "1.5")
        )
        self.max_priority_fee = float(
            config.get("flashbots", {}).get("max_priority_fee", "3")
        )
        self.sandwich_detection = config.get("flashbots", {}).get(
            "sandwich_detection", True
        )
        self.frontrun_detection = config.get("flashbots", {}).get(
            "frontrun_detection", True
        )
        self.adaptive_gas = config.get("flashbots", {}).get("adaptive_gas", True)

        super().__init__(web3_manager, config)
        self.factory: Optional[AsyncContract] = None
        self.router: Optional[AsyncContract] = None
        self.flashbots = None

    async def initialize(self) -> bool:
        """Initialize contracts."""
        try:
            # Load factory contract
            factory_address = self.config.get("factory")
            if not factory_address:
                logger.error("Factory address not found in config")
                return False

            # Load router contract
            router_address = self.config.get("router")
            if not router_address:
                logger.error("Router address not found in config")
                return False

            # Load ABIs
            factory_abi = self.web3_manager.load_abi("swapbased_factory")
            if not factory_abi:
                logger.error("Failed to load factory ABI")
                return False

            router_abi = self.web3_manager.load_abi("swapbased_router")
            if not router_abi:
                logger.error("Failed to load router ABI")
                return False

            # Initialize contracts
            self.factory = await self.web3_manager.get_contract_async(
                factory_address, factory_abi
            )

            self.router = await self.web3_manager.get_contract_async(
                router_address,
                router_abi,
            )

            # Initialize Flashbots if enabled
            if self.flashbots_enabled:
                try:
                    auth_key = self.web3_manager.config.get("flashbots", {}).get(
                        "auth_signer_key"
                    )
                    if not auth_key:
                        logger.warning(
                            "Flashbots auth key not found, disabling Flashbots"
                        )
                        self.flashbots_enabled = False
                    else:
                        self.flashbots = self.web3_manager.get_flashbots_client(
                            auth_key
                        )
                        logger.info("Flashbots client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Flashbots: {e}")
                    self.flashbots_enabled = False

            logger.info(f"Initialized SwapBased DEX with factory {factory_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize SwapBased: {e}")
            return False

    async def get_reserves(
        self, token0: str, token1: str, block_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get reserves for token pair."""
        try:
            # Sort tokens
            token0, token1 = sorted([token0, token1])

            # Get pool address
            pool_address = await self.factory.functions.getPool(
                token0, token1, 3000  # Default fee tier
            ).call()

            if not pool_address or pool_address == "0x" + "0" * 40:
                logger.debug(f"No pool found for {token0}/{token1}")
                return None

            # Load pool contract
            pool_abi = self.web3_manager.load_abi("swapbased_pool")
            if not pool_abi:
                logger.error("Failed to load pool ABI")
                return None

            pool = await self.web3_manager.get_contract_async(pool_address, pool_abi)

            # Get slot0 data
            slot0 = await pool.functions.slot0().call(block_identifier=block_number)
            sqrt_price_x96 = slot0[0]

            # Get liquidity
            liquidity = await pool.functions.liquidity().call(
                block_identifier=block_number
            )

            # Calculate reserves from sqrtPriceX96 and liquidity
            price = (sqrt_price_x96**2) / (2**192)
            reserve0 = liquidity / (price**0.5)
            reserve1 = liquidity * (price**0.5)

            return {
                "reserve0": str(int(reserve0)),
                "reserve1": str(int(reserve1)),
                "block_timestamp_last": 0,  # Not used for V3
            }

        except Exception as e:
            logger.debug(f"Error in Reserve lookup - {e}")
            return None

    async def get_quote_with_impact(
        self, amount_in: int, path: list
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact."""
        try:
            # Check for MEV risks if enabled
            if self.flashbots_enabled and (
                self.sandwich_detection or self.frontrun_detection
            ):
                try:
                    mev_risks = await self.web3_manager.use_mcp_tool(
                        "mev-protection",
                        "analyze_mev_risks",
                        {
                            "token": path[0],
                            "amount": amount_in,
                            "check_sandwich": self.sandwich_detection,
                            "check_frontrun": self.frontrun_detection,
                        },
                    )

                    if mev_risks and mev_risks.get("high_risk", False):
                        logger.warning(f"High MEV risk detected: {mev_risks}")
                        return None
                except Exception as e:
                    logger.error(f"MEV risk check failed: {e}")

            # Get pool address
            pool_address = await self.factory.functions.getPool(
                path[0], path[1], 3000  # Default fee tier
            ).call()

            if not pool_address or pool_address == "0x" + "0" * 40:
                return None

            # Load pool contract
            pool_abi = self.web3_manager.load_abi("swapbased_pool")
            if not pool_abi:
                logger.error("Failed to load pool ABI")
                return None

            pool = await self.web3_manager.get_contract_async(pool_address, pool_abi)

            # Get slot0 data
            slot0 = await pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]

            # Get liquidity
            liquidity = await pool.functions.liquidity().call()

            # Calculate quote
            price = (sqrt_price_x96**2) / (2**192)
            amount_out = amount_in * price

            # Calculate price impact
            price_impact = abs(1 - (amount_out / amount_in / price))

            return {"amount_out": str(int(amount_out)), "price_impact": price_impact}

        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            return None

    async def get_amount_out(self, amount_in: int, path: list) -> Optional[int]:
        """Get output amount for input amount."""
        try:
            quote = await self.get_quote_with_impact(amount_in, path)
            if quote:
                return int(quote["amount_out"])
            return None
        except Exception as e:
            logger.error(f"Error getting amount out: {e}")
            return None

    async def swap_exact_tokens_for_tokens(
        self,
        amount_in: int,
        min_amount_out: int,
        path: List[str],
        to: str,
        deadline: int,
        gas_price: Optional[int] = None,
    ) -> Optional[str]:
        """Execute token swap."""
        try:
            # Get gas parameters
            if self.flashbots_enabled and self.adaptive_gas:
                gas_params = await get_optimal_gas_params(
                    self.web3_manager, self.min_priority_fee, self.max_priority_fee
                )
                if gas_params:
                    gas_price = gas_params["maxFeePerGas"]
                    priority_fee = gas_params["maxPriorityFeePerGas"]
                else:
                    logger.warning("Failed to get optimal gas params, using defaults")
                    gas_price = await self.web3_manager.get_max_fee()
                    priority_fee = await self.web3_manager.get_priority_fee()
            else:
                gas_price = (
                    gas_price if gas_price else await self.web3_manager.get_max_fee()
                )
                priority_fee = await self.web3_manager.get_priority_fee()

            # Build swap params
            params = {
                "tokenIn": path[0],
                "tokenOut": path[1],
                "fee": 3000,  # Default fee tier
                "recipient": to,
                "amountIn": amount_in,
                "amountOutMinimum": min_amount_out,
                "sqrtPriceLimitX96": 0,  # No price limit
            }

            # Build transaction
            tx = await self.router.functions.exactInputSingle(params).build_transaction(
                {
                    "from": self.web3_manager.account.address,
                    "gas": self.config.get("gas_limit", 300000),
                    "maxFeePerGas": gas_price,
                    "maxPriorityFeePerGas": priority_fee,
                    "nonce": await self.web3_manager.get_nonce(),
                }
            )

            if self.flashbots_enabled:
                try:
                    # Sign transaction
                    signed_tx = self.web3_manager.account.sign_transaction(tx)

                    # Create bundle
                    bundle = [{"signed_transaction": signed_tx.rawTransaction}]

                    # Get target block
                    current_block = await self.web3_manager.eth.block_number
                    target_block = current_block + 1

                    # Simulate bundle
                    simulation = await simulate_bundle(
                        self.flashbots, bundle, target_block
                    )

                    if not simulation or not simulation.get("success", False):
                        logger.error(f"Bundle simulation failed: {simulation}")
                        return None

                    # Submit bundle
                    bundle_hash = await submit_bundle(
                        self.flashbots, bundle, target_block
                    )

                    if not bundle_hash:
                        logger.error("Bundle submission failed")
                        return None

                    return bundle_hash

                except Exception as e:
                    logger.error(f"Flashbots execution failed: {e}")
                    return None
            else:
                # Fallback to regular transaction
                signed_tx = self.web3_manager.account.sign_transaction(tx)
                tx_hash = await self.web3_manager.w3.eth.send_raw_transaction(
                    signed_tx.rawTransaction
                )
                return tx_hash.hex()

        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            return None
