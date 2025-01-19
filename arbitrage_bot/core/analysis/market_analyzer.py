"""Market analysis utilities."""

__all__ = [
    'MarketAnalyzer',
    'MarketCondition',
    'MarketTrend',
    'PricePoint',
    'create_market_analyzer'
]

import logging
import math
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from decimal import Decimal
from ..web3.web3_manager import Web3Manager
from ..models.opportunity import Opportunity
from ...utils.mcp_client import use_mcp_tool

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)d)')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

@dataclass
class PricePoint:
    """Price data point."""
    timestamp: float
    price: Decimal
    volume: Decimal
    liquidity: Decimal

@dataclass
class MarketTrend:
    """Market trend information."""
    direction: str  # up, down, sideways
    strength: float  # 0-1
    duration: float  # in seconds
    volatility: float  # standard deviation
    confidence: float  # 0-1

@dataclass
class MarketCondition:
    """Current market condition."""
    price: Decimal
    trend: MarketTrend
    volume_24h: Decimal
    liquidity: Decimal
    volatility_24h: float
    price_impact: float
    last_updated: float


class RateLimiter:
    """Rate limiter for API requests with exponential backoff."""
    def __init__(self, requests_per_minute: int = 30, burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self.lock = asyncio.Lock()
        self.error_count = 0
        self.last_error_time = 0
        self.min_wait = 60 / requests_per_minute  # Minimum wait time between requests

    async def acquire(self):
        """Acquire a token for making a request with exponential backoff."""
        async with self.lock:
            now = time.time()
            
            # Apply exponential backoff if there were recent errors
            if self.error_count > 0:
                time_since_error = now - self.last_error_time
                if time_since_error < 300:  # Reset error count after 5 minutes
                    backoff_time = min(30, self.min_wait * (2 ** self.error_count))
                    logger.debug(f"Applying backoff: {backoff_time:.2f}s (errors: {self.error_count})")
                    await asyncio.sleep(backoff_time)
                else:
                    self.error_count = 0

            # Standard token bucket logic
            time_passed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + time_passed * (self.requests_per_minute / 60)
            )
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) * self.min_wait
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1

            # Always wait at least min_wait between requests
            await asyncio.sleep(self.min_wait)
            self.tokens -= 1

    def on_error(self):
        """Record a rate limit error."""
        self.error_count += 1
        self.last_error_time = time.time()
        logger.debug(f"Rate limit error recorded (total: {self.error_count})")

