"""
Enhanced Log Viewer with Config Display

Displays log files and configuration information from your arbitrage bot.
"""

import os
import sys
import time
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Change this to a port that isn't in use
PORT = 9090

# Directories where data is stored
LOGS_DIR = Path("logs")
CONFIG_DIR = Path("configs")

class EnhancedLogViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Handle different paths
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.render_main_page().encode())
        elif self.path == "/logs":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.render_logs_page().encode())
        elif self.path == "/config":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.render_config_page().encode())
        elif self.path == "/style.css":
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            self.wfile.write(self.get_css().encode())
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")

    def render_main_page(self):
        """Render the main dashboard page with both logs and config."""
        return f"""
        <html>
        <head>
            <title>Arbitrage Bot Dashboard</title>
            <link rel="stylesheet" href="/style.css">
            <meta http-equiv="refresh" content="30">
        </head>
        <body>
            <div class="navbar">
                <div class="navbar-brand">Arbitrage Bot Dashboard</div>
                <div class="navbar-links">
                    <a href="/" class="active">Dashboard</a>
                    <a href="/logs">Logs</a>
                    <a href="/config">Configuration</a>
                </div>
            </div>
            
            <div class="container">
                <div class="header">
                    <h1>Arbitrage Bot Dashboard</h1>
                    <p>Server time: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                
                <div class="row">
                    <div class="column">
                        <div class="card">
                            <div class="card-header">Recent Logs</div>
                            <div class="card-body">
                                {self.get_latest_log_content()}
                                <p><a href="/logs">View all logs →</a></p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="column">
                        <div class="card">
                            <div class="card-header">Configuration</div>
                            <div class="card-body">
                                {self.get_config_summary()}
                                <p><a href="/config">View full configuration →</a></p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
                </div>
            </div>
        </body>
        </html>
        """

    def render_logs_page(self):
        """Render the logs page."""
        log_content = self.get_all_logs_content()
        
        return f"""
        <html>
        <head>
            <title>Arbitrage Bot Logs</title>
            <link rel="stylesheet" href="/style.css">
            <meta http-equiv="refresh" content="30">
        </head>
        <body>
            <div class="navbar">
                <div class="navbar-brand">Arbitrage Bot Dashboard</div>
                <div class="navbar-links">
                    <a href="/">Dashboard</a>
                    <a href="/logs" class="active">Logs</a>
                    <a href="/config">Configuration</a>
                </div>
            </div>
            
            <div class="container">
                <div class="header">
                    <h1>Arbitrage Bot Logs</h1>
                    <p>Server time: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                
                <div class="card">
                    <div class="card-header">Log Files</div>
                    <div class="card-body">
                        {log_content}
                    </div>
                </div>
                
                <div class="footer">
                    <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
                </div>
            </div>
        </body>
        </html>
        """

    def render_config_page(self):
        """Render the configuration page."""
        config_content = self.get_full_config_content()
        
        return f"""
        <html>
        <head>
            <title>Arbitrage Bot Configuration</title>
            <link rel="stylesheet" href="/style.css">
            <meta http-equiv="refresh" content="30">
        </head>
        <body>
            <div class="navbar">
                <div class="navbar-brand">Arbitrage Bot Dashboard</div>
                <div class="navbar-links">
                    <a href="/">Dashboard</a>
                    <a href="/logs">Logs</a>
                    <a href="/config" class="active">Configuration</a>
                </div>
            </div>
            
            <div class="container">
                <div class="header">
                    <h1>Arbitrage Bot Configuration</h1>
                    <p>Server time: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                
                <div class="card">
                    <div class="card-header">Configuration Files</div>
                    <div class="card-body">
                        {config_content}
                    </div>
                </div>
                
                <div class="footer">
                    <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
                </div>
            </div>
        </body>
        </html>
        """

    def get_latest_log_content(self):
        """Get content from the most recent log file."""
        if not LOGS_DIR.exists():
            return "<p>Logs directory not found!</p>"
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<p>No log files found in logs directory.</p>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        latest_log = log_files[0]
        
        html = f"""
        <h3>{latest_log.name}</h3>
        <p>Last modified: {time.ctime(latest_log.stat().st_mtime)}</p>
        <p>Size: {latest_log.stat().st_size} bytes</p>
        <h4>Last 10 lines:</h4>
        <pre class="log-content">
        """
        
        # Read the last 10 lines
        try:
            with open(latest_log, "r", errors="replace") as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) > 10 else lines
                for line in last_lines:
                    # Escape HTML characters
                    line = line.replace("<", "&lt;").replace(">", "&gt;")
                    html += line
        except Exception as e:
            html += f"Error reading log file: {e}"
        
        html += "</pre>"
        return html

    def get_all_logs_content(self):
        """Get content from all log files."""
        if not LOGS_DIR.exists():
            return "<p>Logs directory not found!</p>"
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<p>No log files found in logs directory.</p>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        html = ""
        
        # Display the 10 most recent log files
        for log_file in log_files[:10]:
            html += f"""
            <div class="log-file">
                <h3>{log_file.name}</h3>
                <p>Last modified: {time.ctime(log_file.stat().st_mtime)}</p>
                <p>Size: {log_file.stat().st_size} bytes</p>
                <h4>Last 20 lines:</h4>
                <pre class="log-content">
            """
            
            # Read the last 20 lines
            try:
                with open(log_file, "r", errors="replace") as f:
                    lines = f.readlines()
                    last_lines = lines[-20:] if len(lines) > 20 else lines
                    for line in last_lines:
                        # Escape HTML characters
                        line = line.replace("<", "&lt;").replace(">", "&gt;")
                        html += line
            except Exception as e:
                html += f"Error reading log file: {e}"
            
            html += """
                </pre>
            </div>
            """
        
        return html

    def get_config_summary(self):
        """Get a summary of the configuration."""
        if not CONFIG_DIR.exists():
            return "<p>Configuration directory not found!</p>"
        
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
            main_config = config_files[0]  # Use first config if no main config
        
        html = f"""
        <h3>{main_config.name}</h3>
        <p>Last modified: {time.ctime(main_config.stat().st_mtime)}</p>
        """
        
        # Read the config file
        try:
            with open(main_config, "r") as f:
                config_data = json.load(f)
                
                # Extract some key information
                if isinstance(config_data, dict):
                    # Check for common configuration sections
                    html += "<table class='config-table'>"
                    
                    if "network" in config_data:
                        html += "<tr><td><strong>Network</strong></td><td>"
                        if isinstance(config_data["network"], dict):
                            network = config_data["network"]
                            if "rpc_url" in network:
                                html += "RPC URL: "
                                url = network["rpc_url"]
                                # Mask API keys in URLs for security
                                if isinstance(url, str) and len(url) > 30:
                                    if "?" in url:
                                        base, params = url.split("?", 1)
                                        html += f"{base}?...masked..."
                                    else:
                                        html += f"{url[:20]}...masked..."
                                else:
                                    html += "Configured"
                        html += "</td></tr>"
                    
                    if "dexes" in config_data:
                        html += "<tr><td><strong>DEXes</strong></td><td>"
                        if isinstance(config_data["dexes"], dict):
                            dexes = config_data["dexes"]
                            enabled_dexes = []
                            for dex_name, dex_config in dexes.items():
                                if isinstance(dex_config, dict) and dex_config.get("enabled", False):
                                    enabled_dexes.append(dex_name)
                            if enabled_dexes:
                                html += f"{len(enabled_dexes)} Enabled: " + ", ".join(enabled_dexes[:3])
                                if len(enabled_dexes) > 3:
                                    html += f", and {len(enabled_dexes) - 3} more..."
                            else:
                                html += "None enabled"
                        html += "</td></tr>"
                    
                    if "flashloan" in config_data:
                        html += "<tr><td><strong>Flash Loan</strong></td><td>Configured</td></tr>"
                    
                    if "dynamic_allocation" in config_data:
                        html += "<tr><td><strong>Dynamic Allocation</strong></td><td>Configured</td></tr>"
                    
                    html += "</table>"
                    
                else:
                    html += "<p>Invalid configuration format</p>"
        except Exception as e:
            html += f"<p>Error reading configuration: {e}</p>"
        
        return html

    def get_full_config_content(self):
        """Get content from all configuration files."""
        if not CONFIG_DIR.exists():
            return "<p>Configuration directory not found!</p>"
        
        config_files = list(CONFIG_DIR.glob("*.json"))
        if not config_files:
            return "<p>No configuration files found.</p>"
        
        # Sort by name
        config_files.sort(key=lambda x: x.name)
        
        html = ""
        
        for config_file in config_files:
            html += f"""
            <div class="config-file">
                <h3>{config_file.name}</h3>
                <p>Last modified: {time.ctime(config_file.stat().st_mtime)}</p>
                <p>Size: {config_file.stat().st_size} bytes</p>
                <pre class="config-content">
            """
            
            # Read the config file
            try:
                with open(config_file, "r") as f:
                    config_text = f.read()
                    
                    # Try to parse and pretty-print if it's valid JSON
                    try:
                        config_data = json.loads(config_text)
                        pretty_config = json.dumps(config_data, indent=2)
                        
                        # Escape HTML characters
                        pretty_config = pretty_config.replace("<", "&lt;").replace(">", "&gt;")
                        html += pretty_config
                    except json.JSONDecodeError:
                        # If not valid JSON, just display as is
                        config_text = config_text.replace("<", "&lt;").replace(">", "&gt;")
                        html += config_text
            except Exception as e:
                html += f"Error reading configuration file: {e}"
            
            html += """
                </pre>
            </div>
            """
        
        return html

    def get_css(self):
        """Get the CSS styles for the dashboard."""
        return """
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        
        .navbar {
            background-color: #4a6fdc;
            color: white;
            display: flex;
            justify-content: space-between;
            padding: 10px 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .navbar-brand {
            font-size: 1.5em;
            font-weight: bold;
        }
        
        .navbar-links a {
            color: white;
            text-decoration: none;
            margin-left: 20px;
            padding: 5px 10px;
            border-radius: 5px;
        }
        
        .navbar-links a.active {
            background-color: rgba(255, 255, 255, 0.2);
        }
        
        .navbar-links a:hover {
            background-color: rgba(255, 255, 255, 0.3);
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            margin-bottom: 20px;
        }
        
        .header h1 {
            color: #4a6fdc;
            margin-bottom: 5px;
        }
        
        .row {
            display: flex;
            flex-wrap: wrap;
            margin: 0 -10px;
        }
        
        .column {
            flex: 1;
            padding: 0 10px;
            min-width: 300px;
        }
        
        .card {
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .card-header {
            background-color: #f0f0f0;
            padding: 10px 15px;
            font-weight: bold;
            border-bottom: 1px solid #ddd;
        }
        
        .card-body {
            padding: 15px;
        }
        
        .log-file, .config-file {
            margin-bottom: 30px;
            border-bottom: 1px solid #eee;
            padding-bottom: 20px;
        }
        
        .log-file:last-child, .config-file:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        
        pre.log-content, pre.config-content {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            white-space: pre-wrap;
            font-size: 12px;
            border: 1px solid #ddd;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .footer {
            margin-top: 20px;
            color: #666;
            font-size: 12px;
            text-align: center;
        }
        
        table.config-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        table.config-table td {
            padding: 8px;
            border-bottom: 1px solid #eee;
        }
        
        table.config-table tr:last-child td {
            border-bottom: none;
        }
        
        @media (max-width: 768px) {
            .column {
                flex: 100%;
            }
        }
        """

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, EnhancedLogViewerHandler)
    print(f"Server started at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()