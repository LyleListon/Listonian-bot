"""Backtesting routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.backtesting.backtesting import BacktestingSystem

backtesting_bp = Blueprint('backtesting', __name__)

def get_backtesting_system():
    """Get backtesting system from app context."""
    from flask import current_app
    return current_app.backtesting_system

@backtesting_bp.route('/api/backtesting/run', methods=['POST'])
def run_backtest():
    """Run backtest simulation."""
    try:
        backtesting = get_backtesting_system()
        simulation_data = request.get_json()
        results = backtesting.run_simulation(simulation_data)
        return jsonify({
            'status': 'success',
            'data': results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@backtesting_bp.route('/api/backtesting/results')
def get_backtest_results():
    """Get backtest results."""
    try:
        backtesting = get_backtesting_system()
        results = backtesting.get_results()
        return jsonify({
            'status': 'success',
            'data': results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@backtesting_bp.route('/api/backtesting/compare', methods=['POST'])
def compare_strategies():
    """Compare different strategies."""
    try:
        backtesting = get_backtesting_system()
        strategy_data = request.get_json()
        comparison_results = backtesting.compare_strategies(strategy_data)
        return jsonify({
            'status': 'success',
            'data': comparison_results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
