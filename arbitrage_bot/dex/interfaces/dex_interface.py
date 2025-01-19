"""
DEX Interface Module
Handles interactions with different decentralized exchanges
"""

import logging
import json
import time
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
        try:
            self.web3_manager = create_web3_manager()
            self.rate_limiter = create_rate_limiter()

            # Ensure config exists and load it
            ensure_config_exists()
            self.config = load_config()
            self.dex_configs = self.config.get("dexes", {})
            self.token_configs = self.config.get("tokens", {})
            self.pair_configs = self.config.get("pairs", [])

            # Initialize DEX contracts
            self.dex_contracts: Dict[str, Dict[str, Contract]] = {}
            self._initialize_contracts()

            logger.info("DexInterface initialized")
            logger.info(f"Loaded {len(self.dex_configs)} DEXes")
            logger.info(f"Loaded {len(self.token_configs)} tokens")

        except ImportError as e:
            logger.error(f"Failed to import required modules: {e}")
            raise
        except Exception as e:
            logger.error(f"Error initializing DexInterface: {e}")
            raise

    def _initialize_contracts(self):
        """Initialize Web3 contract instances for each DEX"""
        try:
            root_dir = Path(__file__).parent.parent.parent.parent
            abi_dir = root_dir / "abi"

            # Log configured DEXes
            logger.debug("Configured DEXes:")
            for dex_name in self.dex_configs:
                logger.debug(f"- {dex_name}")

            for dex_name, config in self.dex_configs.items():
                contracts = {}
                version = config.get("version", "v2")
                logger.debug(f"Initializing {dex_name} contracts (version {version})")

                # Initialize router
                if version == "v2":
                    router_abi_path = abi_dir / "IUniswapV2Router.json"
                else:
                    router_abi_path = abi_dir / f"{dex_name}_router_v3.json"

                if router_abi_path.exists() and "router" in config:
                    with open(router_abi_path, "r") as f:
                        router_abi = json.load(f)
                    contracts["router"] = self.web3_manager.web3.eth.contract(
                        address=Web3.to_checksum_address(config["router"]),
                        abi=router_abi,
                    )
                    logger.info(f"Initialized router for {dex_name}")

                # Initialize quoter for V3
                if version == "v3" and "quoter" in config:
                    quoter_abi_path = abi_dir / f"{dex_name}_quoter.json"
                    if quoter_abi_path.exists():
                        with open(quoter_abi_path, "r") as f:
                            quoter_abi = json.load(f)
                        contracts["quoter"] = self.web3_manager.web3.eth.contract(
                            address=Web3.to_checksum_address(config["quoter"]),
                            abi=quoter_abi,
                        )
                        logger.info(f"Initialized quoter for {dex_name}")
                    else:
                        logger.error(f"Quoter ABI not found at {quoter_abi_path}")

                self.dex_contracts[dex_name] = contracts
                logger.info(f"Initialized all contracts for {dex_name}")

        except Exception as e:
            logger.error(f"Error initializing contracts: {e}")
            raise

    def _get_token_address(self, symbol: str) -> str:
        """Get token address from symbol"""
        token_config = self.token_configs.get(symbol)
        if not token_config:
            raise ValueError(f"Token {symbol} not found in config")
        return token_config["address"]

    def _get_token_decimals(self, symbol: str) -> int:
        """Get token decimals from symbol"""
        token_config = self.token_configs.get(symbol)
        if not token_config:
            raise ValueError(f"Token {symbol} not found in config")
        return token_config["decimals"]

    def _to_token_units(self, amount: Decimal, token: str) -> int:
        """Convert amount to token units based on decimals"""
        decimals = self._get_token_decimals(token)
        return int(amount * Decimal(10**decimals))

    def _from_token_units(self, amount: int, token: str) -> Decimal:
        """Convert token units to decimal based on decimals"""
        decimals = self._get_token_decimals(token)
        return Decimal(amount) / Decimal(10**decimals)

    async def get_quote(
        self, dex_name: str, token_in: str, token_out: str, amount_in: Decimal
    ) -> Tuple[bool, Optional[Decimal], Optional[str]]:
        """Get quote for trade"""
        try:
            # Skip if DEX is not configured
            if dex_name not in self.dex_configs:
                logger.warning(f"DEX {dex_name} not configured, skipping")
                return False, None, f"DEX {dex_name} not configured"

            # Skip if DEX contracts not initialized
            if dex_name not in self.dex_contracts:
                logger.warning(f"DEX {dex_name} contracts not initialized, skipping")
                return False, None, f"DEX {dex_name} contracts not initialized"

            contracts = self.dex_contracts[dex_name]
            version = self.dex_configs[dex_name].get("version", "v2")
            logger.debug(f"Getting quote from {dex_name} (version {version})")

            # Get token addresses
            token_in_address = Web3.to_checksum_address(
                self._get_token_address(token_in)
            )
            token_out_address = Web3.to_checksum_address(
                self._get_token_address(token_out)
            )

            # Convert amount to token units
            amount_in_units = self._to_token_units(amount_in, token_in)
            logger.debug(
                f"Converting {amount_in} {token_in} to {amount_in_units} units"
            )

            try:
                if version == "v2":
                    logger.debug(f"Using V2 quote method for {dex_name}")
                    # Use V2 router for quotes
                    if "router" not in contracts:
                        logger.error(f"Router contract not found for {dex_name}")
                        return False, None, f"Router contract not found for {dex_name}"

                    router = contracts["router"]
                    path = [token_in_address, token_out_address]
                    amounts = router.functions.getAmountsOut(
                        amount_in_units, path
                    ).call()
                    amount_out = amounts[1]
                else:
                    logger.debug(f"Using V3 quote method for {dex_name}")
                    # Use V3 quoter for quotes
                    if "quoter" not in contracts:
                        logger.error(f"Quoter contract not found for {dex_name}")
                        return False, None, f"Quoter contract not found for {dex_name}"

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
                        logger.debug(
                            f"Calling PancakeSwap quoteExactInputSingle with params: {params}"
                        )
                        quote_result = quoter.functions.quoteExactInputSingle(
                            params
                        ).call()
                    else:
                        # Uniswap V3 expects individual parameters
                        logger.debug(
                            f"Calling Uniswap quoteExactInputSingle with params: tokenIn={token_in_address}, tokenOut={token_out_address}, fee={fee}, amountIn={amount_in_units}"
                        )
                        quote_result = quoter.functions.quoteExactInputSingle(
                            token_in_address,
                            token_out_address,
                            fee,
                            amount_in_units,
                            0,  # sqrtPriceLimitX96
                        ).call()

                    # Extract amountOut from the result tuple
                    # quote_result format: (amountOut, sqrtPriceX96After, initializedTicksCrossed, gasEstimate)
                    amount_out = (
                        quote_result[0]
                        if isinstance(quote_result, (list, tuple))
                        else quote_result
                    )

                # Convert amount out from token units
                amount_out_decimal = self._from_token_units(amount_out, token_out)
                logger.debug(
                    f"Converting {amount_out} units to {amount_out_decimal} {token_out}"
                )

                return True, amount_out_decimal, None

            except Exception as e:
                logger.error(f"Error getting quote: {e}")
                logger.error(f"Error details:", exc_info=True)
                return False, None, str(e)

        except Exception as e:
            logger.error(f"Error getting quote: {e}")
            logger.error(f"Error details:", exc_info=True)
            return False, None, str(e)

    async def execute_trade(
        self,
        dex_name: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        wallet_address: str,
        private_key: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Execute trade on specified DEX"""
        try:
            # Skip if DEX is not configured
            if dex_name not in self.dex_configs:
                logger.warning(f"DEX {dex_name} not configured, skipping")
                return False, None, f"DEX {dex_name} not configured"

            # Skip if DEX contracts not initialized
            if dex_name not in self.dex_contracts:
                logger.warning(f"DEX {dex_name} contracts not initialized, skipping")
                return False, None, f"DEX {dex_name} contracts not initialized"

            contracts = self.dex_contracts[dex_name]
            version = self.dex_configs[dex_name].get("version", "v2")
            logger.debug(f"Executing trade on {dex_name} (version {version})")

            if "router" not in contracts:
                return False, None, f"Router contract not found for {dex_name}"

            router = contracts["router"]

            # Get token addresses
            token_in_address = Web3.to_checksum_address(
                self._get_token_address(token_in)
            )
            token_out_address = Web3.to_checksum_address(
                self._get_token_address(token_out)
            )

            # Convert amounts to token units
            amount_in_units = self._to_token_units(amount_in, token_in)
            min_out_units = self._to_token_units(min_amount_out, token_out)

            # Get deadline
            deadline = int(time.time()) + 300  # 5 minutes

            try:
                if version == "v2":
                    logger.debug(f"Using V2 trade method for {dex_name}")
                    # Build V2 transaction
                    path = [token_in_address, token_out_address]
                    tx = router.functions.swapExactTokensForTokens(
                        amount_in_units,
                        min_out_units,
                        path,
                        Web3.to_checksum_address(wallet_address),
                        deadline,
                    ).build_transaction(
                        {
                            "from": Web3.to_checksum_address(wallet_address),
                            "gas": 500000,
                            "nonce": self.web3_manager.web3.eth.get_transaction_count(
                                wallet_address
                            ),
                            "gasPrice": self.web3_manager.web3.eth.gas_price,
                        }
                    )
                else:
                    logger.debug(f"Using V3 trade method for {dex_name}")
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
                        tx = router.functions.exactInputSingle(
                            params
                        ).build_transaction(
                            {
                                "from": Web3.to_checksum_address(wallet_address),
                                "gas": 500000,
                                "nonce": self.web3_manager.web3.eth.get_transaction_count(
                                    wallet_address
                                ),
                                "gasPrice": self.web3_manager.web3.eth.gas_price,
                            }
                        )
                    else:
                        # Uniswap V3 expects individual parameters
                        tx = router.functions.exactInputSingle(
                            token_in_address,
                            token_out_address,
                            fee,
                            wallet_address,
                            deadline,
                            amount_in_units,
                            min_out_units,
                            0,  # sqrtPriceLimitX96
                        ).build_transaction(
                            {
                                "from": Web3.to_checksum_address(wallet_address),
                                "gas": 500000,
                                "nonce": self.web3_manager.web3.eth.get_transaction_count(
                                    wallet_address
                                ),
                                "gasPrice": self.web3_manager.web3.eth.gas_price,
                            }
                        )

                # Sign transaction
                signed_tx = self.web3_manager.web3.eth.account.sign_transaction(
                    tx, private_key
                )

                # Send transaction
                tx_hash = self.web3_manager.web3.eth.send_raw_transaction(
                    signed_tx.rawTransaction
                )

                # Wait for confirmation
                receipt = self.web3_manager.web3.eth.wait_for_transaction_receipt(
                    tx_hash
                )

                if receipt["status"] == 1:
                    logger.info(f"Trade executed successfully: {tx_hash.hex()}")
                    return True, tx_hash.hex(), None
                else:
                    logger.error(f"Trade failed: {tx_hash.hex()}")
                    return False, tx_hash.hex(), "Transaction reverted"

            except Exception as e:
                logger.error(f"Error executing trade: {e}")
                logger.error(f"Error details:", exc_info=True)
                return False, None, str(e)

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            logger.error(f"Error details:", exc_info=True)
            return False, None, str(e)


def create_dex_interface() -> DexInterface:
    """Factory function to create DexInterface instance"""
    return DexInterface()
