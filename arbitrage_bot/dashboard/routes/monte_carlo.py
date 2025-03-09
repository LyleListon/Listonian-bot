"""Monte Carlo simulation routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.backtesting.monte_carlo import MonteCarloSystem

monte_carlo_bp = Blueprint('monte_carlo', __name__)

def get_monte_carlo_system():
    """Get Monte Carlo system from app context."""
    from flask import current_app
    return current_app.monte_carlo_system

@monte_carlo_bp.route('/api/monte-carlo/simulate', methods=['POST'])
def run_simulation():
    """Run Monte Carlo simulation."""
    try:
        monte_carlo = get_monte_carlo_system()
        simulation_params = request.get_json()
        results = monte_carlo.run_simulation(simulation_params)
        return jsonify({
            'status': 'success',
            'data': results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monte_carlo_bp.route('/api/monte-carlo/scenarios')
def get_scenarios():
    """Get Monte Carlo scenarios."""
    try:
        monte_carlo = get_monte_carlo_system()
        scenarios = monte_carlo.get_scenarios()
        return jsonify({
            'status': 'success',
            'data': scenarios
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@monte_carlo_bp.route('/api/monte-carlo/risk')
def get_risk_metrics():
    """Get risk metrics from Monte Carlo analysis."""
    try:
        monte_carlo = get_monte_carlo_system()
        risk_metrics = monte_carlo.get_risk_metrics()
        return jsonify({
            'status': 'success',
            'data': risk_metrics
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
