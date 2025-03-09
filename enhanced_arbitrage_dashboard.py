"""
Enhanced Arbitrage Dashboard

This dashboard provides comprehensive monitoring of the arbitrage system,
including both critical metrics and interesting statistics.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Any
import json
from pathlib import Path
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedDashboard:
    def __init__(self):
        self.stats = {
            'system_status': {
                'start_time': datetime.now().isoformat(),
                'uptime': 0,
                'last_update': datetime.now().isoformat(),
                'mev_risk_level': 'unknown',
                'flash_loans_enabled': False,
                'flashbots_enabled': False
            },
            'performance': {
                'opportunities_found': 0,
                'successful_trades': 0,
                'failed_trades': 0,
                'total_profit_eth': 0.0,
                'avg_execution_time': 0.0,
                'gas_saved': 0.0
            },
            'network': {
                'chain_id': 1,
                'gas_price': 0,
                'block_number': 0,
                'connected_nodes': 0,
                'rpc_latency': 0.0
            },
            'dex_stats': {
                'active_dexes': 0,
                'total_pools': 0,
                'monitored_tokens': 0,
                'price_updates': 0
            },
            'flash_loans': {
                'total_borrowed': 0.0,
                'successful_repayments': 0,
                'failed_repayments': 0,
                'avg_loan_size': 0.0
            },
            'mev_protection': {
                'bundles_submitted': 0,
                'bundles_included': 0,
                'frontrun_attempts': 0,
                'sandwich_attacks': 0
            },
            'path_finder': {
                'paths_analyzed': 0,
                'profitable_paths': 0,
                'max_profit_seen': 0.0,
                'avg_path_length': 0.0
            },
            'token_metrics': {},
            'recent_events': []
        }
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)
        self.stats_file = self.log_dir / 'dashboard_stats.json'
        self.max_events = 100
        
    def save_stats(self):
        """Save current stats to file"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save dashboard stats: {e}")
            
    def load_stats(self):
        """Load stats from file"""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    saved_stats = json.load(f)
                    # Merge saved stats with default values
                    for category in self.stats:
                        if category in saved_stats:
                            if isinstance(self.stats[category], dict):
                                self.stats[category].update(saved_stats[category])
                            else:
                                self.stats[category] = saved_stats[category]
                    logger.info("Loaded dashboard stats from file")
                    logger.info(f"System Status: {self.stats['system_status']}")
                    logger.info(f"Performance: {self.stats['performance']}")
                    logger.info(f"Network: {self.stats['network']}")
        except Exception as e:
            logger.error(f"Failed to load dashboard stats: {e}")
            
    def print_dashboard(self):
        """Print current dashboard stats to console"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 80)
        print("ENHANCED ARBITRAGE DASHBOARD")
        print("=" * 80)
        
        # System Status
        print("\nSystem Status:")
        print(f"Uptime: {int(self.stats['system_status']['uptime'])} seconds")
        print(f"MEV Risk Level: {self.stats['system_status']['mev_risk_level']}")
        print(f"Flash Loans: {'Enabled' if self.stats['system_status']['flash_loans_enabled'] else 'Disabled'}")
        print(f"Flashbots: {'Enabled' if self.stats['system_status']['flashbots_enabled'] else 'Disabled'}")
        
        # Performance
        print("\nPerformance:")
        print(f"Opportunities Found: {self.stats['performance']['opportunities_found']}")
        print(f"Successful Trades: {self.stats['performance']['successful_trades']}")
        print(f"Total Profit (ETH): {self.stats['performance']['total_profit_eth']:.4f}")
        print(f"Avg Execution Time: {self.stats['performance']['avg_execution_time']:.2f}s")
        
        # Network
        print("\nNetwork Status:")
        print(f"Chain ID: {self.stats['network']['chain_id']}")
        print(f"Gas Price: {self.stats['network']['gas_price']} gwei")
        print(f"Block: {self.stats['network']['block_number']}")
        print(f"RPC Latency: {self.stats['network']['rpc_latency']:.2f}ms")
        
        # DEX Stats
        print("\nDEX Statistics:")
        print(f"Active DEXes: {self.stats['dex_stats']['active_dexes']}")
        print(f"Total Pools: {self.stats['dex_stats']['total_pools']}")
        print(f"Monitored Tokens: {self.stats['dex_stats']['monitored_tokens']}")
        
        # Flash Loans
        print("\nFlash Loan Stats:")
        print(f"Total Borrowed (ETH): {self.stats['flash_loans']['total_borrowed']:.2f}")
        print(f"Successful/Failed: {self.stats['flash_loans']['successful_repayments']}/{self.stats['flash_loans']['failed_repayments']}")
        
        # MEV Protection
        print("\nMEV Protection:")
        print(f"Bundles: {self.stats['mev_protection']['bundles_included']}/{self.stats['mev_protection']['bundles_submitted']}")
        print(f"Frontrun Attempts Blocked: {self.stats['mev_protection']['frontrun_attempts']}")
        print(f"Sandwich Attacks Prevented: {self.stats['mev_protection']['sandwich_attacks']}")
        
        # Path Finder
        print("\nPath Analysis:")
        print(f"Paths Analyzed: {self.stats['path_finder']['paths_analyzed']}")
        print(f"Profitable Paths: {self.stats['path_finder']['profitable_paths']}")
        print(f"Max Profit Seen (ETH): {self.stats['path_finder']['max_profit_seen']:.4f}")
        print(f"Avg Path Length: {self.stats['path_finder']['avg_path_length']:.2f}")
        
        # Recent Events
        print("\nRecent Events:")
        for event in self.stats['recent_events'][:5]:
            print(f"[{event['timestamp']}] {event['type']}: {event['description']}")
        
        print("\nPress Ctrl+C to exit")
        
    async def run(self):
        """Run the dashboard"""
        try:
            while True:
                self.load_stats()  # Load latest stats from file
                self.print_dashboard()
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nDashboard stopped.")
        except Exception as e:
            logger.error(f"Error in dashboard: {e}", exc_info=True)
            raise

def main():
    """Main entry point"""
    dashboard = EnhancedDashboard()
    try:
        asyncio.run(dashboard.run())
    except KeyboardInterrupt:
        print("\nShutting down dashboard...")

if __name__ == "__main__":
    main()