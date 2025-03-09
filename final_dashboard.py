"""
Arbitrage Bot Real-Time Dashboard

A specialized dashboard for monitoring the Listonian arbitrage bot with real data.
"""

import os
import sys
import time
import json
import socket
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Use a unique port to avoid conflicts
PORT = 9095

# Data directories
LOGS_DIR = Path("logs")
CONFIG_DIR = Path("configs")
ANALYTICS_DIR = Path("analytics")

class ArbitrageDashboardHandler(SimpleHTTPRequestHandler):
    """Handler for the arbitrage dashboard."""
    
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
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")
    
    def generate_html(self):
        """Generate HTML for the dashboard."""
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
    <div class="header">
        <h1>Arbitrage Bot Dashboard</h1>
        <div class="server-info">
            <span>Server Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
            <span>Host: {socket.gethostname()}</span>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="card">
            <div class="card-header">
                <h2>System Status</h2>
            </div>
            <div class="card-body">
                <div class="status online">
                    <div class="status-indicator"></div>
                    <div class="status-text">System Online</div>
                </div>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-label">Log Files</div>
                        <div class="stat-value">{self.count_files(LOGS_DIR, "*.log")}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Config Files</div>
                        <div class="stat-value">{self.count_files(CONFIG_DIR, "*.json")}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Analytics Files</div>
                        <div class="stat-value">{self.count_files(ANALYTICS_DIR, "*.json")}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2>MEV Protection Analysis</h2>
            </div>
            <div class="card-body">
                {self.get_mev_analysis()}
            </div>
        </div>
        
        <div class="card logs-card">
            <div class="card-header">
                <h2>Latest Log Activity</h2>
            </div>
            <div class="card-body">
                {self.get_latest_logs()}
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Arbitrage Bot Dashboard | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Auto-refreshes every 30 seconds</p>
    </div>
