#!/usr/bin/env python3
"""
Terminal Dashboard for Listonian Arbitrage Bot

This script provides a terminal-based dashboard for monitoring the Listonian Arbitrage Bot
in real-time. It displays financial metrics, operational metrics, and system health metrics.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp
import rich.box
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App
from textual.widgets import Header, Footer, Static, DataTable, ProgressBar
from textual.reactive import reactive
from textual.containers import Container, Horizontal, Vertical

# Configuration
API_URL = "http://localhost:9051"
UPDATE_INTERVAL = 1.0  # seconds

class MetricsPanel(Static):
    """A panel that displays metrics."""
    
    def __init__(self, title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.metrics = {}
        
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update the metrics data."""
        self.metrics = metrics
        self.refresh()
        
    def render(self):
        """Render the panel."""
        table = Table(expand=True, box=rich.box.SIMPLE)
        table.add_column("Metric")
        table.add_column("Value")
        
        for key, value in self.metrics.items():
            if isinstance(value, dict):
                # Skip nested dictionaries
                continue
            elif isinstance(value, (int, float)):
                # Format numbers
                if abs(value) > 1000000:
                    formatted_value = f"{value/1000000:.2f}M"
                elif abs(value) > 1000:
                    formatted_value = f"{value/1000:.2f}K"
                else:
                    formatted_value = f"{value:.4f}" if isinstance(value, float) else str(value)
            else:
                formatted_value = str(value)
                
            # Convert snake_case to Title Case
            display_key = " ".join(word.capitalize() for word in key.split("_"))
            table.add_row(display_key, formatted_value)
            
        return Panel(table, title=self.title, border_style="blue")

class SystemMetricsPanel(Static):
    """A panel that displays system metrics."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cpu = 0.0
        self.memory = 0.0
        self.disk = 0.0
        self.network_in = 0
        self.network_out = 0
        
    def update_metrics(self, metrics: Dict[str, Any]):
        """Update the system metrics."""
        if "cpu" in metrics and "usage_percent" in metrics["cpu"]:
            self.cpu = metrics["cpu"]["usage_percent"]
            
        if "memory" in metrics and "percent" in metrics["memory"]:
            self.memory = metrics["memory"]["percent"]
            
        if "disk" in metrics and "percent" in metrics["disk"]:
            self.disk = metrics["disk"]["percent"]
            
        if "network" in metrics:
            if "recv_rate" in metrics["network"]:
                self.network_in = metrics["network"]["recv_rate"]
            if "sent_rate" in metrics["network"]:
                self.network_out = metrics["network"]["sent_rate"]
                
        self.refresh()
        
    def render(self):
        """Render the system metrics panel."""
        table = Table(expand=True, box=rich.box.SIMPLE)
        table.add_column("Resource")
        table.add_column("Usage")
        table.add_column("Value")
        
        # CPU usage
        cpu_bar = ProgressBar(total=100, completed=int(self.cpu), width=20)
        table.add_row("CPU", Text(f"{self.cpu:.1f}%"), cpu_bar)
        
        # Memory usage
        memory_bar = ProgressBar(total=100, completed=int(self.memory), width=20)
        table.add_row("Memory", Text(f"{self.memory:.1f}%"), memory_bar)
        
        # Disk usage
        disk_bar = ProgressBar(total=100, completed=int(self.disk), width=20)
        table.add_row("Disk", Text(f"{self.disk:.1f}%"), disk_bar)
        
        # Network usage
        network_in_text = f"{self.network_in/1024:.1f} KB/s" if self.network_in < 1024*1024 else f"{self.network_in/(1024*1024):.1f} MB/s"
        network_out_text = f"{self.network_out/1024:.1f} KB/s" if self.network_out < 1024*1024 else f"{self.network_out/(1024*1024):.1f} MB/s"
        table.add_row("Network In", network_in_text, "")
        table.add_row("Network Out", network_out_text, "")
        
        return Panel(table, title="System Resources", border_style="green")

class TradesPanel(Static):
    """A panel that displays recent trades."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trades = []
        
    def update_trades(self, trades: List[Dict[str, Any]]):
        """Update the trades data."""
        self.trades = trades[-10:]  # Keep only the 10 most recent trades
        self.refresh()
        
    def render(self):
        """Render the trades panel."""
        table = Table(expand=True, box=rich.box.SIMPLE)
        table.add_column("Time")
        table.add_column("Pair")
        table.add_column("Profit")
        table.add_column("Gas")
        
        for trade in self.trades:
            # Format timestamp
            timestamp = trade.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    formatted_time = dt.strftime("%H:%M:%S")
                except (ValueError, TypeError):
                    formatted_time = timestamp
            else:
                formatted_time = ""
                
            # Get other trade data
            pair = trade.get("token_pair", "")
            profit = trade.get("profit", 0.0)
            gas_cost = trade.get("gas_cost", 0.0)
            
            # Format profit with color
            profit_text = Text(f"{profit:.6f} ETH")
            if profit > 0:
                profit_text.stylize("green")
            elif profit < 0:
                profit_text.stylize("red")
                
            table.add_row(formatted_time, pair, profit_text, f"{gas_cost:.6f} ETH")
            
        return Panel(table, title="Recent Trades", border_style="yellow")

