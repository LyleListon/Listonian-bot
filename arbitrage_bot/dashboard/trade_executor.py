"""Trade Executor Module"""

import logging
import time
import json
import os
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from web3 import Web3
from web3.contract import Contract
from pathlib import Path
from ..utils.eventlet_patch import manager as eventlet_manager

from .web3_utils import get_web3_utils
from ..dex.interfaces.dex_interface import create_dex_interface

logger = logging.getLogger("TradeExecutor")
logger.setLevel(logging.INFO)

# Get eventlet instance from manager
eventlet = eventlet_manager.eventlet

class TradeExecutor:
    """Trade executor class"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TradeExecutor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.web3_utils = get_web3_utils()
        self.dex_interface = create_dex_interface()
        self.token_contracts = {}
        self.router_contracts = {}
        self.last_nonce = None

        # Load DEX config from root directory
        root_dir = Path(__file__).parent.parent.parent
        with open(root_dir / "config.json", "r") as f:
            config = json.load(f)
            self.dex_config = {
                "dexes": config.get("dexes", {}),
                "tokens": config.get("tokens", {}),
                "pairs": config.get("pairs", []),
            }

        self._initialized = True
        logger.info("TradeExecutor initialized with config")
        logger.info("Loaded %d DEXes", len(self.dex_config['dexes']))
        logger.info("Loaded %d tokens", len(self.dex_config['tokens']))
        logger.info("Loaded %d pairs", len(self.dex_config['pairs']))

    def calculate_amount_out(
        self,
        amount_in: int,
        reserve_in: int,
        reserve_out: int,
        decimals_in: int,
        decimals_out: int,
    ) -> int:
        """Calculate output amount using constant product formula"""
        # Adjust reserves to same decimal places
        if decimals_in > decimals_out:
            reserve_out = reserve_out * (10 ** (decimals_in - decimals_out))
        elif decimals_out > decimals_in:
            reserve_in = reserve_in * (10 ** (decimals_out - decimals_in))

        amount_in_with_fee = amount_in * 997  # 0.3% fee
        numerator = amount_in_with_fee * reserve_out
        denominator = (reserve_in * 1000) + amount_in_with_fee

        # Adjust result back to correct decimals
        result = numerator // denominator
        if decimals_in > decimals_out:
            result = result // (10 ** (decimals_in - decimals_out))
        elif decimals_out > decimals_in:
            result = result * (10 ** (decimals_out - decimals_in))

        return result

    def load_abi(self, filename: str) -> Optional[list]:
        """Load contract ABI from file"""
        try:
            root_dir = Path(__file__).parent.parent.parent
            abi_path = root_dir / "abi" / filename
            with open(abi_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading ABI from %s: %s", filename, str(e))
            return None

    def execute_arbitrage_trade(
        self, opportunity: Dict[str, Any], wallet_address: str, private_key: str
    ) -> Dict[str, Any]:
        """Execute arbitrage trade"""
        try:
            logger.info("Executing arbitrage trade: %s", opportunity)

            # Get router contracts
            base_router = self.get_router_contract(opportunity["base_dex"])
            quote_router = self.get_router_contract(opportunity["quote_dex"])

            if not base_router or not quote_router:
                return {"success": False, "error": "Failed to get router contracts"}

            # Get token contracts
            tokens = opportunity["pair_name"].split("/")
            token0_contract = self.get_token_contract(tokens[0])
            token1_contract = self.get_token_contract(tokens[1])

            if not token0_contract or not token1_contract:
                return {"success": False, "error": "Failed to get token contracts"}

            # Calculate trade amount
            amount_in = Web3.to_wei(Decimal(opportunity["trade_amount"]), "ether")

            # Execute trade
            result = self.execute_direct_trade(
                opportunity,
                base_router,
                quote_router,
                token0_contract,
                token1_contract,
                amount_in,
                wallet_address,
            )

            return result

        except Exception as e:
            logger.error("Error executing arbitrage trade: %s", str(e))
            return {"success": False, "error": str(e)}

    def get_router_contract(self, dex_name: str) -> Optional[Contract]:
        """Get router contract for DEX"""
        try:
            if dex_name in self.router_contracts:
                return self.router_contracts[dex_name]

            if dex_name not in self.dex_config["dexes"]:
                logger.error("DEX %s not found in config", dex_name)
                return None

            dex_info = self.dex_config["dexes"][dex_name]
            router_address = dex_info["router"]

            # Load router ABI based on DEX version
            if dex_info.get("version") == "v3":
                if dex_name == "baseswap":
                    router_abi = self.load_abi("baseswap_router.json")
                else:
                    router_abi = self.load_abi("pancakeswap_router.json")
            else:
                router_abi = self.load_abi("IUniswapV2Router.json")

            if not router_abi:
                logger.error("Failed to load router ABI for %s", dex_name)
                return None

            # Create contract
            router = self.web3_utils.get_contract(router_address, router_abi)
            self.router_contracts[dex_name] = router

            # Log router info
            logger.info("Router contract loaded for %s at %s", dex_name, router_address)

            # Test router connection
            try:
                factory = router.functions.factory().call()
                logger.info("Router factory address: %s", factory)
            except Exception as e:
                logger.error("Failed to get factory from router: %s", str(e))

            return router

        except Exception as e:
            logger.error("Error getting router contract: %s", str(e))
            return None

    def get_token_contract(self, token_symbol: str) -> Optional[Contract]:
        """Get token contract"""
        try:
            if token_symbol in self.token_contracts:
                return self.token_contracts[token_symbol]

            if token_symbol not in self.dex_config["tokens"]:
                logger.error("Token %s not found in config", token_symbol)
                return None

            token_info = self.dex_config["tokens"][token_symbol]
            token_address = token_info["address"]

            # Load token ABI
            token_abi = self.load_abi("ERC20.json")
            if not token_abi:
                logger.error("Failed to load ERC20 ABI")
                return None

            # Create contract
            token = self.web3_utils.get_contract(token_address, token_abi)
            self.token_contracts[token_symbol] = token
            return token

        except Exception as e:
            logger.error("Error getting token contract: %s", str(e))
            return None

    def execute_direct_trade(
        self,
        opportunity: Dict[str, Any],
        base_router: Contract,
        quote_router: Contract,
        token0_contract: Contract,
        token1_contract: Contract,
        amount_in: int,
        wallet_address: str,
    ) -> Dict[str, Any]:
        """Execute direct trade"""
        try:
            # Get deadline
            deadline = int(time.time()) + 300  # 5 minutes

            # Get nonce and gas price
            nonce = self.web3_utils.w3.eth.get_transaction_count(wallet_address)
            gas_price = self.web3_utils.w3.eth.gas_price

            # Ensure minimum gas price
            min_gas_price = Web3.to_wei(0.1, "gwei")  # 0.1 gwei minimum
            gas_price = max(
                gas_price * 5, min_gas_price
            )  # Use at least 5x current gas price

            # Get WETH address from router
            weth_address = base_router.functions.WETH().call()
            logger.info("WETH address: %s", weth_address)
            logger.info("USDC address: %s", token1_contract.address)

            # Get DEX info
            dex_info = self.dex_config["dexes"][opportunity["base_dex"]]

            # Build transaction based on DEX version
            if dex_info.get("version") == "v3":
                # For PancakeSwap v3
                params = {
                    "tokenIn": weth_address,
                    "tokenOut": token1_contract.address,
                    "fee": dex_info.get(
                        "fee", 2500
                    ),  # Default to 0.25% if not specified
                    "recipient": wallet_address,
                    "amountIn": amount_in,
                    "amountOutMinimum": 0,  # Will be set after quote
                    "sqrtPriceLimitX96": 0,  # No price limit
                }

                # Get quote
                try:
                    amount_out = base_router.functions.exactInputSingle(
                        params
                    ).call()
                    amount_out_min = int(amount_out * 0.995)  # 0.5% slippage
                    params["amountOutMinimum"] = amount_out_min
                    logger.info("Quote received: %d wei", amount_out)
                    logger.info("Minimum output: %d wei", amount_out_min)
                except Exception as e:
                    logger.error("Failed to get quote: %s", str(e))
                    return {"success": False, "error": "Failed to get quote: %s" % str(e)}

                # Build transaction
                tx_params = {
                    "from": wallet_address,
                    "value": amount_in,  # Send ETH directly
                    "gas": 500000,  # High gas limit for testing
                    "nonce": nonce,
                    "gasPrice": gas_price,
                }

                # Build swap transaction
                swap_tx = base_router.functions.exactInputSingle(
                    params
                ).build_transaction(tx_params)

            else:
                # For BaseSwap v2
                path = [weth_address, token1_contract.address]

                # Get quote
                try:
                    amounts = base_router.functions.getAmountsOut(
                        amount_in, path
                    ).call()
                    amount_out = amounts[1]
                    amount_out_min = int(amount_out * 0.995)  # 0.5% slippage
                    logger.info("Quote received: %d wei", amount_out)
                    logger.info("Minimum output: %d wei", amount_out_min)
                except Exception as e:
                    logger.error("Failed to get quote: %s", str(e))
                    return {"success": False, "error": "Failed to get quote: %s" % str(e)}

                # Build transaction
                tx_params = {
                    "from": wallet_address,
                    "value": amount_in,  # Send ETH directly
                    "gas": 500000,  # High gas limit for testing
                    "nonce": nonce,
                    "gasPrice": gas_price,
                }

                # Build swap transaction
                swap_tx = base_router.functions.swapExactETHForTokens(
                    amount_out_min,  # amountOutMin
                    path,  # path
                    wallet_address,  # to
                    deadline,  # deadline
                ).build_transaction(tx_params)

            # Log transaction details
            logger.info("Transaction parameters: %s", tx_params)

            # Send transaction
            tx_hash = self.web3_utils.eth_call(swap_tx)
            if not tx_hash:
                return {"success": False, "error": "Failed to send swap transaction"}

            # Wait for confirmation
            receipt = self.web3_utils.w3.eth.wait_for_transaction_receipt(tx_hash)
            if not receipt["status"]:
                return {"success": False, "error": "Swap transaction failed"}

            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt["gasUsed"],
                "used_flash_loan": False,
            }

        except Exception as e:
            logger.error("Direct trade execution error: %s", str(e))
            return {"success": False, "error": str(e)}


def get_trade_executor() -> TradeExecutor:
    """Get trade executor instance"""
    return TradeExecutor()
