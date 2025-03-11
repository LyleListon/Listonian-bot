"""
Multi-Chain Arbitrage Dashboard

Dashboard for monitoring arbitrage opportunities across Ethereum, Arbitrum, and Base.
Reads data directly from log files.
"""

import os
import sys
import json
import csv
import sqlite3
import logging
import random
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dashboard configuration
PORT = 9097  # Using a specific port to avoid conflicts

# Database setup
def setup_database():
    """Set up SQLite database for storing opportunity checks"""
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Create table for opportunity checks
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS opportunity_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        pair TEXT NOT NULL,
        source_dex TEXT NOT NULL,
        target_dex TEXT NOT NULL,
        network TEXT,
        source_price REAL,
        target_price REAL,
        price_diff_pct REAL,
        amount REAL,
        profit_usd REAL,
        gas_cost_usd REAL,
        net_profit_usd REAL,
        executed INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    return conn

# Global database connection
db_conn = setup_database()

# Default trading pairs to monitor
DEFAULT_PAIRS = {
    "ethereum": [
        "WETH/USDC",
        "WETH/USDT", 
        "WETH/DAI",
        "ETH/USDC",
        "ETH/USDT",
        "WBTC/USDC"
    ],
    "arbitrum": [
        "WETH/USDC.e",
        "WETH/USDT.e",
        "WETH/ARB",
        "ARB/USDC.e",
        "GMX/WETH",
        "MAGIC/WETH"
    ],
    "base": [
        "WETH/USDbC",
        "BALD/WETH",
        "TOSHI/WETH"
    ]
}

# DEX lists by network
NETWORK_DEXES = {
    "ethereum": [
        "uniswap_v2", "uniswap_v3", "sushiswap", "pancakeswap", "curve",
        "balancer", "dodo", "kyberswap", "bancor", "shibaswap"
    ],
    "arbitrum": [
        "camelot", "ramses", "trader_joe", "sushiswap_arb", "uniswap_v3_arb",
        "balancer_arb", "curve_arb", "dodo_arb", "swapr", "gmx", "chronos"
    ],
    "base": [
        "baseswap", "aerodrome", "swapbased", "rocketswap", "baseX",
        "alienbase", "solid_lizard", "maverick"
    ]
}

# Networks supported by the dashboard
NETWORKS = [
    {
        "name": "Ethereum",
        "chain_id": 1,
        "symbol": "ETH",
        "dexes": NETWORK_DEXES["ethereum"]
    },
    {
        "name": "Arbitrum",
        "chain_id": 42161,
        "symbol": "ETH",
        "dexes": NETWORK_DEXES["arbitrum"]
    },
    {
        "name": "Base",
        "chain_id": 8453,
        "symbol": "ETH",
        "dexes": NETWORK_DEXES["base"]
    }
]

