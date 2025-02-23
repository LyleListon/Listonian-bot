"""Trade Executor Module"""

import logging
import time
import json
import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from web3 import Web3
from web3.contract import Contract
from pathlib import Path

from .web3_utils import get_web3_utils
from ..dex.interfaces.dex_interface import create_dex_interface

logger = logging.getLogger("TradeExecutor")
logger.setLevel(logging.INFO)

class TradeExecutor:
    """Trade executor class"""

    _instance = None
    _initialized = False
    _lock = asyncio.Lock()
    _contract_lock = asyncio.Lock()
    _nonce_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TradeExecutor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.web3_utils = None
        self.dex_interface = None
        self.token_contracts = {}
        self.router_contracts = {}
        self.last_nonce = None
        self.transaction_timeout = 300  # 5 minutes
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the trade executor."""
        if self._initialized:
            return True

        async with self._lock:
            if self._initialized:  # Double-check under lock
                return True

            try:
                # Initialize web3 utils
                self.web3_utils = await get_web3_utils()
                self.dex_interface = await create_dex_interface()

                # Load DEX config from root directory
                root_dir = Path(__file__).parent.parent.parent
                async with asyncio.Lock():
                    with open(root_dir / "config.json", "r") as f:
                        config = json.load(f)
                        self.dex_config = {
                            "dexes": config.get("dexes", {}),
                            "tokens": config.get("tokens", {}),
                            "pairs": config.get("pairs", []),
                        }

                self._initialized = True
                logger.info("TradeExecutor initialized with config")
                logger.info("Loaded {} DEXes".format(len(self.dex_config['dexes'])))
                logger.info("Loaded {} tokens".format(len(self.dex_config['tokens'])))
                logger.info("Loaded {} pairs".format(len(self.dex_config['pairs'])))
                return True

            except Exception as e:
                logger.error("Failed to initialize trade executor: {}".format(e))
                return False

    def calculate_amount_out(self, amount_in, reserve_in, reserve_out, decimals_in, decimals_out):
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

    async def load_abi(self, filename):
        """Load contract ABI from file"""
        try:
            root_dir = Path(__file__).parent.parent.parent
            abi_path = root_dir / "abi" / filename
            async with asyncio.Lock():
                with open(abi_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Error loading ABI from {}: {}".format(filename, str(e)))
            return None

    async def execute_arbitrage_trade(self, opportunity, wallet_address, private_key):
        """Execute arbitrage trade"""
        try:
            if not self._initialized and not await self.initialize():
                return {"success": False, "error": "Trade executor not initialized"}

            logger.info("Executing arbitrage trade: {}".format(opportunity))

            # Get router contracts
            base_router = await self.get_router_contract(opportunity["base_dex"])
            quote_router = await self.get_router_contract(opportunity["quote_dex"])

            if not base_router or not quote_router:
                return {"success": False, "error": "Failed to get router contracts"}

            # Get token contracts
            tokens = opportunity["pair_name"].split("/")
            token0_contract = await self.get_token_contract(tokens[0])
            token1_contract = await self.get_token_contract(tokens[1])

            if not token0_contract or not token1_contract:
                return {"success": False, "error": "Failed to get token contracts"}

            # Calculate trade amount
            amount_in = Web3.to_wei(Decimal(opportunity["trade_amount"]), "ether")

            # Execute trade
            result = await self.execute_direct_trade(
                opportunity,
                base_router,
                quote_router,
                token0_contract,
                token1_contract,
                amount_in,
                wallet_address
            )

            return result

        except Exception as e:
            logger.error("Error executing arbitrage trade: {}".format(e))
            return {"success": False, "error": str(e)}

    async def get_router_contract(self, dex_name):
        """Get router contract for DEX"""
        try:
            async with self._contract_lock:
                if dex_name in self.router_contracts:
                    return self.router_contracts[dex_name]

                if dex_name not in self.dex_config["dexes"]:
                    logger.error("DEX {} not found in config".format(dex_name))
                    return None

                dex_info = self.dex_config["dexes"][dex_name]
                router_address = dex_info["router"]

                # Load router ABI based on DEX version
                if dex_info.get("version") == "v3":
                    if dex_name == "baseswap":
                        router_abi = await self.load_abi("baseswap_router.json")
                    else:
                        router_abi = await self.load_abi("pancakeswap_router.json")
                else:
                    router_abi = await self.load_abi("IUniswapV2Router.json")

                if not router_abi:
                    logger.error("Failed to load router ABI for {}".format(dex_name))
                    return None

                # Create contract
                router = await self.web3_utils.get_contract(router_address, router_abi)
                self.router_contracts[dex_name] = router

                # Log router info
                logger.info("Router contract loaded for {} at {}".format(dex_name, router_address))

                # Test router connection
                try:
                    factory = await router.functions.factory().call()
                    logger.info("Router factory address: {}".format(factory))
                except Exception as e:
                    logger.error("Failed to get factory from router: {}".format(e))

                return router

        except Exception as e:
            logger.error("Error getting router contract: {}".format(e))
            return None

    async def get_token_contract(self, token_symbol):
        """Get token contract"""
        try:
            async with self._contract_lock:
                if token_symbol in self.token_contracts:
                    return self.token_contracts[token_symbol]

                if token_symbol not in self.dex_config["tokens"]:
                    logger.error("Token {} not found in config".format(token_symbol))
                    return None

                token_info = self.dex_config["tokens"][token_symbol]
                token_address = token_info["address"]

                # Load token ABI
                token_abi = await self.load_abi("ERC20.json")
                if not token_abi:
                    logger.error("Failed to load ERC20 ABI")
                    return None

                # Create contract
                token = await self.web3_utils.get_contract(token_address, token_abi)
                self.token_contracts[token_symbol] = token
                return token

        except Exception as e:
            logger.error("Error getting token contract: {}".format(e))
            return None

    async def execute_direct_trade(self, opportunity, base_router, quote_router,
                                 token0_contract, token1_contract, amount_in, wallet_address):
        """Execute direct trade"""
        try:
            # Get deadline
            deadline = int(time.time()) + self.transaction_timeout

            # Get nonce and gas price
            async with self._nonce_lock:
                nonce = await self.web3_utils.get_transaction_count(wallet_address)
                gas_price = await self.web3_utils.w3.eth.gas_price

                # Ensure minimum gas price
                min_gas_price = Web3.to_wei(0.1, "gwei")  # 0.1 gwei minimum
                gas_price = max(gas_price * 5, min_gas_price)  # Use at least 5x current gas price

            # Get WETH address from router
            weth_address = await base_router.functions.WETH().call()
            logger.info("WETH address: {}".format(weth_address))
            logger.info("USDC address: {}".format(token1_contract.address))

            # Get DEX info
            dex_info = self.dex_config["dexes"][opportunity["base_dex"]]

            # Build transaction based on DEX version
            if dex_info.get("version") == "v3":
                return await self._execute_v3_trade(
                    opportunity, base_router, weth_address, token1_contract,
                    amount_in, wallet_address, nonce, gas_price
                )
            else:
                return await self._execute_v2_trade(
                    opportunity, base_router, weth_address, token1_contract,
                    amount_in, wallet_address, nonce, gas_price, deadline
                )

        except Exception as e:
            logger.error("Direct trade execution error: {}".format(e))
            return {"success": False, "error": str(e)}

    async def _execute_v3_trade(self, opportunity, router, weth_address, token_out,
                              amount_in, wallet_address, nonce, gas_price):
        """Execute v3 trade"""
        try:
            params = {
                "tokenIn": weth_address,
                "tokenOut": token_out.address,
                "fee": opportunity.get("fee", 2500),  # Default to 0.25%
                "recipient": wallet_address,
                "amountIn": amount_in,
                "amountOutMinimum": 0,  # Will be set after quote
                "sqrtPriceLimitX96": 0  # No price limit
            }

            # Get quote
            try:
                amount_out = await router.functions.exactInputSingle(params).call()
                amount_out_min = int(amount_out * 0.995)  # 0.5% slippage
                params["amountOutMinimum"] = amount_out_min
                logger.info("Quote received: {} wei".format(amount_out))
                logger.info("Minimum output: {} wei".format(amount_out_min))
            except Exception as e:
                logger.error("Failed to get quote: {}".format(e))
                return {"success": False, "error": "Failed to get quote: {}".format(e)}

            # Build transaction
            tx_params = {
                "from": wallet_address,
                "value": amount_in,
                "gas": 500000,
                "nonce": nonce,
                "gasPrice": gas_price
            }

            swap_tx = await router.functions.exactInputSingle(params).build_transaction(tx_params)
            return await self._send_and_wait_transaction(swap_tx)

        except Exception as e:
            logger.error("V3 trade execution error: {}".format(e))
            return {"success": False, "error": str(e)}

    async def _execute_v2_trade(self, opportunity, router, weth_address, token_out,
                              amount_in, wallet_address, nonce, gas_price, deadline):
        """Execute v2 trade"""
        try:
            path = [weth_address, token_out.address]

            # Get quote
            try:
                amounts = await router.functions.getAmountsOut(amount_in, path).call()
                amount_out = amounts[1]
                amount_out_min = int(amount_out * 0.995)  # 0.5% slippage
                logger.info("Quote received: {} wei".format(amount_out))
                logger.info("Minimum output: {} wei".format(amount_out_min))
            except Exception as e:
                logger.error("Failed to get quote: {}".format(e))
                return {"success": False, "error": "Failed to get quote: {}".format(e)}

            # Build transaction
            tx_params = {
                "from": wallet_address,
                "value": amount_in,
                "gas": 500000,
                "nonce": nonce,
                "gasPrice": gas_price
            }

            swap_tx = await router.functions.swapExactETHForTokens(
                amount_out_min,
                path,
                wallet_address,
                deadline
            ).build_transaction(tx_params)
            return await self._send_and_wait_transaction(swap_tx)

        except Exception as e:
            logger.error("V2 trade execution error: {}".format(e))
            return {"success": False, "error": str(e)}

    async def _send_and_wait_transaction(self, transaction):
        """Send transaction and wait for confirmation"""
        try:
            # Send transaction
            tx_hash = await self.web3_utils.eth_call(transaction)
            if not tx_hash:
                return {"success": False, "error": "Failed to send swap transaction"}

            # Wait for confirmation with timeout
            try:
                receipt = await self.web3_utils.wait_for_transaction_receipt(
                    tx_hash,
                    timeout=self.transaction_timeout
                )
            except asyncio.TimeoutError:
                return {"success": False, "error": "Transaction confirmation timeout"}

            if not receipt["status"]:
                return {"success": False, "error": "Swap transaction failed"}

            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt["gasUsed"],
                "used_flash_loan": False
            }

        except Exception as e:
            logger.error("Transaction execution error: {}".format(e))
            return {"success": False, "error": str(e)}

async def get_trade_executor():
    """Get trade executor instance"""
    executor = TradeExecutor()
    if not executor._initialized:
        await executor.initialize()
    return executor
