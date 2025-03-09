"""Machine learning routes for the dashboard."""

from flask import Blueprint, render_template, jsonify
from ...core.ml.ml_system import MLSystem

ml_bp = Blueprint('ml', __name__)

def get_ml_system():
    """Get ML system from app context."""
    from flask import current_app
    return current_app.ml_system

@ml_bp.route('/api/ml/predictions')
def get_predictions():
    """Get price predictions."""
    try:
        ml_system = get_ml_system()
        predictions = ml_system.get_price_predictions()
        return jsonify({
            'status': 'success',
            'data': predictions
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@ml_bp.route('/api/ml/patterns')
def get_patterns():
    """Get detected patterns."""
    try:
        ml_system = get_ml_system()
        patterns = ml_system.get_detected_patterns()
        return jsonify({
            'status': 'success',
            'data': patterns
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@ml_bp.route('/api/ml/risk')
def get_risk_analysis():
    """Get risk analysis."""
    try:
        ml_system = get_ml_system()
        risk_analysis = ml_system.get_risk_analysis()
        return jsonify({
            'status': 'success',
            'data': risk_analysis
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
