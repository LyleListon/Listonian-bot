"""Arbitrage execution engine."""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal

from ..web3.web3_manager import Web3Manager, create_web3_manager
from ..dex.dex_manager import DEXManager, create_dex_manager
from ..gas.gas_optimizer import GasOptimizer, create_gas_optimizer
from ..dex.utils import (
    calculate_price_impact,
    estimate_gas_cost,
    format_amount_with_decimals,
    COMMON_TOKENS
)
from ..gas.gas_optimizer import GasOptimizer

logger = logging.getLogger(__name__)

class ArbitrageExecutor:
    """Executes arbitrage opportunities across multiple DEXs."""

    def __init__(
        self,
        dex_manager: DEXManager,
        web3_manager: Web3Manager,
        gas_optimizer: GasOptimizer,
        min_profit_usd: float = 0.05,  # Minimum profit in USD (5 cents)
        max_price_impact: float = 0.01,  # Maximum 1% price impact
        slippage_tolerance: float = 0.005,  # 0.5% slippage tolerance
        max_trade_size_usd: float = 1000.0,  # Maximum trade size in USD
        min_liquidity_usd: float = 10000.0,  # Minimum pool liquidity in USD
        max_gas_price_gwei: int = 100,  # Maximum gas price in gwei
        tx_timeout_seconds: int = 30,  # Transaction timeout in seconds
        tx_monitor: Optional[Any] = None,
        market_analyzer: Optional[Any] = None,
        flash_loan_contract: Optional[str] = None  # Flash loan contract address
    ):
        """Initialize arbitrage executor."""
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager
        self.gas_optimizer = gas_optimizer
        self.min_profit_usd = min_profit_usd
        self.wallet_address = web3_manager.wallet_address
        self.max_price_impact = max_price_impact
        self.slippage_tolerance = slippage_tolerance
        self.max_trade_size_usd = max_trade_size_usd
        self.min_liquidity_usd = min_liquidity_usd
        self.max_gas_price_gwei = max_gas_price_gwei
        self.tx_timeout_seconds = tx_timeout_seconds
        self.tx_monitor = tx_monitor
        self.market_analyzer = market_analyzer
        self.last_error = None
        self._cached_eth_price = None
        self._last_price_update = 0
        self._price_cache_duration = 10  # Cache price for 10 seconds
        
        # Flash loan setup
        self.flash_loan_contract_address = flash_loan_contract
        self.flash_loan_contract = None
        if flash_loan_contract:
            try:
                self.flash_loan_abi = self.web3_manager.load_abi('BaseFlashLoanArbitrage')
                self.flash_loan_contract = self.web3_manager.w3.eth.contract(
                    address=flash_loan_contract,
                    abi=self.flash_loan_abi
                )
                logger.info(f"Flash loan contract initialized at {flash_loan_contract}")
            except Exception as e:
                logger.error(f"Failed to initialize flash loan contract: {e}")

    async def initialize(self) -> bool:
        """Initialize arbitrage executor."""
        try:
            # Reset error state
            self.last_error = None

            # Connect to Web3
            await self.web3_manager.connect()

            # Initialize DEX manager
            if not await self.dex_manager.initialize():
                self.last_error = "Failed to initialize DEX manager"
                return False

            # Initialize gas optimizer
            if not await self.gas_optimizer.initialize():
                self.last_error = "Failed to initialize gas optimizer"
                return False

            # Check wallet balance
            balance = await self.web3_manager.get_eth_balance()
            if balance == 0:
                self.last_error = "Wallet has no ETH balance"
                return False

            # Verify gas price is within limits
            gas_price_gwei = self.web3_manager.w3.from_wei(
                await self.web3_manager.w3.eth.gas_price,
                'gwei'
            )
            if gas_price_gwei > self.max_gas_price_gwei:
                self.last_error = f"Current gas price {gas_price_gwei} gwei exceeds maximum {self.max_gas_price_gwei}"
                return False

            logger.info("Arbitrage executor initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize arbitrage executor: {e}")
            return False

    async def _execute_flash_loan_trade(
        self,
        asset: str,
        amount: int,
        dex_from: str,
        dex_to: str,
        path: List[str],
        deadline: int
    ) -> str:
        """Execute trade using flash loan."""
        if not self.flash_loan_contract:
            raise ValueError("Flash loan contract not initialized")

        try:
            # Get DEX instances to check if they're V3
            dex_from_instance = self.dex_manager.get_dex(dex_from)
            dex_to_instance = self.dex_manager.get_dex(dex_to)
            if not dex_from_instance or not dex_to_instance:
                raise ValueError(f"DEX not found: {dex_from} or {dex_to}")

            # Encode flash loan parameters
            dex_paths = [dex_from_instance.router_address, dex_to_instance.router_address]
            amounts = [amount, amount]  # Same amount for both trades
            is_v3 = [
                isinstance(dex_from_instance, 'V3DEX'),  # Replace with actual V3 class check
                isinstance(dex_to_instance, 'V3DEX')
            ]

            # Encode parameters for flash loan
            params = self.web3_manager.w3.eth.contract(abi=self.flash_loan_abi).encodeParameters(
                ['address[]', 'uint256[]', 'bool[]'],
                [dex_paths, amounts, is_v3]
            )

            # Build flash loan transaction
            tx = await self.flash_loan_contract.functions.executeFlashLoan(
                asset,
                amount,
                params
            ).build_transaction({
                'from': self.wallet_address,
                'gas': 500000,  # Higher gas limit for flash loans
                'nonce': await self.web3_manager.w3.eth.get_transaction_count(self.wallet_address)
            })

            # Send transaction using secure web3 manager
            tx_hash = await self.web3_manager.send_transaction(tx)
            
            return tx_hash

        except Exception as e:
            logger.error(f"Failed to execute flash loan trade: {e}")
            raise

    async def start_execution(self):
        """Start arbitrage execution loop."""
        try:
            while True:
                try:
                    # Get current gas price
                    gas_price = await self.web3_manager.w3.eth.gas_price
                    gas_price_gwei = self.web3_manager.w3.from_wei(gas_price, 'gwei')
                    
                    # Check if gas price is too high
                    if gas_price_gwei > self.max_gas_price_gwei:
                        logger.warning(f"Gas price {gas_price_gwei} gwei too high")
                        await asyncio.sleep(10)
                        continue
                        
                    # Get opportunities from market analyzer
                    if self.market_analyzer:
                        opportunities = await self.market_analyzer.get_opportunities()
                        for opp in opportunities:
                            try:
                                # Validate opportunity
                                if opp['profit_usd'] < self.min_profit_usd:
                                    continue
                                    
                                # Execute trade
                                logger.info(f"Executing trade with {opp['profit_usd']:.2f} USD profit")
                                
                                # Get DEX instances
                                dex_from = self.dex_manager.get_dex(opp['dex_from'])
                                if not dex_from:
                                    logger.error(f"DEX {opp['dex_from']} not found")
                                    continue
                                
                                # Validate gas costs
                                estimated_gas = await dex_from.estimate_gas(
                                    amount_in=Decimal(str(opp['amount_in'])),
                                    amount_out_min=Decimal(str(opp['amount_out'] * (1 - self.slippage_tolerance))),
                                    path=opp['token_path'],
                                    to=self.wallet_address
                                )
                                
                                gas_price = await self.web3_manager.w3.eth.gas_price
                                gas_cost_wei = estimated_gas * gas_price
                                gas_cost_eth = self.web3_manager.w3.from_wei(gas_cost_wei, 'ether')
                                
                                # Get ETH price from market analyzer
                                eth_price = await self.market_analyzer.get_market_condition("WETH")
                                if not eth_price:
                                    logger.error("Failed to get ETH price")
                                    continue
                                    
                                gas_cost_usd = float(gas_cost_eth) * float(eth_price['price'])
                                
                                # Verify profit after gas
                                net_profit = opp['profit_usd'] - gas_cost_usd
                                if net_profit < self.min_profit_usd:
                                    logger.info(f"Trade not profitable after gas: ${net_profit:.2f}")
                                    continue
                                
                                # Build and send transaction
                                try:
                                    # Get deadline
                                    deadline = (await self.web3_manager.w3.eth.get_block('latest')).timestamp + self.tx_timeout_seconds
                                    
                                    if self.flash_loan_contract:
                                        # Execute via flash loan
                                        tx_hash = await self._execute_flash_loan_trade(
                                            opp['token_path'][0],  # Asset to borrow
                                            opp['amount_in'],
                                            opp['dex_from'],
                                            opp['dex_to'],
                                            opp['token_path'],
                                            deadline
                                        )
                                    else:
                                        # Build regular transaction
                                        tx = await dex_from.build_swap_transaction(
                                            amount_in=Decimal(str(opp['amount_in'])),
                                            amount_out_min=Decimal(str(opp['amount_out'] * (1 - self.slippage_tolerance))),
                                            path=opp['token_path'],
                                            to=self.wallet_address,
                                            deadline=deadline
                                        )
                                        
                                        # Send transaction
                                        tx_hash = await self.web3_manager.send_transaction(tx)
                                        
                                    logger.info(f"Transaction sent: {tx_hash.hex()}")
                                    
                                    # Monitor transaction
                                    if self.tx_monitor:
                                        await self.tx_monitor.add_transaction(
                                            tx_hash=tx_hash.hex(),
                                            dex=opp['dex_from'],
                                            amount_in=opp['amount_in'],
                                            amount_out_min=opp['amount_out'] * (1 - self.slippage_tolerance),
                                            expected_profit=net_profit,
                                            gas_cost=gas_cost_usd
                                        )
                                    
                                    # Wait for transaction receipt
                                    receipt = await self.web3_manager.w3.eth.wait_for_transaction_receipt(
                                        tx_hash,
                                        timeout=self.tx_timeout_seconds
                                    )
                                    
                                    if receipt['status'] == 1:
                                        logger.info(f"Trade executed successfully. Net profit: ${net_profit:.2f}")
                                    else:
                                        logger.error("Transaction failed")
                                        
                                except Exception as e:
                                    logger.error(f"Failed to execute trade: {e}")
                                
                            except Exception as e:
                                logger.error(f"Error executing trade: {e}")
                                
                    await asyncio.sleep(1)  # Sleep between checks
                    
                except Exception as e:
                    logger.error(f"Error in execution loop: {e}")
                    await asyncio.sleep(5)
                    
        except asyncio.CancelledError:
            logger.info("Arbitrage execution cancelled")
        except Exception as e:
            logger.error(f"Fatal error in execution loop: {e}")

