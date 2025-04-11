"""
Report Generator Module

Provides report generation capabilities for the arbitrage system.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
import json
import os
import csv
import io
from pathlib import Path

logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generates reports for the arbitrage system.

    Features:
    - Daily/weekly/monthly performance reports
    - Profit and loss statements
    - Strategy performance breakdown
    - Tax reporting assistance
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the report generator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()

        # Report settings
        self.report_dir = self.config.get('report_dir', 'analytics')
        self.report_formats = self.config.get('report_formats', ['json', 'csv', 'html']) # Added html back
        self.auto_generate = self.config.get('auto_generate', False)

        # Data sources
        self.profit_tracker = None
        self.performance_analyzer = None
        self.trading_journal = None

        # Report templates
        self._report_templates = {
            'daily': self._generate_daily_report,
            'weekly': self._generate_weekly_report,
            'monthly': self._generate_monthly_report,
            'profit_loss': self._generate_profit_loss_report,
            'strategy': self._generate_strategy_report,
            'tax': self._generate_tax_report
        }

    async def initialize(self) -> bool:
        """
        Initialize the report generator.

        Returns:
            True if initialization successful
        """
        try:
            # Create report directory if it doesn't exist
            os.makedirs(self.report_dir, exist_ok=True)

            self.initialized = True
            logger.info("Report generator initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize report generator: {e}")
            return False

    def set_profit_tracker(self, profit_tracker: Any) -> None:
        """Set the profit tracker instance."""
        self.profit_tracker = profit_tracker

    def set_performance_analyzer(self, performance_analyzer: Any) -> None:
        """Set the performance analyzer instance."""
        self.performance_analyzer = performance_analyzer

    def set_trading_journal(self, trading_journal: Any) -> None:
        """Set the trading journal instance."""
        self.trading_journal = trading_journal

    async def generate_report(self, report_type: str,
                             timeframe: Optional[str] = None,
                             format: str = 'json') -> bytes:
        """
        Generate a report.

        Args:
            report_type: Type of report to generate
            timeframe: Optional timeframe for the report
            format: Report format ('json', 'csv', 'html')

        Returns:
            Report data as bytes
        """
        if not self.initialized:
            raise RuntimeError("Report generator not initialized")

        # Check if report type is valid
        if report_type not in self._report_templates:
            raise ValueError(f"Invalid report type: {report_type}")

        # Check if format is valid
        if format not in self.report_formats:
            raise ValueError(f"Invalid report format: {format}")

        # Generate report data
        report_data = await self._report_templates[report_type](timeframe)

        # Format report
        if format == 'json':
            return self._format_json(report_data)
        elif format == 'csv':
            return self._format_csv(report_data)
        elif format == 'html':
            return self._format_html(report_data, report_type)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_json(self, data: Dict[str, Any]) -> bytes:
        """Format report data as JSON."""
        return json.dumps(data, indent=2, default=self._json_serializer).encode('utf-8')

    def _json_serializer(self, obj: Any) -> Any:
        """JSON serializer for objects not serializable by default json code."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Type {type(obj)} not serializable")

    def _format_csv(self, data: Dict[str, Any]) -> bytes:
        """Format report data as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Report Generated', datetime.utcnow().isoformat()])
        writer.writerow([])

        # Write sections
        for section_name, section_data in data.items():
            writer.writerow([section_name.upper()])

            if isinstance(section_data, dict):
                # Write dictionary as rows
                for key, value in section_data.items():
                    if isinstance(value, dict):
                        # Nested dictionary
                        writer.writerow([key])
                        for subkey, subvalue in value.items():
                            writer.writerow(['', subkey, subvalue])
                    else:
                        writer.writerow([key, value])
            elif isinstance(section_data, list):
                # Write list as table
                if section_data and isinstance(section_data[0], dict):
                    # List of dictionaries - extract headers
                    headers = list(section_data[0].keys())
                    writer.writerow(headers)

                    # Write rows
                    for item in section_data:
                        writer.writerow([item.get(header, '') for header in headers])
                else:
                    # Simple list
                    for item in section_data:
                        writer.writerow([item])
            else:
                # Simple value
                writer.writerow([section_data])

            writer.writerow([])

        return output.getvalue().encode('utf-8')

    def _format_html(self, data: Dict[str, Any], report_type: str) -> bytes:
        """Format report data as HTML."""
        # Simple HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_type.capitalize()} Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .section {{ margin-bottom: 30px; }}
            </style>
        </head>
        <body>
            <h1>{report_type.capitalize()} Report</h1>
            <p>Generated: {datetime.utcnow().isoformat()}</p>
        """

        # Add sections
        for section_name, section_data in data.items():
            html += f"""
            <div class="section">
                <h2>{section_name.replace('_', ' ').title()}</h2>
            """

            if isinstance(section_data, dict):
                # Render dictionary as table
                html += """
                <table>
                    <tr>
                        <th>Key</th>
                        <th>Value</th>
                    </tr>
                """

                for key, value in section_data.items():
                    if isinstance(value, dict):
                        # Nested dictionary
                        html += f"""
                        <tr>
                            <td colspan="2"><strong>{key}</strong></td>
                        </tr>
                        """

                        for subkey, subvalue in value.items():
                            html += f"""
                            <tr>
                                <td>&nbsp;&nbsp;{subkey}</td>
                                <td>{subvalue}</td>
                            </tr>
                            """
                    else:
                        html += f"""
                        <tr>
                            <td>{key}</td>
                            <td>{value}</td>
                        </tr>
                        """

                html += """
                </table>
                """
            elif isinstance(section_data, list):
                # Render list as table
                if section_data and isinstance(section_data[0], dict):
                    # List of dictionaries
                    headers = list(section_data[0].keys())

                    html += """
                    <table>
                        <tr>
                    """

                    for header in headers:
                        html += f"""
                        <th>{header.replace('_', ' ').title()}</th>
                        """

                    html += """
                        </tr>
                    """

                    for item in section_data:
                        html += """
                        <tr>
                        """

                        for header in headers:
                            html += f"""
                            <td>{item.get(header, '')}</td>
                            """

                        html += """
                        </tr>
                        """

                    html += """
                    </table>
                    """
                else:
                    # Simple list
                    html += """
                    <ul>
                    """

                    for item in section_data:
                        html += f"""
                        <li>{item}</li>
                        """

                    html += """
                    </ul>
                    """
            else:
                # Simple value
                html += f"""
                <p>{section_data}</p>
                """

            html += """
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html.encode('utf-8')

    async def _generate_daily_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a daily performance report.

        Args:
            date: Optional date string (YYYY-MM-DD), defaults to today

        Returns:
            Report data
        """
        # Parse date
        if date:
            try:
                report_date = datetime.fromisoformat(date)
            except ValueError:
                raise ValueError(f"Invalid date format: {date}. Expected YYYY-MM-DD")
        else:
            report_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Define time range
        start_time = report_date
        end_time = start_time + timedelta(days=1)

        # Collect data
        report_data = {
            'report_info': {
                'type': 'daily',
                'date': report_date.date().isoformat(),
                'generated_at': datetime.utcnow().isoformat()
            },
            'summary': {}
        }

        # Get profit data if available
        if self.profit_tracker:
            try:
                # Get profit data for the day
                profit_data = await self.profit_tracker.get_profit_by_token_pair(timeframe="24h")
                roi_data = await self.profit_tracker.get_roi(timeframe="24h")

                report_data['profit'] = {
                    'total_profit': profit_data.get('total_profit', 0),
                    'total_volume': profit_data.get('total_volume', 0),
                    'trade_count': profit_data.get('trade_count', 0),
                    'roi': roi_data.get('roi', 0),
                    'net_profit': roi_data.get('net_profit', 0),
                    'gas_cost': roi_data.get('total_gas_cost', 0)
                }

                # Add to summary
                report_data['summary']['total_profit'] = profit_data.get('total_profit', 0)
                report_data['summary']['trade_count'] = profit_data.get('trade_count', 0)
                report_data['summary']['roi'] = roi_data.get('roi', 0)

                # Add top token pairs
                top_pairs = await self.profit_tracker.get_top_token_pairs(timeframe="24h", limit=5)
                if top_pairs:
                    report_data['top_token_pairs'] = top_pairs
            except Exception as e:
                logger.error(f"Error getting profit data for daily report: {e}")

        # Get performance data if available
        if self.performance_analyzer:
            try:
                # Get performance metrics
                performance_metrics = await self.performance_analyzer.get_performance_metrics(timeframe="1d")

                report_data['performance'] = {
                    'total_return': performance_metrics.get('total_return', 0),
                    'volatility': performance_metrics.get('volatility', 0),
                    'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0),
                    'sortino_ratio': performance_metrics.get('sortino_ratio', 0),
                    'win_rate': performance_metrics.get('win_rate', 0),
                    'profit_factor': performance_metrics.get('profit_factor', 0)
                }

                # Add to summary
                report_data['summary']['win_rate'] = performance_metrics.get('win_rate', 0)
                report_data['summary']['profit_factor'] = performance_metrics.get('profit_factor', 0)
            except Exception as e:
                logger.error(f"Error getting performance data for daily report: {e}")

        # Get trade data if available
        if self.trading_journal:
            try:
                # Get trades for the day
                trades = await self.trading_journal.get_trades(timeframe="24h")

                if trades:
                    # Add trade summary
                    trade_analysis = await self.trading_journal.analyze_trade_outcomes(timeframe="24h")

                    report_data['trades'] = {
                        'count': len(trades),
                        'successful': trade_analysis.get('successful_trades', 0),
                        'failed': trade_analysis.get('failed_trades', 0),
                        'success_rate': trade_analysis.get('success_rate', 0),
                        'avg_profit': trade_analysis.get('avg_profit_per_trade', 0),
                        'avg_gas_cost': trade_analysis.get('avg_gas_cost', 0)
                    }

                    # Add to summary
                    report_data['summary']['success_rate'] = trade_analysis.get('success_rate', 0)

                    # Add trade list (limited to 10 for brevity)
                    report_data['trade_list'] = trades[:10]
            except Exception as e:
                logger.error(f"Error getting trade data for daily report: {e}")

        return report_data

    async def _generate_weekly_report(self, week_start: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a weekly performance report.

        Args:
            week_start: Optional week start date string (YYYY-MM-DD), defaults to current week

        Returns:
            Report data
        """
        # Parse week start date
        if week_start:
            try:
                start_date = datetime.fromisoformat(week_start)
            except ValueError:
                raise ValueError(f"Invalid date format: {week_start}. Expected YYYY-MM-DD")
        else:
            # Default to current week (starting Monday)
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = today - timedelta(days=today.weekday())

        # Define time range
        end_date = start_date + timedelta(days=7)

        # Collect data
        report_data = {
            'report_info': {
                'type': 'weekly',
                'week_start': start_date.date().isoformat(),
                'week_end': end_date.date().isoformat(),
                'generated_at': datetime.utcnow().isoformat()
            },
            'summary': {}
        }

        # Get profit data if available
        if self.profit_tracker:
            try:
                # Get profit data for the week
                profit_data = await self.profit_tracker.get_profit_by_token_pair(timeframe="7d")
                roi_data = await self.profit_tracker.get_roi(timeframe="7d")

                report_data['profit'] = {
                    'total_profit': profit_data.get('total_profit', 0),
                    'total_volume': profit_data.get('total_volume', 0),
                    'trade_count': profit_data.get('trade_count', 0),
                    'roi': roi_data.get('roi', 0),
                    'annualized_roi': roi_data.get('annualized_roi', 0),
                    'net_profit': roi_data.get('net_profit', 0),
                    'gas_cost': roi_data.get('total_gas_cost', 0)
                }

                # Add to summary
                report_data['summary']['total_profit'] = profit_data.get('total_profit', 0)
                report_data['summary']['trade_count'] = profit_data.get('trade_count', 0)
                report_data['summary']['roi'] = roi_data.get('roi', 0)

                # Add top token pairs
                top_pairs = await self.profit_tracker.get_top_token_pairs(timeframe="7d", limit=5)
                if top_pairs:
                    report_data['top_token_pairs'] = top_pairs

                # Add profit time series
                time_series = await self.profit_tracker.get_profit_time_series(timeframe="7d", interval="1d")
                if time_series:
                    report_data['profit_time_series'] = time_series
            except Exception as e:
                logger.error(f"Error getting profit data for weekly report: {e}")

        # Get performance data if available
        if self.performance_analyzer:
            try:
                # Get performance metrics
                performance_metrics = await self.performance_analyzer.get_performance_metrics(timeframe="7d")
                drawdown_analysis = await self.performance_analyzer.get_drawdown_analysis(timeframe="7d")

                report_data['performance'] = {
                    'total_return': performance_metrics.get('total_return', 0),
                    'annualized_return': performance_metrics.get('annualized_return', 0),
                    'volatility': performance_metrics.get('volatility', 0),
                    'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0),
                    'sortino_ratio': performance_metrics.get('sortino_ratio', 0),
                    'calmar_ratio': performance_metrics.get('calmar_ratio', 0),
                    'max_drawdown': drawdown_analysis.get('max_drawdown', 0),
                    'win_rate': performance_metrics.get('win_rate', 0),
                    'profit_factor': performance_metrics.get('profit_factor', 0)
                }

                # Add to summary
                report_data['summary']['win_rate'] = performance_metrics.get('win_rate', 0)
                report_data['summary']['max_drawdown'] = drawdown_analysis.get('max_drawdown', 0)
            except Exception as e:
                logger.error(f"Error getting performance data for weekly report: {e}")

        # Get trade data if available
        if self.trading_journal:
            try:
                # Get trade analysis
                trade_analysis = await self.trading_journal.analyze_trade_outcomes(timeframe="7d")

                if trade_analysis:
                    report_data['trades'] = {
                        'count': trade_analysis.get('total_trades', 0),
                        'successful': trade_analysis.get('successful_trades', 0),
                        'failed': trade_analysis.get('failed_trades', 0),
                        'success_rate': trade_analysis.get('success_rate', 0),
                        'avg_profit': trade_analysis.get('avg_profit_per_trade', 0),
                        'avg_gas_cost': trade_analysis.get('avg_gas_cost', 0)
                    }

                    # Add to summary
                    report_data['summary']['success_rate'] = trade_analysis.get('success_rate', 0)

                # Get learning insights
                insights = await self.trading_journal.extract_learning_insights(timeframe="7d")
                if insights:
                    report_data['insights'] = insights
            except Exception as e:
                logger.error(f"Error getting trade data for weekly report: {e}")

        return report_data

    async def _generate_monthly_report(self, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a monthly performance report.

        Args:
            month: Optional month string (YYYY-MM), defaults to current month

        Returns:
            Report data
        """
        # Parse month
        if month:
            try:
                year, month_num = map(int, month.split('-'))
                start_date = datetime(year, month_num, 1)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid month format: {month}. Expected YYYY-MM")
        else:
            # Default to current month
            today = datetime.utcnow()
            start_date = datetime(today.year, today.month, 1)

        # Define time range
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)

        # Collect data
        report_data = {
            'report_info': {
                'type': 'monthly',
                'month': start_date.strftime('%Y-%m'),
                'generated_at': datetime.utcnow().isoformat()
            },
            'summary': {}
        }

        # Get profit data if available
        if self.profit_tracker:
            try:
                # Get profit data for the month
                profit_data = await self.profit_tracker.get_profit_by_token_pair(timeframe="30d") # Approximation
                roi_data = await self.profit_tracker.get_roi(timeframe="30d") # Approximation

                report_data['profit'] = {
                    'total_profit': profit_data.get('total_profit', 0),
                    'total_volume': profit_data.get('total_volume', 0),
                    'trade_count': profit_data.get('trade_count', 0),
                    'roi': roi_data.get('roi', 0),
                    'annualized_roi': roi_data.get('annualized_roi', 0),
                    'net_profit': roi_data.get('net_profit', 0),
                    'gas_cost': roi_data.get('total_gas_cost', 0)
                }

                # Add to summary
                report_data['summary']['total_profit'] = profit_data.get('total_profit', 0)
                report_data['summary']['trade_count'] = profit_data.get('trade_count', 0)
                report_data['summary']['roi'] = roi_data.get('roi', 0)

                # Add top token pairs
                top_pairs = await self.profit_tracker.get_top_token_pairs(timeframe="30d", limit=10)
                if top_pairs:
                    report_data['top_token_pairs'] = top_pairs

                # Add profit time series
                time_series = await self.profit_tracker.get_profit_time_series(timeframe="30d", interval="1d")
                if time_series:
                    report_data['profit_time_series'] = time_series
            except Exception as e:
                logger.error(f"Error getting profit data for monthly report: {e}")

        # Get performance data if available
        if self.performance_analyzer:
            try:
                # Get performance metrics
                performance_metrics = await self.performance_analyzer.get_performance_metrics(timeframe="30d") # Approximation
                drawdown_analysis = await self.performance_analyzer.get_drawdown_analysis(timeframe="30d") # Approximation

                report_data['performance'] = {
                    'total_return': performance_metrics.get('total_return', 0),
                    'annualized_return': performance_metrics.get('annualized_return', 0),
                    'volatility': performance_metrics.get('volatility', 0),
                    'sharpe_ratio': performance_metrics.get('sharpe_ratio', 0),
                    'sortino_ratio': performance_metrics.get('sortino_ratio', 0),
                    'calmar_ratio': performance_metrics.get('calmar_ratio', 0),
                    'max_drawdown': drawdown_analysis.get('max_drawdown', 0),
                    'win_rate': performance_metrics.get('win_rate', 0),
                    'profit_factor': performance_metrics.get('profit_factor', 0)
                }

                # Add drawdown periods
                if drawdown_analysis.get('drawdown_periods'):
                    report_data['drawdown_periods'] = drawdown_analysis.get('drawdown_periods')

                # Try to get benchmark comparison if available
                try:
                    benchmark = await self.performance_analyzer.benchmark_performance(benchmark_id="ETH", timeframe="30d")
                    if benchmark:
                        report_data['benchmark'] = {
                            'benchmark_id': benchmark.get('benchmark_id'),
                            'benchmark_return': benchmark.get('benchmark_return', 0),
                            'relative_return': benchmark.get('relative_return', 0),
                            'alpha': benchmark.get('alpha', 0),
                            'beta': benchmark.get('beta', 0),
                            'correlation': benchmark.get('correlation', 0),
                            'information_ratio': benchmark.get('information_ratio', 0)
                        }
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error getting performance data for monthly report: {e}")

        # Get trade data if available
        if self.trading_journal:
            try:
                # Get trade analysis
                trade_analysis = await self.trading_journal.analyze_trade_outcomes(timeframe="30d") # Approximation

                if trade_analysis:
                    report_data['trades'] = {
                        'count': trade_analysis.get('total_trades', 0),
                        'successful': trade_analysis.get('successful_trades', 0),
                        'failed': trade_analysis.get('failed_trades', 0),
                        'success_rate': trade_analysis.get('success_rate', 0),
                        'avg_profit': trade_analysis.get('avg_profit_per_trade', 0),
                        'avg_gas_cost': trade_analysis.get('avg_gas_cost', 0),
                        'most_profitable_trade': trade_analysis.get('most_profitable_trade'),
                        'least_profitable_trade': trade_analysis.get('least_profitable_trade')
                    }

                # Get learning insights
                insights = await self.trading_journal.extract_learning_insights(timeframe="30d") # Approximation
                if insights:
                    report_data['insights'] = {
                        'common_patterns': insights.get('common_patterns', []),
                        'improvement_areas': insights.get('improvement_areas', [])
                    }
            except Exception as e:
                logger.error(f"Error getting trade data for monthly report: {e}")

        return report_data

    async def _generate_profit_loss_report(self, timeframe: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a profit and loss report.

        Args:
            timeframe: Optional timeframe for the report ("24h", "7d", "30d", "all")

        Returns:
            Report data
        """
        # Default to "all" if timeframe not specified
        if not timeframe:
            timeframe = "all"

        # Collect data
        report_data = {
            'report_info': {
                'type': 'profit_loss',
                'timeframe': timeframe,
                'generated_at': datetime.utcnow().isoformat()
            },
            'summary': {}
        }

        # Get profit data if available
        if self.profit_tracker:
            try:
                # Get profit data
                profit_data = await self.profit_tracker.get_profit_by_token_pair(timeframe=timeframe)
                roi_data = await self.profit_tracker.get_roi(timeframe=timeframe)

                report_data['profit_loss'] = {
                    'total_profit': profit_data.get('total_profit', 0),
                    'total_volume': profit_data.get('total_volume', 0),
                    'trade_count': profit_data.get('trade_count', 0),
                    'avg_profit': profit_data.get('avg_profit', 0),
                    'profit_per_volume': profit_data.get('profit_per_volume', 0),
                    'total_gas_cost': roi_data.get('total_gas_cost', 0),
                    'net_profit': roi_data.get('net_profit', 0),
                    'roi': roi_data.get('roi', 0)
                }

                # Add token pair breakdown
                token_pairs = []
                for pair_id, pair_data in profit_data.get('token_pairs', {}).items():
                    token_pairs.append({
                        'token_pair': pair_id,
                        'total_profit': pair_data.get('total_profit', 0),
                        'total_volume': pair_data.get('total_volume', 0),
                        'trade_count': pair_data.get('trade_count', 0),
                        'avg_profit': pair_data.get('avg_profit', 0),
                        'profit_per_volume': pair_data.get('profit_per_volume', 0),
                        'percentage_of_total': pair_data.get('percentage_of_total', 0)
                    })

                # Sort by total profit (descending)
                token_pairs.sort(key=lambda x: x.get('total_profit', 0), reverse=True)
                report_data['token_pair_breakdown'] = token_pairs

                # Add to summary
                report_data['summary']['total_profit'] = profit_data.get('total_profit', 0)
                report_data['summary']['net_profit'] = roi_data.get('net_profit', 0)
                report_data['summary']['roi'] = roi_data.get('roi', 0)
            except Exception as e:
                logger.error(f"Error getting profit data for profit/loss report: {e}")

        # Get trade data if available
        if self.trading_journal:
            try:
                # Get trade analysis
                trade_analysis = await self.trading_journal.analyze_trade_outcomes(timeframe=timeframe)

                if trade_analysis:
                    # Populate trade details in the report_data
                    report_data['trades'] = {
                        'count': trade_analysis.get('total_trades', 0),
                        'successful': trade_analysis.get('successful_trades', 0),
                        'failed': trade_analysis.get('failed_trades', 0),
                        'success_rate': trade_analysis.get('success_rate', 0),
                        'avg_profit': trade_analysis.get('avg_profit_per_trade', 0),
                        'avg_gas_cost': trade_analysis.get('avg_gas_cost', 0)
                    }
                    # Add relevant trade info to summary if needed
                    report_data['summary']['success_rate'] = trade_analysis.get('success_rate', 0)

            except Exception as e:
                logger.error(f"Error getting trade data for profit/loss report: {e}")

        return report_data

    async def _generate_strategy_report(self, timeframe: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a strategy performance report.

        Args:
            timeframe: Optional timeframe for the report ("24h", "7d", "30d", "all")

        Returns:
            Report data
        """
        # Default to "all" if timeframe not specified
        if not timeframe:
            timeframe = "all"

        report_data = {
            'report_info': {
                'type': 'strategy',
                'timeframe': timeframe,
                'generated_at': datetime.utcnow().isoformat()
            },
            'strategy_performance': {}
        }

        # Placeholder: Needs actual strategy tracking implementation
        # Example structure:
        # if self.strategy_tracker:
        #     try:
        #         strategies = await self.strategy_tracker.get_strategies()
        #         for strategy_name in strategies:
        #             performance = await self.strategy_tracker.get_strategy_performance(strategy_name, timeframe)
        #             report_data['strategy_performance'][strategy_name] = performance
        #     except Exception as e:
        #         logger.error(f"Error getting strategy data: {e}")

        logger.warning("Strategy report generation is not fully implemented.")
        report_data['strategy_performance'] = {
            'TriangularArbitrage': {'status': 'Not Implemented'},
            'CrossDexArbitrage': {'status': 'Not Implemented'}
        }

        return report_data

    async def _generate_tax_report(self, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate a tax report (summary of gains/losses).

        Args:
            year: Optional year for the report, defaults to current year

        Returns:
            Report data
        """
        if not year:
            year = datetime.utcnow().year

        report_data = {
            'report_info': {
                'type': 'tax',
                'year': year,
                'generated_at': datetime.utcnow().isoformat()
            },
            'tax_summary': {}
        }

        # Placeholder: Needs actual tax calculation logic based on trades
        # This would likely involve fetching all trades for the year and calculating
        # capital gains/losses based on acquisition cost and sale price.
        # This is complex and depends heavily on jurisdiction and accounting method (FIFO, LIFO, etc.)

        logger.warning("Tax report generation is a placeholder and requires specific implementation.")
        report_data['tax_summary'] = {
            'status': 'Not Implemented',
            'disclaimer': 'This is not financial advice. Consult a tax professional.'
        }

        # Example structure if implemented:
        # if self.trading_journal:
        #     try:
        #         tax_data = await self.trading_journal.calculate_tax_liability(year)
        #         report_data['tax_summary'] = tax_data
        #     except Exception as e:
        #         logger.error(f"Error calculating tax data: {e}")

        return report_data

    async def save_report(self, report_type: str,
                          timeframe: Optional[str] = None,
                          formats: Optional[List[str]] = None) -> List[str]:
        """
        Generate and save a report to disk.

        Args:
            report_type: Type of report to generate
            timeframe: Optional timeframe for the report
            formats: List of formats to save (defaults to configured formats)

        Returns:
            List of file paths where the reports were saved
        """
        if not self.initialized:
            raise RuntimeError("Report generator not initialized")

        formats_to_save = formats or self.report_formats
        saved_files = []

        for format in formats_to_save:
            try:
                report_bytes = await self.generate_report(report_type, timeframe, format)

                # Construct filename
                now = datetime.utcnow()
                filename_parts = [report_type]
                if timeframe:
                    filename_parts.append(timeframe.replace(":", "-")) # Handle potential timeframe formats
                filename_parts.append(now.strftime('%Y%m%d_%H%M%S'))
                filename = f"{'_'.join(filename_parts)}.{format}"
                filepath = Path(self.report_dir) / filename

                # Save file
                with open(filepath, 'wb') as f:
                    f.write(report_bytes)

                logger.info(f"Saved {format.upper()} report to {filepath}")
                saved_files.append(str(filepath))

            except Exception as e:
                logger.error(f"Failed to generate or save {format.upper()} report for {report_type}: {e}")

        return saved_files

    async def schedule_reports(self):
        """
        Schedule automatic report generation based on config.
        (Placeholder - requires a scheduler implementation)
        """
        if not self.auto_generate:
            return

        logger.info("Scheduling automatic report generation...")
        # Placeholder: Integrate with an async scheduler (e.g., APScheduler with AsyncIOScheduler)
        # Example: Schedule daily report at midnight
        # scheduler.add_job(self.save_report, 'cron', hour=0, args=['daily'])
        # Example: Schedule weekly report every Monday at 1 AM
        # scheduler.add_job(self.save_report, 'cron', day_of_week='mon', hour=1, args=['weekly'])
        logger.warning("Automatic report scheduling is not yet implemented.")

    async def close(self):
        """Clean up resources."""
        logger.info("Closing report generator.")
        # Placeholder for any cleanup needed
        self.initialized = False
