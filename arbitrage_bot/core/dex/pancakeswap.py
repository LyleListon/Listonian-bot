"""PancakeSwap V3 DEX implementation."""

from typing import Dict, Any, Optional, List
from web3.types import TxReceipt

from .base_dex_v3 import BaseDEXV3
from ..web3.web3_manager import Web3Manager
from .utils import (
    validate_config,
    estimate_gas_cost,
    calculate_price_impact,
    encode_path_for_v3,
    get_common_base_tokens,
)


class PancakeSwapDEX(BaseDEXV3):
    """Implementation of PancakeSwap V3 DEX."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize PancakeSwap V3 interface."""
        # PancakeSwap V3 uses 0.25% fee by default
        config["fee"] = config.get("fee", 2500)

        # Validate config
        is_valid, error = validate_config(
            config, {"router": str, "factory": str, "quoter": str, "fee": int}
        )
        if not is_valid:
            raise ValueError(f"Invalid config: {error}")

        super().__init__(web3_manager, config)
        self.name = "PancakeSwap"

    async def get_pool_fee(self, token0: str, token1: str) -> Optional[int]:
        """
        Get the optimal fee tier based on market conditions.

        Args:
            token0: First token address
            token1: Second token address

        Returns:
            Optional[int]: Fee in basis points (e.g., 2500 for 0.25%) or None if pool doesn't exist
        """
        try:
            # Get token symbols
            token0_symbol = self.TOKEN_SYMBOLS.get(token0)
            token1_symbol = self.TOKEN_SYMBOLS.get(token1)

            # If we don't have symbols, use default fee
            if not token0_symbol or not token1_symbol:
                return self.fee

            # Get market conditions from market-analysis server
            market_conditions = await self.web3_manager.use_mcp_tool(
                "market-analysis",
                "assess_market_conditions",
                {
                    "token": token0_symbol.lower(),
                    "metrics": ["volatility", "volume", "liquidity"],
                },
            )

            # Determine optimal fee tier based on market conditions
            volatility = market_conditions["metrics"]["volatility"]
            volume = market_conditions["metrics"]["volume"]
            liquidity = market_conditions["metrics"]["liquidity"]

            # High volume, low volatility -> lowest fee
            if volume > 1000000 and volatility < 0.1:
                fee = 100  # 0.01%
            # High volume, medium volatility -> low fee
            elif volume > 500000 and volatility < 0.3:
                fee = 500  # 0.05%
            # Medium conditions -> medium fee
            elif volume > 100000 and volatility < 0.5:
                fee = 2500  # 0.25%
            # High volatility or low volume -> high fee
            else:
                fee = 10000  # 1%

            # Verify pool exists with selected fee
            pool = await self.factory.functions.getPool(token0, token1, fee).call()

            if pool != "0x0000000000000000000000000000000000000000":
                return fee

            # If pool doesn't exist with optimal fee, try other tiers
            fee_tiers = [100, 500, 2500, 10000]
            for alt_fee in fee_tiers:
                if alt_fee != fee:
                    pool = await self.factory.functions.getPool(
                        token0, token1, alt_fee
                    ).call()
                    if pool != "0x0000000000000000000000000000000000000000":
                        return alt_fee

            return None

        except Exception as e:
            self._handle_error(e, "Pool fee lookup")
            return None

    async def get_best_pool(self, token0: str, token1: str) -> Optional[Dict[str, Any]]:
        """
        Find the pool with the best liquidity using market analysis.

        Args:
            token0: First token address
            token1: Second token address

        Returns:
            Optional[Dict[str, Any]]: Pool details including:
                - address: Pool contract address
                - fee: Fee tier
                - liquidity: Pool liquidity
                - sqrt_price_x96: Current sqrt price
        """
        try:
            # Get token symbols
            token0_symbol = self.TOKEN_SYMBOLS.get(token0)
            token1_symbol = self.TOKEN_SYMBOLS.get(token1)

            # If we don't have symbols, use default fee
            if not token0_symbol or not token1_symbol:
                return None

            # Analyze opportunities using market-analysis server
            analysis = await self.web3_manager.use_mcp_tool(
                "market-analysis",
                "analyze_opportunities",
                {
                    "token": token0_symbol.lower(),
                    "days": 1,
                    "min_profit_threshold": 0.1,
                },
            )

            # Get current market conditions
            market_conditions = await self.web3_manager.use_mcp_tool(
                "market-analysis",
                "assess_market_conditions",
                {"token": token0_symbol.lower(), "metrics": ["liquidity", "volume"]},
            )

            # Use the analysis to determine best fee tier
            if market_conditions["metrics"]["volume"] > 1000000:  # High volume
                fee = 100  # 0.01% for high volume
            elif market_conditions["metrics"]["volume"] > 100000:  # Medium volume
                fee = 500  # 0.05% for medium volume
            else:
                fee = 2500  # 0.25% for low volume

            # Get pool address
            pool_address = await self.factory.functions.getPool(
                token0, token1, fee
            ).call()

            if pool_address == "0x0000000000000000000000000000000000000000":
                return None

            return {
                "address": pool_address,
                "fee": fee,
                "liquidity": market_conditions["metrics"]["liquidity"],
                "sqrt_price_x96": analysis["current_price"]
                * (2**96),  # Convert to sqrtPriceX96
            }

        except Exception as e:
            self._handle_error(e, "Best pool lookup")
            return None

    async def estimate_gas_cost(self, path: List[str]) -> int:
        """
        Estimate gas cost for a swap path.

        Args:
            path: List of token addresses in the swap path

        Returns:
            int: Estimated gas cost in wei
        """
        return estimate_gas_cost(path, "v3")

    def _encode_path(self, path: List[str]) -> bytes:
        """
        Encode path with fees for V3 swap.

        Args:
            path: List of token addresses

        Returns:
            bytes: Encoded path with fees
        """
        return encode_path_for_v3(path, self.fee)

    async def get_common_pairs(self) -> List[str]:
        """Get list of common base tokens for routing."""
        return get_common_base_tokens()

    # Token address to symbol mapping
    TOKEN_SYMBOLS = {
        # Common Base tokens
        "0x4200000000000000000000000000000000000006": "WETH",  # WETH on Base
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "USDC",  # USDC on Base
        "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb": "DAI",  # DAI on Base
        "0x4A3A6Dd60A34bB2Aba60D73B4C88315E9CeB6A3D": "USDT",  # USDT on Base
        # Add more token mappings as needed
    }

    async def get_quote_with_impact(
        self, amount_in: int, path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get quote including price impact and liquidity depth analysis using MCP servers.
        Falls back to base V3 implementation if MCP servers fail.

        Args:
            amount_in: Input amount in wei
            path: List of token addresses in the swap path

        Returns:
            Optional[Dict[str, Any]]: Quote details including:
                - amount_in: Input amount
                - amount_out: Expected output amount
                - price_impact: Estimated price impact percentage
                - liquidity_depth: Available liquidity
                - fee_rate: DEX fee rate
                - estimated_gas: Estimated gas cost
                - min_out: Minimum output with slippage
        """
        try:
            # Get token symbols from addresses
            token_in_symbol = self.TOKEN_SYMBOLS.get(path[0])
            token_out_symbol = self.TOKEN_SYMBOLS.get(path[1])

            # If we don't have symbols for the tokens, fall back to base implementation
            if not token_in_symbol or not token_out_symbol:
                return await super().get_quote_with_impact(amount_in, path)

            # Get current prices from crypto-price server
            prices_response = await self.web3_manager.use_mcp_tool(
                "crypto-price",
                "get_prices",
                {
                    "coins": [token_in_symbol.lower(), token_out_symbol.lower()],
                    "include_24h_change": True,
                },
            )

            # Get market conditions from market-analysis server
            market_response = await self.web3_manager.use_mcp_tool(
                "market-analysis",
                "assess_market_conditions",
                {
                    "token": token_in_symbol.lower(),
                    "metrics": ["volatility", "volume", "liquidity", "trend"],
                },
            )

            # Validate MCP responses
            if not prices_response or not market_response:
                return await super().get_quote_with_impact(amount_in, path)

            # Extract prices from response
            token_in_price = prices_response.get(token_in_symbol.lower(), {}).get(
                "price"
            )
            token_out_price = prices_response.get(token_out_symbol.lower(), {}).get(
                "price"
            )

            if not token_in_price or not token_out_price:
                return await super().get_quote_with_impact(amount_in, path)

            # Calculate output amount based on price ratio
            price_ratio = float(token_out_price) / float(token_in_price)
            amount_out = int(amount_in * price_ratio)

            # Extract market metrics
            metrics = market_response.get("metrics", {})
            price_impact = float(metrics.get("volatility", 0)) / 100
            liquidity = int(metrics.get("liquidity", 0))

            # Validate metrics
            if price_impact <= 0 or liquidity <= 0:
                return await super().get_quote_with_impact(amount_in, path)

            return {
                "amount_in": amount_in,
                "amount_out": amount_out,
                "price_impact": price_impact,
                "liquidity_depth": liquidity,
                "fee_rate": self.fee / 1000000,  # Convert from basis points
                "estimated_gas": estimate_gas_cost(path, "v3"),
                "min_out": int(amount_out * 0.995),  # 0.5% slippage default
            }

        except Exception as e:
            self.logger.warning(
                f"MCP quote failed, falling back to base implementation: {e}"
            )
            return await super().get_quote_with_impact(amount_in, path)
