"""Distribution system for managing trade execution across DEXes."""

from typing import Dict, List, Optional, NamedTuple, Tuple
from dataclasses import dataclass
from decimal import Decimal
import json
import time
from ..storage.factory import create_storage_hub
from ..memory import MemoryBank

@dataclass
class DistributionConfig:
    """Configuration for distribution system."""
    max_exposure_per_dex: Decimal  # Maximum capital exposure per DEX
    max_exposure_per_pair: Decimal  # Maximum capital exposure per trading pair
    min_liquidity_threshold: Decimal  # Minimum liquidity required for trading
    rebalance_threshold: Decimal  # Threshold for triggering rebalancing
    gas_price_weight: float  # Weight for gas price in scoring (0-1)
    liquidity_weight: float  # Weight for liquidity in scoring (0-1)
    volume_weight: float  # Weight for volume in scoring (0-1)
    success_rate_weight: float  # Weight for success rate in scoring (0-1)

class DexScore(NamedTuple):
    """Score components for a DEX."""
    gas_score: float
    liquidity_score: float
    volume_score: float
    success_score: float
    total_score: float

class DistributionManager:
    """Manages distribution of trades across DEXes."""
    
    def __init__(self, config: DistributionConfig, memory_bank: Optional[MemoryBank] = None):
        """Initialize distribution manager.
        
        Args:
            config: Distribution configuration
            memory_bank: Optional memory bank for caching
        """
        self.config = config
        self.memory_bank = memory_bank
        self.storage = create_storage_hub(memory_bank=memory_bank)
        
        # Current distribution state
        self._dex_exposure: Dict[str, Decimal] = {}  # Current exposure per DEX
        self._pair_exposure: Dict[str, Decimal] = {}  # Current exposure per pair
        self._dex_scores: Dict[str, DexScore] = {}  # Current DEX scores
        
        # Load initial state
        self._load_state()
    
    def _load_state(self) -> None:
        """Load distribution state from storage."""
        try:
            state = self.storage.config.retrieve("distribution_state")
            if state:
                self._dex_exposure = {k: Decimal(str(v)) for k, v in state['dex_exposure'].items()}
                self._pair_exposure = {k: Decimal(str(v)) for k, v in state['pair_exposure'].items()}
        except Exception:
            # Start fresh if state can't be loaded
            self._dex_exposure = {}
            self._pair_exposure = {}
    
    def _save_state(self) -> None:
        """Save current distribution state to storage."""
        state = {
            'dex_exposure': {k: str(v) for k, v in self._dex_exposure.items()},
            'pair_exposure': {k: str(v) for k, v in self._pair_exposure.items()},
            'timestamp': time.time()
        }
        self.storage.config.store("distribution_state", state)
    
    def _calculate_dex_scores(self) -> None:
        """Calculate scores for each DEX based on performance metrics."""
        try:
            # Get performance metrics
            metrics = self.storage.performance.retrieve("dex_metrics")
            if not metrics:
                return
            
            # Calculate scores for each DEX
            for dex_name, dex_metrics in metrics.items():
                # Normalize gas prices (lower is better)
                max_gas = max(m['avg_gas_price'] for m in metrics.values())
                gas_score = 1 - (dex_metrics['avg_gas_price'] / max_gas if max_gas > 0 else 0)
                
                # Normalize liquidity (higher is better)
                max_liquidity = max(m['total_liquidity'] for m in metrics.values())
                liquidity_score = dex_metrics['total_liquidity'] / max_liquidity if max_liquidity > 0 else 0
                
                # Normalize volume (higher is better)
                max_volume = max(m['volume_24h'] for m in metrics.values())
                volume_score = dex_metrics['volume_24h'] / max_volume if max_volume > 0 else 0
                
                # Calculate success rate
                total_trades = dex_metrics['successful_trades'] + dex_metrics['failed_trades']
                success_score = dex_metrics['successful_trades'] / total_trades if total_trades > 0 else 0
                
                # Calculate weighted total score
                total_score = (
                    self.config.gas_price_weight * gas_score +
                    self.config.liquidity_weight * liquidity_score +
                    self.config.volume_weight * volume_score +
                    self.config.success_rate_weight * success_score
                )
                
                self._dex_scores[dex_name] = DexScore(
                    gas_score=gas_score,
                    liquidity_score=liquidity_score,
                    volume_score=volume_score,
                    success_score=success_score,
                    total_score=total_score
                )
        except Exception:
            # Keep existing scores if calculation fails
            pass
    
    def get_dex_allocation(self, amount: Decimal, pair: str) -> List[Tuple[str, Decimal]]:
        """Get optimal DEX allocation for a trade.
        
        Args:
            amount: Total trade amount
            pair: Trading pair (e.g. "ETH/USDC")
            
        Returns:
            List of (dex_name, amount) tuples for trade distribution
        """
        # Update DEX scores
        self._calculate_dex_scores()
        
        # Sort DEXes by score
        sorted_dexes = sorted(
            self._dex_scores.items(),
            key=lambda x: x[1].total_score,
            reverse=True
        )
        
        # Allocate trade amounts
        allocations = []
        remaining = amount
        
        for dex_name, score in sorted_dexes:
            # Skip if DEX would exceed exposure limit
            current_exposure = self._dex_exposure.get(dex_name, Decimal('0'))
            if current_exposure + remaining > self.config.max_exposure_per_dex:
                continue
            
            # Skip if pair would exceed exposure limit
            pair_exposure = self._pair_exposure.get(pair, Decimal('0'))
            if pair_exposure + remaining > self.config.max_exposure_per_pair:
                continue
            
            # Allocate proportionally to score
            allocation = min(
                remaining,
                self.config.max_exposure_per_dex - current_exposure,
                self.config.max_exposure_per_pair - pair_exposure
            )
            
            if allocation > 0:
                allocations.append((dex_name, allocation))
                remaining -= allocation
            
            if remaining <= 0:
                break
        
        return allocations
    
    def update_exposure(self, dex: str, pair: str, amount: Decimal) -> None:
        """Update exposure tracking after trade execution.
        
        Args:
            dex: DEX name
            pair: Trading pair
            amount: Trade amount (positive for increase, negative for decrease)
        """
        # Update DEX exposure
        current_dex = self._dex_exposure.get(dex, Decimal('0'))
        self._dex_exposure[dex] = max(Decimal('0'), current_dex + amount)
        
        # Update pair exposure
        current_pair = self._pair_exposure.get(pair, Decimal('0'))
        self._pair_exposure[pair] = max(Decimal('0'), current_pair + amount)
        
        # Save updated state
        self._save_state()
    
    def check_rebalance_needed(self) -> bool:
        """Check if rebalancing is needed based on exposure distribution."""
        if not self._dex_exposure:
            return False
        
        # Calculate exposure imbalance
        max_exposure = max(self._dex_exposure.values())
        min_exposure = min(self._dex_exposure.values())
        
        if max_exposure <= 0:
            return False
        
        imbalance = (max_exposure - min_exposure) / max_exposure
        return imbalance > self.config.rebalance_threshold
    
    def get_rebalancing_trades(self) -> List[Tuple[str, str, str, Decimal]]:
        """Get list of trades needed for rebalancing.
        
        Returns:
            List of (from_dex, to_dex, pair, amount) tuples
        """
        if not self.check_rebalance_needed():
            return []
        
        trades = []
        sorted_dexes = sorted(
            self._dex_exposure.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Calculate target exposure
        total_exposure = sum(self._dex_exposure.values())
        num_dexes = len(self._dex_exposure)
        target_exposure = total_exposure / num_dexes
        
        # Generate rebalancing trades
        for i, (from_dex, from_exposure) in enumerate(sorted_dexes[:-1]):
            if from_exposure <= target_exposure:
                continue
                
            for to_dex, to_exposure in sorted_dexes[i+1:]:
                if to_exposure >= target_exposure:
                    continue
                
                # Calculate transfer amount
                amount = min(
                    from_exposure - target_exposure,
                    target_exposure - to_exposure
                )
                
                if amount > 0:
                    # Find best pair for transfer
                    # TODO: Implement pair selection logic
                    pair = "ETH/USDC"  # Placeholder
                    
                    trades.append((from_dex, to_dex, pair, amount))
                    
                    # Update exposures
                    from_exposure -= amount
                    to_exposure += amount
        
        return trades
    
    def get_distribution_stats(self) -> Dict:
        """Get current distribution statistics."""
        return {
            'dex_exposure': {k: str(v) for k, v in self._dex_exposure.items()},
            'pair_exposure': {k: str(v) for k, v in self._pair_exposure.items()},
            'dex_scores': {k: v._asdict() for k, v in self._dex_scores.items()},
            'needs_rebalancing': self.check_rebalance_needed(),
            'timestamp': time.time()
        }
