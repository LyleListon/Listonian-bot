"""
Simple Log Reader Dashboard

A lightweight dashboard that displays arbitrage bot logs with minimal dependencies.
"""

import os
import sys
import time
import socket
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Log directory
LOG_DIR = Path("logs")

class LogReaderHandler(SimpleHTTPRequestHandler):
    """Custom handler to display log files"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Get log files in the logs directory
            log_files = []
            if LOG_DIR.exists():
                log_files = sorted(
                    [f for f in LOG_DIR.iterdir() if f.is_file() and f.name.endswith('.log')],
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )[:10]  # Get 10 most recent log files
            
            # Generate HTML for the page
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Arbitrage Log Reader</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    .log-list {{ margin: 20px 0; }}
                    .log-entry {{ 
                        padding: 10px; 
                        margin-bottom: 10px; 
                        background-color: #f5f5f5; 
                        border-left: 4px solid #4a6fdc;
                    }}
                    .server-info {{ 
                        background-color: #e9ecef; 
                        padding: 10px; 
                        border-radius: 5px; 
                        margin-bottom: 20px; 
                    }}
                    pre {{ 
                        background-color: #f8f9fa; 
                        padding: 10px; 
                        overflow-x: auto; 
                        white-space: pre-wrap; 
                        word-wrap: break-word; 
                    }}
                </style>
                <meta http-equiv="refresh" content="15">
            </head>
            <body>
                <h1>Arbitrage Bot Log Reader</h1>
                
                <div class="server-info">
                    <h3>Server Information</h3>
                    <p><strong>Server time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Hostname:</strong> {socket.gethostname()}</p>
                    <p><strong>Python version:</strong> {sys.version}</p>
                </div>
                
                <h2>Log Files (Most Recent)</h2>
            """
            
            # Add log files section
            if log_files:
                for log_file in log_files:
                    html_content += f"""
                    <div class="log-entry">
                        <h3>{log_file.name}</h3>
                        <p><strong>Last modified:</strong> {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p><strong>Size:</strong> {log_file.stat().st_size} bytes</p>
                        <details>
                            <summary>View Last 10 Lines</summary>
                            <pre>
                    """
                    
                    # Get the last 10 lines of the log file
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                            last_lines = lines[-10:] if len(lines) >= 10 else lines
                            for line in last_lines:
                                html_content += line.replace("<", "&lt;").replace(">", "&gt;")
                    except Exception as e:
                        html_content += f"Error reading log file: {str(e)}"
                    
                    html_content += """
                            </pre>
                        </details>
                    </div>
                    """
            else:
                html_content += "<p>No log files found.</p>"
            
            # Close HTML
            html_content += """
                <div>
                    <p>This page automatically refreshes every 15 seconds.</p>
                </div>
            </body>
            </html>
            """
            
            self.wfile.write(html_content.encode())
            return
        
        return super().do_GET()

def run_server(port=8080):
    """Run the HTTP server"""
    print(f"Starting Log Reader on port {port}...")
    print(f"Open your browser at http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    
    server = HTTPServer(('', port), LogReaderHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped")

if __name__ == "__main__":
    run_server()