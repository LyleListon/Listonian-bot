"""Integration routes for the dashboard."""

from flask import Blueprint, render_template, jsonify, request
from ...core.integration.integration import IntegrationSystem

integration_bp = Blueprint('integration', __name__)

def get_integration_system():
    """Get integration system from app context."""
    from flask import current_app
    return current_app.integration_system

@integration_bp.route('/api/integration/status')
def get_integration_status():
    """Get status of all integrations."""
    try:
        integration = get_integration_system()
        status = integration.get_integration_status()
        return jsonify({
            'status': 'success',
            'data': status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@integration_bp.route('/api/integration/configure', methods=['POST'])
def configure_integration():
    """Configure an integration."""
    try:
        integration = get_integration_system()
        config_data = request.get_json()
        result = integration.configure_integration(config_data)
        return jsonify({
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@integration_bp.route('/api/integration/test', methods=['POST'])
def test_integration():
    """Test an integration connection."""
    try:
        integration = get_integration_system()
        test_data = request.get_json()
        test_result = integration.test_integration(test_data)
        return jsonify({
            'status': 'success',
            'data': test_result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@integration_bp.route('/api/integration/logs')
def get_integration_logs():
    """Get integration logs."""
    try:
        integration = get_integration_system()
        logs = integration.get_integration_logs()
        return jsonify({
            'status': 'success',
            'data': logs
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
