"""
DEX Interface Module
Handles interactions with different decentralized exchanges
"""

import logging
import json
import time
import asyncio
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from pathlib import Path
from web3.contract import Contract
from web3.types import TxParams, Wei
from web3.exceptions import ContractLogicError

from arbitrage_bot.utils.web3_utils import Web3, create_web3_manager
from arbitrage_bot.utils.rate_limiter import create_rate_limiter
from arbitrage_bot.utils.config_loader import load_config, ensure_config_exists
from arbitrage_bot.configs.logging_config import get_logger

logger = get_logger("DexInterface")

class DexInterface:
    """Interface for interacting with different DEXes"""

    def __init__(self):
        """Initialize DEX interface"""
        self.web3_manager = None
        self.rate_limiter = None
        self.config = None
        self.dex_configs = {}
        self.token_configs = {}
        self.pair_configs = []
        self.dex_contracts = {}
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize DEX interface asynchronously"""
        if self._initialized:
            return True

        async with self._init_lock:
            if self._initialized:  # Double-check under lock
                return True

            try:
                self.web3_manager = await create_web3_manager()
                self.rate_limiter = await create_rate_limiter()

                # Ensure config exists and load it
                ensure_config_exists()
                self.config = load_config()
                self.dex_configs = self.config.get("dexes", {})
                self.token_configs = self.config.get("tokens", {})
                self.pair_configs = self.config.get("pairs", [])

                # Initialize DEX contracts
                self.dex_contracts = {}
                await self._initialize_contracts()

                self._initialized = True
                logger.info("DexInterface initialized")
                logger.info("Loaded {} DEXes".format(len(self.dex_configs)))
                logger.info("Loaded {} tokens".format(len(self.token_configs)))
                return True

            except ImportError as e:
                logger.error("Failed to import required modules: {}".format(e))
                raise
            except Exception as e:
                logger.error("Error initializing DexInterface: {}".format(e))
                raise

    async def _initialize_contracts(self):
        """Initialize Web3 contract instances for each DEX"""
        try:
            root_dir = Path(__file__).parent.parent.parent.parent
            abi_dir = root_dir / "abi"

            # Log configured DEXes
            logger.debug("Configured DEXes:")
            for dex_name in self.dex_configs:
                logger.debug("- {}".format(dex_name))

            for dex_name, config in self.dex_configs.items():
                contracts = {}
                version = config.get("version", "v2")
                logger.debug("Initializing {} contracts (version {})".format(dex_name, version))

                # Initialize router
                if version == "v2":
                    router_abi_path = abi_dir / "IUniswapV2Router.json"
                else:
                    router_abi_path = abi_dir / "{}_router_v3.json".format(dex_name)

                if router_abi_path.exists() and "router" in config:
                    with open(router_abi_path, "r") as f:
                        router_abi = json.load(f)
                    contracts["router"] = self.web3_manager.web3.eth.contract(
                        address=Web3.to_checksum_address(config["router"]),
                        abi=router_abi,
                    )
                    logger.info("Initialized router for {}".format(dex_name))

                # Initialize quoter for V3
                if version == "v3" and "quoter" in config:
                    quoter_abi_path = abi_dir / "{}_quoter.json".format(dex_name)
                    if quoter_abi_path.exists():
                        with open(quoter_abi_path, "r") as f:
                            quoter_abi = json.load(f)
                        contracts["quoter"] = self.web3_manager.web3.eth.contract(
                            address=Web3.to_checksum_address(config["quoter"]),
                            abi=quoter_abi,
                        )
                        logger.info("Initialized quoter for {}".format(dex_name))
                    else:
                        logger.error("Quoter ABI not found at {}".format(quoter_abi_path))

                self.dex_contracts[dex_name] = contracts
                logger.info("Initialized all contracts for {}".format(dex_name))

        except Exception as e:
            logger.error("Error initializing contracts: {}".format(e))
            raise

    def _get_token_address(self, symbol: str) -> str:
        """Get token address from symbol"""
        token_config = self.token_configs.get(symbol)
        if not token_config:
            raise ValueError("Token {} not found in config".format(symbol))
        return token_config["address"]

    def _get_token_decimals(self, symbol: str) -> int:
        """Get token decimals from symbol"""
        token_config = self.token_configs.get(symbol)
        if not token_config:
            raise ValueError("Token {} not found in config".format(symbol))
        return token_config["decimals"]

    def _to_token_units(self, amount: Decimal, token: str) -> int:
        """Convert amount to token units based on decimals"""
        decimals = self._get_token_decimals(token)
        return int(amount * Decimal(10**decimals))

    def _from_token_units(self, amount: int, token: str) -> Decimal:
        """Convert token units to decimal based on decimals"""
        decimals = self._get_token_decimals(token)
        return Decimal(amount) / Decimal(10**decimals)

    async def get_quote(self, dex_name: str, token_in: str, token_out: str,
                       amount_in: Decimal) -> Tuple[bool, Optional[Decimal], Optional[str]]:
        """Get quote for trade"""
        if not self._initialized:
            await self.initialize()

        try:
            # Skip if DEX is not configured
            if dex_name not in self.dex_configs:
                logger.warning("DEX {} not configured, skipping".format(dex_name))
                return False, None, "DEX {} not configured".format(dex_name)

            # Skip if DEX contracts not initialized
            if dex_name not in self.dex_contracts:
                logger.warning("DEX {} contracts not initialized, skipping".format(dex_name))
                return False, None, "DEX {} contracts not initialized".format(dex_name)

            contracts = self.dex_contracts[dex_name]
            version = self.dex_configs[dex_name].get("version", "v2")
            logger.debug("Getting quote from {} (version {})".format(dex_name, version))

            # Get token addresses
            token_in_address = Web3.to_checksum_address(self._get_token_address(token_in))
            token_out_address = Web3.to_checksum_address(self._get_token_address(token_out))

            # Convert amount to token units
            amount_in_units = self._to_token_units(amount_in, token_in)
            logger.debug("Converting {} {} to {} units".format(amount_in, token_in, amount_in_units))

            try:
                if version == "v2":
                    logger.debug("Using V2 quote method for {}".format(dex_name))
                    # Use V2 router for quotes
                    if "router" not in contracts:
                        logger.error("Router contract not found for {}".format(dex_name))
                        return False, None, "Router contract not found for {}".format(dex_name)

                    router = contracts["router"]
                    path = [token_in_address, token_out_address]
                    amounts = await router.functions.getAmountsOut(amount_in_units, path).call()
                    amount_out = amounts[1]
                else:
                    logger.debug("Using V3 quote method for {}".format(dex_name))
                    # Use V3 quoter for quotes
                    if "quoter" not in contracts:
                        logger.error("Quoter contract not found for {}".format(dex_name))
                        return False, None, "Quoter contract not found for {}".format(dex_name)

                    quoter = contracts["quoter"]
                    fee = self.dex_configs[dex_name].get("fee", 3000)

                    if dex_name == "pancakeswap":
                        # PancakeSwap V3 expects a tuple parameter
                        params = (
                            token_in_address,
                            token_out_address,
                            amount_in_units,
                            fee,
                            0,  # sqrtPriceLimitX96
                        )
                        logger.debug("Calling PancakeSwap quoteExactInputSingle with params: {}".format(params))
                        quote_result = await quoter.functions.quoteExactInputSingle(params).call()
                    else:
                        # Uniswap V3 expects individual parameters
                        logger.debug(
                            "Calling Uniswap quoteExactInputSingle with params: tokenIn={}, tokenOut={}, fee={}, amountIn={}".format(
                                token_in_address, token_out_address, fee, amount_in_units
                            )
                        )
                        quote_result = await quoter.functions.quoteExactInputSingle(
                            token_in_address,
                            token_out_address,
                            fee,
                            amount_in_units,
                            0,  # sqrtPriceLimitX96
                        ).call()

                    # Extract amountOut from the result tuple
                    amount_out = (
                        quote_result[0]
                        if isinstance(quote_result, (list, tuple))
                        else quote_result
                    )

                # Convert amount out from token units
                amount_out_decimal = self._from_token_units(amount_out, token_out)
                logger.debug("Converting {} units to {} {}".format(amount_out, amount_out_decimal, token_out))

                return True, amount_out_decimal, None

            except Exception as e:
                logger.error("Error getting quote: {}".format(e))
                logger.error("Error details:", exc_info=True)
                return False, None, str(e)

        except Exception as e:
            logger.error("Error getting quote: {}".format(e))
            logger.error("Error details:", exc_info=True)
            return False, None, str(e)

    async def execute_trade(self, dex_name: str, token_in: str, token_out: str,
                          amount_in: Decimal, min_amount_out: Decimal,
                          wallet_address: str, private_key: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Execute trade on specified DEX"""
        if not self._initialized:
            await self.initialize()

        try:
            # Skip if DEX is not configured
            if dex_name not in self.dex_configs:
                logger.warning("DEX {} not configured, skipping".format(dex_name))
                return False, None, "DEX {} not configured".format(dex_name)

            # Skip if DEX contracts not initialized
            if dex_name not in self.dex_contracts:
                logger.warning("DEX {} contracts not initialized, skipping".format(dex_name))
                return False, None, "DEX {} contracts not initialized".format(dex_name)

            contracts = self.dex_contracts[dex_name]
            version = self.dex_configs[dex_name].get("version", "v2")
            logger.debug("Executing trade on {} (version {})".format(dex_name, version))

            if "router" not in contracts:
                return False, None, "Router contract not found for {}".format(dex_name)

            router = contracts["router"]

            # Get token addresses
            token_in_address = Web3.to_checksum_address(self._get_token_address(token_in))
            token_out_address = Web3.to_checksum_address(self._get_token_address(token_out))

            # Convert amounts to token units
            amount_in_units = self._to_token_units(amount_in, token_in)
            min_out_units = self._to_token_units(min_amount_out, token_out)

            # Get deadline
            deadline = int(time.time()) + 300  # 5 minutes

            try:
                if version == "v2":
                    logger.debug("Using V2 trade method for {}".format(dex_name))
                    # Build V2 transaction
                    path = [token_in_address, token_out_address]
                    tx = await router.functions.swapExactTokensForTokens(
                        amount_in_units,
                        min_out_units,
                        path,
                        Web3.to_checksum_address(wallet_address),
                        deadline,
                    ).build_transaction({
                        "from": Web3.to_checksum_address(wallet_address),
                        "gas": 500000,
                        "nonce": await self.web3_manager.web3.eth.get_transaction_count(wallet_address),
                        "gasPrice": await self.web3_manager.web3.eth.gas_price,
                    })
                else:
                    logger.debug("Using V3 trade method for {}".format(dex_name))
                    fee = self.dex_configs[dex_name].get("fee", 3000)

                    if dex_name == "pancakeswap":
                        # PancakeSwap V3 expects a tuple parameter
                        params = (
                            token_in_address,
                            token_out_address,
                            fee,
                            Web3.to_checksum_address(wallet_address),
                            deadline,
                            amount_in_units,
                            min_out_units,
                            0,  # sqrtPriceLimitX96
                        )
                        tx = await router.functions.exactInputSingle(params).build_transaction({
                            "from": Web3.to_checksum_address(wallet_address),
                            "gas": 500000,
                            "nonce": await self.web3_manager.web3.eth.get_transaction_count(wallet_address),
                            "gasPrice": await self.web3_manager.web3.eth.gas_price,
                        })
                    else:
                        # Uniswap V3 expects individual parameters
                        tx = await router.functions.exactInputSingle(
                            token_in_address,
                            token_out_address,
                            fee,
                            wallet_address,
                            deadline,
                            amount_in_units,
                            min_out_units,
                            0,  # sqrtPriceLimitX96
                        ).build_transaction({
                            "from": Web3.to_checksum_address(wallet_address),
                            "gas": 500000,
                            "nonce": await self.web3_manager.web3.eth.get_transaction_count(wallet_address),
                            "gasPrice": await self.web3_manager.web3.eth.gas_price,
                        })

                # Sign transaction
                signed_tx = self.web3_manager.web3.eth.account.sign_transaction(tx, private_key)

                # Send transaction
                tx_hash = await self.web3_manager.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

                # Wait for confirmation
                receipt = await self.web3_manager.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt["status"] == 1:
                    logger.info("Trade executed successfully: {}".format(tx_hash.hex()))
                    return True, tx_hash.hex(), None
                else:
                    logger.error("Trade failed: {}".format(tx_hash.hex()))
                    return False, tx_hash.hex(), "Transaction reverted"

            except Exception as e:
                logger.error("Error executing trade: {}".format(e))
                logger.error("Error details:", exc_info=True)
                return False, None, str(e)

        except Exception as e:
            logger.error("Error executing trade: {}".format(e))
            logger.error("Error details:", exc_info=True)
            return False, None, str(e)

async def create_dex_interface() -> DexInterface:
    """Factory function to create DexInterface instance"""
    interface = DexInterface()
    await interface.initialize()
    return interface
