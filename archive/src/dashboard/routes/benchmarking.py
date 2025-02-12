"""Benchmarking routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.benchmarking.benchmarking import BenchmarkingSystem

benchmarking_bp = Blueprint('benchmarking', __name__)

def get_benchmarking_system():
    """Get benchmarking system from app context."""
    from flask import current_app
    return current_app.benchmarking_system

@benchmarking_bp.route('/api/benchmarking/performance')
def get_performance_metrics():
    """Get performance benchmarking metrics."""
    try:
        benchmarking = get_benchmarking_system()
        metrics = benchmarking.get_performance_metrics()
        return jsonify({
            'status': 'success',
            'data': metrics
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@benchmarking_bp.route('/api/benchmarking/compare', methods=['POST'])
def compare_strategies():
    """Compare strategy performance."""
    try:
        benchmarking = get_benchmarking_system()
        strategy_data = request.get_json()
        comparison_results = benchmarking.compare_strategies(strategy_data)
        return jsonify({
            'status': 'success',
            'data': comparison_results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@benchmarking_bp.route('/api/benchmarking/market-impact')
def analyze_market_impact():
    """Analyze market impact of trades."""
    try:
        benchmarking = get_benchmarking_system()
        impact_analysis = benchmarking.analyze_market_impact()
        return jsonify({
            'status': 'success',
            'data': impact_analysis
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
