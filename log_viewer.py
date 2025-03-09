"""
Super Simple Log Viewer

Displays log files from the logs directory with no dependencies.
"""

import os
import sys
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Change this to a port that isn't in use
PORT = 9090

# Directory where logs are stored
LOGS_DIR = Path("logs")

class LogViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        html = f"""
        <html>
        <head>
            <title>Arbitrage Log Viewer</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #4a6fdc; }}
                .log-file {{ 
                    margin-bottom: 20px; 
                    border: 1px solid #ddd; 
                    padding: 10px;
                    border-radius: 5px;
                }}
                .log-file h2 {{ margin-top: 0; }}
                pre {{ 
                    background-color: #f5f5f5; 
                    padding: 10px; 
                    border-radius: 5px;
                    overflow-x: auto;
                    max-height: 300px;
                    overflow-y: auto;
                }}
            </style>
        </head>
        <body>
            <h1>Arbitrage Bot Log Viewer</h1>
            <p>Server time: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>
            <div id="log-files">
        """
        
        # Check if logs directory exists
        if not LOGS_DIR.exists():
            html += "<p>Logs directory not found!</p>"
        else:
            # Get all log files
            log_files = list(LOGS_DIR.glob("*.log"))
            
            if not log_files:
                html += "<p>No log files found in logs directory.</p>"
            else:
                # Sort by modification time (newest first)
                log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                # Display the 10 most recent log files
                for log_file in log_files[:10]:
                    html += f"""
                    <div class="log-file">
                        <h2>{log_file.name}</h2>
                        <p>Last modified: {time.ctime(log_file.stat().st_mtime)}</p>
                        <p>Size: {log_file.stat().st_size} bytes</p>
                        <h3>Last 20 lines:</h3>
                        <pre>
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
        
        html += """
            </div>
            <p><a href="/">Refresh page</a> | Auto-refresh in 30 seconds</p>
            <script>
                // Auto-refresh the page every 30 seconds
                setTimeout(function() {
                    window.location.reload();
                }, 30000);
            </script>
        </body>
        </html>
        """
        
        self.wfile.write(html.encode())

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, LogViewerHandler)
    print(f"Server started at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()