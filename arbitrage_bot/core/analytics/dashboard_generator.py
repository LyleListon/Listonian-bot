"""
Dashboard Generator Module

Provides dashboard visualization components for the arbitrage system.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import base64
import io

logger = logging.getLogger(__name__)

class DashboardGenerator:
    """
    Generates dashboard components for visualization.
    
    Features:
    - Real-time dashboard components
    - Interactive charts and graphs
    - Customizable views
    - Data export capabilities
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the dashboard generator.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()
        
        # Dashboard settings
        self.template_dir = self.config.get('template_dir', 'new_dashboard/templates')
        self.static_dir = self.config.get('static_dir', 'new_dashboard/static')
        self.output_dir = self.config.get('output_dir', 'new_dashboard/output')
        
        # Data sources
        self.profit_tracker = None
        self.performance_analyzer = None
        self.market_analyzer = None
        self.trading_journal = None
        
        # Cache settings
        self.cache_ttl = int(self.config.get('cache_ttl', 300))  # 5 minutes
        self._last_cache_update = 0
        self._cached_components = {}
        
    async def initialize(self) -> bool:
        """
        Initialize the dashboard generator.
        
        Returns:
            True if initialization successful
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            self.initialized = True
            logger.info("Dashboard generator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard generator: {e}")
            return False
    
    def set_profit_tracker(self, profit_tracker: Any) -> None:
        """Set the profit tracker instance."""
        self.profit_tracker = profit_tracker
    
    def set_performance_analyzer(self, performance_analyzer: Any) -> None:
        """Set the performance analyzer instance."""
        self.performance_analyzer = performance_analyzer
    
    def set_market_analyzer(self, market_analyzer: Any) -> None:
        """Set the market analyzer instance."""
        self.market_analyzer = market_analyzer
    
    def set_trading_journal(self, trading_journal: Any) -> None:
        """Set the trading journal instance."""
        self.trading_journal = trading_journal
    
    async def generate_profit_dashboard(self, timeframe: str = "7d") -> Dict[str, Any]:
        """
        Generate profit dashboard data.
        
        Args:
            timeframe: Time frame for data ("1h", "24h", "7d", "30d", "all")
            
        Returns:
            Dictionary with profit dashboard data
        """
        if not self.initialized:
            raise RuntimeError("Dashboard generator not initialized")
        
        if not self.profit_tracker:
            raise RuntimeError("Profit tracker not set")
        
        # Check cache
        cache_key = f"profit_dashboard_{timeframe}"
        current_time = asyncio.get_event_loop().time()
        if cache_key in self._cached_components and current_time - self._last_cache_update < self.cache_ttl:
            return self._cached_components[cache_key]
        
        async with self.lock:
            # Get profit data
            profit_summary = await self.profit_tracker.get_profit_summary()
            profit_time_series = await self.profit_tracker.get_profit_time_series(timeframe=timeframe, interval="1h")
            top_token_pairs = await self.profit_tracker.get_top_token_pairs(timeframe=timeframe, limit=5)
            roi_data = await self.profit_tracker.get_roi(timeframe=timeframe)
            
            # Prepare dashboard data
            dashboard_data = {
                'timeframe': timeframe,
                'summary': profit_summary.get(timeframe, {}),
                'time_series': profit_time_series,
                'top_token_pairs': top_token_pairs,
                'roi': roi_data,
                'chart_data': {
                    'profit_chart': self._prepare_profit_chart_data(profit_time_series),
                    'token_pair_chart': self._prepare_token_pair_chart_data(top_token_pairs),
                    'roi_chart': self._prepare_roi_chart_data(roi_data)
                }
            }
            
            # Update cache
            self._cached_components[cache_key] = dashboard_data
            self._last_cache_update = current_time
            
            return dashboard_data
    
    def _prepare_profit_chart_data(self, time_series_data: Dict[str, List[Any]]) -> Dict[str, Any]:
        """Prepare profit chart data for visualization."""
        return {
            'type': 'line',
            'data': {
                'labels': time_series_data.get('timestamps', []),
                'datasets': [
                    {
                        'label': 'Profit',
                        'data': time_series_data.get('profit', []),
                        'borderColor': 'rgb(75, 192, 192)',
                        'tension': 0.1
                    },
                    {
                        'label': 'Cumulative Profit',
                        'data': time_series_data.get('cumulative_profit', []),
                        'borderColor': 'rgb(153, 102, 255)',
                        'tension': 0.1
                    }
                ]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True
                    }
                }
            }
        }
    
    def _prepare_token_pair_chart_data(self, token_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare token pair chart data for visualization."""
        labels = [pair.get('token_pair', '').split('_')[0][-6:] + '/' + pair.get('token_pair', '').split('_')[1][-6:] for pair in token_pairs]
        profits = [pair.get('total_profit', 0) for pair in token_pairs]
        
        return {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Profit by Token Pair',
                        'data': profits,
                        'backgroundColor': [
                            'rgba(255, 99, 132, 0.2)',
                            'rgba(54, 162, 235, 0.2)',
                            'rgba(255, 206, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)',
                            'rgba(153, 102, 255, 0.2)'
                        ],
                        'borderColor': [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)'
                        ],
                        'borderWidth': 1
                    }
                ]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True
                    }
                }
            }
        }
    
    def _prepare_roi_chart_data(self, roi_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare ROI chart data for visualization."""
        return {
            'type': 'doughnut',
            'data': {
                'labels': ['Profit', 'Gas Cost'],
                'datasets': [
                    {
                        'label': 'ROI Breakdown',
                        'data': [
                            roi_data.get('total_profit', 0),
                            roi_data.get('total_gas_cost', 0)
                        ],
                        'backgroundColor': [
                            'rgba(75, 192, 192, 0.2)',
                            'rgba(255, 99, 132, 0.2)'
                        ],
                        'borderColor': [
                            'rgba(75, 192, 192, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        'borderWidth': 1
                    }
                ]
            },
            'options': {
                'responsive': True
            }
        }
    
    async def generate_performance_dashboard(self, timeframe: str = "7d") -> Dict[str, Any]:
        """
        Generate performance dashboard data.
        
        Args:
            timeframe: Time frame for data ("1d", "7d", "30d", "90d", "1y", "all")
            
        Returns:
            Dictionary with performance dashboard data
        """
        if not self.initialized:
            raise RuntimeError("Dashboard generator not initialized")
        
        if not self.performance_analyzer:
            raise RuntimeError("Performance analyzer not set")
        
        # Check cache
        cache_key = f"performance_dashboard_{timeframe}"
        current_time = asyncio.get_event_loop().time()
        if cache_key in self._cached_components and current_time - self._last_cache_update < self.cache_ttl:
            return self._cached_components[cache_key]
        
        async with self.lock:
            # Get performance data
            performance_metrics = await self.performance_analyzer.get_performance_metrics(timeframe=timeframe)
            drawdown_analysis = await self.performance_analyzer.get_drawdown_analysis(timeframe=timeframe)
            
            # Get benchmark data if available
            benchmark_comparison = None
            try:
                benchmark_comparison = await self.performance_analyzer.benchmark_performance(benchmark_id="ETH", timeframe=timeframe)
            except (ValueError, RuntimeError):
                logger.warning("Benchmark data not available")
            
            # Prepare dashboard data
            dashboard_data = {
                'timeframe': timeframe,
                'metrics': performance_metrics,
                'drawdown': drawdown_analysis,
                'benchmark': benchmark_comparison,
                'chart_data': {
                    'metrics_chart': self._prepare_metrics_chart_data(performance_metrics),
                    'drawdown_chart': self._prepare_drawdown_chart_data(drawdown_analysis),
                    'benchmark_chart': self._prepare_benchmark_chart_data(benchmark_comparison) if benchmark_comparison else None
                }
            }
            
            # Update cache
            self._cached_components[cache_key] = dashboard_data
            self._last_cache_update = current_time
            
            return dashboard_data
    
    def _prepare_metrics_chart_data(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare performance metrics chart data for visualization."""
        return {
            'type': 'radar',
            'data': {
                'labels': ['Total Return', 'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio', 'Win Rate'],
                'datasets': [
                    {
                        'label': 'Performance Metrics',
                        'data': [
                            metrics.get('total_return', 0) * 100,  # Convert to percentage
                            metrics.get('sharpe_ratio', 0),
                            metrics.get('sortino_ratio', 0),
                            metrics.get('calmar_ratio', 0),
                            metrics.get('win_rate', 0) * 100  # Convert to percentage
                        ],
                        'fill': True,
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                        'borderColor': 'rgb(54, 162, 235)',
                        'pointBackgroundColor': 'rgb(54, 162, 235)',
                        'pointBorderColor': '#fff',
                        'pointHoverBackgroundColor': '#fff',
                        'pointHoverBorderColor': 'rgb(54, 162, 235)'
                    }
                ]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'r': {
                        'angleLines': {
                            'display': True
                        },
                        'suggestedMin': 0
                    }
                }
            }
        }
    
    def _prepare_drawdown_chart_data(self, drawdown: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare drawdown chart data for visualization."""
        # Extract drawdown periods
        periods = drawdown.get('drawdown_periods', [])
        labels = [f"Period {i+1}" for i in range(len(periods))]
        max_drawdowns = [period.get('max_drawdown', 0) * 100 for period in periods]  # Convert to percentage
        durations = [period.get('duration_days', 0) for period in periods]
        
        return {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Max Drawdown (%)',
                        'data': max_drawdowns,
                        'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'borderWidth': 1,
                        'yAxisID': 'y'
                    },
                    {
                        'label': 'Duration (days)',
                        'data': durations,
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'borderWidth': 1,
                        'yAxisID': 'y1'
                    }
                ]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'position': 'left',
                        'title': {
                            'display': True,
                            'text': 'Max Drawdown (%)'
                        }
                    },
                    'y1': {
                        'beginAtZero': True,
                        'position': 'right',
                        'title': {
                            'display': True,
                            'text': 'Duration (days)'
                        },
                        'grid': {
                            'drawOnChartArea': False
                        }
                    }
                }
            }
        }
    
    def _prepare_benchmark_chart_data(self, benchmark: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare benchmark comparison chart data for visualization."""
        return {
            'type': 'bar',
            'data': {
                'labels': ['Return', 'Alpha', 'Beta', 'Information Ratio'],
                'datasets': [
                    {
                        'label': 'Strategy',
                        'data': [
                            benchmark.get('relative_return', 0) * 100,  # Convert to percentage
                            benchmark.get('alpha', 0) * 100,  # Convert to percentage
                            benchmark.get('beta', 0),
                            benchmark.get('information_ratio', 0)
                        ],
                        'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                        'borderColor': 'rgba(75, 192, 192, 1)',
                        'borderWidth': 1
                    },
                    {
                        'label': benchmark.get('benchmark_id', 'Benchmark'),
                        'data': [
                            benchmark.get('benchmark_return', 0) * 100,  # Convert to percentage
                            0,  # Alpha is relative to benchmark
                            1,  # Beta of benchmark is 1
                            0   # Information ratio is relative to benchmark
                        ],
                        'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                        'borderColor': 'rgba(153, 102, 255, 1)',
                        'borderWidth': 1
                    }
                ]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True
                    }
                }
            }
        }
    
    async def generate_market_dashboard(self, tokens: List[str], timeframe: str = "24h") -> Dict[str, Any]:
        """
        Generate market analysis dashboard data.
        
        Args:
            tokens: List of token addresses to include
            timeframe: Time frame for data ("1h", "4h", "12h", "24h", "7d", "30d")
            
        Returns:
            Dictionary with market dashboard data
        """
        if not self.initialized:
            raise RuntimeError("Dashboard generator not initialized")
        
        if not self.market_analyzer:
            raise RuntimeError("Market analyzer not set")
        
        # Check cache
        token_key = '_'.join(sorted(tokens))
        cache_key = f"market_dashboard_{token_key}_{timeframe}"
        current_time = asyncio.get_event_loop().time()
        if cache_key in self._cached_components and current_time - self._last_cache_update < self.cache_ttl:
            return self._cached_components[cache_key]
        
        async with self.lock:
            # Get market data for each token
            token_trends = {}
            for token in tokens:
                try:
                    trend = await self.market_analyzer.detect_market_trend(token_address=token, timeframe=timeframe)
                    token_trends[token] = trend
                except Exception as e:
                    logger.error(f"Error getting market trend for token {token}: {e}")
            
            # Get correlation analysis if multiple tokens
            correlation_analysis = None
            if len(tokens) >= 2:
                try:
                    correlation_analysis = await self.market_analyzer.analyze_token_correlation(token_addresses=tokens, timeframe=timeframe)
                except Exception as e:
                    logger.error(f"Error getting correlation analysis: {e}")
            
            # Get volatility forecasts
            volatility_forecasts = {}
            for token in tokens:
                try:
                    forecast = await self.market_analyzer.forecast_volatility(token_address=token, timeframe=timeframe)
                    volatility_forecasts[token] = forecast
                except Exception as e:
                    logger.error(f"Error getting volatility forecast for token {token}: {e}")
            
            # Prepare dashboard data
            dashboard_data = {
                'timeframe': timeframe,
                'tokens': tokens,
                'trends': token_trends,
                'correlation': correlation_analysis,
                'volatility': volatility_forecasts,
                'chart_data': {
                    'trend_charts': {token: self._prepare_trend_chart_data(trend) for token, trend in token_trends.items()},
                    'correlation_chart': self._prepare_correlation_chart_data(correlation_analysis) if correlation_analysis else None,
                    'volatility_chart': self._prepare_volatility_chart_data(volatility_forecasts)
                }
            }
            
            # Update cache
            self._cached_components[cache_key] = dashboard_data
            self._last_cache_update = current_time
            
            return dashboard_data
    
    def _prepare_trend_chart_data(self, trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare market trend chart data for visualization."""
        # Extract price data
        price_data = trend_data.get('price_data', {})
        timestamps = price_data.get('timestamps', [])
        prices = price_data.get('prices', [])
        
        # Prepare support and resistance levels
        support_levels = trend_data.get('support_levels', [])
        resistance_levels = trend_data.get('resistance_levels', [])
        
        # Create horizontal line datasets for support and resistance levels
        support_datasets = []
        for i, level in enumerate(support_levels):
            support_datasets.append({
                'label': f'Support {i+1}',
                'data': [level] * len(timestamps),
                'borderColor': 'rgba(75, 192, 192, 0.5)',
                'borderDash': [5, 5],
                'fill': False,
                'pointRadius': 0
            })
        
        resistance_datasets = []
        for i, level in enumerate(resistance_levels):
            resistance_datasets.append({
                'label': f'Resistance {i+1}',
                'data': [level] * len(timestamps),
                'borderColor': 'rgba(255, 99, 132, 0.5)',
                'borderDash': [5, 5],
                'fill': False,
                'pointRadius': 0
            })
        
        return {
            'type': 'line',
            'data': {
                'labels': timestamps,
                'datasets': [
                    {
                        'label': 'Price',
                        'data': prices,
                        'borderColor': 'rgb(54, 162, 235)',
                        'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                        'fill': True,
                        'tension': 0.1
                    },
                    *support_datasets,
                    *resistance_datasets
                ]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'title': {
                            'display': True,
                            'text': 'Price'
                        }
                    },
                    'x': {
                        'title': {
                            'display': True,
                            'text': 'Time'
                        }
                    }
                },
                'plugins': {
                    'title': {
                        'display': True,
                        'text': f"Market Trend: {trend_data.get('trend', 'Unknown').capitalize()} (Confidence: {trend_data.get('confidence', 0) * 100:.1f}%)"
                    }
                }
            }
        }
    
    def _prepare_correlation_chart_data(self, correlation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare correlation chart data for visualization."""
        # Extract correlation matrix
        matrix = correlation_data.get('correlation_matrix', {})
        tokens = list(matrix.keys())
        
        # Prepare data for heatmap
        labels = [token[-6:] for token in tokens]  # Use last 6 characters of token address
        data = []
        
        for i, token1 in enumerate(tokens):
            row = []
            for j, token2 in enumerate(tokens):
                row.append(matrix[token1][token2])
            data.append(row)
        
        return {
            'type': 'heatmap',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Correlation',
                    'data': data,
                    'backgroundColor': [
                        'rgba(0, 0, 255, 0.8)',   # Strong negative correlation
                        'rgba(173, 216, 230, 0.8)',  # Weak negative correlation
                        'rgba(255, 255, 255, 0.8)',  # No correlation
                        'rgba(255, 228, 196, 0.8)',  # Weak positive correlation
                        'rgba(255, 0, 0, 0.8)'    # Strong positive correlation
                    ]
                }]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'x': {
                        'title': {
                            'display': true,
                            'text': 'Token'
                        }
                    },
                    'y': {
                        'title': {
                            'display': true,
                            'text': 'Token'
                        }
                    }
                },
                'plugins': {
                    'title': {
                        'display': true,
                        'text': 'Token Correlation Matrix'
                    },
                    'tooltip': {
                        'callbacks': {
                            'label': 'function(context) { return "Correlation: " + context.raw.toFixed(2); }'
                        }
                    }
                }
            }
        }
    
    def _prepare_volatility_chart_data(self, volatility_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare volatility chart data for visualization."""
        tokens = list(volatility_data.keys())
        labels = [token[-6:] for token in tokens]  # Use last 6 characters of token address
        
        historical_volatility = [volatility_data[token].get('historical_volatility', 0) * 100 for token in tokens]  # Convert to percentage
        forecasted_volatility = [volatility_data[token].get('forecasted_volatility', 0) * 100 for token in tokens]  # Convert to percentage
        
        return {
            'type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Historical Volatility (%)',
                        'data': historical_volatility,
                        'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'borderWidth': 1
                    },
                    {
                        'label': 'Forecasted Volatility (%)',
                        'data': forecasted_volatility,
                        'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'borderWidth': 1
                    }
                ]
            },
            'options': {
                'responsive': true,
                'scales': {
                    'y': {
                        'beginAtZero': true,
                        'title': {
                            'display': true,
                            'text': 'Volatility (%)'
                        }
                    },
                    'x': {
                        'title': {
                            'display': true,
                            'text': 'Token'
                        }
                    }
                },
                'plugins': {
                    'title': {
                        'display': true,
                        'text': 'Token Volatility Comparison'
                    }
                }
            }
        }
    
    async def export_dashboard_data(self, dashboard_type: str, format: str = "json") -> bytes:
        """
        Export dashboard data in the specified format.
        
        Args:
            dashboard_type: Type of dashboard to export ("profit", "performance", "market")
            format: Export format ("json", "csv", "html")
            
        Returns:
            Exported data as bytes
        """
        if not self.initialized:
            raise RuntimeError("Dashboard generator not initialized")
        
        # Get dashboard data
        dashboard_data = None
        if dashboard_type == "profit":
            dashboard_data = await self.generate_profit_dashboard(timeframe="all")
        elif dashboard_type == "performance":
            dashboard_data = await self.generate_performance_dashboard(timeframe="all")
        elif dashboard_type == "market":
            # Get all tokens with price data
            tokens = []
            if self.market_analyzer:
                # This is a simplified approach - in a real implementation, we would need to get the list of tokens
                # from the market analyzer
                tokens = ["0x..."]  # Placeholder
            dashboard_data = await self.generate_market_dashboard(tokens=tokens, timeframe="7d")
        else:
            raise ValueError(f"Invalid dashboard type: {dashboard_type}")
        
        # Export in the specified format
        if format == "json":
            return json.dumps(dashboard_data, indent=2).encode('utf-8')
        elif format == "csv":
            # Simplified CSV export - in a real implementation, we would need to flatten the data structure
            output = io.StringIO()
            output.write("Dashboard Export\n")
            output.write(f"Type: {dashboard_type}\n")
            output.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")
            
            # Write some key metrics
            if dashboard_type == "profit":
                summary = dashboard_data.get('summary', {})
                output.write("Profit Summary\n")
                output.write(f"Total Profit: {summary.get('total_profit', 0)}\n")
                output.write(f"ROI: {dashboard_data.get('roi', {}).get('roi', 0)}\n")
            elif dashboard_type == "performance":
                metrics = dashboard_data.get('metrics', {})
                output.write("Performance Metrics\n")
                output.write(f"Total Return: {metrics.get('total_return', 0)}\n")
                output.write(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0)}\n")
                output.write(f"Max Drawdown: {metrics.get('max_drawdown', 0)}\n")
            elif dashboard_type == "market":
                output.write("Market Analysis\n")
                for token, trend in dashboard_data.get('trends', {}).items():
                    output.write(f"Token: {token}\n")
                    output.write(f"Trend: {trend.get('trend', 'unknown')}\n")
                    output.write(f"Price Change: {trend.get('price_change', 0)}%\n\n")
            
            return output.getvalue().encode('utf-8')
        elif format == "html":
            # Simplified HTML export - in a real implementation, we would use a template engine
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{dashboard_type.capitalize()} Dashboard Export</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    .section {{ margin-bottom: 20px; }}
                    .metric {{ margin: 10px 0; }}
                    .metric-name {{ font-weight: bold; }}
                    .metric-value {{ color: #0066cc; }}
                </style>
            </head>
            <body>
                <h1>{dashboard_type.capitalize()} Dashboard Export</h1>
                <div class="section">
                    <p>Generated: {datetime.utcnow().isoformat()}</p>
                </div>
            """
            
            # Add dashboard-specific content
            if dashboard_type == "profit":
                summary = dashboard_data.get('summary', {})
                html += f"""
                <div class="section">
                    <h2>Profit Summary</h2>
                    <div class="metric">
                        <span class="metric-name">Total Profit:</span>
                        <span class="metric-value">{summary.get('total_profit', 0)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-name">ROI:</span>
                        <span class="metric-value">{dashboard_data.get('roi', {}).get('roi', 0)}</span>
                    </div>
                </div>
                """
