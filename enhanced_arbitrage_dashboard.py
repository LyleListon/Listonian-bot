"""
Enhanced Arbitrage Dashboard

Comprehensive dashboard with token prices, opportunity tracking, and wallet monitoring.
"""

import os
import sys
import asyncio
import json
import logging
import random
import csv
import rsqlite3import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Add the current directory to path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dashboard configuration
PORT = 9097  # Using a specific port to avoid conflicts

# Database setup (in-memory for simplicity)
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
DEFAULT_PAIRS = [
    "WETH/USDC",
    "WETH/USDT",
    "WETH/DAI",
    "ETH/USDC",
    "ETH/USDT",
    "WBTC/USDC"
]

# Default DEX list
DEFAULT_DEXES = [
    "uniswap_v2",
    "uniswap_v3",
    "sushiswap",
    "pancakeswap",
    "curve"
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
                    
                    # Insert into database
                    cursor.execute('''
                    INSERT INTO opportunity_checks 
                    (timestamp, pair, source_dex, target_dex, source_price, target_price, 
                     price_diff_pct, amount, profit_usd, gas_cost_usd, net_profit_usd, executed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('timestamp', datetime.now().isoformat()),
                        row.get('pair', 'UNKNOWN'),
                        row.get('source_dex', 'UNKNOWN'),
                        row.get('target_dex', 'UNKNOWN'),
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
                        for default_pair in DEFAULT_PAIRS:
                            if default_pair in line:
                                pair = default_pair
                                break
                        
                        # Extract DEXes
                        for dex in DEFAULT_DEXES:
                            if dex in line and source_dex == "UNKNOWN":
                                source_dex = dex
                            elif dex in line and source_dex != "UNKNOWN":
                                target_dex = dex
                                break
                        
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
                        (timestamp, pair, source_dex, target_dex, source_price, target_price, 
                         price_diff_pct, amount, profit_usd, gas_cost_usd, net_profit_usd, executed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            timestamp,
                            pair,
                            source_dex,
                            target_dex,
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
            
    def _create_sample_data(self):
        """Create minimal sample data for testing the UI"""
        cursor = self.db_conn.cursor()
        
        pairs = [
            "WETH/USDC",
            "WETH/USDT",
            "WETH/DAI"
        ]
        
        dexes = [
            "uniswap_v2",
            "uniswap_v3",
            "sushiswap",
            "pancakeswap",
            "curve"
        ]
        
        # Add a message to let user know we're using minimal sample data
        logger.warning("No log data found - displaying minimal sample data")
        print("No opportunity check logs found. Using minimal sample data for UI display.")
        print("To see real data, place your log files in logs/ directory.")
        
        # Create a small sample of records
        for i in range(3):
            pair = pairs[i % len(pairs)]
            source_dex = dexes[i % len(dexes)]
            target_dex = dexes[(i + 1) % len(dexes)]
            
            cursor.execute('''
            INSERT INTO opportunity_checks 
            (timestamp, pair, source_dex, target_dex, source_price, target_price, 
             price_diff_pct, amount, profit_usd, gas_cost_usd, net_profit_usd, executed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                pair,
                source_dex,
                target_dex,
                1000.0,
                1001.0,
                0.1,
                1.0,
                1.0,
                0.5,
                0.5,
                0
            ))
        
        self.db_conn.commit()
        
    def get_opportunities(self, limit=100, min_profit=None, pair=None, dex=None):
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
    
    def get_pair_stats(self):
        """Get statistics by trading pair"""
        cursor = self.db_conn.cursor()
        
        cursor.execute("""
        SELECT pair, 
               COUNT(*) as check_count,
               SUM(CASE WHEN net_profit_usd > 0 THEN 1 ELSE 0 END) as profitable_count,
               AVG(net_profit_usd) as avg_profit,
               MAX(net_profit_usd) as max_profit
        FROM opportunity_checks
        GROUP BY pair
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
        SELECT source_dex as dex, 
               COUNT(*) as check_count,
               SUM(CASE WHEN net_profit_usd > 0 THEN 1 ELSE 0 END) as profitable_count,
               AVG(net_profit_usd) as avg_profit,
               MAX(net_profit_usd) as max_profit,
               'source' as role
        FROM opportunity_checks
        GROUP BY source_dex
        """)
        
        columns = [desc[0] for desc in cursor.description]
        result = []
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        # Then for target_dex
        cursor.execute("""
        SELECT target_dex as dex, 
               COUNT(*) as check_count,
               SUM(CASE WHEN net_profit_usd > 0 THEN 1 ELSE 0 END) as profitable_count,
               AVG(net_profit_usd) as avg_profit,
               MAX(net_profit_usd) as max_profit,
               'target' as role
        FROM opportunity_checks
        GROUP BY target_dex
        """)
        
        columns = [desc[0] for desc in cursor.description]
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
        
        return result
    
    def get_pairs_list(self):
        """Get list of all unique trading pairs"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT DISTINCT pair FROM opportunity_checks ORDER BY pair")
        return [row[0] for row in cursor.fetchall()]
    
    def get_dexes_list(self):
        """Get list of all unique DEXes"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT DISTINCT source_dex as dex FROM opportunity_checks UNION SELECT DISTINCT target_dex FROM opportunity_checks ORDER BY dex")
        return [row[0] for row in cursor.fetchall()]

# Global data manager instance
data_manager = DataManager(db_conn)

# Load opportunity data from available logs
data_manager.load_log_data()

class ArbitrageDashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the Arbitrage dashboard."""
    
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
            
            # Get filtered opportunities
            opportunities = data_manager.get_opportunities(
                limit=limit, min_profit=min_profit, pair=pair, dex=dex
            )
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'opportunities': opportunities,
                'stats': data_manager.get_stats(),
                'filter': {'limit': limit, 'min_profit': min_profit, 'pair': pair, 'dex': dex}
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-time Arbitrage Dashboard</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="300">
    <script src="/dashboard.js" defer></script>
</head>
<body>
    <div class="header">
        <h1>Arbitrage Operations Dashboard</h1>
        <div class="sub-header">Real-time monitoring and opportunity tracking</div>
        <div class="last-updated">
            Last Updated: <span id="last-updated">Loading...</span>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="tabs">
            <button class="tab-link active" onclick="openTab(event, 'opportunity-tab')">Opportunities</button>
            <button class="tab-link" onclick="openTab(event, 'stats-tab')">Stats</button>
        </div>
        
        <div id="opportunity-tab" class="tab-content active">
            <h2>Opportunity Tracker</h2>
            <div class="filter-controls">
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
                        <tr><td colspan="10" class="loading">Loading opportunity data...</td></tr>
                    </tbody>
                </table>
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
        <p>Arbitrage Dashboard | Reads data directly from bot logs</p>
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
            padding: 30px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
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
            margin: 30px auto;
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
        }
        """
    
    def get_js(self):
        """Get JavaScript for the dashboard."""
        return """
        // Auto-refresh the opportunity data every 5 seconds
        setInterval(function() {
            refreshOpportunities();
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
            
            // Load specific data for the selected tab
            if (tabName === 'stats-tab') {
                loadPairStats();
                loadDexStats();
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
            
            let tableHtml = `
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
            
            pairStats.forEach(pair => {
                const profitRate = pair.profitable_count / pair.check_count * 100;
                tableHtml += `
                <tr>
                    <td>${pair.pair}</td>
                    <td>${pair.check_count}</td>
                    <td>${pair.profitable_count} (${profitRate.toFixed(1)}%)</td>
                    <td>$${pair.avg_profit.toFixed(4)}</td>
                    <td>$${pair.max_profit.toFixed(4)}</td>
                </tr>
                `;
            });
            
            tableHtml += `
                </tbody>
            </table>
            `;
            
            pairStatsEl.innerHTML = tableHtml;
        }
        
        // Update DEX stats
        function updateDexStats(dexStats) {
            const dexStatsEl = document.getElementById('dex-stats');
            
            if (!dexStats || dexStats.length === 0) {
                dexStatsEl.innerHTML = '<p>No DEX statistics available</p>';
                return;
            }
            
            let tableHtml = `
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
            
            dexStats.forEach(dex => {
                const profitRate = dex.profitable_count / dex.check_count * 100;
                tableHtml += `
                <tr>
                    <td>${formatDexName(dex.dex)}</td>
                    <td>${dex.role === 'source' ? 'Buy' : 'Sell'}</td>
                    <td>${dex.check_count}</td>
                    <td>${dex.profitable_count} (${profitRate.toFixed(1)}%)</td>
                    <td>$${dex.avg_profit.toFixed(4)}</td>
                    <td>$${dex.max_profit.toFixed(4)}</td>
                </tr>
                `;
            });
            
            tableHtml += `
                </tbody>
            </table>
            `;
            
            dexStatsEl.innerHTML = tableHtml;
        }
        
        // Load filter dropdowns on page load
        function loadFilterOptions() {
            // Load pairs
            fetch('/api/pairs')
                .then(response => response.json())
                .then(data => {
                    const pairSelect = document.getElementById('filter-pair');
                    
                    // Clear existing options (except first)
                    while (pairSelect.options.length > 1) {
                        pairSelect.remove(1);
                    }
                    
                    // Add new options
                    data.pairs.forEach(pair => {
                        const option = document.createElement('option');
                        option.value = pair;
                        option.text = pair;
                        pairSelect.appendChild(option);
                    });
                });
            
            // Load DEXes
            fetch('/api/dexes')
                .then(response => response.json())
                .then(data => {
                    const dexSelect = document.getElementById('filter-dex');
                    
                    // Clear existing options (except first)
                    while (dexSelect.options.length > 1) {
                        dexSelect.remove(1);
                    }
                    
                    // Add new options
                    data.dexes.forEach(dex => {
                        const option = document.createElement('option');
                        option.value = dex;
                        option.text = formatDexName(dex);
                        dexSelect.appendChild(option);
                    });
                });
        }
        
        // Fetch and update opportunity data
        function refreshOpportunities() {
            // Get filter values
            const pair = document.getElementById('filter-pair').value;
            const dex = document.getElementById('filter-dex').value;
            const minProfit = document.getElementById('filter-profit').value;
            const limit = document.getElementById('filter-limit').value;
            
            // Build API URL with filters
            let url = `/api/opportunities/filter?limit=${limit}`;
            if (pair) url += `&pair=${pair}`;
            if (dex) url += `&dex=${dex}`;
            if (minProfit) url += `&min_profit=${minProfit}`;
            
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    updateOpportunityTable(data.opportunities);
                    updateStats(data.stats);
                    // Update last updated time
                    document.getElementById('last-updated').textContent = new Date().toLocaleString();
                });
        }
        
        // Update opportunity table with data
        function updateOpportunityTable(opportunities) {
            const tableBody = document.getElementById('opportunity-rows');
            
            // Clear existing rows
            tableBody.innerHTML = '';
            
            if (!opportunities || opportunities.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="10" class="loading">No opportunities found with current filters</td></tr>';
                return;
            }

            // Add each opportunity as a row
            opportunities.forEach(opp => {
                // Format the timestamp
                let timestamp;
                try {
                    timestamp = new Date(opp.timestamp).toLocaleTimeString();
                } catch (e) {
                    timestamp = opp.timestamp;
                }
                
                const netProfit = opp.net_profit_usd || 0;
                const profitClass = netProfit > 0 ? 'positive' : (netProfit < 0 ? 'negative' : '');
                const statusClass = opp.executed ? 'status-executed' : 'status-skipped';
                const statusText = opp.executed ? 'Executed' : 'Skipped';
                
                tableBody.innerHTML += `
                <tr>
                    <td>${timestamp}</td>
                    <td>${opp.pair || 'N/A'}</td>
                    <td>${formatDexName(opp.source_dex)}</td>
                    <td>${formatDexName(opp.target_dex)}</td>
                    <td>${opp.price_diff_pct ? opp.price_diff_pct.toFixed(2) + '%' : 'N/A'}</td>
                    <td>${opp.amount ? opp.amount.toFixed(4) : 'N/A'}</td>
                    <td class="${profitClass}">$${opp.profit_usd ? opp.profit_usd.toFixed(4) : '0.00'}</td>
                    <td>$${opp.gas_cost_usd ? opp.gas_cost_usd.toFixed(4) : '0.00'}</td>
                    <td class="${profitClass}">$${netProfit.toFixed(4)}</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
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
                'uniswap_v2': 'Uniswap V2',
                'uniswap_v3': 'Uniswap V3',
                'uniswapv2': 'Uniswap V2',
                'uniswapv3': 'Uniswap V3',
                'sushiswap': 'SushiSwap',
                'pancakeswap': 'PancakeSwap',
                'pancakeswapv2': 'PancakeSwap',
                'dodo': 'DODO',
                'curve': 'Curve'
            };
            
            if (replacements[dexName.toLowerCase()]) {
                return replacements[dexName.toLowerCase()];
            }
            
            // Default formatting for other DEXes
            return dexName.replace('_', ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); });
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
            
            // Load stats data
            loadPairStats();
            loadDexStats();
        });
        """

