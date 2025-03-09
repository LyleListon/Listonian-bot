"""
Arbitrage Bot Connector

This module provides direct integration with the arbitrage bot for transaction execution.
It enables the dashboard to trigger arbitrage operations and manage trades for profit maximization.
"""

import os
import sys
import json
import logging
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple

# Configure logging
logger = logging.getLogger("arbitrage_dashboard.connector")

# Path to the main arbitrage bot module
ARBITRAGE_BOT_PATH = Path("arbitrage_bot")
CORE_PATH = ARBITRAGE_BOT_PATH / "core"
WEB3_MANAGER_PATH = CORE_PATH / "web3" / "web3_manager.py"
DEX_MANAGER_PATH = CORE_PATH / "dex" / "dex_manager.py"
SECURE_PATH = Path("secure")

class ArbitrageConnector:
    """Connector class to interface with the arbitrage bot system."""
    
    def __init__(self):
        self.web3_manager = None
        self.dex_manager = None
        self.path_finder = None
        self.flash_loan_manager = None
        self.config = self._load_config()
        self.initialized = False
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from arbitrage bot config files."""
        try:
            config_paths = [
                "configs/production.json",
                "configs/config.json"
            ]
            
            for path in config_paths:
                if os.path.exists(path):
                    logger.info(f"Loading configuration from {path}")
                    with open(path, "r") as f:
                        return json.load(f)
                        
            logger.warning("No configuration file found, using empty config")
            return {}
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return {}
    
    def initialize(self) -> Tuple[bool, str]:
        """Initialize connection to the arbitrage bot components."""
        try:
            # First check if the required modules exist
            if not WEB3_MANAGER_PATH.exists():
                return False, f"Web3 manager not found at {WEB3_MANAGER_PATH}"
            
            if not DEX_MANAGER_PATH.exists():
                return False, f"DEX manager not found at {DEX_MANAGER_PATH}"
            
            # Import the web3_manager module
            sys.path.append(str(ARBITRAGE_BOT_PATH.parent))
            
            # Try to import directly from the arbitrage_bot package
            try:
                from arbitrage_bot.core.web3.web3_manager import Web3Manager
                from arbitrage_bot.core.dex.dex_manager import DexManager
                
                logger.info("Successfully imported arbitrage bot modules via package")
                
                # Initialize Web3Manager using the configuration
                self.web3_manager = Web3Manager(self.config)
                
                # Initialize DexManager
                self.dex_manager = DexManager(self.web3_manager, self.config)
                
                # Try to import path finder if available
                try:
                    from arbitrage_bot.core.path_finder import PathFinder
                    self.path_finder = PathFinder(self.dex_manager, self.config)
                except ImportError:
                    logger.warning("PathFinder module not found, some functions may be limited")
                
                # Try to import flash loan manager if available
                try:
                    from arbitrage_bot.core.flash_loan_manager_async import AsyncFlashLoanManager
                    self.flash_loan_manager = AsyncFlashLoanManager(self.web3_manager, self.config)
                except ImportError:
                    logger.warning("FlashLoanManager module not found, some functions may be limited")
                
                self.initialized = True
                return True, "Successfully initialized connection to arbitrage bot"
                
            except ImportError as e:
                logger.error(f"Error importing arbitrage_bot modules: {e}")
                return False, f"Failed to import arbitrage_bot modules: {e}"
                
        except Exception as e:
            logger.error(f"Failed to initialize arbitrage connector: {e}")
            return False, f"Error initializing arbitrage connector: {e}"
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get the status of connections to various components."""
        status = {
            "initialized": self.initialized,
            "web3_manager": self.web3_manager is not None,
            "dex_manager": self.dex_manager is not None,
            "path_finder": self.path_finder is not None,
            "flash_loan_manager": self.flash_loan_manager is not None
        }
        
        # Add more detailed info if components are available
        if self.web3_manager:
            status["web3_connected"] = self.web3_manager.is_connected()
            
        if self.dex_manager:
            status["dexes_loaded"] = len(self.dex_manager.dexes) if hasattr(self.dex_manager, "dexes") else 0
            
        return status
    
    def find_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """Find current arbitrage opportunities."""
        if not self.initialized or not self.path_finder:
            logger.error("Cannot find opportunities: path_finder not initialized")
            return []
        
        try:
            # Try to use the path_finder to find opportunities
            opportunities = self.path_finder.find_opportunities()
            return opportunities if opportunities else []
        except Exception as e:
            logger.error(f"Error finding arbitrage opportunities: {e}")
            return []
    
    def execute_arbitrage(self, opportunity_id: str) -> Dict[str, Any]:
        """Execute an arbitrage opportunity."""
        if not self.initialized:
            return {"success": False, "error": "Arbitrage connector not initialized"}
        
        if not self.path_finder:
            return {"success": False, "error": "PathFinder not available"}
        
        try:
            # Execute the arbitrage opportunity
            result = self.path_finder.execute_opportunity(opportunity_id)
            return result
        except Exception as e:
            logger.error(f"Error executing arbitrage: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_flash_loan_arbitrage(self, path: List[str], amount: float) -> Dict[str, Any]:
        """Execute a flash loan arbitrage trade."""
        if not self.initialized:
            return {"success": False, "error": "Arbitrage connector not initialized"}
        
        if not self.flash_loan_manager:
            return {"success": False, "error": "Flash loan manager not available"}
        
        try:
            # Execute flash loan arbitrage
            result = self.flash_loan_manager.execute_arbitrage(path, amount)
            return result
        except Exception as e:
            logger.error(f"Error executing flash loan arbitrage: {e}")
            return {"success": False, "error": str(e)}
    
    def get_dex_prices(self, token_address: str) -> Dict[str, float]:
        """Get token prices across multiple DEXes."""
        if not self.initialized or not self.dex_manager:
            return {}
        
        try:
            prices = {}
            for dex_name, dex in self.dex_manager.dexes.items():
                try:
                    price = dex.get_token_price(token_address)
                    if price:
                        prices[dex_name] = price
                except Exception as e:
                    logger.debug(f"Error getting price from {dex_name}: {e}")
            
            return prices
        except Exception as e:
            logger.error(f"Error getting DEX prices: {e}")
            return {}
    
    def calculate_profit_potential(self, token_address: str) -> Dict[str, Any]:
        """Calculate profit potential for a token across DEXes."""
        if not self.initialized or not self.dex_manager:
            return {"error": "Not initialized"}
        
        prices = self.get_dex_prices(token_address)
        if not prices:
            return {"error": "No prices available"}
        
        # Find the min and max prices
        min_price = min(prices.values())
        max_price = max(prices.values())
        
        # Find the DEXes with min and max prices
        min_dex = [dex for dex, price in prices.items() if price == min_price][0]
        max_dex = [dex for dex, price in prices.items() if price == max_price][0]
        
        # Calculate the profit percentage
        profit_percentage = ((max_price - min_price) / min_price) * 100
        
        return {
            "token": token_address,
            "buy_dex": min_dex,
            "buy_price": min_price,
            "sell_dex": max_dex,
            "sell_price": max_price,
            "profit_percentage": profit_percentage
        }
    
    def manual_trade(self, buy_dex: str, sell_dex: str, token_address: str, amount: float) -> Dict[str, Any]:
        """Execute a manual trade between two DEXes."""
        if not self.initialized:
            return {"success": False, "error": "Arbitrage connector not initialized"}
        
        if not self.dex_manager:
            return {"success": False, "error": "DEX manager not available"}
        
        try:
            # Get the DEX objects
            buy_dex_obj = self.dex_manager.get_dex(buy_dex)
            sell_dex_obj = self.dex_manager.get_dex(sell_dex)
            
            if not buy_dex_obj:
                return {"success": False, "error": f"Buy DEX '{buy_dex}' not found"}
            
            if not sell_dex_obj:
                return {"success": False, "error": f"Sell DEX '{sell_dex}' not found"}
            
            # Execute the buy
            buy_result = buy_dex_obj.buy_token(token_address, amount)
            if not buy_result["success"]:
                return {"success": False, "error": f"Buy failed: {buy_result['error']}"}
            
            # Execute the sell
            token_amount = buy_result["amount"]
            sell_result = sell_dex_obj.sell_token(token_address, token_amount)
            
            # Calculate profit
            profit = sell_result["amount"] - amount
            
            return {
                "success": True,
                "profit": profit,
                "profit_percentage": (profit / amount) * 100,
                "buy_tx": buy_result["tx_hash"],
                "sell_tx": sell_result["tx_hash"]
            }
            
        except Exception as e:
            logger.error(f"Error executing manual trade: {e}")
            return {"success": False, "error": str(e)}
    
    def get_wallet_balance(self, address: Optional[str] = None) -> Dict[str, Any]:
        """Get wallet balance information."""
        if not self.initialized or not self.web3_manager:
            return {"error": "Not initialized"}
        
        try:
            if address:
                # Get balance for specified address
                balance = self.web3_manager.get_eth_balance(address)
            else:
                # Get balance for account being used by arbitrage bot
                balance = self.web3_manager.get_eth_balance()
            
            return {
                "eth_balance": balance,
                "usd_value": self.web3_manager.get_eth_to_usd(balance) if hasattr(self.web3_manager, "get_eth_to_usd") else None
            }
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return {"error": str(e)}
    
    def get_gas_settings(self) -> Dict[str, Any]:
        """Get current gas settings."""
        if not self.initialized or not self.web3_manager:
            return {}
        
        try:
            return {
                "gas_price": self.web3_manager.get_gas_price(),
                "max_fee_per_gas": self.web3_manager.get_max_fee_per_gas() if hasattr(self.web3_manager, "get_max_fee_per_gas") else None,
                "max_priority_fee": self.web3_manager.get_max_priority_fee() if hasattr(self.web3_manager, "get_max_priority_fee") else None,
                "gas_limit_multiplier": self.config.get("gas", {}).get("gas_limit_multiplier", 1.2)
            }
        except Exception as e:
            logger.error(f"Error getting gas settings: {e}")
            return {}
    
    def update_gas_settings(self, settings: Dict[str, Any]) -> bool:
        """Update gas settings for transactions."""
        if not self.initialized:
            return False
        
        try:
            # Update the configuration
            if "gas" not in self.config:
                self.config["gas"] = {}
            
            for key, value in settings.items():
                self.config["gas"][key] = value
            
            # Try to update the web3_manager gas settings if applicable
            if hasattr(self.web3_manager, "update_gas_settings"):
                self.web3_manager.update_gas_settings(settings)
            
            return True
        except Exception as e:
            logger.error(f"Error updating gas settings: {e}")
            return False

# Create singleton instance
connector = ArbitrageConnector()