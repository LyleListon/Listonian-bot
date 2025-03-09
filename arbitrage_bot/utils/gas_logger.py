"""Gas usage logging utilities."""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GasLogger:
    """Logs gas usage statistics."""

    def __init__(self, log_dir: str = "logs/gas"):
        """Initialize gas logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_month = self._get_current_log_file()
        self.stats = self._load_stats()
        
    def _get_current_log_file(self) -> str:
        """Get current month's log file name."""
        return datetime.now().strftime("%Y%m")
        
    def _load_stats(self) -> Dict[str, Any]:
        """Load existing stats or create new ones."""
        try:
            log_file = self.log_dir / f"gas_{self.current_month}.json"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load gas stats: {e}")
            
        return {
            'total_gas_used': 0,
            'total_gas_cost_wei': 0,
            'transaction_count': 0,
            'transfers_to_recipient': 0,
            'kept_in_wallet': 0,
            'average_gas_price': 0,
            'highest_gas_price': 0,
            'lowest_gas_price': float('inf'),
            'transactions': []
        }
        
    def log_gas_usage(
        self,
        gas_used: int,
        gas_price: int,
        tx_hash: str,
        sent_to_recipient: bool,
        eth_balance: float,
        estimated_gas_cost: int
    ):
        """Log gas usage for a transaction."""
        try:
            # Update stats
            gas_cost = gas_used * gas_price
            self.stats['total_gas_used'] += gas_used
            self.stats['total_gas_cost_wei'] += gas_cost
            self.stats['transaction_count'] += 1
            
            if sent_to_recipient:
                self.stats['transfers_to_recipient'] += 1
            else:
                self.stats['kept_in_wallet'] += 1
                
            # Update gas price stats
            self.stats['average_gas_price'] = (
                self.stats['total_gas_cost_wei'] / self.stats['total_gas_used']
            )
            self.stats['highest_gas_price'] = max(self.stats['highest_gas_price'], gas_price)
            self.stats['lowest_gas_price'] = min(self.stats['lowest_gas_price'], gas_price)
            
            # Add transaction details
            self.stats['transactions'].append({
                'timestamp': datetime.now().isoformat(),
                'tx_hash': tx_hash,
                'gas_used': gas_used,
                'gas_price': gas_price,
                'gas_cost_wei': gas_cost,
                'sent_to_recipient': sent_to_recipient,
                'eth_balance': eth_balance,
                'estimated_gas_cost': estimated_gas_cost
            })
            
            # Save updated stats
            self._save_stats()
            
            # Log summary
            logger.info("\nGas Usage Summary:")
            logger.info("="*50)
            logger.info(f"Transaction Hash: {tx_hash}")
            logger.info(f"Gas Used: {gas_used:,}")
            logger.info(f"Gas Price: {gas_price / 1e9:.2f} gwei")
            logger.info(f"Total Cost: {gas_cost / 1e18:.6f} ETH")
            logger.info(f"Sent to Recipient: {'Yes' if sent_to_recipient else 'No'}")
            logger.info(f"ETH Balance: {eth_balance:.6f}")
            logger.info(f"Estimated Gas Cost: {estimated_gas_cost / 1e18:.6f} ETH")
            logger.info("="*50)
            
        except Exception as e:
            logger.error(f"Failed to log gas usage: {e}")
            
    def _save_stats(self):
        """Save current stats to file."""
        try:
            log_file = self.log_dir / f"gas_{self.current_month}.json"
            with open(log_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save gas stats: {e}")
            
    def get_monthly_summary(self) -> Dict[str, Any]:
        """Get summary of current month's gas usage."""
        return {
            'total_gas_used': self.stats['total_gas_used'],
            'total_gas_cost_eth': self.stats['total_gas_cost_wei'] / 1e18,
            'transaction_count': self.stats['transaction_count'],
            'transfers_to_recipient': self.stats['transfers_to_recipient'],
            'kept_in_wallet': self.stats['kept_in_wallet'],
            'average_gas_price_gwei': self.stats['average_gas_price'] / 1e9,
            'highest_gas_price_gwei': self.stats['highest_gas_price'] / 1e9,
            'lowest_gas_price_gwei': self.stats['lowest_gas_price'] / 1e9
        }