def run_server():
    """Run the server."""
    # Start the HTTP server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, ArbitrageDashboardHandler)
    
    print(f"Starting Arbitrage Dashboard on port {PORT}...")
    print(f"Open this URL in your browser: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
        'address': 'ethereum'  # Alchemy uses 'ethereum' for ETH
    },
    {
        'symbol': 'WETH',
        'name': 'Wrapped Ether',
        'address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'
    },
    {
        'symbol': 'USDC',
        'name': 'USD Coin',
        'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'
    },
    {
        'symbol': 'USDT',
        'name': 'Tether USD',
        'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7'
    },
    {
        'symbol': 'DAI',
        'name': 'Dai Stablecoin',
        'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F'
    },
    {
        'symbol': 'WBTC',
        'name': 'Wrapped Bitcoin',
        'address': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'
    }
]

# Define the exchange sources to track
EXCHANGES = [
    'uniswapv3',
    'uniswapv2',
    'sushiswap',
    'pancakeswapv2',
    'dodo'
]

# Trading pairs to monitor
TRADING_PAIRS = [
    ('WETH', 'USDC'),
    ('WETH', 'USDT'),
    ('WETH', 'DAI'), 
    ('WETH', 'WBTC'),
]

class GlobalCache:
    """Cache for storing dashboard data."""
    
    def __init__(self):
        self.token_prices = {}
        self.use_simulated_data = False
        self.simulation_start_time = None
        self.price_last_updated = None
        self.opportunity_tracker = OpportunityTracker(max_entries=5000)
        self.lock = threading.Lock()
    
    def update_prices(self, prices: Dict[str, Any]):
        """Update the price cache with new data."""
        with self.lock:
            self.token_prices = prices
            self.price_last_updated = datetime.now()
            
    def enable_simulation_mode(self):
        """Enable simulation mode when API calls fail."""
        if not self.use_simulated_data:
            logger.warning("Switching to simulation mode due to API connection issues")
            self.use_simulated_data = True
            self.simulation_start_time = datetime.now()
            self.update_prices(generate_simulated_price_data())
    
    def get_prices(self) -> Dict[str, Any]:
        """Get the current price data."""
        result = {}
        with self.lock:
            result = {
                'prices': self.token_prices or {},
                'last_updated': self.price_last_updated.strftime('%Y-%m-%d %H:%M:%S') 
                               if self.price_last_updated else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'simulation_mode': self.use_simulated_data
            }
        return result
    
    def add_opportunity(self, data: Dict[str, Any]):
        """Add a new opportunity check."""
        self.opportunity_tracker.add_opportunity(data)
    
    def get_opportunities(self, limit=100, min_profit=None, pair=None, dex=None) -> List[Dict[str, Any]]:
        """Get recent opportunity checks."""
        return self.opportunity_tracker.get_opportunities(limit, min_profit, pair, dex)
    
    def get_opportunity_stats(self) -> Dict[str, Any]:
        """Get opportunity statistics."""
        return self.opportunity_tracker.get_stats()

# Global cache instance
global_cache = GlobalCache()

def load_config():
    """Load configuration from various sources."""
    # First try to load from .env.production
    load_dotenv(".env.production")
    
    # Check if we have an Alchemy API key from environment
    api_key = os.environ.get('ALCHEMY_API_KEY')
    if api_key:
        # Check if API key is a secure reference
        if api_key.startswith("$SECURE:"):
            env_var = api_key.replace("$SECURE:", "")
            if env_var in os.environ:
                api_key = os.environ.get(env_var)
                logger.info(f"Resolved API key from environment variable {env_var}")
            else:
                return {}  # Could not resolve secure reference
        return {"alchemy": {"api_key": api_key}}
    
    # If not, try to load from config.json
    try:
        logger.info("Trying to load API key from config.json...")
        with open('configs/config.json', 'r') as f:
            config = json.load(f)
            # Check if the config has network.rpc_url which might contain the Alchemy URL
            if "network" in config and "rpc_url" in config["network"]:
                url = config["network"]["rpc_url"]
                logger.info(f"Found RPC URL in config: {url[:20]}...{url[-5:] if len(url) > 25 else ''}")
                
                # Check if it's a $SECURE: reference
                if url.startswith("$SECURE:"):
                    secure_var = url.replace("$SECURE:", "")
                    logger.info(f"RPC URL is a secure reference to {secure_var}")
                    
                # If this is a secure reference, try to get it from the environment
                if url.startswith("$SECURE:"):
                    env_var = url.replace("$SECURE:", "")
                    # Check if this environment variable exists
                    if env_var in os.environ:
                        url = os.environ.get(env_var)
                    
                # Handle case where URL is still a $SECURE reference (env var not found)
                if url.startswith("$SECURE:"):
                    logger.warning(f"Could not resolve secure reference - environment variable {env_var} not found")
                    return {}
                    
                # Extract API key from Alchemy URL if present
                if "alchemy.com" in url and "/v2/" in url:
                    api_key = url.split("/v2/")[1]
                    # Handle case where API key itself is a secure reference
                    if api_key.startswith("$SECURE:"):
                        return {}  # We can't use this API key, will use simulation instead
                    logger.info("Extracted Alchemy API key from config.json RPC URL")
                    return {"alchemy": {"api_key": api_key}}
        
        logger.warning("Could not find valid Alchemy API key in config.json")
    except Exception as e:
        logger.warning(f"Could not load config.json: {e}")
    
    logger.warning("No Alchemy API key found. Will use simulation mode.")
    return {}

