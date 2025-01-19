"""Aerodrome DEX implementation."""

from typing import Dict, Any, List, Optional
from .base_dex_v2 import BaseDEXV2
from ..web3.web3_manager import Web3Manager

class AerodromeDEX(BaseDEXV2):
    """Aerodrome DEX V2 implementation."""

    def __init__(self, web3_manager: Web3Manager, config: Dict[str, Any]):
        """Initialize Aerodrome DEX."""
        super().__init__(web3_manager, config)
        self.name = "aerodrome"
        self.voter_address = config.get('voter')
        self.supports_stable_pools = config.get('supports_stable_pools', False)

    async def initialize(self) -> bool:
        """Initialize the Aerodrome DEX interface."""
        if not await super().initialize():
            return False
            
        try:
            # Additional Aerodrome-specific initialization
            if self.voter_address:
                await self.factory.functions.voter().call()
            return True
        except Exception as e:
            self._handle_error(e, "Aerodrome voter validation")
            return False

    async def get_quote_with_impact(
        self,
        amount_in: int,
        path: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get quote with price impact analysis for Aerodrome pools."""
        try:
            # Validate inputs
            await self._validate_path(path)
            await self._validate_amounts(amount_in=amount_in)
            
            # Try both stable and volatile pools
            pool_types = [True, False] if self.supports_stable_pools else [False]
            best_quote = None
            
            for is_stable in pool_types:
                # Get pair address
                pair_address = await self.factory.functions.getPair(
                    path[0],
                    path[1],
                    is_stable
                ).call()
                
                if pair_address == "0x0000000000000000000000000000000000000000":
                    continue
                    
                # Get pair contract
                pair = self.w3.eth.contract(
                    address=pair_address,
                    abi=self.pair_abi
                )
                
                # Get reserves
                reserves = await pair.functions.getReserves().call()
                reserve_in = reserves[0] if path[0] < path[1] else reserves[1]
                reserve_out = reserves[1] if path[0] < path[1] else reserves[0]
                
                if reserve_in == 0 or reserve_out == 0:
                    continue
                    
                # Calculate amounts
                amount_out = await self._get_amount_out(
                    amount_in,
                    reserve_in,
                    reserve_out
                )
                
                # Calculate price impact
                price_impact = self._calculate_price_impact(
                    amount_in,
                    amount_out,
                    reserve_in,
                    reserve_out
                )
                
                quote = {
                    'amount_in': amount_in,
                    'amount_out': amount_out,
                    'price_impact': price_impact,
                    'liquidity_depth': min(reserve_in, reserve_out),
                    'fee_rate': self.fee / 1000000,
                    'estimated_gas': 175000,  # Higher estimate for stable/volatile pool checks and getReserves calls
                    'min_out': int(amount_out * 0.995),
                    'is_stable': is_stable
                }
                
                # Update best quote if better amount out
                if not best_quote or quote['amount_out'] > best_quote['amount_out']:
                    best_quote = quote
            
            return best_quote
            
        except Exception as e:
            self._handle_error(e, "Aerodrome quote calculation")
            return None
