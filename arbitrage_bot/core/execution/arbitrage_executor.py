"""Arbitrage execution engine."""

import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from ...utils.config_loader import load_config
from ...utils.gas_logger import GasLogger
from ..web3.web3_manager import Web3Manager
from ..dex import DexManager
from ..gas.gas_optimizer import GasOptimizer

logger = logging.getLogger(__name__)

class ArbitrageExecutor:
    """Executes arbitrage opportunities across multiple DEXs."""

    def __init__(
        self,
        dex_manager: DexManager,
        web3_manager: Web3Manager,
        gas_optimizer: GasOptimizer,
        min_profit_usd: float = 0.05,  # Minimum profit of $0.05
        max_price_impact: float = 0.01,  # Maximum 1% price impact
        slippage_tolerance: float = 0.001,  # 0.1% slippage tolerance
        max_trade_size_usd: float = 5000.0,  # Maximum trade size in USD
        min_liquidity_usd: float = 10000.0,  # Minimum pool liquidity in USD
        max_gas_price_gwei: int = 100,  # Maximum gas price in gwei
        tx_timeout_seconds: int = 30,  # Transaction timeout in seconds
        tx_monitor: Optional[Any] = None,
        market_analyzer: Optional[Any] = None,
        analytics_system: Optional[Any] = None,
        ml_system: Optional[Any] = None,
        memory_bank: Optional[Any] = None,
        flash_loan_manager: Optional[Any] = None,
        balance_manager: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize arbitrage executor."""
        self.dex_manager = dex_manager
        self.web3_manager = web3_manager
        self.gas_optimizer = gas_optimizer
        self.min_profit_usd = min_profit_usd
        self.wallet_address = web3_manager.wallet_address
        self.profit_recipient = config.get('wallet', {}).get('profit_recipient') or self.wallet_address
        self.weth_address = config.get('tokens', {}).get('WETH', {}).get('address')
        if not self.weth_address:
            raise ConfigurationError("WETH address not found in config")
        logger.info(f"WETH address: {self.weth_address}")
        logger.info(f"Profit recipient: {self.profit_recipient}")
        self.max_price_impact = max_price_impact
        self.slippage_tolerance = slippage_tolerance
        self.max_trade_size_usd = max_trade_size_usd
        self.min_liquidity_usd = min_liquidity_usd
        self.max_gas_price_gwei = max_gas_price_gwei
        self.tx_timeout_seconds = tx_timeout_seconds
        self.tx_monitor = tx_monitor
        self.market_analyzer = market_analyzer
        self.analytics_system = analytics_system
        self.ml_system = ml_system
        self.memory_bank = memory_bank
        self.flash_loan_manager = flash_loan_manager
        self.balance_manager = balance_manager
        self.config = config or {}
        self.last_error = None
        self._cached_eth_price = None
        self._last_price_update = 0
        self._price_cache_duration = 10  # Cache price for 10 seconds
        self._executor = ThreadPoolExecutor(max_workers=4)  # For parallel execution
        self._pending_approvals = set()  # Track pending token approvals
        self._last_nonce = None  # Track last used nonce
        self._last_trade_time = 0  # Track last trade time
        self._min_trade_interval = 0.5  # Minimum 0.5s between trades
        
        # Initialize gas logger
        self.gas_logger = GasLogger()

    async def _check_and_approve_token(self, token_address: str, dex: Any) -> bool:
        """Check and approve token for trading if needed."""
        try:
            # Get token contract
            token_contract = self.web3_manager.get_token_contract(token_address)
            
            # Get DEX router address
            router_address = dex.get_router_address()
            
            # Check current allowance
            allowance = token_contract.functions.allowance(
                self.wallet_address,
                router_address
            ).call()
            
            # If allowance is too low, approve max amount
            if allowance < self.web3_manager.w3.to_wei(1000000, 'ether'):  # 1M tokens
                logger.info(f"Approving {token_address} for DEX router {router_address}")
                
                # Create approval transaction
                max_amount = 2**256 - 1  # Max uint256
                tx = token_contract.functions.approve(
                    router_address,
                    max_amount
                ).build_transaction({
                    'from': self.wallet_address,
                    'nonce': self.web3_manager.w3.eth.get_transaction_count(self.wallet_address),
                })
                
                # Send and wait for approval transaction
                receipt = self.web3_manager.send_transaction(tx)
                return receipt and receipt['status'] == 1
                
            return True
        except Exception as e:
            logger.error(f"Failed to approve token: {e}")
            return False

    async def _execute_single_trade(self, dex: Any, amount_in: Decimal, amount_out_min: Decimal, path: List[str], deadline: int) -> Tuple[bool, str]:
        """Execute a single trade on a DEX."""
        try:
            # Get initial balances and contracts
            token_in = path[0]
            token_out = path[-1]
            
            token_in_contract = self.web3_manager.get_token_contract(token_in)
            token_out_contract = self.web3_manager.get_token_contract(token_out)
            
            # Always send output to profit recipient for final WETH trades
            # For intermediate trades, use wallet address to maintain control
            is_final_weth_trade = token_out.lower() == self.weth_address.lower()
            
            # For final WETH trades, check if we have enough ETH for gas
            if is_final_weth_trade:
                # Get gas cost estimate for the transfer
                gas_params = self.gas_optimizer.optimize_gas({'priority': 'standard'})
                # Use actual gas estimate with 20% buffer
                base_gas_cost = gas_params['gas'] * gas_params['maxFeePerGas']
                estimated_gas_cost = int(base_gas_cost * 1.2)  # 20% buffer
                
                # Get current ETH balance
                eth_balance = self.web3_manager.get_eth_balance()
                eth_balance_wei = self.web3_manager.w3.to_wei(eth_balance, 'ether')
                
                # Keep enough ETH for gas with 1.5x buffer
                if eth_balance_wei > estimated_gas_cost * 1.5:  # Reduced from 3x to 1.5x
                    recipient = self.profit_recipient
                    amount_out_min = Decimal(str(int(amount_out_min) - estimated_gas_cost))
                    logger.info(f"Sufficient ETH for gas ({eth_balance} ETH), sending to profit recipient")
                    logger.info(f"Adjusted minimum output for gas cost: {amount_out_min}")
                else:
                    # Even if we don't have the buffer, still try to send to profit recipient
                    # Just keep exact gas cost
                    recipient = self.profit_recipient
                    amount_out_min = Decimal(str(int(amount_out_min) - base_gas_cost))
                    logger.info(f"Limited ETH for gas ({eth_balance} ETH), but still sending to profit recipient")
                    logger.info(f"Adjusted minimum output for exact gas cost: {amount_out_min}")
            else:
                recipient = self.wallet_address
            
            logger.info(f"Trade details:")
            logger.info(f"- Input token: {token_in}")
            logger.info(f"- Output token: {token_out}")
            logger.info(f"- Is final WETH trade: {is_final_weth_trade}")
            logger.info(f"- Recipient address: {recipient}")
            
            # Check and approve input token if needed
            approval_result = await self._check_and_approve_token(token_in, dex)
            if not approval_result:
                logger.error(f"Failed to approve token {token_in}")
                self.last_error = "Token approval failed"
                return False, "Token approval failed"
            
            # Execute the trade
            receipt = dex.swap_exact_tokens_for_tokens(
                amount_in=amount_in,
                amount_out_min=amount_out_min,
                path=path,
                to=recipient,
                deadline=deadline
            )
            
            # Log gas usage if transaction successful
            if receipt and receipt['status'] == 1:
                self.gas_logger.log_gas_usage(
                    gas_used=receipt['gasUsed'],
                    gas_price=receipt['effectiveGasPrice'],
                    tx_hash=receipt['transactionHash'].hex(),
                    sent_to_recipient=(recipient == self.profit_recipient),
                    eth_balance=eth_balance,
                    estimated_gas_cost=estimated_gas_cost
                )
                
                # Log monthly summary after each transaction
                summary = self.gas_logger.get_monthly_summary()
                logger.info("\nMonthly Gas Usage Summary:")
                logger.info("="*50)
                logger.info(f"Total Gas Used: {summary['total_gas_used']:,}")
                logger.info(f"Total Gas Cost: {summary['total_gas_cost_eth']:.6f} ETH")
                logger.info(f"Average Gas Price: {summary['average_gas_price_gwei']:.2f} gwei")
                logger.info(f"Transfers to Recipient: {summary['transfers_to_recipient']}")
                logger.info(f"Kept in Wallet: {summary['kept_in_wallet']}")
                logger.info("="*50)
                
                return True, receipt['transactionHash'].hex()
            else:
                logger.error("Transaction failed or returned invalid receipt")
                return False, ""

                
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return False, str(e)

async def create_arbitrage_executor(
    web3_manager: Web3Manager,
    dex_manager: DexManager,
    gas_optimizer: GasOptimizer,
    tx_monitor: Optional[Any] = None,
    market_analyzer: Optional[Any] = None,
    analytics_system: Optional[Any] = None,
    ml_system: Optional[Any] = None,
    memory_bank: Optional[Any] = None,
    flash_loan_manager: Optional[Any] = None,
    balance_manager: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None
) -> Optional[ArbitrageExecutor]:
    """Create and initialize an arbitrage executor instance."""
    try:
        executor = ArbitrageExecutor(
            dex_manager=dex_manager,
            web3_manager=web3_manager,
            gas_optimizer=gas_optimizer,
            tx_monitor=tx_monitor,
            market_analyzer=market_analyzer,
            analytics_system=analytics_system,
            ml_system=ml_system,
            memory_bank=memory_bank,
            flash_loan_manager=flash_loan_manager,
            balance_manager=balance_manager,
            config=config
        )
        return executor
    except Exception as e:
        logger.error(f"Failed to create arbitrage executor: {e}")
        return None

# Export the create function
__all__ = ['create_arbitrage_executor', 'ArbitrageExecutor']
