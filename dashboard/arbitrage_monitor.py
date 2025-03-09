"""
Arbitrage Monitoring Dashboard

This module provides a web-based dashboard to monitor:
- Arbitrage performance
- Flash loan success rates
- MEV protection effectiveness
- Gas usage optimization
- Profit metrics

This dashboard helps identify optimization opportunities and track system performance.
"""

import asyncio
import datetime
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from pathlib import Path

import aiohttp
from aiohttp import web
import aiofiles
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from io import BytesIO
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Dashboard configuration
DEFAULT_CONFIG = {
    "host": "localhost",
    "port": 8080,
    "refresh_interval": 30,  # seconds
    "data_directory": "monitoring_data",
    "metrics_history_size": 100,
    "charts_enabled": True,
    "alerts_enabled": True,
    "profit_threshold_alert": 0.001,  # ETH
    "gas_price_threshold_alert": 150,  # GWEI
    "mev_risk_threshold_alert": "high"
}

class ArbitrageMonitor:
    """
    Monitor and dashboard for arbitrage performance with MEV protection.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the arbitrage monitor.
        
        Args:
            config: Optional configuration dictionary
        """
        # Load configuration
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Create data directory if it doesn't exist
        self.data_dir = Path(self.config["data_directory"])
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize data structures
        self.arbitrage_metrics: List[Dict[str, Any]] = []
        self.flash_loan_metrics: List[Dict[str, Any]] = []
        self.mev_protection_metrics: List[Dict[str, Any]] = []
        self.gas_metrics: List[Dict[str, Any]] = []
        self.profit_metrics: List[Dict[str, Any]] = []
        
        # Last update timestamp
        self.last_update = time.time()
        
        # Initialize web app
        self.app = web.Application()
        self.setup_routes()
        
        logger.info(f"Arbitrage monitor initialized with config: {self.config}")
    
    def setup_routes(self) -> None:
        """Set up web routes for the dashboard."""
        self.app.router.add_get('/', self.handle_dashboard)
        self.app.router.add_get('/api/metrics', self.handle_get_metrics)
        self.app.router.add_post('/api/metrics', self.handle_post_metrics)
        self.app.router.add_get('/api/metrics/arbitrage', self.handle_get_arbitrage_metrics)
        self.app.router.add_get('/api/metrics/flash_loan', self.handle_get_flash_loan_metrics)
        self.app.router.add_get('/api/metrics/mev_protection', self.handle_get_mev_protection_metrics)
        self.app.router.add_get('/api/metrics/gas', self.handle_get_gas_metrics)
        self.app.router.add_get('/api/metrics/profit', self.handle_get_profit_metrics)
        self.app.router.add_get('/charts/arbitrage', self.handle_get_arbitrage_chart)
        self.app.router.add_get('/charts/flash_loan', self.handle_get_flash_loan_chart)
        self.app.router.add_get('/charts/mev_protection', self.handle_get_mev_protection_chart)
        self.app.router.add_get('/charts/gas', self.handle_get_gas_chart)
        self.app.router.add_get('/charts/profit', self.handle_get_profit_chart)
        self.app.router.add_static('/static', Path(__file__).parent / 'static')
    
    async def handle_dashboard(self, request: web.Request) -> web.Response:
        """Handle dashboard page request."""
        try:
            dashboard_html = self._generate_dashboard_html()
            return web.Response(text=dashboard_html, content_type='text/html')
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}", exc_info=True)
            return web.Response(text=f"Error generating dashboard: {str(e)}", status=500)
    
    async def handle_get_metrics(self, request: web.Request) -> web.Response:
        """Handle API request to get all metrics."""
        try:
            metrics = {
                "arbitrage": self.arbitrage_metrics,
                "flash_loan": self.flash_loan_metrics,
                "mev_protection": self.mev_protection_metrics,
                "gas": self.gas_metrics,
                "profit": self.profit_metrics,
                "last_update": self.last_update
            }
            return web.json_response(metrics)
        except Exception as e:
            logger.error(f"Error getting metrics: {e}", exc_info=True)
            return web.Response(text=f"Error: {str(e)}", status=500)
    
    async def handle_post_metrics(self, request: web.Request) -> web.Response:
        """Handle API request to post new metrics."""
        try:
            data = await request.json()
            
            # Validate data
            if not isinstance(data, dict):
                return web.Response(text="Invalid data format", status=400)
            
            # Process metrics by type
            if "arbitrage" in data:
                self._add_metrics(self.arbitrage_metrics, data["arbitrage"])
            
            if "flash_loan" in data:
                self._add_metrics(self.flash_loan_metrics, data["flash_loan"])
            
            if "mev_protection" in data:
                self._add_metrics(self.mev_protection_metrics, data["mev_protection"])
            
            if "gas" in data:
                self._add_metrics(self.gas_metrics, data["gas"])
            
            if "profit" in data:
                self._add_metrics(self.profit_metrics, data["profit"])
            
            # Update timestamp
            self.last_update = time.time()
            
            # Save to file in background
            asyncio.create_task(self._save_metrics_to_file())
            
            # Check for alerts
            self._check_alerts(data)
            
            return web.Response(text="Metrics recorded successfully")
        except Exception as e:
            logger.error(f"Error posting metrics: {e}", exc_info=True)
            return web.Response(text=f"Error: {str(e)}", status=500)
    
    async def handle_get_arbitrage_metrics(self, request: web.Request) -> web.Response:
        """Handle API request to get arbitrage metrics."""
        return web.json_response(self.arbitrage_metrics)
    
    async def handle_get_flash_loan_metrics(self, request: web.Request) -> web.Response:
        """Handle API request to get flash loan metrics."""
        return web.json_response(self.flash_loan_metrics)
    
    async def handle_get_mev_protection_metrics(self, request: web.Request) -> web.Response:
        """Handle API request to get MEV protection metrics."""
        return web.json_response(self.mev_protection_metrics)
    
    async def handle_get_gas_metrics(self, request: web.Request) -> web.Response:
        """Handle API request to get gas metrics."""
        return web.json_response(self.gas_metrics)
    
    async def handle_get_profit_metrics(self, request: web.Request) -> web.Response:
        """Handle API request to get profit metrics."""
        return web.json_response(self.profit_metrics)
    
    async def handle_get_arbitrage_chart(self, request: web.Request) -> web.Response:
        """Handle request for arbitrage chart."""
        if not self.config["charts_enabled"]:
            return web.Response(text="Charts are disabled", status=404)
        
        try:
            # Generate chart
            chart_data = self._generate_chart(
                self.arbitrage_metrics, 
                "timestamp", 
                ["paths_found", "paths_executed", "success_rate"],
                "Arbitrage Performance"
            )
            return web.Response(body=chart_data, content_type='image/png')
        except Exception as e:
            logger.error(f"Error generating arbitrage chart: {e}", exc_info=True)
            return web.Response(text=f"Error: {str(e)}", status=500)
    
    async def handle_get_flash_loan_chart(self, request: web.Request) -> web.Response:
        """Handle request for flash loan chart."""
        if not self.config["charts_enabled"]:
            return web.Response(text="Charts are disabled", status=404)
        
        try:
            # Generate chart
            chart_data = self._generate_chart(
                self.flash_loan_metrics, 
                "timestamp", 
                ["loans_executed", "success_rate", "average_cost"],
                "Flash Loan Performance"
            )
            return web.Response(body=chart_data, content_type='image/png')
        except Exception as e:
            logger.error(f"Error generating flash loan chart: {e}", exc_info=True)
            return web.Response(text=f"Error: {str(e)}", status=500)
    
    async def handle_get_mev_protection_chart(self, request: web.Request) -> web.Response:
        """Handle request for MEV protection chart."""
        if not self.config["charts_enabled"]:
            return web.Response(text="Charts are disabled", status=404)
        
        try:
            # Generate chart
            chart_data = self._generate_chart(
                self.mev_protection_metrics, 
                "timestamp", 
                ["attacks_detected", "bundles_submitted", "bundle_success_rate"],
                "MEV Protection Performance"
            )
            return web.Response(body=chart_data, content_type='image/png')
        except Exception as e:
            logger.error(f"Error generating MEV protection chart: {e}", exc_info=True)
            return web.Response(text=f"Error: {str(e)}", status=500)
    
    async def handle_get_gas_chart(self, request: web.Request) -> web.Response:
        """Handle request for gas chart."""
        if not self.config["charts_enabled"]:
            return web.Response(text="Charts are disabled", status=404)
        
        try:
            # Generate chart
            chart_data = self._generate_chart(
                self.gas_metrics, 
                "timestamp", 
                ["average_gas_price", "average_gas_used", "total_gas_cost"],
                "Gas Usage"
            )
            return web.Response(body=chart_data, content_type='image/png')
        except Exception as e:
            logger.error(f"Error generating gas chart: {e}", exc_info=True)
            return web.Response(text=f"Error: {str(e)}", status=500)
    
    async def handle_get_profit_chart(self, request: web.Request) -> web.Response:
        """Handle request for profit chart."""
        if not self.config["charts_enabled"]:
            return web.Response(text="Charts are disabled", status=404)
        
        try:
            # Generate chart
            chart_data = self._generate_chart(
                self.profit_metrics, 
                "timestamp", 
                ["total_profit", "average_profit", "profit_after_gas"],
                "Profit Metrics"
            )
            return web.Response(body=chart_data, content_type='image/png')
        except Exception as e:
            logger.error(f"Error generating profit chart: {e}", exc_info=True)
            return web.Response(text=f"Error: {str(e)}", status=500)
    
    def _add_metrics(self, metric_list: List[Dict[str, Any]], new_metrics: Any) -> None:
        """Add new metrics to a metric list with size limiting."""
        if isinstance(new_metrics, list):
            metric_list.extend(new_metrics)
        else:
            metric_list.append(new_metrics)
        
        # Add timestamp if not present
        for metric in metric_list:
            if "timestamp" not in metric:
                metric["timestamp"] = time.time()
        
        # Keep list size limited
        max_size = self.config["metrics_history_size"]
        if len(metric_list) > max_size:
            metric_list[:] = metric_list[-max_size:]
    
    async def _save_metrics_to_file(self) -> None:
        """Save metrics to files for persistence."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d")
            
            # Save each metric type
            await self._save_metric_to_file("arbitrage", self.arbitrage_metrics, timestamp)
            await self._save_metric_to_file("flash_loan", self.flash_loan_metrics, timestamp)
            await self._save_metric_to_file("mev_protection", self.mev_protection_metrics, timestamp)
            await self._save_metric_to_file("gas", self.gas_metrics, timestamp)
            await self._save_metric_to_file("profit", self.profit_metrics, timestamp)
            
        except Exception as e:
            logger.error(f"Error saving metrics to file: {e}", exc_info=True)
    
    async def _save_metric_to_file(self, metric_type: str, metrics: List[Dict[str, Any]], timestamp: str) -> None:
        """Save a specific metric type to file."""
        if not metrics:
            return
            
        file_path = self.data_dir / f"{metric_type}_{timestamp}.json"
        
        try:
            # Read existing data if file exists
            existing_data = []
            if file_path.exists():
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    if content:
                        existing_data = json.loads(content)
            
            # Combine with new data
            combined_data = existing_data + metrics
            
            # Write back to file
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(combined_data, default=str))
                
        except Exception as e:
            logger.error(f"Error saving {metric_type} metrics to {file_path}: {e}", exc_info=True)
    
    def _check_alerts(self, data: Dict[str, Any]) -> None:
        """Check for alert conditions in new metrics."""
        if not self.config["alerts_enabled"]:
            return
            
        try:
            # Check profit threshold
            if "profit" in data:
                profit_metrics = data["profit"]
                if isinstance(profit_metrics, list):
                    for metric in profit_metrics:
                        self._check_profit_alert(metric)
                else:
                    self._check_profit_alert(profit_metrics)
            
            # Check gas price threshold
            if "gas" in data:
                gas_metrics = data["gas"]
                if isinstance(gas_metrics, list):
                    for metric in gas_metrics:
                        self._check_gas_alert(metric)
                else:
                    self._check_gas_alert(gas_metrics)
            
            # Check MEV risk threshold
            if "mev_protection" in data:
                mev_metrics = data["mev_protection"]
                if isinstance(mev_metrics, list):
                    for metric in mev_metrics:
                        self._check_mev_alert(metric)
                else:
                    self._check_mev_alert(mev_metrics)
                    
        except Exception as e:
            logger.error(f"Error checking alerts: {e}", exc_info=True)
    
    def _check_profit_alert(self, metric: Dict[str, Any]) -> None:
        """Check if profit metric triggers an alert."""
        threshold = self.config["profit_threshold_alert"]
        
        if "total_profit" in metric and float(metric["total_profit"]) > threshold:
            logger.info(f"PROFIT ALERT: Total profit {metric['total_profit']} exceeds threshold {threshold}")
    
    def _check_gas_alert(self, metric: Dict[str, Any]) -> None:
        """Check if gas metric triggers an alert."""
        threshold = self.config["gas_price_threshold_alert"]
        
        if "average_gas_price" in metric and float(metric["average_gas_price"]) > threshold:
            logger.warning(f"GAS ALERT: Average gas price {metric['average_gas_price']} exceeds threshold {threshold}")
    
    def _check_mev_alert(self, metric: Dict[str, Any]) -> None:
        """Check if MEV metric triggers an alert."""
        threshold = self.config["mev_risk_threshold_alert"]
        
        if "risk_level" in metric and metric["risk_level"] == threshold:
            logger.warning(f"MEV ALERT: Risk level {metric['risk_level']} matches threshold {threshold}")
    
    def _generate_chart(
        self,
        metrics: List[Dict[str, Any]],
        x_key: str,
        y_keys: List[str],
        title: str
    ) -> bytes:
        """Generate chart for metrics."""
        if not metrics:
            # Create empty chart
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_title(f"{title} - No Data")
            ax.text(0.5, 0.5, "No data available", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
            
            # Save to bytes
            buf = BytesIO()
            fig.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            return buf.getvalue()
        
        # Convert to DataFrame
        df = pd.DataFrame(metrics)
        
        # Convert timestamp to datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot each y key
        for y_key in y_keys:
            if y_key in df.columns:
                ax.plot(df[x_key], df[y_key], label=y_key)
        
        # Add labels and legend
        ax.set_title(title)
        ax.set_xlabel("Time")
        ax.set_ylabel("Value")
        ax.legend()
        ax.grid(True)
        
        # Format x-axis as datetime
        fig.autofmt_xdate()
        
        # Save to bytes
        buf = BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    
    def _generate_dashboard_html(self) -> str:
        """Generate HTML for the dashboard."""
        # Get the last metrics for each type
        last_arbitrage = self.arbitrage_metrics[-1] if self.arbitrage_metrics else {}
        last_flash_loan = self.flash_loan_metrics[-1] if self.flash_loan_metrics else {}
        last_mev = self.mev_protection_metrics[-1] if self.mev_protection_metrics else {}
        last_gas = self.gas_metrics[-1] if self.gas_metrics else {}
        last_profit = self.profit_metrics[-1] if self.profit_metrics else {}
        
        # Format update time
        update_time = datetime.datetime.fromtimestamp(self.last_update).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Arbitrage Monitor Dashboard</title>
            <meta http-equiv="refresh" content="{self.config['refresh_interval']}">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                h1, h2, h3 {{
                    color: #333;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .card {{
                    background-color: white;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .metric-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 15px;
                }}
                .metric-card {{
                    padding: 15px;
                    border-radius: 5px;
                    background-color: #ecf0f1;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .metric-label {{
                    font-size: 14px;
                    color: #7f8c8d;
                }}
                .chart-container {{
                    margin-top: 20px;
                }}
                .good {{
                    color: #27ae60;
                }}
                .warning {{
                    color: #f39c12;
                }}
                .danger {{
                    color: #e74c3c;
                }}
                .info {{
                    color: #3498db;
                }}
                footer {{
                    margin-top: 30px;
                    text-align: center;
                    font-size: 12px;
                    color: #7f8c8d;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Arbitrage Monitoring Dashboard</h1>
                    <p>Last updated: {update_time}</p>
                </div>
                
                <!-- Profit Section -->
                <div class="card">
                    <h2>Profit Metrics</h2>
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-label">Total Profit (ETH)</div>
                            <div class="metric-value good">{last_profit.get('total_profit', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Average Profit (ETH)</div>
                            <div class="metric-value good">{last_profit.get('average_profit', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Profit After Gas (ETH)</div>
                            <div class="metric-value good">{last_profit.get('profit_after_gas', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Profit Margin (%)</div>
                            <div class="metric-value good">{last_profit.get('profit_margin', 'N/A')}</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <img src="/charts/profit" alt="Profit Chart" width="100%">
                    </div>
                </div>
                
                <!-- Arbitrage Section -->
                <div class="card">
                    <h2>Arbitrage Performance</h2>
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-label">Paths Found</div>
                            <div class="metric-value info">{last_arbitrage.get('paths_found', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Paths Executed</div>
                            <div class="metric-value info">{last_arbitrage.get('paths_executed', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Success Rate (%)</div>
                            <div class="metric-value info">{last_arbitrage.get('success_rate', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Average Execution Time (ms)</div>
                            <div class="metric-value info">{last_arbitrage.get('avg_execution_time', 'N/A')}</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <img src="/charts/arbitrage" alt="Arbitrage Chart" width="100%">
                    </div>
                </div>
                
                <!-- Flash Loan Section -->
                <div class="card">
                    <h2>Flash Loan Performance</h2>
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-label">Loans Executed</div>
                            <div class="metric-value info">{last_flash_loan.get('loans_executed', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Success Rate (%)</div>
                            <div class="metric-value info">{last_flash_loan.get('success_rate', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Average Cost (ETH)</div>
                            <div class="metric-value info">{last_flash_loan.get('average_cost', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Total Volume (ETH)</div>
                            <div class="metric-value info">{last_flash_loan.get('total_volume', 'N/A')}</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <img src="/charts/flash_loan" alt="Flash Loan Chart" width="100%">
                    </div>
                </div>
                
                <!-- MEV Protection Section -->
                <div class="card">
                    <h2>MEV Protection Performance</h2>
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-label">Attacks Detected</div>
                            <div class="metric-value warning">{last_mev.get('attacks_detected', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Bundles Submitted</div>
                            <div class="metric-value info">{last_mev.get('bundles_submitted', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Bundle Success Rate (%)</div>
                            <div class="metric-value info">{last_mev.get('bundle_success_rate', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Risk Level</div>
                            <div class="metric-value warning">{last_mev.get('risk_level', 'N/A')}</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <img src="/charts/mev_protection" alt="MEV Protection Chart" width="100%">
                    </div>
                </div>
                
                <!-- Gas Section -->
                <div class="card">
                    <h2>Gas Metrics</h2>
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-label">Average Gas Price (GWEI)</div>
                            <div class="metric-value warning">{last_gas.get('average_gas_price', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Average Gas Used</div>
                            <div class="metric-value info">{last_gas.get('average_gas_used', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Total Gas Cost (ETH)</div>
                            <div class="metric-value warning">{last_gas.get('total_gas_cost', 'N/A')}</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Transactions Count</div>
                            <div class="metric-value info">{last_gas.get('tx_count', 'N/A')}</div>
                        </div>
                    </div>
                    <div class="chart-container">
                        <img src="/charts/gas" alt="Gas Chart" width="100%">
                    </div>
                </div>
                
                <footer>
                    <p>Arbitrage Monitoring Dashboard | Refreshes every {self.config['refresh_interval']} seconds</p>
                </footer>
            </div>
            
            <script>
                // Auto-refresh charts and data
                function refreshData() {{
                    const charts = document.querySelectorAll('img[src^="/charts/"]');
                    charts.forEach(chart => {{
                        const src = chart.src.split('?')[0];
                        chart.src = src + '?t=' + new Date().getTime();
                    }});
                }}
                
                // Refresh every {self.config['refresh_interval']} seconds
                setInterval(refreshData, {self.config['refresh_interval'] * 1000});
            </script>
        </body>
        </html>
        """
        
        return html
    
    async def start(self) -> None:
        """Start the dashboard server."""
        # Load existing metrics from files
        await self._load_metrics_from_files()
        
        # Start the web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.config["host"], self.config["port"])
        await site.start()
        
        logger.info(f"Dashboard started at http://{self.config['host']}:{self.config['port']}")
        
        # Keep the server running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    
    async def _load_metrics_from_files(self) -> None:
        """Load metrics from saved files."""
        try:
            # Get all metric files
            for file_path in self.data_dir.glob("*.json"):
                # Determine metric type from filename
                file_name = file_path.name
                metric_type = file_name.split("_")[0]
                
                # Read file
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    metrics = json.loads(content)
                
                # Add to appropriate metric list
                if metric_type == "arbitrage":
                    self._add_metrics(self.arbitrage_metrics, metrics)
                elif metric_type == "flash_loan":
                    self._add_metrics(self.flash_loan_metrics, metrics)
                elif metric_type == "mev_protection":
                    self._add_metrics(self.mev_protection_metrics, metrics)
                elif metric_type == "gas":
                    self._add_metrics(self.gas_metrics, metrics)
                elif metric_type == "profit":
                    self._add_metrics(self.profit_metrics, metrics)
            
            logger.info(f"Loaded metrics from {self.data_dir}")
            
        except Exception as e:
            logger.error(f"Error loading metrics from files: {e}", exc_info=True)

