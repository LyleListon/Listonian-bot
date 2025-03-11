import os
import time
import json
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from pathlib import Path

# Track start time for uptime calculation
START_TIME = time.time()

class BasicDashboardHandler(BaseHTTPRequestHandler):
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
            
            # Create simple data
            data = {
                "status": "Running",
                "uptime": uptime,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "server_info": {
                    "hostname": socket.gethostname(),
                    "python_version": os.sys.version,
                }
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
            """
            
            self.wfile.write(css.encode())
            
        # 404 for any other path
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")
    
    def render_html(self, data):
        """Render HTML with the provided data."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Basic Arbitrage Dashboard</title>
    <link rel="stylesheet" href="/style.css">
    <meta http-equiv="refresh" content="30"> <!-- Auto-refresh every 30 seconds -->
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Basic Arbitrage Dashboard</h1>
        </div>
        
        <div class="alert alert-success">
            <h3>Dashboard is running!</h3>
            <p>This is a basic dashboard with no dependencies required.</p>
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
            <div class="card-header">Next Steps</div>
            <div class="card-body">
                <p>Now that this basic dashboard is working, you can:</p>
                <ol>
                    <li>Implement the FastAPI version with templates</li>
                    <li>Connect to blockchain data via Web3.py</li>
                    <li>Integrate with your arbitrage bot modules</li>
                    <li>Add real-time data updates with JavaScript</li>
                </ol>
            </div>
        </div>
        
        <footer style="text-align: center; margin-top: 20px; color: #666;">
            Basic Arbitrage Dashboard | Last Updated: {data['current_time']}
        </footer>
    </div>
</body>
</html>
"""

def run_server(port=8080):
    """Run the HTTP server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, BasicDashboardHandler)
    print(f"Starting server on port {port}...")
    print(f"Dashboard URL: http://localhost:{port}")
    print("Press Ctrl+C to stop the server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")

if __name__ == "__main__":
    # Create data directory
    Path("data").mkdir(exist_ok=True)
    
    # Run the server
    run_server()