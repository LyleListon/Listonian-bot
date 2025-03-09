"""
Wallet Integration Module

Connects to Ethereum wallets to monitor balance, transactions and gas usage.
"""
import os
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests

logger = logging.getLogger(__name__)

# Default address if none is provided
DEFAULT_ADDRESS = "0x0000000000000000000000000000000000000000"

class WalletMonitor:
    """Monitors wallet activity and balances."""
    
    def __init__(self):
        """Initialize the wallet monitor."""
        self.wallet_address = None
        self.api_key = None
        self.chain_id = None
        self.network_name = "ethereum"
        self.balance = 0
        self.token_balances = {}
        self.last_transactions = []
        self.gas_usage = 0
        self.use_simulation = True
        self.last_update = None
        
        # Load wallet configuration
        self._load_config()
    
    def _load_config(self):
        """Load wallet configuration from environment or config file."""
        # First try environment variables
        self.wallet_address = os.environ.get('ETH_WALLET_ADDRESS')
        self.api_key = os.environ.get('ETHERSCAN_API_KEY')
        
        # If not found, try config file
        if not self.wallet_address or not self.api_key:
            try:
                with open('configs/config.json', 'r') as f:
                    config = json.load(f)
                    
                    # Get wallet address
                    if 'wallet' in config and 'address' in config['wallet']:
                        addr = config['wallet']['address']
                        # Handle secure references
                        if addr.startswith('$SECURE:'):
                            env_var = addr.replace('$SECURE:', '')
                            addr = os.environ.get(env_var, '')
                        self.wallet_address = addr
                    
                    # Get chain ID
                    if 'network' in config and 'chain_id' in config['network']:
                        self.chain_id = config['network']['chain_id']
                        
                        # Map chain ID to network name
                        network_map = {
                            1: "ethereum",
                            56: "bsc",
                            137: "polygon",
                            42161: "arbitrum",
                            10: "optimism",
                            8453: "base",
                            5: "goerli"
                        }
                        self.network_name = network_map.get(self.chain_id, "ethereum")
                    
                    # Get API keys
                    if 'api_keys' in config:
                        if 'etherscan' in config['api_keys']:
                            api_key = config['api_keys']['etherscan']
                            # Handle secure references
                            if api_key.startswith('$SECURE:'):
                                env_var = api_key.replace('$SECURE:', '')
                                api_key = os.environ.get(env_var, '')
                            self.api_key = api_key
            except Exception as e:
                logger.warning(f"Could not load wallet config: {e}")
        
        # Determine if we should use simulation
        if not self.wallet_address or not self.api_key:
            self.use_simulation = True
            logger.info("Using simulated wallet data")
            
            # Use profit recipient address if available
            try:
                with open('configs/config.json', 'r') as f:
                    config = json.load(f)
                    if 'arbitrage' in config and 'profit_recipient' in config['arbitrage']:
                        self.wallet_address = config['arbitrage']['profit_recipient']
            except:
                pass
            
            if not self.wallet_address:
                self.wallet_address = DEFAULT_ADDRESS
        else:
            self.use_simulation = False
            logger.info(f"Monitoring wallet: {self.wallet_address[:10]}...")
    
    def get_balance(self) -> Dict[str, Any]:
        """Get wallet balance for ETH and tokens."""
        if self.use_simulation:
            return self._get_simulated_balance()
        
        try:
            # Build API URL based on network
            if self.network_name == "ethereum":
                api_url = f"https://api.etherscan.io/api?module=account&action=balance&address={self.wallet_address}&tag=latest&apikey={self.api_key}"
            else:
                # For now, fall back to simulation for other networks
                return self._get_simulated_balance()
            
            # Fetch balance
            response = requests.get(api_url)
            data = response.json()
            
            if data.get('status') == '1':
                balance_wei = int(data.get('result', '0'))
                balance_eth = balance_wei / 1e18
                
                # Cache the result
                self.balance = balance_eth
                self.last_update = datetime.now()
                
                # Return formatted data
                return {
                    'address': self.wallet_address,
                    'eth_balance': balance_eth,
                    'token_balances': self._get_token_balances(),
                    'last_update': self.last_update.isoformat()
                }
            else:
                logger.warning(f"Failed to get balance: {data.get('message')}")
                return self._get_simulated_balance()
                
        except Exception as e:
            logger.warning(f"Error getting wallet balance: {e}")
            return self._get_simulated_balance()
    
    def _get_token_balances(self) -> Dict[str, float]:
        """Get token balances for the wallet."""
        try:
            # Build API URL
            if self.network_name == "ethereum":
                api_url = f"https://api.etherscan.io/api?module=account&action=tokenbalance&contractaddress={{token_address}}&address={self.wallet_address}&tag=latest&apikey={self.api_key}"
            else:
                # Fall back to simulation for other networks
                return self._get_simulated_token_balances()
            
            # Token addresses to check
            token_addresses = {
                'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
                'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
                'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
                'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
            }
            
            # Get balances for each token
            balances = {}
            for symbol, address in token_addresses.items():
                try:
                    token_url = api_url.format(token_address=address)
                    response = requests.get(token_url)
                    data = response.json()
                    
                    if data.get('status') == '1':
                        # Get decimals for the token (default to 18 if not found)
                        decimals = 18
                        if symbol == 'USDC' or symbol == 'USDT':
                            decimals = 6
                        elif symbol == 'WBTC':
                            decimals = 8
                            
                        balance_raw = int(data.get('result', '0'))
                        balance = balance_raw / (10 ** decimals)
                        
                        # Only include non-zero balances
                        if balance > 0:
                            balances[symbol] = balance
                except Exception as e:
                    logger.debug(f"Error getting {symbol} balance: {e}")
            
            # Cache the results
            self.token_balances = balances
            return balances
            
        except Exception as e:
            logger.warning(f"Error getting token balances: {e}")
            return self._get_simulated_token_balances()
    
    def _get_simulated_balance(self) -> Dict[str, Any]:
        """Generate simulated wallet balance data."""
        # If we already have a simulated balance, modify it slightly to simulate changes
        if self.balance > 0:
            # Random change between -0.1% and +0.2%
            change_pct = random.uniform(-0.001, 0.002)
            self.balance = self.balance * (1 + change_pct)
        else:
            # Initial balance between 0.5 and 5 ETH
            self.balance = random.uniform(0.5, 5.0)
        
        # Get simulated token balances
        token_balances = self._get_simulated_token_balances()
        
        self.last_update = datetime.now()
        
        return {
            'address': self.wallet_address,
            'eth_balance': self.balance,
            'token_balances': token_balances,
            'last_update': self.last_update.isoformat(),
            'simulated': True
        }
    
    def _get_simulated_token_balances(self) -> Dict[str, float]:
        """Generate simulated token balances."""
        # If we already have balances, modify them slightly
        if self.token_balances:
            balances = {}
            for symbol, balance in self.token_balances.items():
                # Random change between -0.1% and +0.2%
                change_pct = random.uniform(-0.001, 0.002)
                balances[symbol] = balance * (1 + change_pct)
            return balances
        else:
            # Generate initial balances
            return {
                'USDC': random.uniform(1000, 10000),
                'WETH': random.uniform(1, 10),
                'DAI': random.uniform(500, 5000),
                'WBTC': random.uniform(0.05, 0.5),
                'USDT': random.uniform(500, 5000)
            }
    
    def get_transactions(self, limit=10) -> List[Dict[str, Any]]:
        """Get recent transactions for the wallet."""
        if self.use_simulation:
            return self._get_simulated_transactions(limit)
        
        try:
            # Build API URL
            if self.network_name == "ethereum":
                api_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={self.wallet_address}&startblock=0&endblock=99999999&page=1&offset={limit}&sort=desc&apikey={self.api_key}"
            else:
                # Fall back to simulation for other networks
                return self._get_simulated_transactions(limit)
            
            # Fetch transactions
            response = requests.get(api_url)
            data = response.json()
            
            if data.get('status') == '1':
                txs = data.get('result', [])
                formatted_txs = []
                
                for tx in txs:
                    formatted_tx = {
                        'hash': tx.get('hash'),
                        'timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))).isoformat(),
                        'from': tx.get('from'),
                        'to': tx.get('to'),
                        'value': float(tx.get('value', '0')) / 1e18,
                        'gas_used': int(tx.get('gasUsed', 0)),
                        'gas_price': int(tx.get('gasPrice', 0)) / 1e9,
                        'gas_fee_eth': (int(tx.get('gasUsed', 0)) * int(tx.get('gasPrice', 0))) / 1e18,
                        'type': 'in' if tx.get('to').lower() == self.wallet_address.lower() else 'out',
                        'status': 'success' if tx.get('txreceipt_status') == '1' else 'failed',
                        'method': self._get_tx_method(tx.get('input', '0x'))
                    }
                    formatted_txs.append(formatted_tx)
                
                # Cache the results
                self.last_transactions = formatted_txs
                return formatted_txs
            else:
                logger.warning(f"Failed to get transactions: {data.get('message')}")
                return self._get_simulated_transactions(limit)
                
        except Exception as e:
            logger.warning(f"Error getting transactions: {e}")
            return self._get_simulated_transactions(limit)
    
    def _get_tx_method(self, input_data: str) -> str:
        """Get transaction method from input data."""
        # Common method signatures
        method_signatures = {
            '0x': 'Transfer',
            '0xa9059cbb': 'Transfer Token',
            '0x095ea7b3': 'Approve',
            '0xf305d719': 'Add Liquidity',
            '0x02751cec': 'Remove Liquidity',
            '0x7ff36ab5': 'Swap',
            '0x85f6d155': 'FlashLoan',
            '0xe8e33700': 'Harvest',
            '0xc797730b': 'Arbitrage'
        }
        
        if input_data.startswith('0x'):
            # Get method signature (first 10 characters, including 0x)
            signature = input_data[:10] if len(input_data) >= 10 else input_data
            return method_signatures.get(signature, 'Contract Interaction')
        
        return 'Unknown'
    
    def _get_simulated_transactions(self, limit=10) -> List[Dict[str, Any]]:
        """Generate simulated transaction data."""
        # If we already have transactions, use those and maybe add a new one
        if self.last_transactions and random.random() > 0.3:  # 30% chance to add a new tx
            # Just return the existing ones
            return self.last_transactions[:limit]
        
        # Generate transactions
        current_time = datetime.now()
        transactions = []
        
        # Transaction types with probabilities
        tx_types = [
            ('Swap', 0.4),
            ('Arbitrage', 0.2),
            ('FlashLoan', 0.1),
            ('Add Liquidity', 0.1),
            ('Remove Liquidity', 0.1),
            ('Transfer', 0.1)
        ]
        
        # Common addresses for trading
        dex_addresses = [
            '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',  # Uniswap Router
            '0xE592427A0AEce92De3Edee1F18E0157C05861564',  # Uniswap V3 Router
            '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F',  # SushiSwap Router
            '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506',  # SushiSwap Router 02
            '0x10ED43C718714eb63d5aA57B78B54704E256024E',  # PancakeSwap Router
            '0x13f4EA83D0bd40E75C8222255bc855a974568Dd4'   # FlashBot MEV Router
        ]
        
        # Generate transactions going back in time
        for i in range(limit):
            # Time decreases by 10-60 minutes per transaction to look like real activity
            tx_time = current_time - timedelta(minutes=random.randint(10, 60) * (i + 1))
            
            # Select a transaction type based on probabilities
            tx_method = random.choices(
                [t[0] for t in tx_types],
                weights=[t[1] for t in tx_types],
                k=1
            )[0]
            
            # Generate values
            gas_price = random.uniform(20, 80)  # in gwei
            gas_used = random.randint(80000, 350000)
            gas_fee = (gas_price * gas_used) / 1e9
            
            # Transaction value depends on type
            if tx_method == 'Arbitrage' or tx_method == 'FlashLoan':
                value = 0.0  # Usually 0 ETH for these
            elif tx_method == 'Transfer':
                value = random.uniform(0.1, 2.0)
            else:
                value = random.uniform(0.0, 0.5)
            
            # Generate unique hash
            tx_hash = f"0x{''.join(random.choices('0123456789abcdef', k=64))}"
            
            # For outgoing transactions
            if tx_method != 'Transfer' or random.random() > 0.7:  # 30% chance of incoming transfer
                from_addr = self.wallet_address
                to_addr = random.choice(dex_addresses)
                tx_type = 'out'
            else:
                from_addr = random.choice(dex_addresses)
                to_addr = self.wallet_address
                tx_type = 'in'
            
            # Create the transaction
            transaction = {
                'hash': tx_hash,
                'timestamp': tx_time.isoformat(),
                'from': from_addr,
                'to': to_addr,
                'value': value,
                'gas_used': gas_used,
                'gas_price': gas_price,
                'gas_fee_eth': gas_fee,
                'type': tx_type,
                'status': 'success',
                'method': tx_method
            }
            
            transactions.append(transaction)
        
        # Cache the results
        self.last_transactions = transactions
        return transactions
    
    def get_gas_usage(self) -> Dict[str, Any]:
        """Get gas usage statistics for the wallet."""
        # Use transactions to calculate gas usage
        transactions = self.get_transactions(30)  # Last 30 transactions
        
        if not transactions:
            return {
                'total_eth': 0,
                'total_usd': 0,
                'average_per_tx': 0,
                'highest': 0,
                'lowest': 0,
                'last_24h': 0,
                'last_7d': 0
            }
        
        # Calculate gas stats
        gas_fees = [tx.get('gas_fee_eth', 0) for tx in transactions]
        
        # Get dates for time filtering
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        # Filter transactions by time
        day_txs = [tx for tx in transactions 
                  if datetime.fromisoformat(tx.get('timestamp', now.isoformat())) > day_ago]
        week_txs = [tx for tx in transactions 
                   if datetime.fromisoformat(tx.get('timestamp', now.isoformat())) > week_ago]
        
        # Calculate gas usage
        total_gas = sum(gas_fees)
        avg_gas = total_gas / len(transactions) if transactions else 0
        max_gas = max(gas_fees) if gas_fees else 0
        min_gas = min(gas_fees) if gas_fees else 0
        day_gas = sum(tx.get('gas_fee_eth', 0) for tx in day_txs)
        week_gas = sum(tx.get('gas_fee_eth', 0) for tx in week_txs)
        
        # Estimate USD values (current ETH price estimate)
        eth_price = 3500  # Estimated ETH price in USD
        
        return {
            'total_eth': total_gas,
            'total_usd': total_gas * eth_price,
            'average_per_tx': avg_gas,
            'highest': max_gas,
            'lowest': min_gas,
            'last_24h': day_gas,
            'last_7d': week_gas,
            'eth_price_usd': eth_price,
            'transactions_count': len(transactions)
        }
    
    def get_wallet_stats(self) -> Dict[str, Any]:
        """Get comprehensive wallet statistics."""
        # Get basic data
        balance_data = self.get_balance()
        transactions = self.get_transactions(10)
        gas_data = self.get_gas_usage()
        
        # Calculate additional stats
        # Transaction frequency
        if transactions:
            try:
                first_tx_time = datetime.fromisoformat(transactions[-1].get('timestamp'))
                last_tx_time = datetime.fromisoformat(transactions[0].get('timestamp'))
                time_diff = (last_tx_time - first_tx_time).total_seconds()
                if time_diff > 0 and len(transactions) > 1:
                    tx_per_day = (len(transactions) - 1) * 86400 / time_diff
                else:
                    tx_per_day = 0
            except:
                tx_per_day = 0
        else:
            tx_per_day = 0
        
        # Incoming/outgoing ratio
        incoming = sum(1 for tx in transactions if tx.get('type') == 'in')
        outgoing = len(transactions) - incoming
        in_out_ratio = incoming / outgoing if outgoing > 0 else float('inf')
        
        # Most common interaction
        method_counts = {}
        for tx in transactions:
            method = tx.get('method', 'Unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        most_common_method = max(method_counts.items(), key=lambda x: x[1])[0] if method_counts else 'None'
        
        # Combine all data
        return {
            'address': balance_data.get('address'),
            'balance': {
                'eth': balance_data.get('eth_balance', 0),
                'tokens': balance_data.get('token_balances', {})
            },
            'transactions': {
                'recent': transactions,
                'frequency_per_day': tx_per_day,
                'in_out_ratio': in_out_ratio,
                'most_common_method': most_common_method
            },
            'gas': gas_data,
            'last_update': datetime.now().isoformat(),
            'simulated': self.use_simulation
        }

# Global instance for easy importing
wallet_monitor = WalletMonitor()