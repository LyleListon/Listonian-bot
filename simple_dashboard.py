"""
Simplified Arbitrage Bot Dashboard
"""

import os
import time
import logging
from datetime import datetime
from pathlib import Path

# Basic FastAPI imports
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("simple_dashboard")

# Initialize FastAPI app
app = FastAPI(
    title="Simple Arbitrage Dashboard",
    description="Basic monitoring dashboard for troubleshooting",
    version="0.1.0",
)

# Ensure directories exist
Path("templates").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path("static/css").mkdir(exist_ok=True)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables
start_time = time.time()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render dashboard index page."""
    # Format uptime
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    return templates.TemplateResponse("simple.html", {
        "request": request,
        "status": "Connected",
        "uptime": uptime,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

@app.get("/api/status")
async def api_status():
    """API endpoint for dashboard status."""
    # Format uptime
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    return {
        "status": "Connected",
        "uptime": uptime,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

if __name__ == "__main__":
    print("=" * 70)
    print("STARTING SIMPLIFIED DASHBOARD")
    print("=" * 70)
    print("Dashboard URL: http://localhost:8080")
    
    # Write a simple HTML template
    with open("templates/simple.html", "w") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Arbitrage Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <div class="row">
            <div class="col-12">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h2>Simple Arbitrage Dashboard</h2>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-success">
                            <h4>Dashboard is running!</h4>
                            <p>This is a simplified version to troubleshoot connectivity issues.</p>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header bg-info text-white">
                                        <h5>Status</h5>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>Status:</strong> {{ status }}</p>
                                        <p><strong>Uptime:</strong> {{ uptime }}</p>
                                        <p><strong>Current Time:</strong> {{ current_time }}</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header bg-warning">
                                        <h5>Next Steps</h5>
                                    </div>
                                    <div class="card-body">
                                        <p>If you can see this page, your FastAPI installation is working correctly!</p>
                                        <p>Next steps:</p>
                                        <ul>
                                            <li>Set up proper directory structure</li>
                                            <li>Configure proper .env file with RPC URL</li>
                                            <li>Test connectivity to arbitrage bot modules</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer text-center">
                        Simple Arbitrage Dashboard v0.1.0
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")
    
    # Create a simple CSS file
    with open("static/css/styles.css", "w") as f:
        f.write("""
body {
    background-color: #f8f9fa;
}
.card {
    margin-bottom: 20px;
}
.card-header {
    font-weight: bold;
}
""")
    
    uvicorn.run(
        "simple_dashboard:app", 
        host="localhost", 
        port=8080, 
        reload=True,
        log_level="info"
    )