"""
Minimal Real Arbitrage Dashboard

A lightweight dashboard that displays actual arbitrage bot data from logs directory.
"""

import os
import sys
import time
import json
import socket
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Dashboard configuration
PORT = 9090  # Using a different port
LOGS_DIR = Path("logs")
CONFIG_DIR = Path("configs")

class MinimalDashboardHandler(SimpleHTTPRequestHandler):
    """Custom handler for the minimal dashboard."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_dashboard().encode())
            return
        elif self.path == "/style.css":
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            self.wfile.write(self.get_css().encode())
            return
        
        # For all other paths, use the default handler
        return super().do_GET()
    
    def generate_dashboard(self):
        """Generate the dashboard HTML."""
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
    <div class="container">
        <header>
            <h1>Arbitrage Bot Dashboard</h1>
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
                    <p><strong>Python Version:</strong> {sys.version.split()[0]}</p>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">Latest Log Activity</div>
                <div class="card-body log-preview">
                    {self.get_latest_logs()}
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">MEV Protection Status</div>
                <div class="card-body">
                    {self.get_mev_status()}
                </div>
            </div>
        </div>
        
        <footer>
            <p>Arbitrage Bot Dashboard | Auto-refreshes every 30 seconds</p>
        </footer>
    </div>
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
    
    def get_latest_logs(self):
        """Get the latest log entries."""
        if not LOGS_DIR.exists():
            return "<p>No logs directory found.</p>"
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<p>No log files found.</p>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        html = ""
        
        # Display the 3 most recent log files
        for log_file in log_files[:3]:
            file_size_kb = log_file.stat().st_size / 1024
            modified_time = datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            html += f"""
            <div class="log-file">
                <h3>{log_file.name}</h3>
                <p>Modified: {modified_time} | Size: {file_size_kb:.2f} KB</p>
                <div class="log-content">
            """
            
            # Read the last 10 lines
            try:
                with open(log_file, "r", errors="replace") as f:
                    lines = f.readlines()
                    last_lines = lines[-10:] if len(lines) > 10 else lines
                    
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
    
    def get_mev_status(self):
        """Analyze MEV protection status from log files."""
        if not LOGS_DIR.exists():
            return "<p>No logs directory found.</p>"
        
        # Count MEV-related entries in logs
        mev_low_count = 0
        mev_high_count = 0
        
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
            except:
                pass
        
        total_mev = mev_low_count + mev_high_count
        
        if total_mev == 0:
            return "<p>No MEV protection data found in recent logs.</p>"
        
        html = f"""
        <div class="mev-summary">
            <div class="mev-stat">
                <span class="stat-label">Total MEV Events</span>
                <span class="stat-value">{total_mev}</span>
            </div>
            <div class="mev-stat">
                <span class="stat-label">Low Risk</span>
                <span class="stat-value">{mev_low_count}</span>
            </div>
            <div class="mev-stat">
                <span class="stat-label">High Risk</span>
                <span class="stat-value">{mev_high_count}</span>
            </div>
        </div>
        
        <p>The arbitrage bot is actively monitoring for MEV attacks.</p>
        """
        
        return html
    
    def get_css(self):
        """Get the CSS for the dashboard."""
        return """
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
        }
        
        header h1 {
            color: #4a6fdc;
            margin-bottom: 10px;
        }
        
        .header-info {
            display: flex;
            justify-content: space-between;
            color: #666;
            font-size: 0.9rem;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .dashboard-card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .card-header {
            background-color: #f8f9fa;
            padding: 12px 15px;
            font-weight: bold;
            border-bottom: 1px solid #eee;
            font-size: 1.1rem;
        }
        
        .card-body {
            padding: 15px;
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding: 8px 12px;
            border-radius: 5px;
            background-color: rgba(40, 167, 69, 0.1);
            color: #28a745;
            font-weight: bold;
        }
        
        .status-indicator .dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #28a745;
            margin-right: 10px;
        }
        
        .log-preview {
            max-height: 500px;
            overflow-y: auto;
        }
        
        .log-file {
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        
        .log-file h3 {
            margin-bottom: 5px;
            font-size: 1rem;
            color: #4a6fdc;
        }
        
        .log-file p {
            color: #666;
            font-size: 0.85rem;
            margin-bottom: 10px;
        }
        
        .log-content {
            background-color: #f8f9fa;
            padding: 8px;
            border-radius: 5px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
        }
        
        .log-line {
            white-space: pre-wrap;
            word-break: break-all;
            margin-bottom: 2px;
            padding: 2px 4px;
        }
        
        .log-line.error {
            color: #dc3545;
            background-color: rgba(220, 53, 69, 0.1);
        }
        
        .log-line.warning {
            color: #ffc107;
            background-color: rgba(255, 193, 7, 0.1);
        }
        
        .log-line.info {
            color: #17a2b8;
            background-color: rgba(23, 162, 184, 0.1);
        }
        
        .mev-summary {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .mev-stat {
            flex: 1;
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }
        
        .stat-label {
            display: block;
            font-size: 0.8rem;
            color: #666;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #4a6fdc;
        }
        
        footer {
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .header-info {
                flex-direction: column;
            }
        }
        """

def run_server():
    """Run the HTTP server."""
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MinimalDashboardHandler)
    print(f"Starting dashboard on port {PORT}...")
    print(f"Dashboard URL: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")

if __name__ == "__main__":
    run_server()