class MarketAnalyzer:
    """Analyzes market conditions and opportunities."""

    # Token mapping as class variable (symbol -> CoinGecko ID)
    TOKEN_MAP = {
        "WETH": "ethereum",
        "USDC": "usd-coin",
        "DAI": "dai"
    }

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize market analyzer."""
        self.web3_manager = web3_manager
        self.w3 = web3_manager.w3
        self.config = config
        self._price_cache = {}
        self._cache_duration = timedelta(seconds=30)  # Cache prices for 30 seconds
        self.market_conditions = {}  # Store market conditions for each token
        self._error_count = []  # Track errors for backoff
        self._session = None  # aiohttp session for MCP requests
        
        # Initialize rate limiters
        rate_limits = config.get('rate_limits', {}).get('market_analysis', {})
        self._price_limiter = RateLimiter(
            requests_per_minute=rate_limits.get('requests_per_minute', 30),
            burst_size=rate_limits.get('burst_size', 10)
        )
        self._analysis_limiter = RateLimiter(
            requests_per_minute=rate_limits.get('requests_per_minute', 30),
            burst_size=rate_limits.get('burst_size', 10)
        )

        # Initialize DEX registry
        self.dex_registry = DEXRegistry()
        self._initialize_dexes()
        
        logger.info("Market analyzer initialized")

    def _initialize_dexes(self):
        """Initialize and register DEXes."""
        from ..dex.implementations.pancakeswap_v3 import PancakeSwapV3
        from ..dex.implementations.baseswap_v2 import BaseSwapV2

        # Get DEX configs
        dex_configs = self.config.get("dexes", {})
        
        # Initialize enabled DEXes
        for dex_name, dex_config in dex_configs.items():
            if not dex_config.get("enabled", False):
                logger.info(f"Skipping disabled DEX: {dex_name}")
                continue

            try:
                if dex_name == "pancakeswap_v3":
                    dex = PancakeSwapV3(self.w3, dex_config)
                    self.dex_registry.register(dex)
                    logger.info(f"Registered PancakeSwap V3 with quoter: {dex_config['quoter']}")
                    
                elif dex_name == "baseswap_v2":
                    dex = BaseSwapV2(self.w3, dex_config)
                    self.dex_registry.register(dex)
                    logger.info(f"Registered BaseSwap V2 with router: {dex_config['router']}")
                    
                else:
                    logger.warning(f"Unknown DEX type: {dex_name}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize {dex_name}: {e}")

        active_dexes = self.dex_registry.list_dexes()
        if not active_dexes:
            logger.warning("No DEXes registered!")
        else:
            logger.info(f"Registered DEXes: {', '.join(active_dexes)}")

    async def cleanup(self):
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None

    def get_backoff_status(self) -> dict:
        """Get current backoff status."""
        now = time.time()
        # Clean up old errors
        self._error_count = [t for t in self._error_count if now - t < 300]
        if not self._error_count:
            return {"status": "normal", "backoff_time": 0, "error_count": 0}
        
        backoff_time = min(30, 5 * (2 ** len(self._error_count)))
        return {
            "status": "backoff",
            "backoff_time": backoff_time,
            "error_count": len(self._error_count)
        }

    async def get_quote(self, dex_name: str, token_in: str, token_out: str, amount_in: int, fee: Optional[int] = None) -> int:
        """
        Get quote from DEX using the DEX registry.
        
        Args:
            dex_name: Name of the DEX
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount
            fee: Optional fee parameter for DEXes that require it
            
        Returns:
            int: Quote amount out, or 0 if quote fails
        """
        try:
            # Get DEX from registry
            dex = self.dex_registry.get_dex(dex_name)
            if not dex:
                logger.warning(f"DEX {dex_name} not found in registry")
                return 0

            # Get quote using DEX's implementation
            quote_result = await dex.get_quote(token_in, token_out, amount_in)
            
            if quote_result.success:
                logger.debug(
                    f"Got quote from {dex_name}: {quote_result.amount_out} "
                    f"(fee: {quote_result.fee}, "
                    f"price impact: {quote_result.price_impact:.2%})"
                )
                return quote_result.amount_out
            else:
                logger.warning(
                    f"Quote failed for {dex_name}: {quote_result.error}"
                )
                return 0

        except Exception as e:
            logger.error(
                f"Error getting quote from {dex_name}: {e}",
                extra={
                    "dex": dex_name,
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": amount_in
                }
            )
            return 0

    def _encode_pancakeswap_v3_path(self, token_in: str, token_out: str, fee: int) -> bytes:
        """
        Encodes the path for PancakeSwap V3's quoteExactInput function.
        Args:
            token_in (str): Address of the input token (with '0x' prefix)
            token_out (str): Address of the output token (with '0x' prefix)
            fee (int): Fee tier (e.g., 500, 3000, 10000)
        Returns:
            bytes: The encoded path as raw bytes
        """
        # Convert token addresses to bytes (strip '0x' and decode as bytes)
        token_in_bytes = bytes.fromhex(token_in[2:])
        token_out_bytes = bytes.fromhex(token_out[2:])
        
        # Convert fee to exactly 3 bytes
        fee_bytes = fee.to_bytes(3, 'big')
        
        # Concatenate token_in, fee, and token_out as raw bytes
        return token_in_bytes + fee_bytes + token_out_bytes

    def validate_price(self, price: float) -> bool:
        """
        Validate if a price is valid.

        Args:
            price (float): Price to validate

        Returns:
            bool: True if price is valid, False otherwise
        """
        if not isinstance(price, (int, float)):
            return False

        return price > 0 and not math.isinf(price) and not math.isnan(price)

    async def calculate_price_difference(self, price1: float, price2: float) -> float:
        """
        Calculate percentage difference between two prices.

        Args:
            price1 (float): First price
            price2 (float): Second price

        Returns:
            float: Price difference as a decimal (e.g., 0.05 for 5%)
        """
        if not (self.validate_price(price1) and self.validate_price(price2)):
            raise ValueError("Invalid prices provided")

        return abs(price2 - price1) / price1

    async def get_current_price(self, token: str) -> float:
        """
        Get current price from DEX quoters.

        Args:
            token (str): Token identifier

        Returns:
            float: Current price
        """
        cache_entry = self._price_cache.get(token)
        if cache_entry:
            timestamp, price = cache_entry
            if datetime.now() - timestamp < self._cache_duration:
                return price

        try:
            # Get token addresses from config
            tokens = self.config.get("tokens", {})
            if token.upper() not in tokens:
                raise ValueError(f"Token {token} not found in config")

            token_address = tokens[token.upper()]["address"]
            weth_address = tokens["WETH"]["address"]
            
            # Get quotes from enabled DEXes
            quotes = []
            amount_in = self.web3_manager.w3.to_wei(1, 'ether')  # 1 WETH
            
            for dex_name, dex_config in self.config["dexes"].items():
                if not dex_config.get("enabled", False):
                    continue
                    
                try:
                    quote = await self.get_quote(
                        dex_name,
                        weth_address,
                        token_address,
                        amount_in,
                        dex_config.get("fee")
                    )
                    if quote > 0:
                        # Convert to proper decimal places
                        token_decimals = tokens[token.upper()]["decimals"]
                        quote_float = float(quote) / (10 ** token_decimals)
                        quotes.append(quote_float)
                except Exception as e:
                    logger.warning(f"{dex_name} quote failed: {e}")
            
            if not quotes:
                raise ValueError("No valid quotes received")
                
            # Use average of available quotes
            price = sum(quotes) / len(quotes)
            self._price_cache[token] = (datetime.now(), price)
            return price
            
        except Exception as e:
            logger.error(f"Error getting price for {token}: {e}")
            raise

    async def get_prices(self, tokens: List[str]) -> Dict[str, float]:
        """
        Get prices for multiple tokens.

        Args:
            tokens (List[str]): List of token identifiers

        Returns:
            Dict[str, float]: Token prices
        """
        try:
            prices = await self.get_mcp_prices(tokens)
            if not prices:
                raise Exception("Failed to fetch prices")

            # Validate all prices
            for token, price in prices.items():
                if not self.validate_price(price):
                    raise ValueError(f"Invalid price for {token}: {price}")

            # Update cache
            now = datetime.now()
            for token, price in prices.items():
                self._price_cache[token] = (now, price)

            return prices

        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            raise  # Re-raise to handle failure at caller level

    async def analyze_market_conditions(self, token: str) -> Dict[str, Any]:
        """
        Analyze market conditions for token.

        Args:
            token (str): Token to analyze

        Returns:
            Dict[str, Any]: Market conditions

        Raises:
            Exception: If unable to get valid market conditions from MCP
        """
        try:
            # Map token symbol to CoinGecko ID for MCP tool
            if token in self.TOKEN_MAP:
                symbol = self.TOKEN_MAP[token]
            else:
                symbol = token.lower()
                
            logger.info(f"Analyzing market conditions for {token} -> {symbol}")
            
            # Get market analysis from MCP with retry logic
            max_retries = 3
            retry_delay = 1.0
            last_error = None

            for attempt in range(max_retries):
                try:
                    # Wait for rate limit
                    await self._analysis_limiter.acquire()
                    
                    response = await use_mcp_tool(
                        server_name="market-analysis",
                        tool_name="assess_market_conditions",
                        arguments={
                            "token": symbol,
                            "metrics": ["volatility", "volume", "liquidity", "trend"],
                        }
                    )
                    
                    if response:
                        break
                        
                except Exception as e:
                    last_error = e
                    if "429" in str(e):  # Rate limit error
                        self._analysis_limiter.on_error()  # Record rate limit error
                        retry_delay = min(30, retry_delay * 2)  # Exponential backoff
                        logger.warning(f"Rate limited, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                        continue
                    raise  # Re-raise non-rate-limit errors
            else:
                if last_error:
                    if "429" in str(last_error):
                        self._analysis_limiter.on_error()  # Record final rate limit error
                    raise last_error

            if not response:
                raise Exception(f"No market analysis response for {symbol}")

            # Validate required fields
            required_fields = ["trend", "volume_24h", "liquidity", "volatility_24h", "price_impact"]
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                raise ValueError(f"Missing required fields in market analysis: {missing_fields}")

            return response

        except Exception as e:
            logger.error(f"Failed to analyze market conditions for {token}: {e}")
            raise  # Re-raise to handle failure at caller level

    async def get_mcp_prices(self, tokens: List[str], max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, float]:
        """
        Get current prices from MCP with retry logic.

        Args:
            tokens (List[str]): List of token identifiers
            max_retries (int): Maximum number of retry attempts
            retry_delay (float): Delay between retries in seconds

        Returns:
            Dict[str, float]: Current prices

        Raises:
            Exception: If unable to get valid prices from MCP after retries
        """
        if not tokens:
            logger.error("No tokens provided to get_mcp_prices")
            return {}

        logger.info(f"Starting price fetch for tokens: {tokens}")
        last_error = None

        for attempt in range(max_retries):
            try:
                # Get token IDs for MCP server
                token_ids = []
                token_map = {
                    "WETH": "ethereum",
                    "USDC": "usd-coin",
                    "DAI": "dai"
                }

                for token in tokens:
                    upper_token = token.upper()
                    if upper_token in token_map:
                        token_ids.append(token_map[upper_token])
                    else:
                        token_ids.append(token.lower())
                        
                logger.info(f"Mapped tokens to CoinGecko IDs:")
                for i, (token, token_id) in enumerate(zip(tokens, token_ids)):
                    logger.info(f"  {i+1}. {token} -> {token_id}")
                
                # Wait for rate limit
                await self._price_limiter.acquire()
                
                # Get prices from MCP server
                logger.info(f"Sending MCP request to crypto-price server (attempt {attempt + 1}/{max_retries}):")
                logger.info(f"  Tool: get_prices")
                logger.info(f"  Arguments: {{'coins': {token_ids}, 'include_24h_change': True}}")
                
                try:
                    response = await use_mcp_tool(
                        server_name="crypto-price",
                        tool_name="get_prices",
                        arguments={
                            "coins": token_ids,
                            "include_24h_change": True
                        }
                    )
                    
                    logger.info(f"Received MCP response: {response}")
                except Exception as e:
                    logger.error(f"MCP tool call failed: {e}")
                    raise

                if not response:
                    raise ValueError("Empty response from MCP")

                # Check for error response
                if isinstance(response, dict) and 'error' in response:
                    raise ValueError(f"MCP error: {response['error']}")

                # The response should already be parsed by mcp_client.py
                if isinstance(response, dict) and 'prices' in response:
                    prices = {}
                    for token, price_data in response['prices'].items():
                        if isinstance(price_data, dict) and 'price_usd' in price_data:
                            price = price_data['price_usd']
                            if self.validate_price(price):
                                prices[token] = price

                    if prices:
                        logger.info(f"Successfully extracted prices: {prices}")
                        return prices

                logger.warning(f"Invalid response format: {response}")
                raise ValueError("Failed to extract valid prices from response")

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to get prices from MCP after {max_retries} attempts: {last_error}")
                    raise Exception(f"Failed to get prices after {max_retries} attempts: {last_error}")

        raise Exception(f"No valid prices found after {max_retries} attempts")

    async def get_opportunities(self) -> List[Dict[str, Any]]:
        """Get current arbitrage opportunities by comparing DEX prices."""
        try:
            opportunities = []
            
            # Get token configurations
            tokens = self.config.get("tokens", {})
            if not tokens:
                logger.error("No tokens configured")
                return []

            # Get enabled DEXes
            enabled_dexes = [
                name for name, config in self.config["dexes"].items()
                if config.get("enabled", False)
            ]
            if len(enabled_dexes) < 2:
                logger.warning("Need at least 2 enabled DEXes for arbitrage")
                return []

            # Define trading pairs
            pairs = [
                ("WETH", "USDC"),
                ("WETH", "DAI")
            ]
            
            for base_token, quote_token in pairs:
                try:
                    if base_token not in tokens or quote_token not in tokens:
                        continue

                    base_address = tokens[base_token]["address"]
                    quote_address = tokens[quote_token]["address"]
                    amount_in = self.web3_manager.w3.to_wei(1, 'ether')  # 1 WETH

                    # Get quotes from all enabled DEXes
                    dex_quotes = {}
                    for dex_name in enabled_dexes:
                        quote = await self.get_quote(
                            dex_name,
                            base_address,
                            quote_address,
                            amount_in
                        )
                        if quote > 0:
                            dex_quotes[dex_name] = quote

                    # Compare prices between DEXes
                    for dex_from in dex_quotes:
                        for dex_to in dex_quotes:
                            if dex_from == dex_to:
                                continue

                            quote_from = dex_quotes[dex_from]
                            quote_to = dex_quotes[dex_to]
                            
                            # Calculate price difference
                            price_diff = abs(quote_to - quote_from)
                            price_diff_percent = price_diff / min(quote_to, quote_from)
                            
                            # Check if opportunity is profitable
                            if price_diff_percent > 0.005:  # 0.5% minimum difference
                                # Determine direction
                                if quote_to > quote_from:
                                    profit = (quote_to - quote_from) / 10 ** tokens[quote_token]["decimals"]
                                    amount_out = quote_to
                                else:
                                    continue  # Skip unprofitable direction
                                
                                # Get DEX-specific gas estimate from config
                                dex_config = self.config["dexes"].get(dex_from)
                                if not dex_config:
                                    continue
                                    
                                # Use DEX-specific gas estimate based on type
                                if "quoter" in dex_config:
                                    # V3 DEXs with quoter typically need more gas
                                    estimated_gas = 200000
                                else:
                                    # V2 DEXs use standard gas amount
                                    estimated_gas = dex_config.get("fee") == 3000 and 150000 or 175000
                                
                                # Calculate gas cost
                                gas_price = await self.web3_manager.w3.eth.gas_price
                                gas_cost_wei = int(estimated_gas * gas_price)
                                gas_cost_eth = self.web3_manager.w3.from_wei(gas_cost_wei, 'ether')
                                
                                # Get ETH price from market conditions or skip opportunity
                                weth_condition = self.market_conditions.get("WETH")
                                if not weth_condition:
                                    logger.warning("No WETH price available, skipping opportunity")
                                    continue
                                eth_price = float(weth_condition.price)
                                
                                gas_cost_usd = float(gas_cost_eth) * eth_price
                                net_profit = profit - gas_cost_usd
                                
                                if net_profit > 0:
                                    opportunity = {
                                        'dex_from': dex_from,
                                        'dex_to': dex_to,
                                        'token_path': [base_address, quote_address],
                                        'amount_in': amount_in,
                                        'amount_out': amount_out,
                                        'profit_usd': net_profit,
                                        'gas_cost_usd': gas_cost_usd,
                                        'price_impact': price_diff_percent,
                                        'status': 'Ready',
                                        'timestamp': time.time(),
                                        'details': {
                                            'pair': f"{base_token}/{quote_token}",
                                            'price_diff_percent': price_diff_percent * 100,
                                            'quote_from': quote_from,
                                            'quote_to': quote_to
                                        }
                                    }
                                    
                                    logger.info(
                                        f"Found arbitrage opportunity:\n"
                                        f"  Pair: {base_token}/{quote_token}\n"
                                        f"  Route: {dex_from} -> {dex_to}\n"
                                        f"  Price diff: {price_diff_percent:.2%}\n"
                                        f"  Profit: ${net_profit:.2f}\n"
                                        f"  Gas Cost: ${gas_cost_usd:.2f}"
                                    )
                                    
                                    opportunities.append(opportunity)
                
                except Exception as e:
                    logger.error(f"Error analyzing pair {base_token}/{quote_token}: {e}")
                    continue
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Failed to get opportunities: {e}")
            return []

    async def get_performance_metrics(self) -> List[Dict[str, Any]]:
        """Get performance metrics for dashboard display."""
        try:
            # Get opportunities for active count
            opportunities = await self.get_opportunities()
            active_opportunities = len([opp for opp in opportunities if opp['status'] == 'Ready'])

            # Get DEX status for metrics
            dex_metrics = {}
            for dex_name, dex_config in self.config["dexes"].items():
                if dex_config.get("enabled", False):
                    dex_metrics[dex_name] = {
                        'active': True,
                        'liquidity': float(self.market_conditions.get('WETH', MarketCondition(
                            price=Decimal("0"),
                            trend=MarketTrend("sideways", 0, 0, 0, 0),
                            volume_24h=Decimal("0"),
                            liquidity=Decimal("0"),
                            volatility_24h=0,
                            price_impact=0,
                            last_updated=0
                        )).liquidity),
                        'volume_24h': float(self.market_conditions.get('WETH', MarketCondition(
                            price=Decimal("0"),
                            trend=MarketTrend("sideways", 0, 0, 0, 0),
                            volume_24h=Decimal("0"),
                            liquidity=Decimal("0"),
                            volatility_24h=0,
                            price_impact=0,
                            last_updated=0
                        )).volume_24h)
                    }

            # Create metrics for each token
            metrics = []
            for symbol, condition in self.market_conditions.items():
                backoff_status = self.get_backoff_status()
                
                # Calculate simulated portfolio metrics
                eth_price = float(self.market_conditions.get('WETH', MarketCondition(
                    price=Decimal("2000.0"),
                    trend=MarketTrend("sideways", 0, 0, 0, 0),
                    volume_24h=Decimal("0"),
                    liquidity=Decimal("0"),
                    volatility_24h=0,
                    price_impact=0,
                    last_updated=0
                )).price)
                
                # Calculate total profit from opportunities
                total_profit = sum(opp['profit_usd'] for opp in opportunities)
                
                # Calculate 24h metrics
                now = time.time()
                opportunities_24h = [opp for opp in opportunities if now - opp.get('timestamp', now) <= 86400]
                profit_24h = sum(opp['profit_usd'] for opp in opportunities_24h)
                
                # Calculate success rate from actual opportunities
                executed_opportunities = [opp for opp in opportunities if opp['status'] == 'Executed']
                success_rate = len(executed_opportunities) / max(1, len(opportunities))
                
                metrics.append({
                    'total_trades': len(executed_opportunities),
                    'trades_24h': len(opportunities_24h),
                    'success_rate': success_rate,
                    'total_profit_usd': total_profit,
                    'portfolio_change_24h': profit_24h,
                    'active_opportunities': active_opportunities,
                    'system_status': backoff_status['status'],
                    'backoff_time': backoff_status['backoff_time'],
                    'price': float(condition.price),
                    'volume_24h': float(condition.volume_24h),
                    'liquidity': float(condition.liquidity),
                    'volatility': condition.volatility_24h,
                    'trend': condition.trend.direction,
                    'trend_strength': condition.trend.strength,
                    'confidence': condition.trend.confidence,
                    'last_updated': condition.last_updated,
                    'dex_metrics': dex_metrics
                })
            return metrics
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return []

    async def monitor_prices(self, tokens: List[str]):
        """
        Monitor prices for tokens.

        Args:
            tokens (List[str]): List of token identifiers

        Yields:
            Dict[str, float]: Updated prices
        """
        while True:
            try:
                prices = await self.get_mcp_prices(tokens)
                if prices:
                    yield prices
            except Exception as e:
                logger.error(f"Price monitoring error: {e}")
                yield {}

    async def start_monitoring(self):
        """Start market monitoring loop."""
        try:
            while True:
                try:
                    await self._update_market_conditions()
                    await asyncio.sleep(60)  # Update every 60 seconds to respect rate limits
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    # Exponential backoff on error
                    retry_delay = min(30, 5 * (2 ** len(self._error_count)))
                    self._error_count.append(time.time())
                    # Clean up old errors
                    self._error_count = [t for t in self._error_count if time.time() - t < 300]
                    logger.info(f"Rate limit backoff: Waiting {retry_delay}s. Recent errors: {len(self._error_count)}")
                    await asyncio.sleep(retry_delay)
        except Exception as e:
            logger.error(f"Market monitoring failed: {e}")
            raise

    async def _update_market_conditions(self):
        """Update market conditions for all tracked tokens."""
        try:
            # Get token configurations
            tokens = self.config.get("tokens", {})
            if not tokens:
                raise ValueError("No tokens configured")

            logger.info("Token configurations:")
            for symbol, token_info in tokens.items():
                logger.info(f"  {symbol}: {token_info}")

            # Get token IDs for price lookup
            token_ids = []
            for symbol in tokens.keys():
                if symbol in self.TOKEN_MAP:
                    token_ids.append(self.TOKEN_MAP[symbol])
                else:
                    token_ids.append(symbol.lower())

            logger.info(f"Tracking tokens: {token_ids}")
            
            # Get current prices with fallback to cache
            try:
                prices = await self.get_mcp_prices(list(tokens.keys()))
            except Exception as e:
                logger.warning(f"Failed to get fresh prices, using cached data: {e}")
                # Use cached market conditions if available
                if self.market_conditions:
                    logger.info("Using cached market conditions")
                    return
                else:
                    logger.error("No cached data available")
                    raise

            # Process each token
            for token_id in token_ids:
                try:
                    # Convert token ID to symbol (reverse lookup)
                    symbol = None
                    for sym, tid in self.TOKEN_MAP.items():
                        if tid == token_id:
                            symbol = sym
                            break
                            
                    if not symbol:
                        logger.warning(f"No symbol mapping for {token_id}")
                        continue

                    logger.info(f"Processing market conditions for {token_id} -> {symbol}")

                    # Get price
                    if token_id not in prices:
                        logger.warning(f"No price data for {token_id}")
                        continue

                    price_decimal = Decimal(str(prices[token_id]))
                    
                    # Get market analysis
                    try:
                        market_data = await self.analyze_market_conditions(token_id)
                    except Exception as e:
                        logger.error(f"Failed to get market analysis for {token_id}: {e}")
                        continue

                    # Create trend object
                    trend = MarketTrend(
                        direction=market_data["trend"],
                        strength=float(market_data["trend_strength"]),
                        duration=float(market_data["trend_duration"]),
                        volatility=float(market_data["volatility"]),
                        confidence=float(market_data["confidence"])
                    )
                    
                    # Create market condition
                    condition = MarketCondition(
                        price=price_decimal,
                        trend=trend,
                        volume_24h=Decimal(str(market_data["volume_24h"])),
                        liquidity=Decimal(str(market_data["liquidity"])),
                        volatility_24h=float(market_data["volatility_24h"]),
                        price_impact=float(market_data["price_impact"]),
                        last_updated=float(datetime.now().timestamp())
                    )
                    
                    # Store market condition
                    self.market_conditions[symbol] = condition
                    
                    logger.info(
                        f"Updated market condition for {token_id}:\n"
                        f"  Price: ${price_decimal:,.2f}\n"
                        f"  Trend: {trend.direction} ({trend.strength:.1%})\n"
                        f"  Volume: ${condition.volume_24h:,.0f}\n"
                        f"  Liquidity: ${condition.liquidity:,.0f}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error updating market condition for {token_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to update market conditions: {e}")
            raise  # Re-raise to handle failure at caller level


class MarketAnalyzerContext:
    """Context manager for MarketAnalyzer to ensure proper cleanup."""
    def __init__(self, analyzer: MarketAnalyzer):
        self.analyzer = analyzer
        self.market_conditions = analyzer.market_conditions

    async def __aenter__(self):
        return self.analyzer

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.analyzer.cleanup()

    @property
    def market_conditions(self):
        return self.analyzer.market_conditions

    @market_conditions.setter
    def market_conditions(self, value):
        self.analyzer.market_conditions = value

    async def start_monitoring(self):
        """Delegate start_monitoring to the analyzer."""
        return await self.analyzer.start_monitoring()

    async def get_performance_metrics(self):
        """Delegate get_performance_metrics to the analyzer."""
        return await self.analyzer.get_performance_metrics()

async def create_market_analyzer(
    web3_manager: Optional[Web3Manager] = None,
    config: Optional[Dict[str, Any]] = None
) -> MarketAnalyzerContext:
    """
    Create and initialize a market analyzer instance.
    
    Args:
        web3_manager: Optional Web3Manager instance
        config: Optional configuration dictionary
        
    Returns:
        MarketAnalyzerContext: Context manager for the analyzer instance
        
    Raises:
        Exception: If initialization fails
    """
    if not web3_manager:
        web3_manager = await Web3Manager().connect()
        
    if not config:
        from ...utils.config_loader import load_config
        config = load_config()
        
    analyzer = MarketAnalyzer(web3_manager=web3_manager, config=config)
    
    try:
        # Start initial data collection
        await analyzer._update_market_conditions()
        logger.info("Market analyzer created and initialized")
        return MarketAnalyzerContext(analyzer)
        
    except Exception as e:
        await analyzer.cleanup()
        logger.error(f"Failed to initialize market analyzer: {e}")
        raise  # Re-raise to handle failure at caller level
