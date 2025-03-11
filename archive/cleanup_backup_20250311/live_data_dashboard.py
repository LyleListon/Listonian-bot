import os
import time
import json
import socket
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from pathlib import Path

# Track start time for uptime calculation
START_TIME = time.time()

# Log file pattern for arbitrage logs
LOG_DIR = Path("logs")
ARB_LOG_PATTERN = re.compile(r"arbitrage.*\.log")

class LiveDataDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        # Root path
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Calculate uptime
            uptime_seconds = int(time.time() - START_TIME)
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{days}d {hours}h {minutes}m {seconds}s"
            
            # Get real log data
            log_entries = self.get_log_entries(max_entries=10)
            
            # Create data object
            data = {
                "status": "Running",
                "uptime": uptime,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "server_info": {
                    "hostname": socket.gethostname(),
                    "python_version": os.sys.version,
                },
                "log_entries": log_entries
            }
            
            # Render HTML
            html = self.render_html(data)
            self.wfile.write(html.encode())
            
        # API endpoint
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            # Calculate uptime
            uptime_seconds = int(time.time() - START_TIME)
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{days}d {hours}h {minutes}m {seconds}s"
            
            # Create simple data
            data = {
                "status": "Running",
                "uptime": uptime,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "log_entries_count": len(self.get_log_entries())
            }
            
            # Return JSON
            self.wfile.write(json.dumps(data).encode())
            
        # CSS
        elif self.path == "/style.css":
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            
            css = """
            body {
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            .header {
                background-color: #4a6fdc;
                color: white;
                padding: 15px 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .card {
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-bottom: 20px;
                overflow: hidden;
            }
            .card-header {
                background-color: #f0f0f0;
                padding: 10px 15px;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
            .card-body {
                padding: 15px;
            }
            .alert {
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
            }
            .alert-success {
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }
            .table {
                width: 100%;
                border-collapse: collapse;
            }
            .table th, .table td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            .table th {
                background-color: #f5f5f5;
            }
            .log-entry {
                padding: 8px;
                margin-bottom: 8px;
                border-left: 4px solid #ccc;
            }
            .log-entry.info {
                border-left-color: #17a2b8;
                background-color: #f0f9fc;
            }
            .log-entry.error {
                border-left-color: #dc3545;
                background-color: #fdf7f7;
            }
            .log-entry.warning {
                border-left-color: #ffc107;
                background-color: #fffdf0;
            }
            """
            
            self.wfile.write(css.encode())
            
        # 404 for any other path
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")
    
    def get_log_entries(self, max_entries=10):
        """
        Read actual log entries from the logs directory.
        Returns a list of log entries with timestamp, level, and message.
        """
        entries = []
        
        # Check if logs directory exists
        if not LOG_DIR.exists():
            return entries
        
        # Find log files related to arbitrage
        log_files = []
        for file in LOG_DIR.glob("*.log"):
            if ARB_LOG_PATTERN.match(file.name) or "arbitrage" in file.name.lower():
                log_files.append(file)
        
        # If no specific arbitrage logs found, use any log file
        if not log_files:
            log_files = list(LOG_DIR.glob("*.log"))
        
        # If still no logs, return empty
        if not log_files:
            return entries
        
        # Sort files by modification time (newest first)
        log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Read the most recent log file
        try:
            with open(log_files[0], "r") as f:
                lines = f.readlines()
                
                # Process lines from newest to oldest
                for line in reversed(lines):
                    if len(entries) >= max_entries:
                        break
                    
                    # Extract parts from log line
                    try:
                        # Try to parse standard format logs first
                        # Example: 2025-02-28 03:15:42,123 - arbitrage_bot.core - INFO - Message
                        parts = line.strip().split(" - ", 3)
                        if len(parts) >= 3:  # Allow for logs without module
                            timestamp = parts[0]
                            
                            # Handle logs with or without module
                            if len(parts) == 4:
                                module, level, message = parts[1:]
                            else:
                                module = ""
                                level, message = parts[1:]
                            
                            # Determine log level for styling
                            if "ERROR" in level.upper():
                                log_type = "error"
                            elif "WARN" in level.upper():
                                log_type = "warning"
                            else:
                                log_type = "info"
                            
                            entries.append({
                                "timestamp": timestamp,
                                "level": level.strip(),
                                "message": message.strip(),
                                "module": module.strip(),
                                "type": log_type
                            })
                        # Fall back to simpler format
                        elif ":" in line and len(line) > 10:
                            # Very simple fallback: Just split on first colon for timestamp
                            timestamp, message = line.split(":", 1)
                            entries.append({
                                "timestamp": timestamp.strip(),
                                "level": "INFO",
                                "message": message.strip(),
                                "module": "",
                                "type": "info"
                            })
                    except Exception as e:
                        # If we can't parse properly, add with minimal formatting
                        if len(line.strip()) > 5:  # Only add non-empty lines
                            entries.append({
                                "timestamp": "",
                                "level": "",
                                "message": line.strip(),
                                "module": "",
                                "type": "info"
                            })
                            
        except Exception as e:
            # If we can't read the log file, add a dummy entry
            entries.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": "ERROR",
                "message": f"Failed to read log file: {str(e)}",
                "module": "dashboard",
                "type": "error"
            })
        
        return entries
    
    def render_html(self, data):
        """Render HTML with the provided data."""
        log_entries_html = ""
        
        for entry in data.get("log_entries", []):
            log_entries_html += f"""
            <div class="log-entry {entry['type']}">
                <strong>{entry['timestamp']}</strong>
                {f" - <span class='badge bg-secondary'>{entry['level']}</span>" if entry['level'] else ""}
                {f" - <em>{entry['module']}</em>" if entry['module'] else ""}
                <div>{entry['message']}</div>
            </div>
            """
        
        if not log_entries_html:
            log_entries_html = "<p class='text-muted'>No log entries found</p>"
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Dashboard with Live Data</title>
    <link rel="stylesheet" href="/style.css">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <meta http-equiv="refresh" content="30"> <!-- Auto-refresh every 30 seconds -->
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Arbitrage Dashboard</h1>
            <p>Real Log Data Display</p>
        </div>
        
        <div class="alert alert-success">
            <h3>Dashboard is running!</h3>
            <p>Displaying actual log data from your arbitrage bot.</p>
        </div>
        
        <div class="card">
            <div class="card-header">System Status</div>
            <div class="card-body">
                <p><strong>Status:</strong> {data['status']}</p>
                <p><strong>Uptime:</strong> {data['uptime']}</p>
                <p><strong>Current Time:</strong> {data['current_time']}</p>
                <p><strong>Hostname:</strong> {data['server_info']['hostname']}</p>
                <p><strong>Python Version:</strong> {data['server_info']['python_version']}</p>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">Arbitrage Bot Logs</div>
            <div class="card-body">
                <p>Recent log entries from your arbitrage bot:</p>
                <div class="log-entries">
                    {log_entries_html}
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">Next Steps</div>
            <div class="card-body">
                <p>Now that we're displaying real log data, we can add:</p>
                <ol>
                    <li>Configuration details from config.json</li>
                    <li>DEX status information</li>
                    <li>Transaction history</li>
                    <li>Profit tracking</li>
                </ol>
            </div>
        </div>
        
        <footer style="text-align: center; margin-top: 20px; color: #666;">
            Arbitrage Dashboard | Last Updated: {data['current_time']}
        </footer>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def run_server(port=8080):
    """Run the HTTP server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, LiveDataDashboardHandler)
    print(f"Starting server on port {port}...")
    print(f"Dashboard URL: http://localhost:{port}")
    print("Press Ctrl+C to stop the server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")

if __name__ == "__main__":
    run_server()