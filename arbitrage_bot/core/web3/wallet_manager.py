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
from typing import Dict, List, Any, Optional
from decimal import Decimal
from web3 import Web3
from eth_typing import ChecksumAddress

from .web3_manager import Web3Manager
from arbitrage_bot.utils.async_manager import AsyncLock
from arbitrage_bot.core.dex.dex_manager import DexManager

logger = logging.getLogger(__name__)

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
            logger.info(
                f"Wallet initialized with {Web3.from_wei(balance, 'ether')} ETH"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize wallet manager: {e}")
            return False

    async def check_and_maintain_balances(self):
        """Check and maintain token balances according to target ratios."""
        async with self._balance_lock:
            try:
                # Get current balances
                eth_balance = await self.web3_manager.w3.eth.get_balance(
                    self.wallet_address
                )
                token_balances = await self._get_token_balances()
                
                # Check ETH balance
                if eth_balance < self.min_eth_balance:
                    await self._replenish_eth()
                elif eth_balance > self.max_eth_balance:
                    await self._convert_excess_eth()
                
                # Check token ratios
                total_value_eth = eth_balance
                for token, balance in token_balances.items():
                    price = await self.web3_manager.get_token_prices([token])
                    value_eth = int(balance * price[token])
                    total_value_eth += value_eth
                
                # Rebalance if needed
                for token, target_ratio in self.target_token_ratios.items():
                    current_balance = token_balances.get(token, 0)
                    price = await self.web3_manager.get_token_prices([token])
                    current_value_eth = int(current_balance * price[token])
                    current_ratio = current_value_eth / total_value_eth
                    
                    if abs(current_ratio - target_ratio) > self.rebalance_threshold:
                        await self._rebalance_token(
                            token,
                            current_value_eth,
                            target_ratio * total_value_eth
                        )
                
                # Check for profit withdrawal
                await self._check_profit_withdrawal()
                
            except Exception as e:
                logger.error(f"Balance maintenance error: {e}")

    async def _get_token_balances(self) -> Dict[str, int]:
        """Get balances for all configured tokens."""
        balances = {}
        for token in self.config['tokens']:
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
        return balances

    async def _replenish_eth(self):
        """Convert tokens to ETH to maintain minimum balance."""
        try:
            eth_needed = self.min_eth_balance - await self.web3_manager.w3.eth.get_balance(
                self.wallet_address
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
            
            if best_token:
                # Calculate amount to swap
                amount_in = int(eth_needed / best_price * 1.02)  # Add 2% slippage
                
                # Execute swap
                await self._execute_swap(
                    best_token,
                    self.config['tokens']['WETH']['address'],
                    amount_in
                )
                
        except Exception as e:
            logger.error(f"ETH replenishment error: {e}")

    async def _convert_excess_eth(self):
        """Convert excess ETH to tokens according to target ratios."""
        try:
            excess_eth = await self.web3_manager.w3.eth.get_balance(
                self.wallet_address
            ) - self.max_eth_balance
            
            if excess_eth > 0:
                # Distribute excess according to target ratios
                for token, ratio in self.target_token_ratios.items():
                    if ratio > 0:
                        amount_eth = int(excess_eth * ratio)
                        await self._execute_swap(
                            self.config['tokens']['WETH']['address'],
                            self.config['tokens'][token]['address'],
                            amount_eth
                        )
                        
        except Exception as e:
            logger.error(f"Excess ETH conversion error: {e}")

    async def _rebalance_token(
        self,
        token: str,
        current_value_eth: int,
        target_value_eth: int
    ):
        """Rebalance specific token to target value."""
        try:
            async with self._swap_lock:
                if current_value_eth < target_value_eth:
                    # Need to buy more
                    eth_needed = target_value_eth - current_value_eth
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
                    await self._execute_swap(
                        token,
                        self.config['tokens']['WETH']['address'],
                        tokens_to_sell
                    )
                    
        except Exception as e:
            logger.error(f"Token rebalancing error: {e}")

    async def _execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: int
    ):
        """Execute token swap using best available DEX."""
        try:
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
            
            if best_dex:
                # Execute swap
                await best_dex.swap_exact_tokens_for_tokens(
                    amount_in,
                    int(best_output * 0.995),  # 0.5% slippage
                    [token_in, token_out],
                    self.wallet_address,
                    int(asyncio.get_event_loop().time()) + 180  # 3 min deadline
                )
                
        except Exception as e:
            logger.error(f"Swap execution error: {e}")

    async def _check_profit_withdrawal(self):
        """Check and process profit withdrawal if threshold reached."""
        try:
            eth_balance = await self.web3_manager.w3.eth.get_balance(
                self.wallet_address
            )
            
            if eth_balance > self.profit_withdrawal_threshold:
                profit_amount = eth_balance - self.max_eth_balance
                if profit_amount > 0:
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
                    
                    signed_tx = self.web3_manager.w3.eth.account.sign_transaction(
                        tx,
                        self.config['web3']['wallet_key']
                    )
                    
                    await self.web3_manager.w3.eth.send_raw_transaction(
                        signed_tx.rawTransaction
                    )
                    
                    logger.info(
                        f"Withdrew {Web3.from_wei(profit_amount, 'ether')} ETH "
                        f"in profits to {withdrawal_address}"
                    )
                    
        except Exception as e:
            logger.error(f"Profit withdrawal error: {e}")

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
    manager = WalletManager(web3_manager, dex_manager, config)
    await manager.initialize()
    return manager