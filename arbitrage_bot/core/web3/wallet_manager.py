"""
Wallet Manager Module

Manages wallet operations including:
- Balance monitoring
- Token ratio maintenance
- Gas reserves
- Profit withdrawals
"""

import logging
import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional
from decimal import Decimal
from web3 import Web3
from eth_typing import ChecksumAddress

from functools import wraps
from .web3_manager import Web3Manager
from arbitrage_bot.utils.async_manager import AsyncLock
from arbitrage_bot.core.dex.dex_manager import DexManager

logger = logging.getLogger(__name__)

def log_async_operation(operation_name: str):
    """Decorator for logging async operations with timing and context."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation_id = str(uuid.uuid4())[:8]
            start_time = time.time()
            self_obj = args[0] if args else None
            
            logger.debug(
                f"Starting {operation_name} [id={operation_id}] "
                f"wallet={getattr(self_obj, 'wallet_address', 'unknown')}"
            )
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"Completed {operation_name} [id={operation_id}] "
                    f"duration={duration:.3f}s"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Failed {operation_name} [id={operation_id}] "
                    f"duration={duration:.3f}s error={str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator

class WalletManager:
    """Manages wallet operations and balance maintenance."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        dex_manager: DexManager,
        config: Dict[str, Any]
    ):
        """
        Initialize wallet manager.

        Args:
            web3_manager: Web3Manager instance
            dex_manager: DexManager instance
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.config = config
        
        # Initialize locks
        self._balance_lock = AsyncLock()
        self._swap_lock = AsyncLock()
        
        # Load settings
        wallet_config = config.get('wallet', {})
        self.min_eth_balance = Web3.to_wei(
            wallet_config.get('min_eth_balance', 0.1),
            'ether'
        )
        self.max_eth_balance = Web3.to_wei(
            wallet_config.get('max_eth_balance', 1.0),
            'ether'
        )
        self.target_token_ratios = wallet_config.get('target_token_ratios', {})
        self.rebalance_threshold = wallet_config.get('rebalance_threshold', 0.1)
        self.profit_withdrawal_threshold = Web3.to_wei(
            wallet_config.get('profit_withdrawal_threshold', 1.0),
            'ether'
        )

    @log_async_operation("wallet_initialization")
    async def initialize(self) -> bool:
        """Initialize wallet manager."""
        try:
            # Verify wallet access
            # Set wallet address using async web3 instance
            self.wallet_address = Web3.to_checksum_address(
                Web3().eth.account.from_key(
                    self.config['web3']['wallet_key']
                ).address
            )
            balance = await self.web3_manager.w3.eth.get_balance(
                self.wallet_address
            )
            logger.debug(f"Verifying wallet access for {self.wallet_address}")
            logger.info(
                f"Wallet initialized successfully: "
                f"address={self.wallet_address} "
                f"balance={Web3.from_wei(balance, 'ether')} ETH"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to initialize wallet manager: {str(e)}",
                exc_info=True
            )
            return False

    @log_async_operation("balance_maintenance")
    async def check_and_maintain_balances(self):
        """Check and maintain token balances according to target ratios."""
        async with self._balance_lock:
            try:
                # Get current balances
                eth_balance = await self.web3_manager.w3.eth.get_balance(
                    self.wallet_address
                )
                token_balances = await self._get_token_balances()
                
                logger.debug(
                    f"Current balances - ETH: {Web3.from_wei(eth_balance, 'ether')}, "
                    f"Tokens: {', '.join(f'{k}: {v}' for k, v in token_balances.items())}"
                )
                
                # Check ETH balance
                if eth_balance < self.min_eth_balance:
                    logger.info(
                        f"ETH balance {Web3.from_wei(eth_balance, 'ether')} below minimum "
                        f"{Web3.from_wei(self.min_eth_balance, 'ether')}, replenishing"
                    )
                    await self._replenish_eth()
                elif eth_balance > self.max_eth_balance:
                    logger.info(
                        f"ETH balance {Web3.from_wei(eth_balance, 'ether')} above maximum "
                        f"{Web3.from_wei(self.max_eth_balance, 'ether')}, converting excess"
                    )
                    await self._convert_excess_eth()
                
                # Check token ratios
                total_value_eth = eth_balance
                for token, balance in token_balances.items():
                    price = await self.web3_manager.get_token_prices([token])
                    value_eth = int(balance * price[token])
                    total_value_eth += value_eth
                    logger.debug(
                        f"Token {token} value: {Web3.from_wei(value_eth, 'ether')} ETH "
                        f"(price: {price[token]})"
                    )
                
                # Rebalance if needed
                for token, target_ratio in self.target_token_ratios.items():
                    current_balance = token_balances.get(token, 0)
                    price = await self.web3_manager.get_token_prices([token])
                    current_value_eth = int(current_balance * price[token])
                    current_ratio = current_value_eth / total_value_eth
                    
                    if abs(current_ratio - target_ratio) > self.rebalance_threshold:
                        logger.info(
                            f"Rebalancing {token}: current ratio {current_ratio:.3f} vs "
                            f"target {target_ratio:.3f}"
                        )
                        await self._rebalance_token(
                            token,
                            current_value_eth,
                            target_ratio * total_value_eth
                        )
                
                # Check for profit withdrawal
                await self._check_profit_withdrawal()
                
            except Exception as e:
                logger.error(
                    f"Balance maintenance error: {str(e)}",
                    exc_info=True
                )

    @log_async_operation("get_token_balances")
    async def _get_token_balances(self) -> Dict[str, int]:
        """Get balances for all configured tokens."""
        balances = {}
        logger.debug("Fetching token balances")
        for token in self.config['tokens']:
            logger.debug(f"Fetching balance for token: {token}")
            contract = self.web3_manager.w3.eth.contract(
                address=Web3.to_checksum_address(
                    self.config['tokens'][token]['address']
                ),
                abi=self.web3_manager.load_abi('ERC20')
            )
            balance = await contract.functions.balanceOf(
                self.wallet_address
            ).call()
            balances[token] = balance
            logger.debug(f"Token {token} balance: {balance}")
        return balances

    @log_async_operation("eth_replenishment")
    async def _replenish_eth(self):
        """Convert tokens to ETH to maintain minimum balance."""
        logger.debug("Starting ETH replenishment")
        try:
            eth_needed = self.min_eth_balance - await self.web3_manager.w3.eth.get_balance(
                self.wallet_address
            )
            logger.info(
                f"Need {Web3.from_wei(eth_needed, 'ether')} ETH to reach minimum balance"
            )
            
            # Find best token to convert
            token_balances = await self._get_token_balances()
            best_token = None
            best_price = 0
            
            for token, balance in token_balances.items():
                if balance > 0:
                    price = await self.web3_manager.get_token_prices([token])
                    if price[token] > best_price:
                        best_token = token
                        best_price = price[token]
                        logger.debug(
                            f"Found better token for conversion: {token} "
                            f"(price: {price[token]})"
                        )
            
            if best_token:
                # Calculate amount to swap
                amount_in = int(eth_needed / best_price * 1.02)  # Add 2% slippage
                logger.info(
                    f"Converting {amount_in} {best_token} to ETH "
                    f"(expected: {Web3.from_wei(eth_needed, 'ether')} ETH)"
                )
                
                # Execute swap
                await self._execute_swap(
                    best_token,
                    self.config['tokens']['WETH']['address'],
                    amount_in
                )
            else:
                logger.warning("No suitable token found for ETH replenishment")
                
        except Exception as e:
            logger.error(
                f"ETH replenishment error: {str(e)}",
                exc_info=True
            )

    @log_async_operation("excess_eth_conversion")
    async def _convert_excess_eth(self):
        """Convert excess ETH to tokens according to target ratios."""
        try:
            excess_eth = await self.web3_manager.w3.eth.get_balance(
                self.wallet_address
            ) - self.max_eth_balance
            logger.info(
                f"Converting excess ETH: {Web3.from_wei(excess_eth, 'ether')} ETH"
            )
            
            if excess_eth > 0:
                # Distribute excess according to target ratios
                for token, ratio in self.target_token_ratios.items():
                    if ratio > 0:
                        amount_eth = int(excess_eth * ratio)
                        logger.debug(
                            f"Converting {Web3.from_wei(amount_eth, 'ether')} ETH to "
                            f"{token} (ratio: {ratio:.3f})"
                        )
                        await self._execute_swap(
                            self.config['tokens']['WETH']['address'],
                            self.config['tokens'][token]['address'],
                            amount_eth
                        )
                        
        except Exception as e:
            logger.error(
                f"Excess ETH conversion error: {str(e)}",
                exc_info=True
            )

    @log_async_operation("token_rebalancing")
    async def _rebalance_token(
        self,
        token: str,
        current_value_eth: int,
        target_value_eth: int
    ):
        """Rebalance specific token to target value."""
        try:
            async with self._swap_lock:
                logger.debug("Acquired swap lock for token rebalancing")
                if current_value_eth < target_value_eth:
                    # Need to buy more
                    eth_needed = target_value_eth - current_value_eth
                    logger.info(
                        f"Buying {Web3.from_wei(eth_needed, 'ether')} ETH worth of {token}"
                    )
                    await self._execute_swap(
                        self.config['tokens']['WETH']['address'],
                        token,
                        eth_needed
                    )
                else:
                    # Need to sell some
                    eth_excess = current_value_eth - target_value_eth
                    price = (await self.web3_manager.get_token_prices([token]))[token]
                    tokens_to_sell = int(eth_excess / price)
                    logger.info(
                        f"Selling {tokens_to_sell} {token} "
                        f"(worth: {Web3.from_wei(eth_excess, 'ether')} ETH)"
                    )
                    await self._execute_swap(
                        token,
                        self.config['tokens']['WETH']['address'],
                        tokens_to_sell
                    )
                    
        except Exception as e:
            logger.error(
                f"Token rebalancing error: {str(e)}",
                exc_info=True
            )
        finally:
            logger.debug("Released swap lock after token rebalancing")

    @log_async_operation("swap_execution")
    async def _execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ):
        """Execute token swap using best available DEX."""
        try:
            logger.debug(
                f"Finding best DEX for swap: {amount_in} {token_in} -> {token_out}"
            )
            # Find best DEX for swap
            best_dex = None
            best_output = 0
            
            for dex_name in self.dex_manager.dexes:
                dex = self.dex_manager.dexes[dex_name]
                quote = await dex.get_quote_from_quoter(
                    amount_in,
                    [token_in, token_out]
                )
                if quote and quote > best_output:
                    best_dex = dex
                    best_output = quote
                    logger.debug(
                        f"Found better quote on {dex_name}: {best_output}"
                    )
            
            if best_dex:
                logger.info(
                    f"Executing swap on {best_dex.__class__.__name__}: "
                    f"{amount_in} {token_in} -> {best_output} {token_out}"
                )
                # Execute swap
                await best_dex.swap_exact_tokens_for_tokens(
                    amount_in,
                    int(best_output * 0.995),  # 0.5% slippage
                    [token_in, token_out],
                    self.wallet_address,
                    int(asyncio.get_event_loop().time()) + 180  # 3 min deadline
                )
                logger.info(f"Swap executed successfully")
                
        except Exception as e:
            logger.error(
                f"Swap execution error: {str(e)}",
                exc_info=True
            )

    @log_async_operation("profit_withdrawal")
    async def _check_profit_withdrawal(self):
        """Check and process profit withdrawal if threshold reached."""
        try:
            eth_balance = await self.web3_manager.w3.eth.get_balance(
                self.wallet_address
            )
            logger.debug(
                f"Checking profit withdrawal - Current balance: "
                f"{Web3.from_wei(eth_balance, 'ether')} ETH"
            )
            
            if eth_balance > self.profit_withdrawal_threshold:
                profit_amount = eth_balance - self.max_eth_balance
                if profit_amount > 0:
                    logger.info(
                        f"Withdrawing profits: {Web3.from_wei(profit_amount, 'ether')} ETH"
                    )
                    # Get withdrawal address
                    withdrawal_address = self.config['wallet'].get(
                        'profit_withdrawal_address',
                        self.wallet_address
                    )
                    
                    # Send profit
                    tx = {
                        'to': withdrawal_address,
                        'value': profit_amount,
                        'gas': 21000,
                        'gasPrice': await self.web3_manager.w3.eth.gas_price,
                        'nonce': await self.web3_manager.w3.eth.get_transaction_count(
                            self.wallet_address
                        )
                    }
                    logger.debug(f"Preparing withdrawal transaction: {tx}")
                    
                    signed_tx = self.web3_manager.w3.eth.account.sign_transaction(
                        tx,
                        self.config['web3']['wallet_key']
                    )
                    
                    await self.web3_manager.w3.eth.send_raw_transaction(
                        signed_tx.rawTransaction
                    )
                    
                    logger.info(
                        f"Successfully withdrew {Web3.from_wei(profit_amount, 'ether')} ETH "
                        f"in profits to {withdrawal_address} "
                        f"(tx hash: {signed_tx.hash.hex()})"
                    )
                    
        except Exception as e:
            logger.error(
                f"Profit withdrawal error: {str(e)}",
                exc_info=True
            )

@log_async_operation("wallet_manager_creation")
async def create_wallet_manager(
    web3_manager: Web3Manager,
    dex_manager: DexManager,
    config: Dict[str, Any]
) -> WalletManager:
    """
    Create and initialize a WalletManager instance.

    Args:
        web3_manager: Web3Manager instance
        dex_manager: DexManager instance
        config: Configuration dictionary

    Returns:
        Initialized WalletManager instance
    """
    logger.debug("Creating new WalletManager instance")
    manager = WalletManager(web3_manager, dex_manager, config)
    await manager.initialize()
    return manager