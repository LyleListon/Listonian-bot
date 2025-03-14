"""
Arbitrage Bot Real-Time Dashboard

A specialized dashboard for monitoring the Listonian arbitrage bot with real data.
"""

import os
import sys
import time
import json
import socket
import asyncio
import socketio
from datetime import datetime
from pathlib import Path
from aiohttp import web

# Use a unique port to avoid conflicts
PORT = 9095

# Data directories
LOGS_DIR = Path("logs")
CONFIG_DIR = Path("configs")
ANALYTICS_DIR = Path("analytics")

# Initialize Socket.IO with engineio_path
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins=['*'],  # Allow all origins for development
    engineio_path='socket.io',
    logger=True,
    engineio_logger=True
)

# Initialize aiohttp app
app = web.Application()
sio.attach(app)

# Store latest stats
latest_stats = {
    'system_status': 'online',
    'memory_usage': {},
    'active_positions': [],
    'recent_opportunities': [],
    'profit_loss': {
        'total': 0,
        'last_24h': 0,
        'pending': 0
    },
    'mev_protection': {
        'active': True,
        'blocked_attacks': 0,
        'risk_level': 'low'
    }
}

@sio.event
async def connect(sid, environ):
    """Handle client connection."""
    print(f"Client connected: {sid}")
    await sio.emit('system_status', {'status': 'online'}, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    print(f"Client disconnected: {sid}")

class ArbitrageDashboard:
    """Real-time arbitrage dashboard implementation."""
    
    @staticmethod
    async def index(request):
        """Serve the dashboard HTML."""
        return web.Response(
            text=ArbitrageDashboard.generate_html(),
            content_type='text/html',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': '*'
            }
        )

    @staticmethod
    async def style(request):
        """Serve the dashboard CSS."""
        return web.Response(
            text=ArbitrageDashboard.get_css(),
            content_type='text/css',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET',
                'Access-Control-Allow-Headers': '*'
            }
        )

    @staticmethod
    def generate_html():
        """Generate HTML for the dashboard."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot Dashboard</title>
    <link rel="stylesheet" href="/style.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>Arbitrage Bot Dashboard</h1>
        <div class="server-info">
            <span>Server Time: <span id="server-time">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></span>
            <span>Host: {socket.gethostname()}</span>
        </div>
    </div>
    
    <div class="dashboard">
        <div class="card">
            <div class="card-header">
                <h2>System Status</h2>
            </div>
            <div class="card-body">
                <div id="system-status" class="status online">
                    <div class="status-indicator"></div>
                    <div class="status-text">System Online</div>
                </div>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-label">Memory Usage</div>
                        <div id="memory-usage" class="stat-value">0%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Active Positions</div>
                        <div id="active-positions" class="stat-value">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">24h Profit</div>
                        <div id="profit-24h" class="stat-value">0 ETH</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2>MEV Protection</h2>
            </div>
            <div class="card-body">
                <div id="mev-protection"></div>
            </div>
        </div>
        
        <div class="card opportunities-card">
            <div class="card-header">
                <h2>Recent Opportunities</h2>
            </div>
            <div class="card-body">
                <div id="opportunities-list"></div>
            </div>
        </div>

        <div class="card profit-card">
            <div class="card-header">
                <h2>Profit/Loss Chart</h2>
            </div>
            <div class="card-body">
                <canvas id="profit-chart"></canvas>
            </div>
        </div>
        
        <div class="card logs-card">
            <div class="card-header">
                <h2>Latest Activity</h2>
            </div>
            <div class="card-body">
                <div id="live-logs"></div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Arbitrage Bot Dashboard | Last Updated: <span id="last-updated">Just now</span></p>
        <p>Real-time updates enabled</p>
    </div>

    <script>
        // Initialize Socket.IO connection with explicit path
        const socket = io({
            path: '/socket.io',
            transports: ['websocket'],
            upgrade: false
        });
        
        // Update server time
        setInterval(() => {{
            document.getElementById('server-time').textContent = new Date().toLocaleString();
        }}, 1000);
        
        // Handle system status updates
        socket.on('system_status', (data) => {{
            const statusDiv = document.getElementById('system-status');
            statusDiv.className = `status ${{data.status}}`;
            statusDiv.querySelector('.status-text').textContent = `System ${{data.status.charAt(0).toUpperCase() + data.status.slice(1)}}`;
            
            document.getElementById('memory-usage').textContent = `${{data.memory_usage}}%`;
            document.getElementById('active-positions').textContent = data.active_positions;
            document.getElementById('profit-24h').textContent = `${{data.profit_24h}} ETH`;
        }});
        
        // Handle MEV protection updates
        socket.on('mev_protection', (data) => {{
            const mevDiv = document.getElementById('mev-protection');
            mevDiv.innerHTML = `
                <div class="mev-stats">
                    <div class="stat-item">
                        <div class="stat-label">Protection Status</div>
                        <div class="stat-value">${{data.active ? 'Active' : 'Inactive'}}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Blocked Attacks</div>
                        <div class="stat-value">${{data.blocked_attacks}}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Risk Level</div>
                        <div class="stat-value ${{data.risk_level}}">${{data.risk_level.toUpperCase()}}</div>
                    </div>
                </div>
            `;
        }});
        
        // Handle opportunity updates
        socket.on('opportunities', (data) => {{
            const opportunitiesDiv = document.getElementById('opportunities-list');
            opportunitiesDiv.innerHTML = data.opportunities.map(opp => `
                <div class="opportunity">
                    <div class="opportunity-header">
                        <span class="pair">${{opp.token_pair}}</span>
                        <span class="profit">${{opp.potential_profit}} ETH</span>
                    </div>
                    <div class="opportunity-details">
                        <span>Route: ${{opp.route}}</span>
                        <span>Confidence: ${{opp.confidence}}%</span>
                    </div>
                </div>
            `).join('');
        }});
        
        // Initialize profit chart
        const profitChart = new Chart(
            document.getElementById('profit-chart'),
            {{
                type: 'line',
                data: {{
                    labels: [],
                    datasets: [{{
                        label: 'Profit/Loss (ETH)',
                        data: [],
                        borderColor: '#4361ee',
                        tension: 0.1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }}
        );
        
        // Handle profit updates
        socket.on('profit_update', (data) => {{
            profitChart.data.labels.push(new Date().toLocaleTimeString());
            profitChart.data.datasets[0].data.push(data.profit);
            
            if (profitChart.data.labels.length > 50) {{
                profitChart.data.labels.shift();
                profitChart.data.datasets[0].data.shift();
            }}
            
            profitChart.update();
        }});
        
        // Handle log updates
        socket.on('log_update', (data) => {{
            const logsDiv = document.getElementById('live-logs');
            const logEntry = document.createElement('div');
            logEntry.className = `log-line ${{data.level.toLowerCase()}}`;
            logEntry.textContent = `[${{new Date().toLocaleTimeString()}}] ${{data.message}}`;
            logsDiv.insertBefore(logEntry, logsDiv.firstChild);
            
            // Keep only last 100 log entries
            while (logsDiv.children.length > 100) {{
                logsDiv.removeChild(logsDiv.lastChild);
            }}
        }});
        
        // Update last updated timestamp
        socket.on('connect', () => {{
            document.getElementById('last-updated').textContent = new Date().toLocaleString();
        }});

        // Handle connection events
        socket.on('connect_error', (error) => {{
            console.error('Connection error:', error);
            const statusDiv = document.getElementById('system-status');
            statusDiv.className = 'status offline';
            statusDiv.querySelector('.status-text').textContent = 'System Offline';
        }});

        socket.on('reconnect', (attemptNumber) => {{
            console.log('Reconnected after', attemptNumber, 'attempts');
        }});
    </script>
</body>
</html>"""

    @staticmethod
    def get_css():
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