class ArbitrageOpportunitiesPanel(Static):
    """A panel that displays arbitrage opportunities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.opportunities = []
        
    def update_opportunities(self, opportunities: List[Dict[str, Any]]):
        """Update the opportunities data."""
        self.opportunities = opportunities[-5:]  # Keep only the 5 most recent opportunities
        self.refresh()
        
    def render(self):
        """Render the opportunities panel."""
        table = Table(expand=True, box=rich.box.SIMPLE)
        table.add_column("DEX Pair")
        table.add_column("Spread")
        table.add_column("Potential Profit")
        
        for opportunity in self.opportunities:
            dex_pair = " → ".join(opportunity.get("dex_pair", ["", ""]))
            spread = opportunity.get("spread", 0.0)
            profit = opportunity.get("profit_potential", 0.0)
            
            table.add_row(dex_pair, f"{spread:.2f}%", f"{profit:.6f} ETH")
            
        return Panel(table, title="Arbitrage Opportunities", border_style="magenta")

class StatusPanel(Static):
    """A panel that displays system status."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = "Initializing"
        self.uptime = 0
        self.block_number = 0
        self.wallet_balance = 0.0
        self.last_update = ""
        
    def update_status(self, status: Dict[str, Any]):
        """Update the status data."""
        self.status = status.get("status", "Unknown")
        self.uptime = status.get("uptime", 0)
        self.block_number = status.get("current_block", 0)
        self.wallet_balance = status.get("wallet_balance", 0.0)
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.refresh()
        
    def render(self):
        """Render the status panel."""
        # Format uptime
        hours, remainder = divmod(int(self.uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        status_text = Text()
        status_text.append("Status: ")
        if self.status == "running":
            status_text.append(self.status, style="green bold")
        else:
            status_text.append(self.status, style="yellow bold")
            
        status_text.append(f"\nUptime: {uptime_str}")
        status_text.append(f"\nCurrent Block: {self.block_number}")
        status_text.append(f"\nWallet Balance: {self.wallet_balance:.6f} ETH")
        status_text.append(f"\nLast Update: {self.last_update}")
        
        return Panel(status_text, title="System Status", border_style="red")

class TerminalDashboard(App):
    """Terminal dashboard application."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("h", "help", "Help"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_client = None
        self.update_task = None
        
    async def on_mount(self):
        """Set up the dashboard layout."""
        # Create API client
        self.api_client = ApiClient(API_URL)
        
        # Create layout
        await self.view.dock(Header(show_clock=True), edge="top")
        await self.view.dock(Footer(), edge="bottom")
        
        # Create main layout
        self.status_panel = StatusPanel()
        self.system_panel = SystemMetricsPanel()
        self.financial_panel = MetricsPanel(title="Financial Metrics")
        self.trades_panel = TradesPanel()
        
        # Create containers
        left_container = Vertical(self.status_panel, self.system_panel, classes="left")
        right_container = Vertical(self.financial_panel, self.trades_panel, classes="right")
        
        horizontal_container = Horizontal(left_container, right_container, id="main_horizontal")
        main_container = Container(horizontal_container, id="main_container")
        
        await self.view.dock(main_container)
        
        # Start update task
        self.update_task = asyncio.create_task(self.update_loop())
        
    async def update_loop(self):
        """Update the dashboard periodically."""
        try:
            while True:
                await self.update_metrics()
                await asyncio.sleep(UPDATE_INTERVAL)
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except Exception as e:
            self.log(f"Error in update loop: {e}")
            
    async def update_metrics(self):
        """Update all metrics panels."""
        try:
            # Get system metrics
            system_metrics = await self.api_client.get_detailed_system_metrics()
            if system_metrics:
                self.system_panel.update_metrics(system_metrics)
                
            # Get financial metrics
            financial_metrics = await self.api_client.get_financial_metrics()
            if financial_metrics:
                self.financial_panel.update_metrics(financial_metrics)
                
            # Get trades
            trades = await self.api_client.get_trades()
            if trades:
                self.trades_panel.update_trades(trades)
                
            # Get status
            status = await self.api_client.get_status()
            if status:
                self.status_panel.update_status(status)
                
        except Exception as e:
            self.log(f"Error updating metrics: {e}")
            
    async def action_refresh(self):
        """Refresh all metrics."""
        await self.update_metrics()
        
    async def action_quit(self):
        """Quit the application."""
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        await self.api_client.close()
        self.exit()
        
    def log(self, message: str):
        """Log a message."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", file=sys.stderr)

class ApiClient:
    """Client for the dashboard API."""
    
    def __init__(self, base_url: str):
        """Initialize the API client."""
        self.base_url = base_url
        self.session = None
        
    async def _ensure_session(self):
        """Ensure that the session is created."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make a GET request to the API."""
        await self._ensure_session()
        try:
            async with self.session.get(f"{self.base_url}{endpoint}", timeout=5) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error: {response.status} - {await response.text()}", file=sys.stderr)
                    return None
        except Exception as e:
            print(f"Error making request to {endpoint}: {e}", file=sys.stderr)
            return None
            
    async def get_detailed_system_metrics(self) -> Optional[Dict[str, Any]]:
        """Get detailed system metrics."""
        # This would normally use a WebSocket, but for simplicity we'll use polling
        return await self._get("/api/system/detailed")
        
    async def get_financial_metrics(self) -> Optional[Dict[str, Any]]:
        """Get financial metrics."""
        metrics = await self._get("/api/metrics")
        if metrics:
            return {
                "total_profit": metrics.get("totalProfit", 0.0),
                "success_rate": metrics.get("successRate", 0.0),
                "average_profit": metrics.get("averageProfit", 0.0),
                "total_executions": metrics.get("totalExecutions", 0),
                "wallet_balance": metrics.get("walletBalance", 0.0),
                "average_gas": metrics.get("averageGas", 0.0),
            }
        return None
        
    async def get_trades(self) -> Optional[List[Dict[str, Any]]]:
        """Get recent trades."""
        trades = await self._get("/api/trades")
        if trades:
            return trades.get("trades", [])
        return []
        
    async def get_status(self) -> Optional[Dict[str, Any]]:
        """Get system status."""
        status = await self._get("/api/status")
        metrics = await self._get("/api/metrics")
        
        if status and metrics:
            return {
                "status": status.get("status", "Unknown"),
                "uptime": status.get("uptime", 0),
                "current_block": status.get("current_block", 0),
                "wallet_balance": metrics.get("walletBalance", 0.0),
            }
        return None

def main():
    """Run the terminal dashboard."""
    app = TerminalDashboard()
    app.run()

if __name__ == "__main__":
    main()