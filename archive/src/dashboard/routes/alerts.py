"""Alert routes for the dashboard."""

from flask import Blueprint, render_template, jsonify
from ...core.alerts.alert_system import AlertSystem

alerts_bp = Blueprint('alerts', __name__)

def get_alert_system():
    """Get alert system from app context."""
    from flask import current_app
    return current_app.alert_system

@alerts_bp.route('/api/alerts')
def get_alerts():
    """Get current alerts."""
    try:
        alert_system = get_alert_system()
        alerts = alert_system.get_current_alerts()
        return jsonify({
            'status': 'success',
            'data': alerts
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@alerts_bp.route('/api/alerts/settings')
def get_alert_settings():
    """Get alert settings."""
    try:
        alert_system = get_alert_system()
        settings = alert_system.get_settings()
        return jsonify({
            'status': 'success',
            'data': settings
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@alerts_bp.route('/api/alerts/history')
def get_alert_history():
    """Get alert history."""
    try:
        alert_system = get_alert_system()
        history = alert_system.get_alert_history()
        return jsonify({
            'status': 'success',
            'data': history
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
