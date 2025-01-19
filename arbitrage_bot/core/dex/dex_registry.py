"""DEX Registry for managing DEX integrations."""

import logging
from typing import Dict, List, Optional, Type, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from web3 import Web3

logger = logging.getLogger(__name__)

@dataclass
class QuoteResult:
    """Result of a DEX quote operation."""
    amount_out: int
    fee: int
    price_impact: float
    path: List[str]
    success: bool
    error: Optional[str] = None

class BaseDEX(ABC):
    """Base class for all DEX integrations."""
    
    def __init__(self, web3: Web3, config: dict):
        """Initialize DEX with Web3 instance and config."""
        self.w3 = web3
        self.config = config
        self.name = config.get('name', 'unknown')
        self.version = config.get('version', 'v2')
        self._initialize_logging()

    def _initialize_logging(self):
        """Initialize DEX-specific logging."""
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self.logger.setLevel(logging.DEBUG)

    @abstractmethod
    async def get_quote(self, token_in: str, token_out: str, amount_in: int) -> QuoteResult:
        """Get quote for token swap."""
        pass

    @abstractmethod
    async def check_liquidity(self, token_in: str, token_out: str) -> Decimal:
        """Check liquidity for token pair."""
        pass

    def log_error(self, error: Exception, context: dict = None):
        """Log error with context."""
        if context is None:
            context = {}
        self.logger.error(
            f"DEX {self.name} error: {str(error)}",
            extra={
                "dex_name": self.name,
                "version": self.version,
                **context
            }
        )

class DEXRegistry:
    """Registry for managing DEX integrations."""

    def __init__(self):
        """Initialize registry."""
        self._dexes: Dict[str, BaseDEX] = {}
        self.logger = logging.getLogger(__name__)

    def register(self, dex: BaseDEX) -> None:
        """Register a DEX instance."""
        self.logger.info(f"Registering DEX: {dex.name} (v{dex.version})")
        self._dexes[dex.name] = dex

    def unregister(self, dex_name: str) -> None:
        """Unregister a DEX."""
        if dex_name in self._dexes:
            self.logger.info(f"Unregistering DEX: {dex_name}")
            del self._dexes[dex_name]

    def get_dex(self, name: str) -> Optional[BaseDEX]:
        """Get DEX by name."""
        return self._dexes.get(name)

    def list_dexes(self) -> List[str]:
        """List all registered DEXes."""
        return list(self._dexes.keys())

    async def get_best_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        excluded_dexes: List[str] = None
    ) -> Optional[tuple[str, QuoteResult]]:
        """
        Get best quote across all registered DEXes.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei
            excluded_dexes: List of DEX names to exclude
            
        Returns:
            Tuple of (dex_name, quote_result) or None if no valid quotes
        """
        if excluded_dexes is None:
            excluded_dexes = []

        best_quote = None
        best_dex = None
        
        for dex_name, dex in self._dexes.items():
            if dex_name in excluded_dexes:
                continue
                
            try:
                quote = await dex.get_quote(token_in, token_out, amount_in)
                if quote.success and (best_quote is None or quote.amount_out > best_quote.amount_out):
                    best_quote = quote
                    best_dex = dex_name
            except Exception as e:
                dex.log_error(e, {
                    "method": "get_quote",
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": amount_in
                })

        if best_quote and best_dex:
            return best_dex, best_quote
        return None

    async def check_opportunities(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        min_profit_bps: int = 50  # 0.5%
    ) -> List[dict]:
        """
        Check for arbitrage opportunities across DEX pairs.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount_in: Input amount in wei
            min_profit_bps: Minimum profit in basis points (1 bp = 0.01%)
            
        Returns:
            List of opportunity details
        """
        opportunities = []
        dex_quotes = {}

        # Get quotes from all DEXes
        for dex_name, dex in self._dexes.items():
            try:
                quote = await dex.get_quote(token_in, token_out, amount_in)
                if quote.success:
                    dex_quotes[dex_name] = quote
            except Exception as e:
                dex.log_error(e, {
                    "method": "check_opportunities",
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": amount_in
                })

        # Compare quotes to find opportunities
        for dex_a, quote_a in dex_quotes.items():
            for dex_b, quote_b in dex_quotes.items():
                if dex_a == dex_b:
                    continue

                # Calculate profit in basis points
                profit_bps = (quote_b.amount_out - quote_a.amount_out) * 10000 // quote_a.amount_out

                if profit_bps >= min_profit_bps:
                    opportunities.append({
                        "dex_from": dex_a,
                        "dex_to": dex_b,
                        "profit_bps": profit_bps,
                        "amount_in": amount_in,
                        "amount_out": quote_b.amount_out,
                        "token_in": token_in,
                        "token_out": token_out,
                        "quote_from": quote_a,
                        "quote_to": quote_b
                    })

        return opportunities