"""
Arbitrage Bot Dashboard

A complete dashboard showing real-time arbitrage bot data including logs,
configuration, and status information.
"""

import os
import sys
import time
import json
import socket
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dashboard.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("dashboard")

# Dashboard configuration
LOGS_DIR = Path("logs")
CONFIG_DIR = Path("configs")
ANALYTICS_DIR = Path("analytics")

app = Flask(__name__)

@app.route('/')
def index():
    """Generate the main dashboard HTML."""
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot Dashboard</title>
    <style>
    /* Dashboard styles */
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

    .content {
        flex: 1;
        margin-left: var(--sidebar-width);
        padding: 20px;
    }

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
    }

    .card-body {
        padding: 20px;
    }

    .status-indicator {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        padding: 10px;
        border-radius: 5px;
    }

    .status-indicator.online {
        background-color: rgba(40, 167, 69, 0.1);
        color: var(--success-color);
    }

    .status-indicator .dot {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 10px;
        background-color: var(--success-color);
    }
    </style>
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
                <span>Server Time: {{ server_time }}</span>
                <span>Host: {{ hostname }}</span>
            </div>
        </header>
        
        <div class="dashboard-grid">
            <div class="dashboard-card">
                <div class="card-header">System Status</div>
                <div class="card-body">
                    <div class="status-indicator online">
                        <span class="dot"></span> Dashboard Online
                    </div>
                    <p><strong>Log Files:</strong> {{ log_files }} found</p>
                    <p><strong>Config Files:</strong> {{ config_files }} found</p>
                    <p><strong>Uptime:</strong> {{ uptime }}</p>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">Latest Log Activity</div>
                <div class="card-body log-preview">
                    {{ latest_logs | safe }}
                </div>
                <div class="card-footer">
                    <a href="/logs" class="view-more">View All Logs →</a>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">MEV Protection Status</div>
                <div class="card-body">
                    {{ mev_status | safe }}
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="card-header">Configuration Summary</div>
                <div class="card-body">
                    {{ config_summary | safe }}
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
    
    <script>
    // Dashboard JavaScript
    document.addEventListener('DOMContentLoaded', function() {
        // Auto-refresh status
        setInterval(function() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    // Update status indicators
                    document.querySelector('.status-indicator').classList.toggle('online', data.status === 'running');
                })
                .catch(error => console.error('Error fetching status:', error));
        }, 30000);
    });
    </script>
</body>
</html>
""", 
        server_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        hostname=socket.gethostname(),
        log_files=count_log_files(),
        config_files=count_config_files(),
        uptime=calculate_uptime(),
        latest_logs=get_latest_logs_preview(),
        mev_status=get_mev_protection_status(),
        config_summary=get_config_summary()
    )

@app.route('/api/status')
def status():
    """Get status data for API endpoint."""
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "log_files_count": count_log_files(),
        "config_files_count": count_config_files(),
        "host": socket.gethostname(),
        "uptime": calculate_uptime()
    })

def count_log_files():
    """Count the number of log files in the logs directory."""
    if not LOGS_DIR.exists():
        return 0
    return len(list(LOGS_DIR.glob("*.log")))

def count_config_files():
    """Count the number of configuration files in the configs directory."""
    if not CONFIG_DIR.exists():
        return 0
    return len(list(CONFIG_DIR.glob("*.json")))

def calculate_uptime():
    """Calculate mock uptime for the dashboard."""
    uptime_seconds = int(time.time()) % 86400  # Just for display purposes
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def get_latest_logs_preview():
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

def get_mev_protection_status():
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

def get_config_summary():
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
                # Check for flashloan configuration
                if "flash_loans" in config:
                    flashloan_status = "Configured"
                    html += "<tr>"
                    html += "<td><strong>Flash Loan</strong></td>"
                    html += f"<td>{flashloan_status}</td>"
                    html += "</tr>"
                
                # Check for MEV protection
                if "mev_protection" in config:
                    mev_status = "Enabled" if config["mev_protection"].get("enabled", False) else "Disabled"
                    html += "<tr>"
                    html += "<td><strong>MEV Protection</strong></td>"
                    html += f"<td>{mev_status}</td>"
                    html += "</tr>"
                
                # Check for gas settings
                if "gas_limit_buffer" in config:
                    gas_status = f"Buffer: {config['gas_limit_buffer']}%"
                    html += "<tr>"
                    html += "<td><strong>Gas Settings</strong></td>"
                    html += f"<td>{gas_status}</td>"
                    html += "</tr>"
            
            html += "</table>"
    
    except Exception as e:
        html += f"<p class='error'>Error reading configuration: {e}</p>"
    
    return html

def main():
    """Run the dashboard server."""
    logger.info("Initializing dashboard...")
    logger.info(f"Logs directory: {LOGS_DIR}")
    logger.info(f"Config directory: {CONFIG_DIR}")
    logger.info(f"Analytics directory: {ANALYTICS_DIR}")
    
    # Ensure required directories exist
    LOGS_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)
    ANALYTICS_DIR.mkdir(exist_ok=True)
    
    # Start the Flask app
    port = 8081
    logger.info(f"Starting dashboard server on port {port}...")
    logger.info(f"Dashboard will be available at http://localhost:{port}")
    app.run(host='localhost', port=port)

if __name__ == "__main__":
    main()
