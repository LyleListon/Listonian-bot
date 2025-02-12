"""BaseSwap DEX implementation."""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from web3.types import ChecksumAddress

from ...interfaces import (
    BaseDEX,
    DEXType,
    LiquidityInfo,
    PoolInfo,
    SwapParams,
    SwapQuote,
    Token,
    TokenAmount,
)
from ...utils import (
    calculate_price_impact,
    get_amount_out,
    get_contract,
    validate_pool_health,
    validate_path,
)

logger = logging.getLogger(__name__)


class BaseSwap(BaseDEX):
    """BaseSwap DEX implementation."""

    def __init__(
        self,
        web3_manager,
        factory_address: ChecksumAddress,
        router_address: ChecksumAddress
    ):
        """Initialize BaseSwap DEX.
        
        Args:
            web3_manager: Web3 manager instance
            factory_address: Factory contract address
            router_address: Router contract address
        """
        super().__init__(
            web3_manager=web3_manager,
            factory_address=factory_address,
            router_address=router_address,
            protocol=DEXType.BASESWAP
        )
        
        # Initialize contracts
        self._factory = get_contract(
            web3_manager,
            factory_address,
            'baseswap_factory'
        )
        self._router = get_contract(
            web3_manager,
            router_address,
            'baseswap_router'
        )
        
        # Cache for pool addresses
        self._pool_cache: Dict[str, ChecksumAddress] = {}

    async def get_pool(
        self,
        token0: Token,
        token1: Token
    ) -> Optional[PoolInfo]:
        """Get pool for token pair.
        
        Args:
            token0: First token
            token1: Second token
            
        Returns:
            Pool info if exists, None otherwise
        """
        try:
            # Get pool address
            pool_address = await self._get_pool_address(
                token0.address,
                token1.address
            )
            if not pool_address:
                return None
                
            # Get pool contract
            pool = get_contract(
                self.web3,
                pool_address,
                'baseswap_pair'
            )
            
            # Get reserves
            reserves = await self.get_reserves(pool_address)
            
            return PoolInfo(
                address=pool_address,
                token0=token0,
                token1=token1,
                fee=Decimal('0.003'),  # 0.3%
                liquidity=reserves,
                protocol=self.protocol
            )
            
        except Exception as e:
            logger.error(f"Failed to get pool: {e}")
            return None

    async def get_pools(self) -> List[PoolInfo]:
        """Get all available pools.
        
        Returns:
            List of pool information
        """
        # TODO: Implement pool discovery
        return []

    async def get_reserves(
        self,
        pool_address: ChecksumAddress
    ) -> LiquidityInfo:
        """Get current reserves for pool.
        
        Args:
            pool_address: Pool contract address
            
        Returns:
            Current liquidity information
            
        Raises:
            ValueError: If pool doesn't exist
        """
        try:
            pool = get_contract(
                self.web3,
                pool_address,
                'baseswap_pair'
            )
            
            # Get reserves and tokens
            reserves = await pool.functions.getReserves().call()
            token0 = await self.get_token(
                await pool.functions.token0().call()
            )
            token1 = await self.get_token(
                await pool.functions.token1().call()
            )
            
            return LiquidityInfo(
                token0_reserve=TokenAmount(
                    token=token0,
                    amount=Decimal(reserves[0]) / Decimal(10 ** token0.decimals)
                ),
                token1_reserve=TokenAmount(
                    token=token1,
                    amount=Decimal(reserves[1]) / Decimal(10 ** token1.decimals)
                ),
                total_supply=await pool.functions.totalSupply().call(),
                updated_at=reserves[2]  # Last updated timestamp
            )
            
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            raise ValueError(f"Failed to get reserves: {e}")

    async def get_quote(
        self,
        input_amount: TokenAmount,
        output_token: Token,
        path: Optional[List[ChecksumAddress]] = None
    ) -> SwapQuote:
        """Get quote for swap.
        
        Args:
            input_amount: Input token amount
            output_token: Output token
            path: Optional specific path to use
            
        Returns:
            Swap quote with price impact
            
        Raises:
            ValueError: If no valid path exists
        """
        try:
            # Find path if not provided
            if not path:
                path, _ = await self.find_best_path(
                    input_amount.token,
                    output_token,
                    input_amount
                )
                
            # Validate path
            pools = []  # TODO: Get pools for path
            is_valid, error = validate_path(path, pools)
            if not is_valid:
                raise ValueError(f"Invalid path: {error}")
                
            # Get amounts out
            amounts = await self._router.functions.getAmountsOut(
                input_amount.to_wei(),
                path
            ).call()
            
            output_amount = TokenAmount(
                token=output_token,
                amount=Decimal(amounts[-1]) / Decimal(10 ** output_token.decimals)
            )
            
            # Calculate price impact
            spot_price = await self.get_price(
                input_amount.token,
                output_token
            )
            price_impact = calculate_price_impact(
                input_amount,
                output_amount,
                spot_price
            )
            
            # Estimate gas
            gas_estimate = await self._router.functions.swapExactTokensForTokens(
                input_amount.to_wei(),
                0,  # Min output (0 for estimation)
                path,
                self.web3.provider.web3.eth.default_account,
                2 ** 256 - 1  # Max deadline for estimation
            ).estimate_gas()
            
            return SwapQuote(
                input_amount=input_amount,
                output_amount=output_amount,
                price_impact=price_impact,
                path=path,
                gas_estimate=gas_estimate
            )
            
        except Exception as e:
            logger.error(f"Failed to get quote: {e}")
            raise ValueError(f"Failed to get quote: {e}")

    async def get_price(
        self,
        base_token: Token,
        quote_token: Token
    ) -> Decimal:
        """Get current price between tokens.
        
        Args:
            base_token: Base token
            quote_token: Quote token
            
        Returns:
            Current price (quote per base)
            
        Raises:
            ValueError: If no valid path exists
        """
        try:
            # Get pool
            pool = await self.get_pool(base_token, quote_token)
            if not pool:
                raise ValueError("No pool exists")
                
            # Validate pool
            is_valid, error = validate_pool_health(pool)
            if not is_valid:
                raise ValueError(f"Unhealthy pool: {error}")
                
            # Calculate price from reserves
            if pool.token0.address == base_token.address:
                return (
                    pool.liquidity.token1_reserve.amount /
                    pool.liquidity.token0_reserve.amount
                )
            else:
                return (
                    pool.liquidity.token0_reserve.amount /
                    pool.liquidity.token1_reserve.amount
                )
                
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            raise ValueError(f"Failed to get price: {e}")

    async def execute_swap(
        self,
        params: SwapParams
    ) -> str:
        """Execute swap transaction.
        
        Args:
            params: Swap parameters
            
        Returns:
            Transaction hash
            
        Raises:
            ValueError: If swap validation fails
            Web3Error: If transaction fails
        """
        # Build transaction
        tx = await self._router.functions.swapExactTokensForTokens(
            params.quote.input_amount.to_wei(),
            params._calculate_min_out(),
            params.quote.path,
            params.recipient,
            params.deadline
        ).build_transaction({
            'from': self.web3.provider.web3.eth.default_account,
            'gas': int(params.quote.gas_estimate * 1.1)  # Add 10% buffer
        })
        
        # Send transaction
        return await self.web3.send_transaction(tx)

    async def find_best_path(
        self,
        input_token: Token,
        output_token: Token,
        amount: Optional[TokenAmount] = None
    ) -> Tuple[List[ChecksumAddress], Decimal]:
        """Find best path between tokens.
        
        Args:
            input_token: Input token
            output_token: Output token
            amount: Optional amount to optimize for
            
        Returns:
            Tuple of (path, expected output amount)
            
        Raises:
            ValueError: If no valid path exists
        """
        # TODO: Implement path finding
        # For now, just return direct path
        path = [input_token.address, output_token.address]
        
        # Get expected output
        if amount:
            amounts = await self._router.functions.getAmountsOut(
                amount.to_wei(),
                path
            ).call()
            expected = Decimal(amounts[-1]) / Decimal(10 ** output_token.decimals)
        else:
            expected = Decimal(0)
            
        return path, expected

    async def validate_pool(
        self,
        pool_info: PoolInfo
    ) -> bool:
        """Validate pool health and status.
        
        Args:
            pool_info: Pool to validate
            
        Returns:
            True if pool is healthy and usable
        """
        is_valid, _ = validate_pool_health(pool_info)
        return is_valid

    async def monitor_price(
        self,
        pool_address: ChecksumAddress,
        callback: callable
    ) -> None:
        """Monitor price changes for pool.
        
        Args:
            pool_address: Pool to monitor
            callback: Function to call on price change
        """
        # TODO: Implement price monitoring
        pass

    async def _get_pool_address(
        self,
        token0: ChecksumAddress,
        token1: ChecksumAddress
    ) -> Optional[ChecksumAddress]:
        """Get pool address for token pair.
        
        Args:
            token0: First token address
            token1: Second token address
            
        Returns:
            Pool address if exists, None otherwise
        """
        # Check cache
        cache_key = f"{token0}-{token1}"
        if cache_key in self._pool_cache:
            return self._pool_cache[cache_key]
            
        try:
            # Get pool from factory
            pool = await self._factory.functions.getPair(
                token0,
                token1
            ).call()
            
            # Cache result
            self._pool_cache[cache_key] = pool
            return pool if pool != "0x0000000000000000000000000000000000000000" else None
            
        except Exception as e:
            logger.error(f"Failed to get pool address: {e}")
            return None