class DataManager:
    """Manages loading and processing opportunity check data"""
    
    def __init__(self, db_connection):
        self.db_conn = db_connection
        self.lock = threading.Lock()
        self.last_update = None
        
    def load_log_data(self, log_file_path=None):
        """
        Load opportunity check data from log files or existing log database
        
        Args:
            log_file_path: Path to log file or directory. If None, looks in default locations.
        """
        # Default to logs directory if no path provided
        if not log_file_path:
            log_candidates = [
                "logs/arbitrage_checks.log",
                "logs/opportunity_checks.log",
                "logs/trading_checks.csv",
                "data/arbitrage_checks.csv"
            ]
            
            # Try to find existing log files
            for candidate in log_candidates:
                if os.path.exists(candidate):
                    log_file_path = candidate
                    break
        
        if not log_file_path or not os.path.exists(log_file_path):
            # Create sample data for testing if no logs found
            self._create_sample_data()
            return
        
        # Determine file type and load accordingly
        if log_file_path.endswith('.csv'):
            self._load_from_csv(log_file_path)
        else:
            self._load_from_text_log(log_file_path)
            
        self.last_update = datetime.now()
    
    def _load_from_csv(self, csv_path):
        """Load opportunity data from CSV file"""
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                cursor = self.db_conn.cursor()
                
                for row in reader:
                    # Format timestamp if needed
                    if 'timestamp' in row and not row['timestamp'].endswith('Z'):
                        try:
                            dt = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                            row['timestamp'] = dt.isoformat()
                        except:
                            pass
                    
                    # Determine network from DEX
                    network = self._determine_network(row.get('source_dex', ''))
                    
                    # Insert into database
                    cursor.execute('''
                    INSERT INTO opportunity_checks 
                    (timestamp, pair, source_dex, target_dex, network, source_price, target_price, 
                     price_diff_pct, amount, profit_usd, gas_cost_usd, net_profit_usd, executed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('timestamp', datetime.now().isoformat()),
                        row.get('pair', 'UNKNOWN'),
                        row.get('source_dex', 'UNKNOWN'),
                        row.get('target_dex', 'UNKNOWN'),
                        network,
                        float(row.get('source_price', 0)),
                        float(row.get('target_price', 0)),
                        float(row.get('price_diff_pct', 0)),
                        float(row.get('amount', 0)),
                        float(row.get('profit_usd', 0)),
                        float(row.get('gas_cost_usd', 0)),
                        float(row.get('net_profit_usd', 0)),
                        int(row.get('executed', 0))
                    ))
                
                self.db_conn.commit()
                logger.info(f"Loaded opportunity data from {csv_path}")
        except Exception as e:
            logger.error(f"Error loading from CSV: {e}")
            
    def _load_from_text_log(self, log_path):
        """Load opportunity data from text log file"""
        try:
            with open(log_path, 'r') as f:
                cursor = self.db_conn.cursor()
                lines = f.readlines()
                
                for line in lines:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Try to parse log line - adapt this pattern to your actual log format
                    try:
                        # Example format: [2025-02-28 12:34:56] Checking WETH/USDC: uniswap_v2 (1.12345) vs sushiswap (1.12456) - diff: 0.0987% potential profit: $0.12 gas: $5.67
                        # Extract parts using regex or string operations - greatly simplified for example
                        
                        # This is placeholder logic - customize to match your actual log format
                        parts = line.split(' - ')
                        if len(parts) < 2:
                            continue
                            
                        timestamp = datetime.now().isoformat()
                        pair = "UNKNOWN"
                        source_dex = "UNKNOWN"
                        target_dex = "UNKNOWN"
                        source_price = 0
                        target_price = 0
                        price_diff_pct = 0
                        amount = 0
                        profit_usd = 0
                        gas_cost_usd = 0
                        net_profit_usd = 0
                        executed = 0
                        
                        # Extract timestamp
                        if '[' in line and ']' in line:
                            timestamp_str = line.split('[')[1].split(']')[0].strip()
                            try:
                                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').isoformat()
                            except:
                                pass
                        
                        # Extract pair
                        for network_pairs in DEFAULT_PAIRS.values():
                            for default_pair in network_pairs:
                                if default_pair in line:
                                    pair = default_pair
                                    break
                            if pair != "UNKNOWN":
                                break
                        
                        # Extract DEXes
                        all_dexes = []
                        for network_dex_list in NETWORK_DEXES.values():
                            all_dexes.extend(network_dex_list)
                            
                        for dex in all_dexes:
                            if dex in line and source_dex == "UNKNOWN":
                                source_dex = dex
                            elif dex in line and source_dex != "UNKNOWN":
                                target_dex = dex
                                break
                        
                        # Determine network from DEX
                        network = self._determine_network(source_dex)
                        
                        # Extract profit if mentioned
                        if 'profit:' in line:
                            profit_text = line.split('profit:')[1].split(' ')[0]
                            try:
                                if profit_text.startswith('$'):
                                    profit_usd = float(profit_text[1:])
                            except:
                                pass
                        
                        # Extract gas cost if mentioned
                        if 'gas:' in line:
                            gas_text = line.split('gas:')[1].split(' ')[0]
                            try:
                                if gas_text.startswith('$'):
                                    gas_cost_usd = float(gas_text[1:])
                            except:
                                pass
                        
                        # Calculate net profit
                        net_profit_usd = profit_usd - gas_cost_usd
                        
                        # Determine if executed based on language in log
                        executed = 1 if 'EXECUTED' in line.upper() else 0
                        
                        # Insert into database
                        cursor.execute('''
                        INSERT INTO opportunity_checks 
                        (timestamp, pair, source_dex, target_dex, network, source_price, target_price, 
                         price_diff_pct, amount, profit_usd, gas_cost_usd, net_profit_usd, executed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            timestamp,
                            pair,
                            source_dex,
                            target_dex,
                            network,
                            source_price,
                            target_price,
                            price_diff_pct,
                            amount,
                            profit_usd,
                            gas_cost_usd,
                            net_profit_usd,
                            executed
                        ))
                    except Exception as e:
                        logger.debug(f"Couldn't parse log line: {e}")
                
                self.db_conn.commit()
                logger.info(f"Loaded opportunity data from {log_path}")
        except Exception as e:
            logger.error(f"Error loading from log file: {e}")
    
    def _determine_network(self, dex_name):
        """Determine network from DEX name"""
        dex = dex_name.lower()
        
        # Check Arbitrum DEXes
        if any(arb_dex in dex for arb_dex in ["camelot", "ramses", "trader_joe", "gmx", "chronos"]) or "arb" in dex:
            return "arbitrum"
            
        # Check Base DEXes  
        if any(base_dex in dex for base_dex in ["baseswap", "aerodrome", "swapbased", "rocketswap", "basex"]):
            return "base"
            
        # Default to Ethereum
        return "ethereum"
            
    def _create_sample_data(self):
        """Create sample data for multi-chain testing"""
        cursor = self.db_conn.cursor()
        
        # Message to let user know we're using sample data
        logger.warning("No log data found - displaying sample data for all networks")
        print("No opportunity check logs found. Using sample data for UI display.")
        print("To see real data, place your log files in logs/ directory.")
        
        # Generate data for each network
        for network_name, pairs in DEFAULT_PAIRS.items():
            dexes = NETWORK_DEXES[network_name]
            
            # Create 5-10 records per network
            for i in range(random.randint(5, 10)):
                # Pick random pair and DEXes
                pair = random.choice(pairs)
                source_dex = random.choice(dexes)
                
                # Make sure target DEX is different
                remaining_dexes = [d for d in dexes if d != source_dex]
                target_dex = random.choice(remaining_dexes) if remaining_dexes else dexes[0]
                
                # Generate random values
                price_diff = random.uniform(0.05, 0.5)
                amount = random.uniform(0.5, 3.0)
                profit = random.uniform(0.5, 5.0)
                gas_cost = random.uniform(0.2, 1.5) if network_name == "ethereum" else random.uniform(0.05, 0.3)
                net_profit = profit - gas_cost
                executed = 1 if net_profit > 0.5 else 0
                
                # Random timestamp within the last hour
                minutes_ago = random.randint(1, 60)
                timestamp = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()
                
                # Insert record
                cursor.execute('''
                INSERT INTO opportunity_checks 
                (timestamp, pair, source_dex, target_dex, network, source_price, target_price, 
                price_diff_pct, amount, profit_usd, gas_cost_usd, net_profit_usd, executed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp,
                    pair,
                    source_dex,
                    target_dex,
                    network_name,
                    1000.0,  # Placeholder source price
                    1000.0 * (1 + price_diff/100),  # Placeholder target price
                    price_diff,
                    amount,
                    profit,
                    gas_cost,
                    net_profit,
                    executed
                ))
        
        self.db_conn.commit()
        
    def get_opportunities(self, limit=100, min_profit=None, pair=None, dex=None, network=None):
        """Get opportunity checks with optional filtering"""
        cursor = self.db_conn.cursor()
        
        # Build query with filters
        query = "SELECT * FROM opportunity_checks"
        params = []
        
        # Add where clauses
        where_clauses = []
        
        if min_profit is not None:
            where_clauses.append("net_profit_usd >= ?")
            params.append(min_profit)
        
        if pair:
            where_clauses.append("pair = ?")
            params.append(pair)
        
        if dex:
            where_clauses.append("(source_dex = ? OR target_dex = ?)")
            params.append(dex)
            params.append(dex)
            
        if network:
            where_clauses.append("network = ?")
            params.append(network)
        
        # Add where clause if needed
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add order and limit
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        # Execute and return
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        result = []
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        return result
    
    def get_stats(self):
        """Get statistics about opportunity checks"""
        cursor = self.db_conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM opportunity_checks")
        total_checks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM opportunity_checks WHERE net_profit_usd > 0")
        profitable_opps = cursor.fetchone()[0]
        
        # Get max profit
        cursor.execute("SELECT MAX(net_profit_usd) FROM opportunity_checks")
        max_profit = cursor.fetchone()[0] or 0
        
        # Get average profit
        cursor.execute("SELECT AVG(net_profit_usd) FROM opportunity_checks")
        avg_profit = cursor.fetchone()[0] or 0
        
        # Calculate profit rate
        profit_rate = profitable_opps / total_checks if total_checks > 0 else 0
        
        return {
            'total_checks': total_checks,
            'profitable_opportunities': profitable_opps,
            'max_profit_usd': max_profit,
            'avg_profit_usd': avg_profit,
            'profit_rate': profit_rate,
            'last_update': datetime.now().isoformat()
        }
    
    def get_network_stats(self):
        """Get statistics by network"""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
        SELECT network, 
               COUNT(*) as check_count,
               SUM(CASE WHEN net_profit_usd > 0 THEN 1 ELSE 0 END) as profitable_count,
               AVG(net_profit_usd) as avg_profit,
               AVG(gas_cost_usd) as avg_gas,
               MAX(net_profit_usd) as max_profit
        FROM opportunity_checks
        GROUP BY network
        """)
        
        columns = [desc[0] for desc in cursor.description]
        result = []
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        return result
    
    def get_pair_stats(self):
        """Get statistics by trading pair"""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
        SELECT pair, network,
               COUNT(*) as check_count,
               SUM(CASE WHEN net_profit_usd > 0 THEN 1 ELSE 0 END) as profitable_count,
               AVG(net_profit_usd) as avg_profit,
               MAX(net_profit_usd) as max_profit
        FROM opportunity_checks
        GROUP BY pair, network
        ORDER BY check_count DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        result = []
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        return result
    
    def get_dex_stats(self):
        """Get statistics by DEX"""
        cursor = self.db_conn.cursor()
        
        # First for source_dex
        cursor.execute("""
        SELECT source_dex as dex, network,
               COUNT(*) as check_count,
               SUM(CASE WHEN net_profit_usd > 0 THEN 1 ELSE 0 END) as profitable_count,
               AVG(net_profit_usd) as avg_profit,
               MAX(net_profit_usd) as max_profit,
               'source' as role
        FROM opportunity_checks
        GROUP BY source_dex, network
        """)
        
        columns = [desc[0] for desc in cursor.description]
        result = []
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        # Then for target_dex
        cursor.execute("""
        SELECT target_dex as dex, network,
               COUNT(*) as check_count,
               SUM(CASE WHEN net_profit_usd > 0 THEN 1 ELSE 0 END) as profitable_count,
               AVG(net_profit_usd) as avg_profit,
               MAX(net_profit_usd) as max_profit,
               'target' as role
        FROM opportunity_checks
        GROUP BY target_dex, network
        """)
        
        columns = [desc[0] for desc in cursor.description]
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        return result
    
    def get_pairs_list(self):
        """Get list of all unique trading pairs"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT DISTINCT pair, network FROM opportunity_checks ORDER BY network, pair")
        return [{"pair": row[0], "network": row[1]} for row in cursor.fetchall()]
    
    def get_dexes_list(self):
        """Get list of all unique DEXes"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
        SELECT DISTINCT source_dex as dex, network FROM opportunity_checks 
        UNION 
        SELECT DISTINCT target_dex as dex, network FROM opportunity_checks 
        ORDER BY network, dex
        """)
        return [{"dex": row[0], "network": row[1]} for row in cursor.fetchall()]

# Global data manager instance
data_manager = DataManager(db_conn)

# Load opportunity data from available logs
data_manager.load_log_data()

class MultiChainDashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the multi-chain dashboard."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_html().encode())
        elif self.path == "/style.css":
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            self.wfile.write(self.get_css().encode())
        elif self.path == "/dashboard.js":
            self.send_response(200)
            self.send_header("Content-type", "application/javascript")
            self.end_headers()
            self.wfile.write(self.get_js().encode())
        elif self.path == "/api/opportunities":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            # Get opportunities (limit to 100 most recent)
            opportunities = data_manager.get_opportunities(limit=100)
            self.wfile.write(json.dumps({
                'opportunities': opportunities,
                'stats': data_manager.get_stats()
            }).encode())
        elif self.path.startswith("/api/opportunities/filter"):
            # Parse query parameters
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            # Extract filter parameters
            limit = int(params.get('limit', ['100'])[0])
            min_profit = float(params.get('min_profit', ['0'])[0]) if 'min_profit' in params else None
            pair = params.get('pair', [None])[0]
            dex = params.get('dex', [None])[0]
            network = params.get('network', [None])[0]
            
            # Get filtered opportunities
            opportunities = data_manager.get_opportunities(
                limit=limit, min_profit=min_profit, pair=pair, dex=dex, network=network
            )
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'opportunities': opportunities,
                'stats': data_manager.get_stats(),
                'filter': {'limit': limit, 'min_profit': min_profit, 'pair': pair, 'dex': dex, 'network': network}
            }).encode())
        elif self.path == "/api/pairs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'pairs': data_manager.get_pairs_list()
            }).encode())
        elif self.path == "/api/dexes":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'dexes': data_manager.get_dexes_list()
            }).encode())
        elif self.path == "/api/networks":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'networks': [network["name"].lower() for network in NETWORKS]
            }).encode())
        elif self.path == "/api/stats/networks":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'network_stats': data_manager.get_network_stats()
            }).encode())
        elif self.path == "/api/stats/pairs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'pair_stats': data_manager.get_pair_stats()
            }).encode())
        elif self.path == "/api/stats/dexes":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'dex_stats': data_manager.get_dex_stats()
            }).encode())
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")
    
    def generate_html(self):
        """Generate HTML for the dashboard."""
        stats = data_manager.get_stats()
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="description" content="Multi-chain arbitrage opportunity monitoring dashboard">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Chain Arbitrage Dashboard</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="300">
    <script src="/dashboard.js" defer></script>
</head>
<body>
    <div class="header">
        <h1>Multi-Chain Arbitrage Operations</h1>
        <div class="sub-header">Opportunity tracking across Ethereum, Arbitrum, and Base</div>
        <div class="last-updated">
            Last Updated: <span id="last-updated">Loading...</span>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="tabs">
            <button class="tab-link active" onclick="openTab(event, 'opportunity-tab')">Opportunities</button>
            <button class="tab-link" onclick="openTab(event, 'networks-tab')">Networks</button>
            <button class="tab-link" onclick="openTab(event, 'stats-tab')">Stats</button>
        </div>
        
        <div id="opportunity-tab" class="tab-content active">
            <h2>Opportunity Tracker</h2>
            <div class="filter-controls">
                <div class="filter-item">
                    <label for="filter-network">Network:</label>
                    <select id="filter-network" onchange="filterOpportunities()">
                        <option value="">All Networks</option>
                        <option value="ethereum">Ethereum</option>
                        <option value="arbitrum">Arbitrum</option>
                        <option value="base">Base</option>
                    </select>
                </div>
                <div class="filter-item">
                    <label for="filter-pair">Trading Pair:</label>
                    <select id="filter-pair" onchange="filterOpportunities()">
                        <option value="">All Pairs</option>
                    </select>
                </div>
                <div class="filter-item">
                    <label for="filter-dex">DEX:</label>
                    <select id="filter-dex" onchange="filterOpportunities()">
                        <option value="">All DEXes</option>
                    </select>
                </div>
                <div class="filter-item">
                    <label for="filter-profit">Min Profit ($):</label>
                    <input type="number" id="filter-profit" min="-9999" step="0.01" value="0" onchange="filterOpportunities()">
                </div>
                <div class="filter-item">
                    <label for="filter-limit">Limit:</label>
                    <select id="filter-limit" onchange="filterOpportunities()">
                        <option value="25">25</option>
                        <option value="50">50</option>
                        <option value="100" selected>100</option>
                        <option value="250">250</option>
                        <option value="500">500</option>
                    </select>
                </div>
                <div class="filter-item">
                    <button onclick="refreshOpportunities()">Refresh</button>
                </div>
            </div>
            
            <div class="opportunity-list">
                <table id="opportunity-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Network</th>
                            <th>Pair</th>
                            <th>Buy DEX</th>
                            <th>Sell DEX</th>
                            <th>Price Diff %</th>
                            <th>Amount</th>
                            <th>Profit ($)</th>
                            <th>Gas ($)</th>
                            <th>Net Profit ($)</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="opportunity-rows">
                        <tr><td colspan="11" class="loading">Loading opportunity data...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <div id="networks-tab" class="tab-content">
            <h2>Multi-Chain Overview</h2>
            
            <div class="network-cards">
                <div class="network-card" id="eth-network">
                    <div class="network-header">
                        <img src="https://cryptologos.cc/logos/ethereum-eth-logo.svg?v=025" 
                             alt="Ethereum" class="network-logo">
                        <h3>Ethereum</h3>
                    </div>
                    <div class="network-stats">
                        <div class="network-stat">
                            <div class="stat-name">Opportunity Checks</div>
                            <div class="stat-value" id="eth-checks">0</div>
                        </div>
                        <div class="network-stat">
                            <div class="stat-name">Profitable</div>
                            <div class="stat-value" id="eth-profitable">0</div>
                        </div>
                        <div class="network-stat">
                            <div class="stat-name">Avg. Profit</div>
                            <div class="stat-value" id="eth-profit">$0.00</div>
                        </div>
                    </div>
                </div>
                
                <div class="network-card" id="arb-network">
                    <div class="network-header">
                        <img src="https://cryptologos.cc/logos/arbitrum-arb-logo.svg?v=025" 
                             alt="Arbitrum" class="network-logo">
                        <h3>Arbitrum</h3>
                    </div>
                    <div class="network-stats">
                        <div class="network-stat">
                            <div class="stat-name">Opportunity Checks</div>
                            <div class="stat-value" id="arb-checks">0</div>
                        </div>
                        <div class="network-stat">
                            <div class="stat-name">Profitable</div>
                            <div class="stat-value" id="arb-profitable">0</div>
                        </div>
                        <div class="network-stat">
                            <div class="stat-name">Avg. Profit</div>
                            <div class="stat-value" id="arb-profit">$0.00</div>
                        </div>
                    </div>
                </div>
                
                <div class="network-card" id="base-network">
                    <div class="network-header">
                        <img src="https://cryptologos.cc/logos/base-logo.svg?v=025" 
                             alt="Base" class="network-logo">
                        <h3>Base</h3>
                    </div>
                    <div class="network-stats">
                        <div class="network-stat">
                            <div class="stat-name">Opportunity Checks</div>
                            <div class="stat-value" id="base-checks">0</div>
                        </div>
                        <div class="network-stat">
                            <div class="stat-name">Profitable</div>
                            <div class="stat-value" id="base-profitable">0</div>
                        </div>
                        <div class="network-stat">
                            <div class="stat-name">Avg. Profit</div>
                            <div class="stat-value" id="base-profit">$0.00</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="network-comparison">
                <h3>Cross-Chain Comparison</h3>
                <div class="comparison-grid">
                    <div class="comparison-item">
                        <h4>Gas Cost Comparison</h4>
                        <div class="comparison-chart" id="gas-comparison">
                            <p class="loading">Loading gas cost data...</p>
                        </div>
                    </div>
                    <div class="comparison-item">
                        <h4>Profit Rate Comparison</h4>
                        <div class="comparison-chart" id="profit-comparison">
                            <p class="loading">Loading profit rate data...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="stats-tab" class="tab-content">
            <h2>Performance Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card" id="total-checks-card">
                    <div class="stat-title">Total Opportunity Checks</div>
                    <div class="stat-value" id="total-checks">Loading...</div>
                </div>
                <div class="stat-card" id="profitable-card">
                    <div class="stat-title">Profitable Opportunities</div>
                    <div class="stat-value" id="profitable-opps">Loading...</div>
                </div>
                <div class="stat-card" id="profit-rate-card">
                    <div class="stat-title">Profit Rate</div>
                    <div class="stat-value" id="profit-rate">Loading...</div>
                </div>
                <div class="stat-card" id="max-profit-card">
                    <div class="stat-title">Maximum Profit</div>
                    <div class="stat-value" id="max-profit">Loading...</div>
                </div>
                <div class="stat-card" id="avg-profit-card">
                    <div class="stat-title">Average Profit</div>
                    <div class="stat-value" id="avg-profit">Loading...</div>
                </div>
                <div class="stat-card" id="refresh-time-card">
                    <div class="stat-title">Last Refreshed</div>
                    <div class="stat-value" id="refresh-time">Loading...</div>
                </div>
            </div>
            
            <div class="pair-performance">
                <h3>Performance by Trading Pair</h3>
                <div id="pair-stats">
                    <p class="loading">Loading pair statistics...</p>
                </div>
            </div>
            
            <div class="dex-performance">
                <h3>Performance by DEX</h3>
                <div id="dex-stats">
                    <p class="loading">Loading DEX statistics...</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Multi-Chain Arbitrage Dashboard | Reads data directly from bot logs</p>
    </div>
</body>
</html>
"""
    
    def get_css(self):
        """Get CSS styles for the dashboard."""
        return """
        :root {
            --primary-color: #3a0ca3;
            --secondary-color: #2d3436;
            --accent-color: #4361ee;
            --positive-color: #4cc9f0;
            --negative-color: #f72585;
            --background-color: #f8f9fa;
            --card-background: #ffffff;
            --text-color: #2d3436;
            --light-text: #636e72;
            --border-color: #dfe6e9;
            --ethereum-color: #627eea;
            --arbitrum-color: #2d374b;
            --base-color: #0052ff;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 25px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.2em;
            font-weight: 700;
        }
        
        .sub-header {
            margin-top: 5px;
            font-size: 1.1em;
            opacity: 0.8;
        }
        
        .last-updated {
            margin-top: 15px;
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 25px auto;
            padding: 0 20px;
        }
        
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }
        
        .tab-link {
            padding: 10px 20px;
            cursor: pointer;
            background: none;
            border: none;
            font-size: 1.1em;
            font-weight: 500;
            color: var(--light-text);
            transition: all 0.3s ease;
        }
        
        .tab-link:hover {
            color: var(--primary-color);
        }
        
        .tab-link.active {
            color: var(--primary-color);
            border-bottom: 3px solid var(--primary-color);
        }
        
        .tab-content {
            display: none;
            padding: 20px 0;
        }
        
        .tab-content.active {
            display: block;
        }
        
        h2 {
            margin-bottom: 20px;
            color: var(--primary-color);
        }
        
        h3 {
            margin: 30px 0 15px;
            color: var(--secondary-color);
        }
        
        /* Opportunity tracker section */
        .filter-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
            padding: 15px;
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        
        .filter-item {
            display: flex;
            flex-direction: column;
            min-width: 150px;
        }
        
        .filter-item label {
            font-size: 0.9em;
            margin-bottom: 5px;
            color: var(--light-text);
        }
        
        .filter-item select,
        .filter-item input {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            font-size: 0.9em;
        }
        
        .filter-item button {
            margin-top: auto;
            padding: 8px 16px;
            background-color: var(--accent-color);
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.2s;
        }
        
        .filter-item button:hover {
            background-color: var(--primary-color);
        }
        
        .opportunity-list {
            overflow-x: auto;
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            max-height: 600px;
            overflow-y: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            background-color: var(--secondary-color);
            color: white;
            font-weight: 500;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        tr:hover {
            background-color: rgba(0, 0, 0, 0.02);
        }
        
        .status-executed {
            color: white;
            background-color: var(--positive-color);
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: 500;
            display: inline-block;
        }
        
        .status-skipped {
            color: white;
            background-color: var(--light-text);
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: 500;
            display: inline-block;
        }
        
        .positive {
            color: var(--positive-color);
            font-weight: 500;
        }
        
        .negative {
            color: var(--negative-color);
            font-weight: 500;
        }
        
        /* Network tab styles */
        .network-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .network-card {
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }
        
        .network-header {
            padding: 15px;
            display: flex;
            align-items: center;
            gap: 15px;
            color: white;
        }
        
        .network-logo {
            width: 30px;
            height: 30px;
            background-color: white;
            border-radius: 50%;
            padding: 3px;
        }
        
        .network-header h3 {
            margin: 0;
            color: white;
        }
        
        .network-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            padding: 15px;
        }
        
        .network-stat {
            text-align: center;
            padding: 10px;
        }
        
        .stat-name {
            font-size: 0.9em;
            color: var(--light-text);
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 1.4em;
            font-weight: bold;
            color: var(--accent-color);
        }
        
        #eth-network .network-header {
            background-color: var(--ethereum-color);
        }
        
        #arb-network .network-header {
            background-color: var(--arbitrum-color);
        }
        
        #base-network .network-header {
            background-color: var(--base-color);
        }
        
        .network-comparison {
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .comparison-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .comparison-item {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
        }
        
        .comparison-item h4 {
            margin-top: 0;
            margin-bottom: 15px;
            color: var(--secondary-color);
            font-size: 1.1em;
        }
        
        .comparison-chart {
            height: 250px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Statistics section */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background-color: var(--card-background);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            text-align: center;
        }
        
        .stat-title {
            font-size: 0.9em;
            color: var(--light-text);
            margin-bottom: 10px;
        }
        
        .stat-value {
            font-size: 1.8em;
            font-weight: 700;
            color: var(--accent-color);
        }
        
        #total-checks-card .stat-value {
            color: var(--secondary-color);
        }
        
        #profitable-card .stat-value {
            color: var(--positive-color);
        }
        
        #profit-rate-card .stat-value {
            color: var(--primary-color);
        }
        
        #max-profit-card .stat-value {
            color: var(--accent-color);
        }
        
        .pair-performance, .dex-performance {
            background-color: var(--card-background);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            margin-bottom: 30px;
        }
        
        .loading {
            padding: 40px;
            text-align: center;
            font-size: 1.2em;
            color: var(--light-text);
        }
        
        .footer {
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            color: var(--light-text);
            font-size: 0.9em;
        }
        
        /* Network badges */
        .network-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: 500;
            color: white;
        }
        
        .network-badge.ethereum {
            background-color: var(--ethereum-color);
        }
        
        .network-badge.arbitrum {
            background-color: var(--arbitrum-color);
        }
        
        .network-badge.base {
            background-color: var(--base-color);
        }
        
        @media (max-width: 768px) {
            .token-info {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .token-symbol {
                margin-bottom: 5px;
            }
            
            .token-name {
                margin-bottom: 10px;
            }
            
            .token-prices {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .filter-item {
                width: 100%;
            }
            
            .comparison-grid {
                grid-template-columns: 1fr;
            }
        }
        """
    
    def get_js(self):
        """Get JavaScript for the dashboard."""
        return """
        // Auto-refresh the opportunity data every 5 seconds
        setInterval(function() {
            refreshOpportunities();
            updateNetworkStats();
        }, 5000);
        
        // Tab functionality
        function openTab(evt, tabName) {
            // Hide all tab content
            var tabContents = document.getElementsByClassName("tab-content");
            for (var i = 0; i < tabContents.length; i++) {
                tabContents[i].classList.remove("active");
            }
            
            // Remove active class from all tab links
            var tabLinks = document.getElementsByClassName("tab-link");
            for (var i = 0; i < tabLinks.length; i++) {
                tabLinks[i].classList.remove("active");
            }
            
            // Show the selected tab content and add active class to the button
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
            
            // Load network stats when switching to networks tab
            if (tabName === 'networks-tab') {
                updateNetworkStats();
            }
            
            // Load specific data for the selected tab
            if (tabName === 'stats-tab') {
                loadPairStats();
                loadDexStats();
            }
        }
        
        // Update network stats
        function updateNetworkStats() {
            fetch('/api/stats/networks')
                .then(response => response.json())
                .then(data => {
                    const networkStats = data.network_stats || [];
                    
                    // Process data for each network
                    networkStats.forEach(network => {
                        const networkName = network.network || 'unknown';
                        
                        switch(networkName) {
                            case 'ethereum':
                                document.getElementById('eth-checks').textContent = network.check_count || 0;
                                document.getElementById('eth-profitable').textContent = network.profitable_count || 0;
                                document.getElementById('eth-profit').textContent = '$' + (network.avg_profit || 0).toFixed(4);
                                break;
                            case 'arbitrum':
                                document.getElementById('arb-checks').textContent = network.check_count || 0;
                                document.getElementById('arb-profitable').textContent = network.profitable_count || 0;
                                document.getElementById('arb-profit').textContent = '$' + (network.avg_profit || 0).toFixed(4);
                                break;
                            case 'base':
                                document.getElementById('base-checks').textContent = network.check_count || 0;
                                document.getElementById('base-profitable').textContent = network.profitable_count || 0;
                                document.getElementById('base-profit').textContent = '$' + (network.avg_profit || 0).toFixed(4);
                                break;
                        }
                    });
                    
                    // Update comparison charts
                    updateComparisonCharts(networkStats);
                });
        }
        
        // Update network comparison charts
        function updateComparisonCharts(networkStats) {
            // Gas cost comparison
            const gasComparisonEl = document.getElementById('gas-comparison');
            const profitComparisonEl = document.getElementById('profit-comparison');
            
            if (!networkStats || networkStats.length === 0) {
                gasComparisonEl.innerHTML = '<p>No network comparison data available</p>';
                profitComparisonEl.innerHTML = '<p>No network comparison data available</p>';
                return;
            }
            
            // Process data for gas comparison
            let gasHtml = '<div class="chart-container">';
            let profitHtml = '<div class="chart-container">';
            
            // Format data for display
            networkStats.forEach(network => {
                const networkName = network.network || 'unknown';
                const avgGas = network.avg_gas || 0;
                const checkCount = network.check_count || 0;
                const profitableCount = network.profitable_count || 0;
                const profitRate = checkCount > 0 ? (profitableCount / checkCount * 100) : 0;
                
                // Add network to gas chart
                gasHtml += `
                <div class="chart-item">
                    <div class="chart-label">${formatNetworkName(networkName)}</div>
                    <div class="chart-bar-container">
                        <div class="chart-bar ${networkName}" style="width: ${Math.min(avgGas * 20, 100)}%;">
                            $${avgGas.toFixed(4)}
                        </div>
                    </div>
                </div>`;
                
                // Add network to profit chart
                profitHtml += `
                <div class="chart-item">
                    <div class="chart-label">${formatNetworkName(networkName)}</div>
                    <div class="chart-bar-container">
                        <div class="chart-bar ${networkName}" style="width: ${Math.min(profitRate, 100)}%;">
                            ${profitRate.toFixed(2)}%
                        </div>
                    </div>
                </div>`;
            });
            
            gasHtml += '</div>';
            profitHtml += '</div>';
            
            // Update DOM
            gasComparisonEl.innerHTML = gasHtml;
            profitComparisonEl.innerHTML = profitHtml;
            
            // Add CSS for chart styling
            const styleEl = document.createElement('style');
            styleEl.textContent = `
                .chart-container {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .chart-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .chart-label {
                    width: 100px;
                    text-align: right;
                    font-weight: 500;
                }
                .chart-bar-container {
                    flex: 1;
                    background-color: #eee;
                    border-radius: 4px;
                    height: 30px;
                    overflow: hidden;
                }
                .chart-bar {
                    height: 100%;
                    background-color: var(--accent-color);
                    color: white;
                    display: flex;
                    align-items: center;
                    padding-left: 10px;
                    font-size: 0.9em;
                    border-radius: 4px;
                    min-width: 40px;
                    transition: width 0.5s ease;
                }
                .chart-bar.ethereum {
                    background-color: var(--ethereum-color);
                }
                .chart-bar.arbitrum {
                    background-color: var(--arbitrum-color);
                }
                .chart-bar.base {
                    background-color: var(--base-color);
                }
            `;
            
            if (!document.getElementById('chart-styles')) {
                styleEl.id = 'chart-styles';
                document.head.appendChild(styleEl);
            }
        }
        
        // Load pair stats
        function loadPairStats() {
            fetch('/api/stats/pairs')
                .then(response => response.json())
                .then(data => {
                    updatePairStats(data.pair_stats);
                });
        }
        
        // Load DEX stats
        function loadDexStats() {
            fetch('/api/stats/dexes')
                .then(response => response.json())
                .then(data => {
                    updateDexStats(data.dex_stats);
                });
        }
        
        // Update pair stats
        function updatePairStats(pairStats) {
            const pairStatsEl = document.getElementById('pair-stats');
            
            if (!pairStats || pairStats.length === 0) {
                pairStatsEl.innerHTML = '<p>No pair statistics available</p>';
                return;
            }
            
            // Group by network
            const networkGroups = {};
            
            pairStats.forEach(pair => {
                const network = pair.network || 'unknown';
                if (!networkGroups[network]) {
                    networkGroups[network] = [];
                }
                networkGroups[network].push(pair);
            });
            
            let tableHtml = '';
            
            // Create a table for each network
            for (const [network, pairs] of Object.entries(networkGroups)) {
                tableHtml += `
                <div class="network-section">
                    <h4>
                        <span class="network-badge ${network}">${formatNetworkName(network)}</span>
                    </h4>
                    <table>
                        <thead>
                            <tr>
                                <th>Pair</th>
                                <th>Checks</th>
                                <th>Profitable</th>
                                <th>Avg Profit</th>
                                <th>Max Profit</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                pairs.forEach(pair => {
                    const profitRate = pair.check_count > 0 ? 
                        (pair.profitable_count / pair.check_count * 100) : 0;
                        
                    tableHtml += `
                    <tr>
                        <td>${pair.pair}</td>
                        <td>${pair.check_count}</td>
                        <td>${pair.profitable_count} (${profitRate.toFixed(1)}%)</td>
                        <td>$${pair.avg_profit ? pair.avg_profit.toFixed(4) : '0.0000'}</td>
                        <td>$${pair.max_profit ? pair.max_profit.toFixed(4) : '0.0000'}</td>
                    </tr>
                    `;
                });
                
                tableHtml += `
                        </tbody>
                    </table>
                </div>
                `;
            }
            
            pairStatsEl.innerHTML = tableHtml;
        }
        
        // Update DEX stats
        function updateDexStats(dexStats) {
            const dexStatsEl = document.getElementById('dex-stats');
            
            if (!dexStats || dexStats.length === 0) {
                dexStatsEl.innerHTML = '<p>No DEX statistics available</p>';
                return;
            }
            
            // Group by network
            const networkGroups = {};
            
            dexStats.forEach(dex => {
                const network = dex.network || 'unknown';
                if (!networkGroups[network]) {
                    networkGroups[network] = [];
                }
                networkGroups[network].push(dex);
            });
            
            let tableHtml = '';
            
            // Create a table for each network
            for (const [network, dexes] of Object.entries(networkGroups)) {
                tableHtml += `
                <div class="network-section">
                    <h4>
                        <span class="network-badge ${network}">${formatNetworkName(network)}</span>
                    </h4>
                    <table>
                        <thead>
                            <tr>
                                <th>DEX</th>
                                <th>Role</th>
                                <th>Checks</th>
                                <th>Profitable</th>
                                <th>Avg Profit</th>
                                <th>Max Profit</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                dexes.forEach(dex => {
                    const profitRate = dex.check_count > 0 ? 
                        (dex.profitable_count / dex.check_count * 100) : 0;
                        
                    tableHtml += `
                    <tr>
                        <td>${formatDexName(dex.dex)}</td>
                        <td>${dex.role === 'source' ? 'Buy' : 'Sell'}</td>
                        <td>${dex.check_count}</td>
                        <td>${dex.profitable_count} (${profitRate.toFixed(1)}%)</td>
                        <td>$${dex.avg_profit ? dex.avg_profit.toFixed(4) : '0.0000'}</td>
                        <td>$${dex.max_profit ? dex.max_profit.toFixed(4) : '0.0000'}</td>
                    </tr>
                    `;
                });
                
                tableHtml += `
                        </tbody>
                    </table>
                </div>
                `;
            }
            
            dexStatsEl.innerHTML = tableHtml;
        }
        
        // Format network name
        function formatNetworkName(network) {
            if (!network) return 'Unknown';
            
            return network.charAt(0).toUpperCase() + network.slice(1);
        }
        
        // Load filter dropdowns on page load
        function loadFilterOptions() {
            // Load pairs grouped by network
            fetch('/api/pairs')
                .then(response => response.json())
                .then(data => {
                    const pairSelect = document.getElementById('filter-pair');
                    
                    // Clear existing options (except first)
                    while (pairSelect.options.length > 1) {
                        pairSelect.remove(1);
                    }
                    
                    // Group pairs by network
                    const networkGroups = {};
                    
                    data.pairs.forEach(pairData => {
                        const network = pairData.network || 'unknown';
                        if (!networkGroups[network]) {
                            networkGroups[network] = [];
                        }
                        networkGroups[network].push(pairData.pair);
                    });
                    
                    // Add options grouped by network
                    for (const [network, pairs] of Object.entries(networkGroups)) {
                        const optgroup = document.createElement('optgroup');
                        optgroup.label = formatNetworkName(network);
                        
                        pairs.forEach(pair => {
                            const option = document.createElement('option');
                            option.value = pair;
                            option.text = pair;
                            optgroup.appendChild(option);
                        });
                        
                        pairSelect.appendChild(optgroup);
                    }
                });
                
            // Load DEXes grouped by network
            fetch('/api/dexes')
                .then(response => response.json())
                .then(data => {
                    const dexSelect = document.getElementById('filter-dex');
                    
                    // Clear existing options (except first)
                    while (dexSelect.options.length > 1) {
                        dexSelect.remove(1);
                    }
                    
                    // Group DEXes by network
                    const networkGroups = {};
                    
                    data.dexes.forEach(dexData => {
                        const network = dexData.network || 'unknown';
                        if (!networkGroups[network]) {
                            networkGroups[network] = [];
                        }
                        networkGroups[network].push(dexData.dex);
                    });
                    
                    // Add options grouped by network
                    for (const [network, dexes] of Object.entries(networkGroups)) {
                        const optgroup = document.createElement('optgroup');
                        optgroup.label = formatNetworkName(network);
                        
                        dexes.forEach(dex => {
                            const option = document.createElement('option');
                            option.value = dex;
                            option.text = formatDexName(dex);
                            optgroup.appendChild(option);
                        });
                        
                        dexSelect.appendChild(optgroup);
                    }
                });
        }
        
        // Fetch and update opportunity data
        function refreshOpportunities() {
            // Get filter values
            const network = document.getElementById('filter-network').value;
            const pair = document.getElementById('filter-pair').value;
            const dex = document.getElementById('filter-dex').value;
            const minProfit = document.getElementById('filter-profit').value;
            const limit = document.getElementById('filter-limit').value;
            
            // Build API URL with filters
            let url = `/api/opportunities/filter?limit=${limit}`;
            if (network) url += `&network=${network}`;
            if (pair) url += `&pair=${pair}`;
            if (dex) url += `&dex=${dex}`;
            if (minProfit) url += `&min_profit=${minProfit}`;
            
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    updateOpportunityTable(data.opportunities);
                    updateStats(data.stats);
                    document.getElementById('last-updated').textContent = new Date().toLocaleString();
                });
        }
        
        // Update opportunity table with data
        function updateOpportunityTable(opportunities) {
            const tableBody = document.getElementById('opportunity-rows');
            
            // Clear existing rows
            tableBody.innerHTML = '';
            
            if (!opportunities || opportunities.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="11" class="loading">No opportunities found with current filters</td></tr>';
                return;
            }

            // Add each opportunity as a row
            opportunities.forEach(opp => {
                // Format the timestamp
                let timestamp;
                try {
                    timestamp = new Date(opp.timestamp).toLocaleTimeString();
                } catch (e) {
                    timestamp = opp.timestamp || new Date().toLocaleTimeString();
                }
                
                const netProfit = opp.net_profit_usd || 0;
                const profitClass = netProfit > 0 ? 'positive' : (netProfit < 0 ? 'negative' : ''); 
                const statusText = opp.executed ? 'Executed' : 'Skipped';
                const networkClass = opp.network || 'unknown';
                
                tableBody.innerHTML += `
                <tr>
                    <td>${timestamp}</td>
                    <td><span class="network-badge ${networkClass}">${formatNetworkName(opp.network || 'unknown')}</span></td>
                    <td>${opp.pair || 'N/A'}</td>
                    <td>${formatDexName(opp.source_dex)}</td>
                    <td>${formatDexName(opp.target_dex)}</td>
                    <td>${opp.price_diff_pct ? opp.price_diff_pct.toFixed(2) + '%' : 'N/A'}</td>
                    <td>${opp.amount ? opp.amount.toFixed(4) : 'N/A'}</td>
                    <td class="${profitClass}">$${opp.profit_usd ? opp.profit_usd.toFixed(4) : '0.00'}</td>
                    <td>$${opp.gas_cost_usd ? opp.gas_cost_usd.toFixed(4) : '0.00'}</td>
                    <td class="${profitClass}">$${netProfit.toFixed(4)}</td>
                    <td><span class="${opp.executed ? 'status-executed' : 'status-skipped'}">${statusText}</span></td>
                </tr>
                `;
            }); 
        }
        
        // Update statistics panel
        function updateStats(stats) {
            if (!stats) return;
            
            document.getElementById('total-checks').textContent = stats.total_checks || 0;
            document.getElementById('profitable-opps').textContent = stats.profitable_opportunities || 0;
            
            const profitRate = stats.profit_rate || 0;
            document.getElementById('profit-rate').textContent = (profitRate * 100).toFixed(2) + '%';
            
            const maxProfit = stats.max_profit_usd || 0;
            document.getElementById('max-profit').textContent = '$' + maxProfit.toFixed(4);
            
            const avgProfit = stats.avg_profit_usd || 0;
            document.getElementById('avg-profit').textContent = '$' + avgProfit.toFixed(4);
            
            // Format and display last update time
            document.getElementById('refresh-time').textContent = new Date().toLocaleTimeString();
        }
        
        // Format DEX name for display
        function formatDexName(dexName) {
            if (!dexName) return 'Unknown';

            // Replacements for common DEX names
            const replacements = {
                // Ethereum DEXes
                'uniswap_v2': 'Uniswap V2',
                'uniswap_v3': 'Uniswap V3',
                'uniswapv2': 'Uniswap V2',
                'uniswapv3': 'Uniswap V3',
                'sushiswap': 'SushiSwap',
                'pancakeswap': 'PancakeSwap',
                'pancakeswapv2': 'PancakeSwap V2',
                'dodo': 'DODO',
                'curve': 'Curve',
                'balancer': 'Balancer',
                
                // Arbitrum DEXes
                'sushiswap_arb': 'SushiSwap (Arb)',
                'uniswap_v3_arb': 'Uniswap V3 (Arb)',
                'camelot': 'Camelot',
                'ramses': 'Ramses',
                'trader_joe': 'Trader Joe',
                'gmx': 'GMX',
                'chronos': 'Chronos',
                
                // Base DEXes
                'baseswap': 'BaseSwap',
                'aerodrome': 'Aerodrome',
                'swapbased': 'SwapBased',
                'rocketswap': 'RocketSwap',
                'basex': 'BaseX'
            };
            
            if (replacements[dexName.toLowerCase()]) {
                return replacements[dexName.toLowerCase()];
            }
            
            // Default formatting for other DEXes
            return dexName
                .replace('_', ' ')
                .replace(/\b\w/g, function(l) { return l.toUpperCase(); });
        }
        
        // Filter opportunities with current filter settings
        function filterOpportunities() { 
            refreshOpportunities();
        }
        
        // Load initial data when page loads
        document.addEventListener('DOMContentLoaded', function() {
            // Load filter options
            loadFilterOptions();
            
            // Load initial data
            refreshOpportunities();
            
            // Load network statistics
            updateNetworkStats();
            
            // Load stats data
            loadPairStats();
            loadDexStats();
        });
        """

def run_server():
    """Run the server."""
    # Start the HTTP server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MultiChainDashboardHandler)
    
    print(f"Starting Multi-Chain Arbitrage Dashboard on port {PORT}...")
    print(f"Open this URL in your browser: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()