async def create_arbitrage_executor(
    web3_manager: Optional[Web3Manager] = None,
    dex_manager: Optional[DEXManager] = None,
    gas_optimizer: Optional[GasOptimizer] = None,
    min_profit_usd: float = 10.0,
    max_price_impact: float = 0.02,
    slippage_tolerance: float = 0.005,
    tx_monitor: Optional[Any] = None,
    market_analyzer: Optional[Any] = None
) -> ArbitrageExecutor:
    """
    Create arbitrage executor instance.

    Args:
        web3_manager: Web3Manager instance
        dex_manager: Optional DEXManager instance
        gas_optimizer: Optional GasOptimizer instance
        min_profit_usd: Minimum profit in USD
        max_price_impact: Maximum price impact
        slippage_tolerance: Slippage tolerance

    Returns:
        ArbitrageExecutor: Arbitrage executor instance
    """
    if not web3_manager:
        web3_manager = await create_web3_manager()
    if not isinstance(web3_manager, Web3Manager):
        raise TypeError(f"Expected Web3Manager instance, got {type(web3_manager)}")
    if not dex_manager:
        dex_manager = await create_dex_manager(web3_manager)
    if not gas_optimizer:
        gas_optimizer = await create_gas_optimizer(dex_manager=dex_manager, web3_manager=web3_manager)

    executor = ArbitrageExecutor(
        dex_manager=dex_manager,
        web3_manager=web3_manager,
        gas_optimizer=gas_optimizer,
        min_profit_usd=min_profit_usd,
        max_price_impact=max_price_impact,
        slippage_tolerance=slippage_tolerance,
        tx_monitor=tx_monitor,
        market_analyzer=market_analyzer
    )
    await executor.initialize()
    return executor

# Export the create function
__all__ = ['create_arbitrage_executor']