</body>
</html>
"""
    
    def count_files(self, directory, pattern):
        """Count files in a directory with a specific pattern."""
        if not directory.exists():
            return 0
        return len(list(directory.glob(pattern)))
    
    def get_latest_logs(self):
        """Get the latest log entries."""
        if not LOGS_DIR.exists():
            return "<div class='no-data'>No logs directory found</div>"
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<div class='no-data'>No log files found</div>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        html = "<div class='logs-container'>"
        
        # Show only the 2 most recent log files
        for log_file in log_files[:2]:
            modified_time = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            file_size = log_file.stat().st_size / 1024  # KB
            
            html += f"""
            <div class='log-file'>
                <div class='log-file-header'>
                    <div class='log-file-name'>{log_file.name}</div>
                    <div class='log-file-info'>
                        <span>Modified: {modified_time}</span>
                        <span>Size: {file_size:.1f} KB</span>
                    </div>
                </div>
            """
            
            # Get last 10 lines of the log
            try:
                with open(log_file, 'r', errors='replace') as f:
                    lines = f.readlines()
                    last_lines = lines[-10:] if len(lines) > 10 else lines
                    
                    html += "<div class='log-content'>"
                    for line in last_lines:
                        line = line.replace("<", "&lt;").replace(">", "&gt;")
                        
                        # Style based on log level
                        if "ERROR" in line.upper():
                            html += f"<div class='log-line error'>{line}</div>"
                        elif "WARN" in line.upper():
                            html += f"<div class='log-line warning'>{line}</div>"
                        elif "INFO" in line.upper():
                            html += f"<div class='log-line info'>{line}</div>"
                        else:
                            html += f"<div class='log-line'>{line}</div>"
                    html += "</div>"
            except Exception as e:
                html += f"<div class='error'>Error reading log file: {str(e)}</div>"
            
            html += "</div>"
        
        html += "</div>"
        return html
    
    def get_mev_analysis(self):
        """Analyze MEV protection from log files."""
        if not LOGS_DIR.exists():
            return "<div class='no-data'>No logs directory found</div>"
        
        log_files = list(LOGS_DIR.glob("*.log"))
        if not log_files:
            return "<div class='no-data'>No log files found</div>"
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Count MEV events in the most recent files
        mev_high = 0
        mev_low = 0
        mempool_high = 0
        mempool_low = 0
        
        # Check the 3 most recent log files
        for log_file in log_files[:3]:
            try:
                with open(log_file, 'r', errors='replace') as f:
                    content = f.read()
                    mev_high += content.count("MEV risk level: high")
                    mev_low += content.count("MEV risk level: low") 
                    mempool_high += content.count("Mempool risk analysis: high")
                    mempool_low += content.count("Mempool risk analysis: low")
            except:
                continue
        
        total_mev = mev_high + mev_low
        total_mempool = mempool_high + mempool_low
        
        if total_mev == 0 and total_mempool == 0:
            return "<div class='no-data'>No MEV or Mempool data found in logs</div>"
        
        html = "<div class='mev-analysis'>"
        
        if total_mev > 0:
            html += f"""
            <div class='analysis-section'>
                <h3>MEV Risk Analysis</h3>
                <div class='analysis-stats'>
                    <div class='stat-item'>
                        <div class='stat-label'>Total Events</div>
                        <div class='stat-value'>{total_mev}</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-label'>High Risk</div>
                        <div class='stat-value'>{mev_high}</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-label'>Low Risk</div>
                        <div class='stat-value'>{mev_low}</div>
                    </div>
                </div>
            """
            
            # Calculate percentages for visualization
            if total_mev > 0:
                low_percent = (mev_low / total_mev) * 100
                high_percent = (mev_high / total_mev) * 100
                
                html += f"""
                <div class='risk-bar'>
                    <div class='risk-segment low' style='width: {low_percent}%'>
                        <span>{low_percent:.1f}%</span>
                    </div>
                    <div class='risk-segment high' style='width: {high_percent}%'>
                        <span>{high_percent:.1f}%</span>
                    </div>
                </div>
                """
            
            html += "</div>"
        
        if total_mempool > 0:
            html += f"""
            <div class='analysis-section'>
                <h3>Mempool Risk Analysis</h3>
                <div class='analysis-stats'>
                    <div class='stat-item'>
                        <div class='stat-label'>Total Events</div>
                        <div class='stat-value'>{total_mempool}</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-label'>High Risk</div>
                        <div class='stat-value'>{mempool_high}</div>
                    </div>
                    <div class='stat-item'>
                        <div class='stat-label'>Low Risk</div>
                        <div class='stat-value'>{mempool_low}</div>
                    </div>
                </div>
            """
            
            # Calculate percentages for visualization
            if total_mempool > 0:
                low_percent = (mempool_low / total_mempool) * 100
                high_percent = (mempool_high / total_mempool) * 100
                
                html += f"""
                <div class='risk-bar'>
                    <div class='risk-segment low' style='width: {low_percent}%'>
                        <span>{low_percent:.1f}%</span>
                    </div>
                    <div class='risk-segment high' style='width: {high_percent}%'>
                        <span>{high_percent:.1f}%</span>
                    </div>
                </div>
                """
            
            html += "</div>"
        
        html += "</div>"
        return html
    
    def get_css(self):
        """Get CSS styles for the dashboard."""
        return """
        :root {
            --primary-color: #4361ee;
            --secondary-color: #3a0ca3;
            --success-color: #4cc9f0;
            --warning-color: #f72585;
            --info-color: #4895ef;
            --dark-color: #370617;
            --light-color: #f8f9fa;
            --background-color: #f5f7fa;
            --card-background: #ffffff;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--background-color);
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background-color: var(--primary-color);
            color: white;
            padding: 20px;
            text-align: center;
            border-bottom: 5px solid var(--secondary-color);
        }
        
        .header h1 {
            margin: 0;
            font-size: 2em;
        }
        
        .server-info {
            margin-top: 10px;
            font-size: 0.9em;
            display: flex;
            justify-content: space-between;
            max-width: 500px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .dashboard {
            max-width: 1200px;
            margin: 20px auto;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            padding: 0 20px;
        }
        
        .logs-card {
            grid-column: 1 / -1;
        }
        
        .card {
            background-color: var(--card-background);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .card-header {
            background-color: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #eaeaea;
        }
        
        .card-header h2 {
            margin: 0;
            font-size: 1.3em;
            color: var(--secondary-color);
        }
        
        .card-body {
            padding: 20px;
        }
        
        .status {
            display: flex;
            align-items: center;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        
        .status.online {
            background-color: rgba(76, 201, 240, 0.1);
        }
        
        .status.offline {
            background-color: rgba(247, 37, 133, 0.1);
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        .status.online .status-indicator {
            background-color: var(--success-color);
            box-shadow: 0 0 10px var(--success-color);
        }
        
        .status.offline .status-indicator {
            background-color: var(--warning-color);
        }
        
        .status-text {
            font-weight: bold;
        }
        
        .status.online .status-text {
            color: var(--success-color);
        }
        
        .status.offline .status-text {
            color: var(--warning-color);
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 15px;
        }
        
        .stat-item {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: var(--primary-color);
        }
        
        .logs-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .log-file {
            border: 1px solid #eaeaea;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .log-file-header {
            background-color: #f8f9fa;
            padding: 10px 15px;
            border-bottom: 1px solid #eaeaea;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .log-file-name {
            font-weight: bold;
            color: var(--primary-color);
        }
        
        .log-file-info {
            font-size: 0.85em;
            color: #666;
            display: flex;
            gap: 15px;
        }
        
        .log-content {
            max-height: 300px;
            overflow-y: auto;
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 10px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
            line-height: 1.5;
        }
        
        .log-line {
            white-space: pre-wrap;
            margin-bottom: 2px;
            border-left: 3px solid transparent;
            padding-left: 5px;
        }
        
        .log-line.error {
            color: #f14668;
            border-left-color: #f14668;
        }
        
        .log-line.warning {
            color: #ffdd57;
            border-left-color: #ffdd57;
        }
        
        .log-line.info {
            color: #3298dc;
            border-left-color: #3298dc;
        }
        
        .mev-analysis {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .analysis-section h3 {
            font-size: 1.1em;
            margin-bottom: 15px;
            color: var(--secondary-color);
        }
        
        .analysis-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .risk-bar {
            height: 25px;
            display: flex;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        
        .risk-segment {
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .risk-segment.low {
            background-color: var(--info-color);
        }
        
        .risk-segment.high {
            background-color: var(--warning-color);
        }
        
        .no-data {
            padding: 20px;
            text-align: center;
            color: #666;
            font-style: italic;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        
        .error {
            padding: 10px;
            color: #f14668;
            background-color: rgba(241, 70, 104, 0.1);
            border-radius: 5px;
        }
        
        .footer {
            text-align: center;
            margin: 20px 0;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .dashboard {
                grid-template-columns: 1fr;
            }
            
            .server-info {
                flex-direction: column;
                gap: 5px;
            }
            
            .analysis-stats {
                grid-template-columns: 1fr;
            }
        }
        """

def run_server():
    """Run the HTTP server."""
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, ArbitrageDashboardHandler)
    print(f"Starting Arbitrage Dashboard on port {PORT}...")
    print(f"Open this URL in your browser: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped")

if __name__ == "__main__":
    run_server()