async def update_metrics(monitor_url: str, metrics: Dict[str, Any]) -> None:
    """
    Update metrics in the monitoring dashboard.
    
    Args:
        monitor_url: URL of the monitoring dashboard API
        metrics: Metrics to update
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{monitor_url}/api/metrics", json=metrics) as response:
                if response.status != 200:
                    content = await response.text()
                    logger.error(f"Failed to update metrics: {response.status} - {content}")
                else:
                    logger.debug("Metrics updated successfully")
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")

async def get_metrics(monitor_url: str) -> Optional[Dict[str, Any]]:
    """
    Get current metrics from the monitoring dashboard.
    
    Args:
        monitor_url: URL of the monitoring dashboard API
        
    Returns:
        Current metrics or None if failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{monitor_url}/api/metrics") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    content = await response.text()
                    logger.error(f"Failed to get metrics: {response.status} - {content}")
                    return None
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return None

async def main():
    """Start the monitoring dashboard."""
    # Load configuration from file if exists
    config_path = Path("config/monitor_config.json")
    config = None
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
    
    # Create and start monitor
    monitor = ArbitrageMonitor(config)
    
    # Add some sample metrics for demonstration
    await _add_sample_metrics(monitor)
    
    # Start the server
    await monitor.start()

async def _add_sample_metrics(monitor: ArbitrageMonitor) -> None:
    """Add sample metrics for demonstration."""
    # Sample arbitrage metrics
    arbitrage_metrics = {
        "paths_found": 15,
        "paths_executed": 8,
        "success_rate": 53.33,
        "avg_execution_time": 120
    }
    
    # Sample flash loan metrics
    flash_loan_metrics = {
        "loans_executed": 8,
        "success_rate": 100.0,
        "average_cost": 0.0009,
        "total_volume": 10.5
    }
    
    # Sample MEV protection metrics
    mev_metrics = {
        "attacks_detected": 3,
        "bundles_submitted": 8,
        "bundle_success_rate": 87.5,
        "risk_level": "medium"
    }
    
    # Sample gas metrics
    gas_metrics = {
        "average_gas_price": 35.2,
        "average_gas_used": 350000,
        "total_gas_cost": 0.012,
        "tx_count": 8
    }
    
    # Sample profit metrics
    profit_metrics = {
        "total_profit": 0.085,
        "average_profit": 0.0106,
        "profit_after_gas": 0.073,
        "profit_margin": 3.2
    }
    
    # Add to monitor
    monitor._add_metrics(monitor.arbitrage_metrics, arbitrage_metrics)
    monitor._add_metrics(monitor.flash_loan_metrics, flash_loan_metrics)
    monitor._add_metrics(monitor.mev_protection_metrics, mev_metrics)
    monitor._add_metrics(monitor.gas_metrics, gas_metrics)
    monitor._add_metrics(monitor.profit_metrics, profit_metrics)

if __name__ == "__main__":
    # Create static directory if it doesn't exist
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # Run the server
    asyncio.run(main())