.opportunities-card,
.profit-card,
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
    animation: pulse 2s infinite;
}

.status.offline .status-indicator {
    background-color: var(--warning-color);
}

@keyframes pulse {
    0% {
        box-shadow: 0 0 0 0 rgba(76, 201, 240, 0.4);
    }
    70% {
        box-shadow: 0 0 0 10px rgba(76, 201, 240, 0);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(76, 201, 240, 0);
    }
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

.opportunity {
    background-color: #f8f9fa;
    border-radius: 5px;
    padding: 15px;
    margin-bottom: 10px;
}

.opportunity-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
}

.opportunity .pair {
    font-weight: bold;
    color: var(--primary-color);
}

.opportunity .profit {
    color: var(--success-color);
    font-weight: bold;
}

.opportunity-details {
    display: flex;
    justify-content: space-between;
    font-size: 0.9em;
    color: #666;
}

#live-logs {
    max-height: 400px;
    overflow-y: auto;
    background-color: #1e1e1e;
    border-radius: 5px;
    padding: 10px;
    font-family: 'Courier New', monospace;
}

.log-line {
    color: #d4d4d4;
    padding: 5px;
    border-left: 3px solid transparent;
    margin-bottom: 2px;
    font-size: 0.9em;
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

.mev-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 15px;
}

.risk-level {
    text-transform: uppercase;
    font-weight: bold;
}

.risk-level.low {
    color: var(--success-color);
}

.risk-level.medium {
    color: #f39c12;
}

.risk-level.high {
    color: var(--warning-color);
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
    
    .opportunity-details {
        flex-direction: column;
        gap: 5px;
    }
}
"""

async def update_stats():
    """Update dashboard statistics periodically."""
    while True:
        try:
            # Emit system status
            await sio.emit('system_status', {
                'status': latest_stats['system_status'],
                'memory_usage': latest_stats['memory_usage'].get('percent', 0),
                'active_positions': len(latest_stats['active_positions']),
                'profit_24h': latest_stats['profit_loss']['last_24h']
            })
            
            # Emit MEV protection stats
            await sio.emit('mev_protection', latest_stats['mev_protection'])
            
            # Emit opportunities
            await sio.emit('opportunities', {
                'opportunities': latest_stats['recent_opportunities'][-5:]  # Last 5 opportunities
            })
            
            # Emit profit update
            await sio.emit('profit_update', {
                'profit': latest_stats['profit_loss']['total']
            })
            
        except Exception as e:
            print(f"Error updating stats: {e}")
        
        await asyncio.sleep(1)  # Update every second

async def init_app():
    """Initialize the web application."""
    # Add routes
    app.router.add_get('/', ArbitrageDashboard.index)
    app.router.add_get('/style.css', ArbitrageDashboard.style)
    
    # Start background tasks
    asyncio.create_task(update_stats())
    
    return app

def run_server():
    """Run the dashboard server."""
    print(f"Starting Arbitrage Dashboard on port {PORT}...")
    print(f"Open this URL in your browser: http://localhost:{PORT}")
    web.run_app(init_app(), port=PORT)

if __name__ == "__main__":
    run_server()