"""
Metrics dashboard for visualizing system performance metrics.
Provides real-time visualization of system, trading, and blockchain metrics.
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List

from .collector import metrics_collector
from .processor import metrics_processor

class MetricsDashboard:
    """Real-time metrics visualization dashboard."""

    def __init__(self, port: int = 8050):
        self.app = dash.Dash(__name__)
        self.port = port
        self._setup_layout()
        self._setup_callbacks()

    def _setup_layout(self):
        """Set up the dashboard layout."""
        self.app.layout = html.Div([
            html.H1('System Performance Dashboard'),
            
            # System Health Overview
            html.Div([
                html.H2('System Health'),
                html.Div(id='health-status'),
                html.Div(id='performance-score')
            ], className='health-overview'),
            
            # System Metrics
            html.Div([
                html.H2('System Metrics'),
                dcc.Graph(id='cpu-memory-graph'),
                dcc.Graph(id='disk-usage-graph')
            ], className='system-metrics'),
            
            # Trading Metrics
            html.Div([
                html.H2('Trading Performance'),
                dcc.Graph(id='profit-graph'),
                dcc.Graph(id='execution-time-graph')
            ], className='trading-metrics'),
            
            # Blockchain Metrics
            html.Div([
                html.H2('Blockchain Metrics'),
                dcc.Graph(id='gas-price-graph'),
                dcc.Graph(id='block-time-graph')
            ], className='blockchain-metrics'),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=1000,  # 1 second refresh
                n_intervals=0
            )
        ])

    def _setup_callbacks(self):
        """Set up dashboard callbacks for real-time updates."""
        
        @self.app.callback(
            [Output('health-status', 'children'),
             Output('performance-score', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_health_status(n):
            # Get latest metrics
            system_metrics = metrics_collector.get_recent_metrics('system', 1)
            trading_metrics = metrics_collector.get_recent_metrics('trading', 1)
            
            # Process metrics
            all_metrics = {
                'system': system_metrics[0] if system_metrics else {},
                'trading': trading_metrics[0] if trading_metrics else {}
            }
            
            # Get health status and score
            status, warnings = metrics_processor.get_health_status(all_metrics)
            score = metrics_processor.calculate_performance_score(all_metrics)
            
            # Create status display
            status_color = {
                'healthy': 'green',
                'degraded': 'orange',
                'critical': 'red'
            }.get(status, 'grey')
            
            status_display = html.Div([
                html.H3(f'Status: {status.upper()}', 
                       style={'color': status_color}),
                html.Ul([html.Li(w) for w in warnings]) if warnings else None
            ])
            
            score_display = html.H3(f'Performance Score: {score:.1f}')
            
            return status_display, score_display

        @self.app.callback(
            Output('cpu-memory-graph', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_cpu_memory_graph(n):
            metrics = metrics_collector.get_recent_metrics('system', 100)
            if not metrics:
                return go.Figure()
            
            df = pd.DataFrame(metrics)
            
            return {
                'data': [
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['cpu_percent'],
                        name='CPU Usage',
                        line={'color': 'blue'}
                    ),
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['memory_percent'],
                        name='Memory Usage',
                        line={'color': 'red'}
                    )
                ],
                'layout': {
                    'title': 'CPU and Memory Usage',
                    'xaxis': {'title': 'Time'},
                    'yaxis': {'title': 'Percentage'}
                }
            }

        @self.app.callback(
            Output('profit-graph', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_profit_graph(n):
            metrics = metrics_collector.get_recent_metrics('trading', 100)
            if not metrics:
                return go.Figure()
            
            df = pd.DataFrame(metrics)
            
            return {
                'data': [
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['profit'],
                        name='Profit',
                        line={'color': 'green'}
                    )
                ],
                'layout': {
                    'title': 'Trading Profit',
                    'xaxis': {'title': 'Time'},
                    'yaxis': {'title': 'Profit'}
                }
            }

        @self.app.callback(
            Output('gas-price-graph', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_gas_price_graph(n):
            metrics = metrics_collector.get_recent_metrics('blockchain', 100)
            if not metrics:
                return go.Figure()
            
            df = pd.DataFrame(metrics)
            
            return {
                'data': [
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['gas_price'],
                        name='Gas Price',
                        line={'color': 'purple'}
                    )
                ],
                'layout': {
                    'title': 'Gas Price Trend',
                    'xaxis': {'title': 'Time'},
                    'yaxis': {'title': 'Gas Price (Gwei)'}
                }
            }

    def start(self):
        """Start the dashboard server."""
        self.app.run_server(debug=True, port=self.port)

# Global dashboard instance
metrics_dashboard = MetricsDashboard()