gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttttdttttttttttd"""
Arbitrage Bot Dashboard

A complete dashboard showing real-time arbitrage bot data including logs,
configuration, and status information.
"""

import os
import sys
import time
import json
import socket
import glob
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Dashboard configuration
PORT = 9095  # Using a different port to avoid conflicts
LOGS_DIR = Path("logs")
CONFIG_DIR = Path("configs")
ANALYTICS_DIR = Path("analytics")

class ArbitrageDashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler for the arbitrage dashboard."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_dashboard().encode())
            return
        elif self.path == "/logs":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_logs_page().encode())
            return
        elif self.path == "/config":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_config_page().encode())
            return
        elif self.path == "/analytics":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_analytics_page().encode())
            return
        elif self.path == "/style.css":
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            self.wfile.write(self.get_css().encode())
            return
        elif self.path == "/dashboard.js":
            self.send_response(200)
            self.send_header("Content-type", "application/javascript")
            self.end_headers()
            self.wfile.write(self.get_javascript().encode())
            return
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.get_status_data()).encode())
            return
        
        # For all other paths, use the default handler
        return super().do_GET()
    
    def generate_dashboard(self):
        """Generate the main dashboard HTML."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot Dashboard</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>Arbitrage Dashboard</h2>
        </div>
        <nav class="sidebar-nav">
            <a href="/" class="active">Overview</a>
            <a href="/logs">Logs</a>
            <a href="/config">Configuration</a>
            <a href="/analytics">Analytics</a>
        </nav>
        <div class="sidebar-footer">
            <p>Version 1.0</p>
        </div>
    </div>
    
    <div class="content">
        <header>
            <h1>Arbitrage Bot Overview</h1>
            <div class="header-info">
                <span>Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                <span>Host: {socket.gethostname()}</span>
            </div>
        </header>
        
        <div class="dashboard-grid">
            <div class="dashboard-card">
                <div class="card-header">System Status</div>
                <div class="card-body">
                    <div class="status-indicator online">
                        <span class="dot"></span> Dashboard Online
                    </div>
                    <p><strong>Log Files:</strong> {self.count_log_files()} found</p>
                    <p><strong>Config Files:</strong> {self.count_config_files()} found</p>
                    <p><strong>Uptime:</strong> {self.calculate_uptime()}</p>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">Latest Log Activity</div>
                <div class="card-body log-preview">
                    {self.get_latest_logs_preview()}
                </div>
                <div class="card-footer">
                    <a href="/logs" class="view-more">View All Logs →</a>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">MEV Protection Status</div>
                <div class="card-body">
                    {self.get_mev_protection_status()}
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">Configuration Summary</div>
                <div class="card-body">
                    {self.get_config_summary()}
                </div>
                <div class="card-footer">
                    <a href="/config" class="view-more">View Full Configuration →</a>
                </div>
            </div>
        </div>
        
        <footer>
            <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
        </footer>
    </div>
    
    <script src="/dashboard.js"></script>
</body>
</html>"""
    
    def generate_logs_page(self):
        """Generate the logs page HTML."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot Logs</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>Arbitrage Dashboard</h2>
        </div>
        <nav class="sidebar-nav">
            <a href="/">Overview</a>
            <a href="/logs" class="active">Logs</a>
            <a href="/config">Configuration</a>
            <a href="/analytics">Analytics</a>
        </nav>
        <div class="sidebar-footer">
            <p>Version 1.0</p>
        </div>
    </div>
    
    <div class="content">
        <header>
            <h1>Arbitrage Bot Logs</h1>
            <div class="header-info">
                <span>Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                <span>Host: {socket.gethostname()}</span>
            </div>
        </header>
        
        <div class="logs-container">
            {self.get_detailed_logs()}
        </div>
        
        <footer>
            <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
        </footer>
    </div>
    
    <script src="/dashboard.js"></script>
</body>
</html>"""
    
    def generate_config_page(self):
        """Generate the configuration page HTML."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot Configuration</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>Arbitrage Dashboard</h2>
        </div>
        <nav class="sidebar-nav">
            <a href="/">Overview</a>
            <a href="/logs">Logs</a>
            <a href="/config" class="active">Configuration</a>
            <a href="/analytics">Analytics</a>
        </nav>
        <div class="sidebar-footer">
            <p>Version 1.0</p>
        </div>
    </div>
    
    <div class="content">
        <header>
            <h1>Arbitrage Bot Configuration</h1>
            <div class="header-info">
                <span>Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                <span>Host: {socket.gethostname()}</span>
            </div>
        </header>
        
        <div class="config-container">
            {self.get_detailed_config()}
        </div>
        
        <footer>
            <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
        </footer>
    </div>
    
    <script src="/dashboard.js"></script>
</body>
</html>"""
    
    def generate_analytics_page(self):
        """Generate the analytics page HTML."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot Analytics</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h2>Arbitrage Dashboard</h2>
        </div>
        <nav class="sidebar-nav">
            <a href="/">Overview</a>
            <a href="/logs">Logs</a>
            <a href="/config">Configuration</a>
            <a href="/analytics" class="active">Analytics</a>
        </nav>
        <div class="sidebar-footer">
            <p>Version 1.0</p>
        </div>
    </div>
    
    <div class="content">
        <header>
            <h1>Arbitrage Bot Analytics</h1>
            <div class="header-info">
                <span>Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                <span>Host: {socket.gethostname()}</span>
            </div>
        </header>
        
        <div class="analytics-container">
            {self.get_analytics_data()}
        </div>
        
        <footer>
            <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
        </footer>
    </div>
    
    <script src="/dashboard.js"></script>
</body>
</html>"""
    
    def count_log_files(self):
        """Count the number of log files in the logs directory."""
        if not LOGS_DIR.exists():
            return 0
        
        return len(list(LOGS_DIR.glob("*.log")))
    
    def count_config_files(self):
        """Count the number of configuration files in the configs directory."""
        if not CONFIG_DIR.exists():
            return 0
        
        return len(list(CONFIG_DIR.glob("*.json")))
    
    def calculate_uptime(self):
        """Calculate mock uptime for the dashboard."""
        uptime_seconds = int(time.time()) % 86400  # Just for display purposes
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    def get_latest_logs_preview(self):
        """Get a preview of the latest log entries."""
        if not LOGS_DIR.exists():
            return "<p>No logs directory found.</p>"
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<p>No log files found.</p>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        latest_file = log_files[0]
        
        html = f"<p class='log-file-name'>{latest_file.name}</p>"
        
        try:
            with open(latest_file, "r", errors="replace") as f:
                lines = f.readlines()
                last_lines = lines[-5:] if len(lines) > 5 else lines
                
                for line in last_lines:
                    line = line.replace("<", "&lt;").replace(">", "&gt;")
                    
                    # Apply some basic styling
                    if "ERROR" in line.upper():
                        html += f"<div class='log-line error'>{line}</div>"
                    elif "WARN" in line.upper():
                        html += f"<div class='log-line warning'>{line}</div>"
                    elif "INFO" in line.upper():
                        html += f"<div class='log-line info'>{line}</div>"
                    else:
                        html += f"<div class='log-line'>{line}</div>"
        
        except Exception as e:
            html += f"<p class='error'>Error reading log file: {e}</p>"
        
        return html
    
    def get_mev_protection_status(self):
        """Get the status of MEV protection based on log analysis."""
        if not LOGS_DIR.exists():
            return "<p>No logs directory found.</p>"
        
        # Look for MEV-related log entries
        mev_low_count = 0
        mev_high_count = 0
        mev_files_checked = 0
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<p>No log files found.</p>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Check the 3 most recent files
        for log_file in log_files[:3]:
            try:
                with open(log_file, "r", errors="replace") as f:
                    content = f.read()
                    mev_low_count += content.count("MEV risk level: low")
                    mev_high_count += content.count("MEV risk level: high")
                mev_files_checked += 1
            except:
                pass
        
        # Determine status based on counts
        if mev_files_checked == 0:
            return "<p>No data available for MEV protection.</p>"
        
        total_mev_entries = mev_low_count + mev_high_count
        if total_mev_entries == 0:
            return "<p>No MEV protection data found in logs.</p>"
        
        low_percentage = (mev_low_count / total_mev_entries) * 100 if total_mev_entries > 0 else 0
        
        html = "<div class='mev-stats'>"
        html += f"<div class='stat-item'><span class='stat-label'>Total MEV Events:</span> <span class='stat-value'>{total_mev_entries}</span></div>"
        html += f"<div class='stat-item'><span class='stat-label'>Low Risk:</span> <span class='stat-value'>{mev_low_count}</span></div>"
        html += f"<div class='stat-item'><span class='stat-label'>High Risk:</span> <span class='stat-value'>{mev_high_count}</span></div>"
        html += "</div>"
        
        # Add status indicator
        if low_percentage >= 70:
            status_class = "good"
            status_text = "Good"
        elif low_percentage >= 50:
            status_class = "moderate"
            status_text = "Moderate"
        else:
            status_class = "poor"
            status_text = "Poor"
        
        html += f"<div class='status-badge {status_class}'>{status_text}</div>"
        html += f"<p>MEV Protection is active and handling {total_mev_entries} events.</p>"
        
        return html
    
    def get_config_summary(self):
        """Get a summary of the configuration."""
        if not CONFIG_DIR.exists():
            return "<p>No configuration directory found.</p>"
        
        config_files = list(CONFIG_DIR.glob("*.json"))
        if not config_files:
            return "<p>No configuration files found.</p>"
        
        # Look for main config file
        main_config = None
        for config_file in config_files:
            if config_file.name == "config.json":
                main_config = config_file
                break
        
        if not main_config:
            # Use the first file found
            main_config = config_files[0]
        
        html = f"<p><strong>Active Configuration:</strong> {main_config.name}</p>"
        
        # Extract some key configuration details
        try:
            with open(main_config, "r") as f:
                config = json.load(f)
                
                # Create a summary table
                html += "<table class='config-summary'>"
                
                # Network configuration
                if isinstance(config, dict):
                    # DEX settings (if available)
                    if "dexes" in config:
                        dexes = config["dexes"]
                        if isinstance(dexes, dict):
                            enabled_dexes = []
                            for dex_name, dex_config in dexes.items():
                                if isinstance(dex_config, dict) and dex_config.get("enabled", False):
                                    enabled_dexes.append(dex_name)
                            
                            html += "<tr>"
                            html += "<td><strong>DEXes Enabled</strong></td>"
                            html += f"<td>{len(enabled_dexes)}</td>"
                            html += "</tr>"
                    
                    # Check for flashloan configuration
                    if "flashloan" in config:
                        flashloan_status = "Configured"
                        html += "<tr>"
                        html += "<td><strong>Flash Loan</strong></td>"
                        html += f"<td>{flashloan_status}</td>"
                        html += "</tr>"
                    
                    # Check for network configuration
                    if "network" in config:
                        network_name = "Configured"
                        if isinstance(config["network"], dict) and "name" in config["network"]:
                            network_name = config["network"]["name"]
                        
                        html += "<tr>"
                        html += "<td><strong>Network</strong></td>"
                        html += f"<td>{network_name}</td>"
                        html += "</tr>"
                    
                    # Check for gas settings
                    if "gas" in config:
                        gas_status = "Configured"
                        html += "<tr>"
                        html += "<td><strong>Gas Settings</strong></td>"
                        html += f"<td>{gas_status}</td>"
                        html += "</tr>"
                
                html += "</table>"
        
        except Exception as e:
            html += f"<p class='error'>Error reading configuration: {e}</p>"
        
        return html
    
    def get_detailed_logs(self):
        """Get detailed log content for the logs page."""
        if not LOGS_DIR.exists():
            return "<p>No logs directory found.</p>"
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<p>No log files found.</p>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        html = ""
        
        # Display the 10 most recent log files
        for log_file in log_files[:10]:
            file_size_kb = log_file.stat().st_size / 1024
            modified_time = datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            html += f"""
            <div class='log-file-card'>
                <div class='log-file-header'>
                    <h3>{log_file.name}</h3>
                    <div class='log-file-meta'>
                        <span>Modified: {modified_time}</span>
                        <span>Size: {file_size_kb:.2f} KB</span>
                    </div>
                </div>
                <div class='log-file-content'>
            """
            
            # Read the last 20 lines
            try:
                with open(log_file, "r", errors="replace") as f:
                    lines = f.readlines()
                    last_lines = lines[-20:] if len(lines) > 20 else lines
                    
                    for line in last_lines:
                        line = line.replace("<", "&lt;").replace(">", "&gt;")
                        
                        # Apply some basic styling
                        if "ERROR" in line.upper():
                            html += f"<div class='log-line error'>{line}</div>"
                        elif "WARN" in line.upper():
                            html += f"<div class='log-line warning'>{line}</div>"
                        elif "INFO" in line.upper():
                            html += f"<div class='log-line info'>{line}</div>"
                        else:
                            html += f"<div class='log-line'>{line}</div>"
            
            except Exception as e:
                html += f"<p class='error'>Error reading log file: {e}</p>"
            
            html += """
                </div>
            </div>
            """
        
        return html
    
    def get_detailed_config(self):
        """Get detailed configuration content for the config page."""
        if not CONFIG_DIR.exists():
            return "<p>No configuration directory found.</p>"
        
        config_files = list(CONFIG_DIR.glob("*.json"))
        if not config_files:
            return "<p>No configuration files found.</p>"
        
        # Sort alphabetically
        config_files.sort(key=lambda x: x.name)
        
        html = ""
        
        for config_file in config_files:
            file_size_kb = config_file.stat().st_size / 1024
            modified_time = datetime.fromtimestamp(config_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            html += f"""
            <div class='config-file-card'>
                <div class='config-file-header'>
                    <h3>{config_file.name}</h3>
                    <div class='config-file-meta'>
                        <span>Modified: {modified_time}</span>
                        <span>Size: {file_size_kb:.2f} KB</span>
                    </div>
                </div>
                <div class='config-file-content'>
            """
            
            # Read and pretty print the config file
            try:
                with open(config_file, "r") as f:
                    config_text = f.read()
                    
                    # Try to parse and pretty-print if it's valid JSON
                    try:
                        config_data = json.loads(config_text)
                        
                        # Mask sensitive values
                        if isinstance(config_data, dict):
                            # Mask API keys or private keys if present
                            for key in config_data:
                                if any(sensitive in key.lower() for sensitive in ["key", "secret", "password", "token", "private"]):
                                    config_data[key] = "*** MASKED ***"
                                    
                            # If there's a nested object, check for sensitive values
                            for key, value in config_data.items():
                                if isinstance(value, dict):
                                    for subkey in value:
                                        if any(sensitive in subkey.lower() for sensitive in ["key", "secret", "password", "token", "private"]):
                                            config_data[key][subkey] = "*** MASKED ***"
                        
                        pretty_config = json.dumps(config_data, indent=2)
                        
                        # Escape HTML characters
                        pretty_config = pretty_config.replace("<", "&lt;").replace(">", "&gt;")
                        html += f"<pre>{pretty_config}</pre>"
                    except json.JSONDecodeError:
                        # If not valid JSON, just display as is
                        config_text = config_text.replace("<", "&lt;").replace(">", "&gt;")
                        html += f"<pre>{config_text}</pre>"
            
            except Exception as e:
                html += f"<p class='error'>Error reading configuration file: {e}</p>"
            
            html += """
                </div>
            </div>
            """
        
        return html
    
    def get_analytics_data(self):
        """Get analytics data if available."""
        if not ANALYTICS_DIR.exists():
            return "<p>No analytics directory found.</p>"
        
        analytics_files = list(ANALYTICS_DIR.glob("*.json"))
        if not analytics_files:
            return "<p>No analytics data found.</p>"
        
        # Sort by modification time (newest first)
        analytics_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        html = ""
        
        # Check for gas reports
        gas_reports = [f for f in analytics_files if "gas" in f.name.lower()]
        if gas_reports:
            html += "<div class='analytics-section'>"
            html += "<h2>Gas Usage Reports</h2>"
            
            for report in gas_reports[:3]:  # Show the 3 most recent reports
                file_size_kb = report.stat().st_size / 1024
                modified_time = datetime.fromtimestamp(report.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                html += f"""
                <div class='analytics-card'>
                    <div class='analytics-header'>
                        <h3>{report.name}</h3>
                        <div class='analytics-meta'>
                            <span>Modified: {modified_time}</span>
                            <span>Size: {file_size_kb:.2f} KB</span>
                        </div>
                    </div>
                    <div class='analytics-content'>
                """
                
                # Read and display the report
                try:
                    with open(report, "r") as f:
                        data = json.load(f)
                        
                        if isinstance(data, dict):
                            html += "<table class='analytics-table'>"
                            html += "<tr><th>Metric</th><th>Value</th></tr>"
                            
                            for key, value in data.items():
                                if not isinstance(value, (dict, list)):
                                    html += f"<tr><td>{key}</td><td>{value}</td></tr>"
                            
                            html += "</table>"
                            
                            # If there's a summary or avg_gas_price field, highlight it
                            if "avg_gas_price" in data:
                                html += f"<p class='highlight'>Average Gas Price: {data['avg_gas_price']} Gwei</p>"
                            if "total_gas_used" in data:
                                html += f"<p class='highlight'>Total Gas Used: {data['total_gas_used']}</p>"
                        else:
                            html += "<p>Invalid data format</p>"
                
                except Exception as e:
                    html += f"<p class='error'>Error reading analytics file: {e}</p>"
                
                html += """
                    </div>
                </div>
                """
            
            html += "</div>"
        
        # Check for performance reports
        performance_reports = [f for f in analytics_files if "performance" in f.name.lower()]
        if performance_reports:
            html += "<div class='analytics-section'>"
            html += "<h2>Performance Reports</h2>"
            
            for report in performance_reports[:3]:  # Show the 3 most recent reports
                file_size_kb = report.stat().st_size / 1024
                modified_time = datetime.fromtimestamp(report.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                html += f"""
                <div class='analytics-card'>
                    <div class='analytics-header'>
                        <h3>{report.name}</h3>
                        <div class='analytics-meta'>
                            <span>Modified: {modified_time}</span>
                            <span>Size: {file_size_kb:.2f} KB</span>
                        </div>
                    </div>
                    <div class='analytics-content'>
                """
                
                # Read and display the report
                try:
                    with open(report, "r") as f:
                        data = json.load(f)
                        
                        if isinstance(data, dict):
                            html += "<table class='analytics-table'>"
                            html += "<tr><th>Metric</th><th>Value</th></tr>"
                            
                            for key, value in data.items():
                                if not isinstance(value, (dict, list)):
                                    html += f"<tr><td>{key}</td><td>{value}</td></tr>"
                            
                            html += "</table>"
                            
                            # If there's a summary or profit field, highlight it
                            if "profit" in data:
                                html += f"<p class='highlight'>Profit: {data['profit']}</p>"
                            if "transactions_count" in data:
                                html += f"<p class='highlight'>Transaction Count: {data['transactions_count']}</p>"
                        else:
                            html += "<p>Invalid data format</p>"
                
                except Exception as e:
                    html += f"<p class='error'>Error reading analytics file: {e}</p>"
                
                html += """
                    </div>
                </div>
                """
            
            html += "</div>"
        
        # If no specific reports found
        if not gas_reports and not performance_reports:
            html += "<p>No specific analytics reports found.</p>"
            
            # Just show the available files
            html += "<div class='analytics-section'>"
            html += "<h2>Available Analytics Files</h2>"
            html += "<ul>"
            
            for file in analytics_files:
                modified_time = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                html += f"<li>{file.name} (Modified: {modified_time})</li>"
            
            html += "</ul>"
            html += "</div>"
        
        return html
    
    def get_status_data(self):
        """Get status data for API endpoint."""
        return {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "log_files_count": self.count_log_files(),
            "config_files_count": self.count_config_files(),
            "host": socket.gethostname(),
            "uptime": self.calculate_uptime()
        }
    
    def get_css(self):
        """Get the CSS for the dashboard."""
        return """
        :root {
            --primary-color: #4a6fdc;
            --secondary-color: #6c757d;
            --success-color: #28a745;
            --danger-color: #dc3545;
            --warning-color: #ffc107;
            --info-color: #17a2b8;
            --light-color: #f8f9fa;
            --dark-color: #343a40;
            --sidebar-width: 250px;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            display: flex;
            min-height: 100vh;
            color: #333;
        }
        
        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width);
            background-color: #2c3e50;
            color: white;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        .sidebar-header {
            padding: 20px;
            background-color: rgba(0, 0, 0, 0.2);
        }
        
        .sidebar-header h2 {
            font-size: 1.5rem;
            margin: 0;
        }
        
        .sidebar-nav {
            flex: 1;
            padding: 20px 0;
        }
        
        .sidebar-nav a {
            display: block;
            padding: 12px 20px;
            color: #ddd;
            text-decoration: none;
            font-size: 1.1rem;
            transition: background-color 0.2s;
        }
        
        .sidebar-nav a:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        .sidebar-nav a.active {
            background-color: rgba(255, 255, 255, 0.2);
            color: white;
            font-weight: bold;
            border-left: 4px solid var(--primary-color);
        }
        
        .sidebar-footer {
            padding: 15px 20px;
            background-color: rgba(0, 0, 0, 0.2);
            font-size: 0.9rem;
            text-align: center;
        }
        
        /* Main Content */
        .content {
            flex: 1;
            margin-left: var(--sidebar-width);
            padding: 20px;
            width: calc(100% - var(--sidebar-width));
        }
        
        header {
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 15px;
        }
        
        header h1 {
            color: var(--primary-color);
            margin-bottom: 10px;
        }
        
        .header-info {
            display: flex;
            justify-content: space-between;
            color: var(--secondary-color);
            font-size: 0.9rem;
        }
        
        /* Dashboard Grid */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .dashboard-card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .card-header {
            background-color: #f0f0f0;
            padding: 15px;
            font-weight: bold;
            border-bottom: 1px solid #ddd;
            font-size: 1.1rem;
        }
        
        .card-body {
            padding: 20px;
        }
        
        .card-footer {
            padding: 10px 15px;
            background-color: #f8f8f8;
            border-top: 1px solid #ddd;
            text-align: right;
        }
        
        .view-more {
            color: var(--primary-color);
            text-decoration: none;
            font-weight: bold;
        }
        
        /* Status Indicator */
        .status-indicator {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        
        .status-indicator .dot {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        .status-indicator.online {
            background-color: rgba(40, 167, 69, 0.1);
            color: var(--success-color);
        }
        
        .status-indicator.online .dot {
            background-color: var(--success-color);
        }
        
        .status-indicator.offline {
            background-color: rgba(220, 53, 69, 0.1);
            color: var(--danger-color);
        }
        
        .status-indicator.offline .dot {
            background-color: var(--danger-color);
        }
        
        /* Log Preview */
        .log-preview {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .log-file-name {
            font-weight: bold;
            margin-bottom: 10px;
            color: var(--dark-color);
        }
        
        .log-line {
            font-family: 'Courier New', Courier, monospace;
            white-space: pre-wrap;
            word-break: break-all;
            margin-bottom: 5px;
            padding: 2px 5px;
            font-size: 0.85rem;
        }
        
        .log-line.error {
            color: var(--danger-color);
            background-color: rgba(220, 53, 69, 0.1);
        }
        
        .log-line.warning {
            color: var(--warning-color);
            background-color: rgba(255, 193, 7, 0.1);
        }
        
        .log-line.info {
            color: var(--info-color);
            background-color: rgba(23, 162, 184, 0.1);
        }
        
        /* MEV Protection Status */
        .mev-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .stat-item {