def get_alchemy_api_key(config=None):
    """Get Alchemy API key from config."""
    if not config:
        return None
        
    if not isinstance(config, dict) or 'alchemy' not in config:
        return None
        
    api_key = config.get('alchemy', {}).get('api_key')
    if not api_key:
        logger.warning("No Alchemy API key available in config.")
    
    return api_key

def get_token_price(token_address, api_key):
    """
    Get token price in USD using Alchemy's Price API.
    
    Args:
        token_address: Token address or 'ethereum' for ETH
        api_key: Alchemy API key
        
    Returns:
        Dictionary with price data or None if request fails
    """
    url = f"https://api.alchemy.com/v2/{api_key}/alchemy/etherspot/price-entities"
    
    payload = {
        "asset": token_address
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        if data and 'price' in data:
            return data
        else:
            logger.warning(f"No price data returned for {token_address}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API Error for {token_address}: Connection failed")
        return None

def get_token_price_on_exchange(token_address, exchange, api_key):
    """
    Get token price on a specific exchange using Alchemy's Price API.
    
    Args:
        token_address: Token address or 'ethereum' for ETH
        exchange: Exchange name (uniswapv3, sushiswap, etc.)
        api_key: Alchemy API key
        
    Returns:
        Dictionary with price data or None if request fails
    """
    url = f"https://api.alchemy.com/v2/{api_key}/alchemy/etherspot/get-exchange-price"
    
    payload = {
        "source": exchange,
        "destination": "USD",
        "amount": "1",
        "sourceAsset": token_address
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        if data and 'price' in data:
            return data
        else:
            logger.warning(f"No price data returned for {token_address} on {exchange}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.debug(f"API Error for {token_address} on {exchange}: Connection failed")
        return None

def generate_simulated_price_data():
    """
    Generate simulated price data when the API is not available.
    
    Returns:
        Dictionary with simulated price data
    """
    logger.info("Generating simulated price data...")
    result = {}
    
    # Base prices for different tokens (in USD)
    base_prices = {
        'ETH': 3500.0,
        'WETH': 3500.0,
        'USDC': 1.0001,
        'USDT': 1.0002,
        'DAI': 0.9995,
        'WBTC': 55000.0,
    }
    
    # Add random price movement to make simulation more realistic
    for token, price in base_prices.items():
        # Add ±0.5% random movement
        base_prices[token] = price * random.uniform(0.995, 1.005)
    
    # Create token data
    for token in TOKENS:
        symbol = token['symbol']
        base_price = base_prices.get(symbol, 100.0)  # Default to 100 if token not in base_prices
        
        # Add some random variation to make the data look real
        global_price = base_price * random.uniform(0.998, 1.002)
        
        result[symbol] = {
            'symbol': symbol,
            'name': token['name'],
            'price': global_price,
            'exchanges': {}
        }
        
        # Generate exchange-specific prices
        for exchange in EXCHANGES:
            exchange_price = base_price * random.uniform(0.995, 1.005)
            result[symbol]['exchanges'][exchange] = {
                'price': exchange_price,
                'source': exchange,
                'timestamp': datetime.now().isoformat()
            }
    
    return result

async def fetch_token_prices():
    """
    Fetch token prices from Alchemy Price API.
    
    Returns:
        Dictionary with price data
    """
    # Load configuration from environment/config files
    config = load_config()
    
    # Get Alchemy API key
    api_key = get_alchemy_api_key(config)
    if not api_key:
        # No API key found in environment or config 
        # Switch to simulation mode
        logger.warning("No Alchemy API key available, using simulated data")
        global_cache.enable_simulation_mode()
        return global_cache.token_prices
    
    result = {}
    
    # First get global prices for all tokens
    for token in TOKENS:
        symbol = token['symbol']
        address = token['address']
        
        price_data = get_token_price(address, api_key)
        if price_data:
            # Store token global price data
            result[symbol] = {
                'symbol': symbol,
                'name': token['name'],
                'price': price_data.get('price', 0),
                'exchanges': {}
            }
        else:
            # Initialize with empty data if API call fails
            result[symbol] = {
                'symbol': symbol, 
                'name': token['name'],
                'price': 0,
                'exchanges': {}
            }
    
    # Now get prices for each token on each exchange
    for token in TOKENS:
        symbol = token['symbol']
        address = token['address']
        
        # Skip if token not in results (shouldn't happen)
        if symbol not in result:
            continue
        
        # Get price on each exchange
        for exchange in EXCHANGES:
            exchange_data = get_token_price_on_exchange(address, exchange, api_key)
            
            if exchange_data:
                # Store exchange-specific price
                result[symbol]['exchanges'][exchange] = {
                    'price': exchange_data.get('price', 0),
                    'source': exchange_data.get('source', exchange),
                    'timestamp': exchange_data.get('timestamp', datetime.now().isoformat())
                }
            else:
                # Store empty data if API call fails
                result[symbol]['exchanges'][exchange] = {
                    'price': 0,
                    'source': exchange,
                    'timestamp': None
                }
    
    # Check if we got any valid price data
    has_valid_data = any(any(ex_data.get('price', 0) > 0 for ex_data in token_data.get('exchanges', {}).values()) 
                         for token_data in result.values())
    
    if not has_valid_data:
        logger.warning("No valid price data from API, switching to simulation mode")
        global_cache.enable_simulation_mode()
        return global_cache.token_prices
    return result

async def simulate_opportunity_checks():
    """Simulate opportunity checks based on current token prices."""
    # Get current token prices
    price_data = global_cache.get_prices()
    token_prices = price_data.get('prices', {})
    
    # If we have no price data, return
    if not token_prices:
        logger.warning("No token price data available for opportunity checks")
        return
    
    # Format token price data for the simulation
    formatted_prices = {}
    for dex in EXCHANGES:
        formatted_prices[dex] = {'prices': {}}
        for token_symbol, token_data in token_prices.items():
            if 'exchanges' in token_data and dex in token_data['exchanges']:
                price = token_data['exchanges'][dex].get('price', 0)
                if price > 0:
                    formatted_prices[dex]['prices'][token_symbol] = {
                        'formatted': price
                    }
    
    # Simulate opportunity checks for each trading pair
    for pair in TRADING_PAIRS:
        # Random number of checks per pair (1-3)
        num_checks = random.randint(1, 3)
        
        for _ in range(num_checks):
            # Simulate opportunity check
            opportunity = simulate_opportunity_check(formatted_prices, pair)
            
            # Add to tracker if valid
            if opportunity:
                global_cache.add_opportunity(opportunity)

def setup_logging():
    """Configure logging behavior."""
    # Create a file handler
    log_file = "arbitrage_dashboard.log"
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)  # Log everything to file
    
    # Create a console handler with higher threshold
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Add formatters to handlers
    file_handler.setFormatter(detailed_formatter)
    console_handler.setFormatter(simple_formatter)
    
    # Remove existing handlers and add our custom ones
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.setLevel(logging.DEBUG)  # Capture all logs, handlers will filter

async def price_update_job():
    """Background job to update prices periodically."""
    while True:
        try:
            logger.info("Updating token prices...")
            prices = await fetch_token_prices()
            global_cache.update_prices(prices)
            logger.info("Prices updated successfully")
            
            # After updating prices, simulate opportunity checks
            await simulate_opportunity_checks()
            
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
        
        # Wait before next update
        await asyncio.sleep(10)  # Update every 10 seconds to reduce API load

class EnhancedArbitrageDashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the Arbitrage dashboard."""
    
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
        elif self.path == "/api/prices":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            # Add simulation status to price data
            price_data = global_cache.get_prices()
            if not 'simulation_mode' in price_data:
                price_data['simulation_mode'] = global_cache.use_simulated_data
                
            # Send the response
            self.wfile.write(json.dumps(price_data).encode())
        elif self.path == "/api/opportunities":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            # Get opportunities (limit to 100 most recent)
            opportunities = global_cache.get_opportunities(limit=100)
            self.wfile.write(json.dumps({
                'opportunities': opportunities,
                'stats': global_cache.get_opportunity_stats()
            }).encode())
        elif self.path.startswith("/api/opportunities/filter"):
            # Parse query parameters
            import urllib.parse
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            # Extract filter parameters
            limit = int(params.get('limit', ['100'])[0])
            min_profit = float(params.get('min_profit', ['0'])[0])
            pair = params.get('pair', [None])[0]
            dex = params.get('dex', [None])[0]
            
            # Get filtered opportunities
            opportunities = global_cache.get_opportunities(
                limit=limit, min_profit=min_profit, pair=pair, dex=dex
            )
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                'opportunities': opportunities,
                'stats': global_cache.get_opportunity_stats(),
                'filter': {'limit': limit, 'min_profit': min_profit, 'pair': pair, 'dex': dex}
            }).encode())
        elif self.path == "/api/wallet":
            # Get wallet data
            wallet_stats = wallet_monitor.get_wallet_stats()
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(wallet_stats).encode())
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")
    
    def generate_html(self):
        """Generate HTML for the dashboard."""
        # Get price data
        data = global_cache.get_prices()
        prices = data.get('prices', {})
        last_updated = data.get('last_updated')
        
        # Create token price section
        token_prices_html = self._generate_token_prices_html(prices)
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Arbitrage Dashboard</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="300">
    <script src="/dashboard.js" defer></script>
</head>
<body>
    <div class="header">
        <h1>Arbitrage Operations Dashboard</h1>
        <div class="sub-header">Real-time monitoring and opportunity tracking</div>
        <div class="last-updated">
            Last Updated: <span id="last-updated">{last_updated or 'Loading...'}</span>
            {self._get_simulation_indicator()}
        </div>
    </div>
    
    <div id="simulation-warning" class="simulation-warning" style="display: {'block' if global_cache.use_simulated_data else 'none'}">
        <div class="warning-container">
            <p><strong>⚠️ Using Simulated Data:</strong> Could not connect to Alchemy API. Showing demonstration data for UI testing.</p>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="tabs">
            <button class="tab-link active" onclick="openTab(event, 'price-tab')">Token Prices</button>
            <button class="tab-link" onclick="openTab(event, 'opportunity-tab')">Opportunities</button>
            <button class="tab-link" onclick="openTab(event, 'stats-tab')">Stats</button>
            <button class="tab-link" onclick="openTab(event, 'wallet-tab')">Wallet Activity</button>
        </div>
        
        <div id="price-tab" class="tab-content active">
            <h2>Token Prices</h2>
            <div class="token-prices">
                {token_prices_html}
            </div>
        </div>
        
        <div id="opportunity-tab" class="tab-content">
            <h2>Opportunity Tracker</h2>
            <div class="filter-controls">
                <div class="filter-item">
                    <label for="filter-pair">Trading Pair:</label>
                    <select id="filter-pair" onchange="filterOpportunities()">
                        <option value="">All Pairs</option>
                        <option value="WETH/USDC">WETH/USDC</option>
                        <option value="WETH/USDT">WETH/USDT</option>
                        <option value="WETH/DAI">WETH/DAI</option>
                        <option value="WETH/WBTC">WETH/WBTC</option>
                    </select>
                </div>
                <div class="filter-item">
                    <label for="filter-dex">DEX:</label>
                    <select id="filter-dex" onchange="filterOpportunities()">
                        <option value="">All DEXes</option>
                        <option value="uniswapv2">Uniswap V2</option>
                        <option value="uniswapv3">Uniswap V3</option>
                        <option value="sushiswap">Sushiswap</option>
                        <option value="pancakeswapv2">PancakeSwap</option>
                        <option value="dodo">DODO</option>
                    </select>
                </div>
                <div class="filter-item">
                    <label for="filter-profit">Min Profit ($):</label>
                    <input type="number" id="filter-profit" min="0" step="0.01" value="0" onchange="filterOpportunities()">
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
                        <tr><td colspan="10" class="loading">Loading opportunity data...</td></tr>
                    </tbody>
                </table>
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
        
        <div id="wallet-tab" class="tab-content">
            <h2>Wallet Activity Monitor</h2>
            
            <div class="wallet-stats-container">
                <div class="wallet-overview">
                    <div class="wallet-address">
                        <strong>Address:</strong> <span id="wallet-address">Loading...</span>
                    </div>
                    <div class="wallet-balance">
                        <h3>Balances</h3>
                        <div class="balance-eth">
                            <strong>ETH:</strong> <span id="eth-balance">Loading...</span>
                        </div>
                        <div class="token-balances" id="token-balances">
                            <div class="loading">Loading token balances...</div>
                        </div>
                    </div>
                </div>
                
                <div class="gas-usage">
                    <h3>Gas Usage Statistics</h3>
                    <div class="gas-stats-grid">
                        <div class="gas-stat-item">
                            <div class="gas-stat-title">Total Gas Spent</div>
                            <div class="gas-stat-value" id="total-gas">Loading...</div>
                        </div>
                        <div class="gas-stat-item">
                            <div class="gas-stat-title">Last 24 Hours</div>
                            <div class="gas-stat-value" id="gas-24h">Loading...</div>
                        </div>
                        <div class="gas-stat-item">
                            <div class="gas-stat-title">Last 7 Days</div>
                            <div class="gas-stat-value" id="gas-7d">Loading...</div>
                        </div>
                        <div class="gas-stat-item">
                            <div class="gas-stat-title">Average Per Tx</div>
                            <div class="gas-stat-value" id="avg-gas">Loading...</div>
                        </div>
                    </div>
                </div>
                
                <div class="recent-transactions">
                    <h3>Recent Transactions</h3>
                    <div class="transaction-list" id="transaction-list">
                        <div class="loading">Loading transactions...</div>
                    </div>
                </div>
                
                <div class="wallet-update-time">
                    Last updated: <span id="wallet-update-time">Loading...</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Enhanced Arbitrage Dashboard | Auto-refreshes data every 10 seconds</p>
    </div>
</body>
</html>
"""
    
    def _generate_token_prices_html(self, prices):
        """Generate HTML for token prices section."""
        if not prices:
            return '<div class="loading">Loading price data...</div>'
        
        token_prices_html = ""
        
        # Group tokens by DEX
        for dex_name in EXCHANGES:
            token_prices_html += f"""
            <div class="dex-column">
                <div class="dex-header">{self._format_dex_name(dex_name)}</div>
                <div class="price-cards">
            """
            
            # Add price cards for each token
            for token in TOKENS:
                symbol = token['symbol']
                if symbol in prices:
                    token_data = prices[symbol]
                    name = token_data.get('name', symbol)
                    
                    # Check if this DEX has price for this token
                    price = 0
                    if 'exchanges' in token_data and dex_name in token_data['exchanges']:
                        price = token_data['exchanges'][dex_name].get('price', 0)
                    
                    # Skip tokens with zero price
                    if price == 0:
                        continue
                    
                    token_prices_html += f"""
                    <div class="price-card">
                        <div class="token-pair">{symbol}/USD</div>
                        <div class="price-value">${price:,.2f}</div>
                    </div>
                    """
            
            token_prices_html += """
                </div>
            </div>
            """
        
        return token_prices_html
    
    def _format_dex_name(self, dex_name):
        """Format DEX name for display."""
        return self._get_formatted_dex_name(dex_name)
    
    def _get_simulation_indicator(self):
        """Get simulation mode indicator if simulation mode is active."""
        return '<span class="simulation-badge">SIMULATION MODE</span>' if global_cache.use_simulated_data else ''
    
    def _get_formatted_dex_name(self, dex_name):
        """Format DEX name for display."""
        if dex_name.lower() == 'uniswapv2':
            return 'Uniswap V2'
        elif dex_name.lower() == 'uniswapv3':
            return 'Uniswap V3'
        elif dex_name.lower() == 'pancakeswapv2':
            return 'PancakeSwap'
        elif dex_name.lower() == 'dodo':
            return 'DODO'
        else:
            return dex_name.replace('_', ' ').title()
    
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
            padding: 30px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
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
        
        .simulation-badge {
            margin-left: 15px;
            background-color: #f72585;
            color: white;
            font-size: 0.8em;
            padding: 3px 8px;
            border-radius: 3px;
            font-weight: bold;
        }
        
        .simulation-warning {
            background-color: rgba(247, 37, 133, 0.1);
            border-left: 4px solid #f72585;
            color: #333;
            font-weight: 500;
            margin: 10px 0;
            padding: 10px 20px;
        }
        
        .warning-container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 30px auto;
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
        
        /* Token prices section */
        .token-prices {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .dex-column {
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }
        
        .dex-header {
            background-color: var(--secondary-color);
            color: white;
            padding: 15px;
            font-size: 1.2em;
            font-weight: bold;
            text-align: center;
        }
        
        .price-cards {
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .price-card {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .token-pair {
            font-weight: bold;
            color: var(--secondary-color);
            margin-bottom: 5px;
        }
        
        .price-value {
            font-size: 1.2em;
            color: var(--accent-color);
        }
        
        /* Wallet styles */
        .wallet-stats-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .wallet-overview {
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            padding: 20px;
        }
        
        .wallet-address {
            margin-bottom: 15px;
            font-family: monospace;
            word-break: break-all;
        }
        
        .wallet-balance h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: var(--primary-color);
            font-size: 1.2em;
        }
        
        .balance-eth {
            font-size: 1.2em;
            margin-bottom: 10px;
        }
        
        .token-balances {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        
        .token-balance-item {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .gas-usage {
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            padding: 20px;
        }
        
        .gas-usage h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: var(--primary-color);
            font-size: 1.2em;
        }
        
        .gas-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .gas-stat-item {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            text-align: center;
        }
        
        .gas-stat-title {
            color: var(--light-text);
            font-size: 0.9em;
            margin-bottom: 8px;
        }
        
        .gas-stat-value {
            font-size: 1.4em;
            font-weight: bold;
            color: var(--accent-color);
        }
        
        .recent-transactions {
            background-color: var(--card-background);
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            padding: 20px;
            overflow: hidden;
        }
        
        .recent-transactions h3 {
            margin-top: 0;
            margin-bottom: 15px;
            color: var(--primary-color);
            font-size: 1.2em;
        }
        
        .transaction-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .transaction-item {
            border-bottom: 1px solid var(--border-color);
            padding: 12px 0;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: space-between;
        }
        
        .tx-hash {
            font-family: monospace;
            flex-basis: 100%;
            word-break: break-all;
            font-size: 0.9em;
            color: var(--light-text);
        }
        
        .tx-value, .tx-gas, .tx-time {
            flex: 1;
            min-width: 100px;
        }
        
        .tx-method {
            flex: 1;
            min-width: 100px;
            font-weight: 500;
        }
        
        .tx-type-in {
            color: var(--positive-color);
        }
        
        .tx-type-out {
            color: var(--accent-color);
        }
        
        .wallet-update-time {
            text-align: right;
            font-size: 0.9em;
            color: var(--light-text);
            margin-top: 15px;
        }
        
        .token-name {
            flex: 1;
            color: var(--light-text);
            font-size: 1.1em;
        }
        
        .token-price {
            font-size: 1.8em;
            font-weight: bold;
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
        }
        """
    
    def get_js(self):
        """Get JavaScript for the dashboard.""" 
        return """
        // Auto-refresh the data every 5 seconds
        setInterval(function() {
            refreshPrices();
            
            // Update wallet data every 15 seconds
            if (document.getElementById('wallet-tab').classList.contains('active')) {
                refreshWalletData();
            }
            
            // Update opportunity data every 5 seconds
            refreshOpportunities();
            
            // Check if simulation warning should be shown
            checkSimulationStatus();
        }, 5000);
        
        // Slower refresh for wallet data (15 seconds)
        setInterval(function() {
            // Only update wallet data if the tab is active
            if (document.getElementById('wallet-tab').classList.contains('active')) {
                refreshWalletData();
            }
        }, 15000);
        
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
            
            // Load wallet data when switching to wallet tab
            if (tabName === 'wallet-tab') {
                refreshWalletData();
            }
        }
        
        // Fetch and update wallet data
        function refreshWalletData() {
            fetch('/api/wallet')
                .then(response => response.json())
                .then(data => {
                    // Update wallet address
                    document.getElementById('wallet-address').textContent = data.address || 'Not available';
                    
                    // Update ETH balance
                    document.getElementById('eth-balance').textContent = 
                        (data.balance && data.balance.eth) ? `${data.balance.eth.toFixed(4)} ETH` : '0 ETH';
                    
                    // Update token balances
                    const tokenBalancesEl = document.getElementById('token-balances');
                    let tokenHtml = '';
                    if (data.balance && data.balance.tokens) {
                        for (const [symbol, amount] of Object.entries(data.balance.tokens)) {
                            tokenHtml += `<div class="token-balance-item"><strong>${symbol}:</strong> ${amount.toFixed(4)}</div>`;
                        }
                    }
                    tokenBalancesEl.innerHTML = tokenHtml || '<div class="empty-message">No token balances found</div>';
                    
                    // Update gas stats
                    if (data.gas) {
                        document.getElementById('total-gas').textContent = `${data.gas.total_eth.toFixed(4)} ETH ($${data.gas.total_usd.toFixed(2)})`;
                        document.getElementById('gas-24h').textContent = `${data.gas.last_24h.toFixed(4)} ETH`;
                        document.getElementById('gas-7d').textContent = `${data.gas.last_7d.toFixed(4)} ETH`;
                        document.getElementById('avg-gas').textContent = `${data.gas.average_per_tx.toFixed(4)} ETH`;
                    }
                    
                    // Update transactions
                    updateTransactionList(data.transactions?.recent || []);
                    
                    // Update last update time
                    document.getElementById('wallet-update-time').textContent = data.last_update ? new Date(data.last_update).toLocaleTimeString() : 'Never';
                });
        }
        
        // Fetch and update token prices
        function refreshPrices() {
            fetch('/api/prices')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('last-updated').textContent = data.last_updated || 'Loading...';
                });
        }
        
        // Update transaction list
        function updateTransactionList(transactions) {
            const txListEl = document.getElementById('transaction-list');
            if (!transactions || transactions.length === 0) {
                txListEl.innerHTML = '<div class="empty-message">No transactions found</div>';
                return;
            }
            
            let txHtml = '';
            transactions.forEach(tx => {
                const txTime = new Date(tx.timestamp).toLocaleTimeString();
                const txDate = new Date(tx.timestamp).toLocaleDateString();
                const directionClass = tx.type === 'in' ? 'tx-type-in' : 'tx-type-out';
                const direction = tx.type === 'in' ? '⬇️ Received' : '⬆️ Sent';
                
                txHtml += `
                <div class="transaction-item">
                    <div class="tx-hash">${tx.hash}</div>
                    <div class="tx-time">${txDate} ${txTime}</div>
                    <div class="tx-method ${directionClass}">${direction} - ${tx.method}</div>
                    <div class="tx-value">${tx.value.toFixed(4)} ETH</div>
                    <div class="tx-gas">Gas: ${tx.gas_fee_eth.toFixed(4)} ETH</div>
                </div>`;
            });
            txListEl.innerHTML = txHtml;
        }
        
        // Check if we're in simulation mode and update UI
        function checkSimulationStatus() {
            fetch('/api/prices')
                .then(response => response.json())
                .then(data => {
                    // Check if simulation mode is active and show/hide warning
                    const isSimulation = data.simulation_mode === true;
                    const warningEl = document.getElementById('simulation-warning');
                    if (warningEl) warningEl.style.display = isSimulation ? 'block' : 'none';
                });
        }
        
        // Fetch and update opportunity data
        function refreshOpportunities() {
            // Get filter values
            const pair = document.getElementById('filter-pair').value;
            const dex = document.getElementById('filter-dex').value;
            const minProfit = document.getElementById('filter-profit').value;
            const limit = document.getElementById('filter-limit').value;
            
            // Build API URL with filters
            let url = `/api/opportunities/filter?limit=${limit}`;
            if (pair) url += `&pair=${pair}`;
            if (dex) url += `&dex=${dex}`;
            if (minProfit) url += `&min_profit=${minProfit}`;
            
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    updateOpportunityTable(data.opportunities);
                    updateStats(data.stats);
                });
        }
        
        // Update opportunity table with data
        function updateOpportunityTable(opportunities) {
            const tableBody = document.getElementById('opportunity-rows');
            
            // Clear existing rows
            tableBody.innerHTML = '';
            
            if (!opportunities || opportunities.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="10" class="loading">No opportunities found with current filters</td></tr>';
                return;
            }

            // Add each opportunity as a row
            opportunities.forEach(opp => {
                const timestamp = new Date(opp.timestamp).toLocaleTimeString();
                const netProfit = opp.net_profit_usd || 0;
                const profitClass = netProfit > 0 ? 'positive' : (netProfit < 0 ? 'negative' : '');
                const statusClass = opp.executed ? 'status-executed' : 'status-skipped';
                const statusText = opp.executed ? 'Executed' : 'Skipped';
                
                tableBody.innerHTML += `
                <tr>
                    <td>${timestamp}</td>
                    <td>${opp.pair}</td>
                    <td>${formatDexName(opp.source_dex)}</td>
                    <td>${formatDexName(opp.target_dex)}</td>
                    <td>${opp.price_diff_pct ? opp.price_diff_pct.toFixed(2) + '%' : 'N/A'}</td>
                    <td>${opp.amount ? opp.amount.toFixed(4) : 'N/A'}</td>
                    <td class="${profitClass}">$${opp.profit_usd ? opp.profit_usd.toFixed(4) : '0.00'}</td>
                    <td>$${opp.gas_cost_usd ? opp.gas_cost_usd.toFixed(4) : '0.00'}</td>
                    <td class="${profitClass}">$${netProfit.toFixed(4)}</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
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
            const lastUpdate = stats.last_update ? new Date(stats.last_update) : new Date();
            document.getElementById('refresh-time').textContent = lastUpdate.toLocaleTimeString();
            
            // Update pair and DEX statistics - these would be added in the future
            document.getElementById('pair-stats').innerHTML = '<p>Detailed pair statistics coming soon</p>';
            document.getElementById('dex-stats').innerHTML = '<p>Detailed DEX statistics coming soon</p>';
        }
        
        // Format DEX name for display
        function formatDexName(dexName) {
            if (!dexName) return 'Unknown';

            if (dexName.toLowerCase() === 'uniswapv2') return 'Uniswap V2';
            if (dexName.toLowerCase() === 'uniswapv3') return 'Uniswap V3';
            if (dexName.toLowerCase() === 'pancakeswapv2') return 'PancakeSwap';
            if (dexName.toLowerCase() === 'dodo') return 'DODO';
            
            return dexName.replace('_', ' ').replace(/\\b\\w/g, c => c.toUpperCase());
        }
        
        // Filter opportunities with current filter settings
        function filterOpportunities() { 
            refreshOpportunities();
        }
        
        // Load initial data when page loads
        document.addEventListener('DOMContentLoaded', function() {
            // Check simulation status immediately
            setTimeout(function() {
                checkSimulationStatus();
            }, 500);
            
            // Load initial data
            refreshPrices();
            refreshOpportunities();
            refreshWalletData();
        });
        """

async def start_server():
    """Start the HTTP server and price update job."""
    # Set up logging
    setup_logging()
    
    # Start the price update job
    asyncio.create_task(price_update_job())
    
    # Start the HTTP server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, EnhancedArbitrageDashboardHandler)
    
    print(f"Starting Enhanced Arbitrage Dashboard on port {PORT}...")
    print(f"Open this URL in your browser: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    
    # Run the server in a separate thread
    import threading
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Keep the main thread running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Server stopped.")
        httpd.shutdown()

def run_server():
    """Run the server."""
    asyncio.run(start_server())

if __name__ == "__main__":
    run_server()